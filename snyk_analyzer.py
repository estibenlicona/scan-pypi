# snyk_analyzer.py
# Módulo para ejecutar análisis con Snyk

import subprocess
import json
import inspect
from config import SNYK_PATH

def run_snyk_test(venv_python, scan_dir, snyk_org=None):
    """
    Ejecuta el análisis de Snyk en formato JSON.
    
    Args:
        venv_python (str): Ruta al Python del entorno virtual.
        scan_dir (str): Directorio donde están los archivos copiados.
    
    Returns:
        subprocess.CompletedProcess: Resultado del comando.
    """
    print("Ejecutando análisis de Snyk...")
    # Permitir parámetro opcional snyk_org
    frame = inspect.currentframe()
    args, _, _, values = inspect.getargvalues(frame)
    snyk_org = values.get('snyk_org', None)
    org_arg = f"--org={snyk_org}" if snyk_org else ""
    cmd = [SNYK_PATH, 'test', '--json', org_arg, '--print-deps', f'--command={venv_python}']
    cmd = [c for c in cmd if c]  # Elimina argumentos vacíos
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=scan_dir)
        # Separar y retornar ambos objetos JSON
    content = result.stdout
    objects = []
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(content):
        content = content.lstrip()
        try:
            obj, end = decoder.raw_decode(content)
            objects.append(obj)
            content = content[end:]
            idx = 0
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


def get_snyk_vuln_info(result):
    """
    Obtiene la información relevante de las vulnerabilidades desde el resultado del análisis de Snyk.
    
    Args:
        result (subprocess.CompletedProcess): Resultado del comando.
    
    Returns:
        list: Lista de diccionarios con información de las vulnerabilidades.
    """
    try:
        data = json.loads(result.stdout)
        vuln_list = []
        dep_tree_set = set()
        # Obtener vulnerabilidades
        if 'vulnerabilities' in data and data['vulnerabilities']:
            for vuln in data['vulnerabilities']:
                vuln_type = vuln.get('type', 'vuln')
                pkg_name = vuln.get('moduleName') or vuln.get('packageName') or vuln.get('name', 'N/A')
                version = vuln.get('version', 'N/A')
                title = vuln.get('title', 'N/A')
                cvss = vuln.get('CVSSv3', 'N/A')
                fixed_in = vuln.get('fixedIn')
                if fixed_in:
                    if isinstance(fixed_in, list):
                        fixed_in_str = ", ".join(fixed_in)
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
        dep_trees = [list(dep) for dep in dep_tree_set]
        return {
            "vulnerabilities": vuln_list,
            "dependency_trees": dep_trees
        }
    except json.JSONDecodeError:
        return {
            "vulnerabilities": [],
            "dependency_trees": []
        }
