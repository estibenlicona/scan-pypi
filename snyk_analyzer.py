# snyk_analyzer.py
# Módulo para ejecutar análisis con Snyk CLI sobre archivos requirements.txt expandidos

import subprocess
import json
import os
from typing import Tuple, Dict, Any, Optional
from config import SNYK_PATH
from cache_manager import get_cache, is_cache_enabled


def run_snyk_test_on_requirements(scan_dir: str, snyk_org: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Ejecuta análisis de Snyk sobre requirements.txt sin instalar dependencias.
    Incluye caché inteligente para evitar reanálisis de los mismos requirements.
    
    Args:
        scan_dir (str): Directorio que contiene requirements.txt expandido.
        snyk_org (str, optional): Organización de Snyk para el análisis.
        
    Returns:
        Tuple[Dict[str, Any], Dict[str, Any]]: (dependencias_obj, vulnerabilidades_obj)
        
    Raises:
        RuntimeError: Si Snyk falla o no retorna JSON válido.
        FileNotFoundError: Si requirements.txt no existe en scan_dir.
    """
    requirements_path = os.path.join(scan_dir, "requirements.txt")
    if not os.path.exists(requirements_path):
        raise FileNotFoundError(f"requirements.txt no encontrado en {scan_dir}")
    
    # Leer contenido del requirements.txt para caché
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements_content = f.read()
    
    # Intentar obtener resultado desde caché
    if is_cache_enabled():
        cache = get_cache()
        cached_result = cache.get_snyk_cache(requirements_content)
        if cached_result:
            return cached_result
    
    print("Ejecutando análisis de Snyk sobre requirements.txt expandido...")
    
    # Construir comando Snyk
    org_arg = f"--org={snyk_org}" if snyk_org else ""
    cmd = [SNYK_PATH, 'test', '--json', org_arg, '--print-deps', '--file=requirements.txt']
    cmd = [c for c in cmd if c]  # Elimina argumentos vacíos
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=scan_dir)
        dependencies_obj, vulnerabilities_obj = _parse_snyk_json_output(result.stdout)
        
        # Guardar en caché si está habilitado
        if is_cache_enabled():
            cache = get_cache()
            cache.set_snyk_cache(requirements_content, dependencies_obj, vulnerabilities_obj)
            
        return dependencies_obj, vulnerabilities_obj
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error ejecutando Snyk CLI: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("Snyk CLI no está disponible. Verifica instalación y autenticación.")


def _parse_snyk_json_output(stdout_content: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Parsea la salida JSON de Snyk CLI y extrae objetos de dependencias y vulnerabilidades.
    
    Args:
        stdout_content (str): Salida estándar del comando Snyk.
        
    Returns:
        Tuple[Dict[str, Any], Dict[str, Any]]: (dependencias_obj, vulnerabilidades_obj)
        
    Raises:
        RuntimeError: Si no se pueden parsear objetos JSON válidos.
    """
    if not stdout_content.strip():
        raise RuntimeError("Snyk no generó salida. Verifica configuración y autenticación.")
    
    objects: list[dict[str, Any]] = []
    decoder = json.JSONDecoder()
    content = stdout_content
    
    while content.strip():
        content = content.lstrip()
        try:
            obj, end = decoder.raw_decode(content)
            objects.append(obj)
            content = content[end:]
        except json.JSONDecodeError:
            break
    
    if len(objects) == 2:
        print("Snyk: se detectaron dos objetos JSON (dependencias y vulnerabilidades)")
        return objects[0], objects[1]
    elif len(objects) == 1:
        print("Snyk: solo se detectó un objeto JSON")
        return objects[0], {}
    else:
        print("Snyk: no se detectaron objetos JSON válidos")
        return {}, {}


from typing import List, Set, Tuple, Dict, Any

def get_snyk_vuln_info(result: subprocess.CompletedProcess[str]) -> Dict[str, Any]:
    """
    Obtiene la información relevante de las vulnerabilidades desde el resultado del análisis de Snyk.
    
    Args:
        result (subprocess.CompletedProcess): Resultado del comando.
    
    Returns:
        Dict[str, Any]: Diccionario con listas de vulnerabilidades y árboles de dependencias.
    """
    try:
        data = json.loads(result.stdout)
        vuln_list: List[Dict[str, Any]] = []
        dep_tree_set: Set[Tuple[str, ...]] = set()
        # Obtener vulnerabilidades
        if 'vulnerabilities' in data and data['vulnerabilities']:
            for vuln in data['vulnerabilities']:
                vuln_type = vuln.get('type', 'vuln')
                pkg_name = vuln.get('moduleName') or vuln.get('packageName') or vuln.get('name', 'N/A')
                version = vuln.get('version', 'N/A')
                title = vuln.get('title', 'N/A')
                cvss = vuln.get('CVSSv3', 'N/A')
                fixed_in: list[Any] | str | None = vuln.get('fixedIn')
                if fixed_in:
                    if isinstance(fixed_in, list):
                        fixed_in_str = ", ".join(str(item) for item in fixed_in)
                    else:
                        fixed_in_str = str(fixed_in)
                else:
                    fixed_in_str = "N/A"
                dep_tree = vuln.get('from', [])
                # Omitir el paquete temporal raíz si existe
                if dep_tree and dep_tree[0].startswith('tmp'):
                    dep_tree = dep_tree[1:]
                if dep_tree:
                    dep_tree_set.add(tuple(dep_tree))
                vuln_list.append({
                    "type": vuln_type,
                    "id": vuln.get('id', 'N/A'),
                    "title": title,
                    "severity": vuln.get('severity', 'N/A'),
                    "package": pkg_name,
                    "version": version,
                    "cvss": cvss,
                    "fixed_in": fixed_in_str
                })
        # Convertir el set de árboles de dependencias en una lista única
        dep_trees: List[List[str]] = [list(dep) for dep in dep_tree_set]
        return {
            "vulnerabilities": vuln_list,
            "dependency_trees": dep_trees
        }
    except json.JSONDecodeError:
        return {
            "vulnerabilities": [],
            "dependency_trees": []
        }
