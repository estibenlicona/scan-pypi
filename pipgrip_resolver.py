# pipgrip_resolver.py
# Módulo para resolver dependencias usando pipgrip sin instalación

import subprocess
import os
import tempfile
from typing import List, Tuple
from cache_manager import get_cache, is_cache_enabled


def resolve_dependencies_with_pipgrip(libraries: List[str]) -> Tuple[str, str]:
    """
    Usa pipgrip para resolver el árbol completo de dependencias sin instalar paquetes.
    Incluye caché inteligente para evitar recálculos en llamadas repetidas.
    
    Args:
        libraries (List[str]): Lista de librerías principales a analizar.
        
    Returns:
        Tuple[str, str]: (directorio_temporal, ruta_requirements_expandido)
        
    Raises:
        RuntimeError: Si pipgrip falla al resolver dependencias.
    """
    if not libraries:
        raise ValueError("La lista de librerías no puede estar vacía")
    
    # Intentar obtener resultado desde caché
    if is_cache_enabled():
        cache = get_cache()
        cached_result = cache.get_pipgrip_cache(libraries)
        if cached_result:
            return cached_result
    
    # Si no hay caché, ejecutar pipgrip normalmente
    # Crear directorio temporal para el análisis
    temp_dir = tempfile.mkdtemp(prefix="snyk_analysis_")
    requirements_path = os.path.join(temp_dir, "requirements.txt")
    
    try:
        # Comando pipgrip para resolver dependencias sin instalación
        cmd = [
            "pipgrip"
        ] + [lib.strip() for lib in libraries]
        
        print(f"Resolviendo dependencias con pipgrip para: {', '.join(libraries)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Escribir la salida de pipgrip directamente al archivo requirements.txt
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write(result.stdout.strip())
        
        print("Dependencias resueltas exitosamente")
        
        # Guardar en caché si está habilitado
        if is_cache_enabled():
            cache = get_cache()
            cache.set_pipgrip_cache(libraries, temp_dir, requirements_path)
        
        return temp_dir, requirements_path
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error resolviendo dependencias con pipgrip: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("pipgrip no está instalado. Ejecuta: pip install pipgrip")


def validate_requirements_file(requirements_path: str) -> bool:
    """
    Valida que el archivo requirements.txt generado contenga dependencias.
    
    Args:
        requirements_path (str): Ruta al archivo requirements.txt.
        
    Returns:
        bool: True si el archivo es válido, False en caso contrario.
    """
    if not os.path.exists(requirements_path):
        return False
    
    with open(requirements_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
        return len(lines) > 0


def validate_libraries_list(libraries: List[str]) -> bool:
    """
    Valida que la lista de librerías no esté vacía y contenga elementos válidos.
    
    Args:
        libraries (List[str]): Lista de librerías a validar.
        
    Returns:
        bool: True si la lista es válida, False en caso contrario.
    """
    if not libraries or len(libraries) == 0:
        return False
    
    # Verificar que no hay elementos vacíos
    valid_libs = [lib.strip() for lib in libraries if lib.strip()]
    return len(valid_libs) > 0


def get_dependency_count(requirements_path: str) -> int:
    """
    Cuenta el número de dependencias en el archivo requirements.txt.
    
    Args:
        requirements_path (str): Ruta al archivo requirements.txt.
        
    Returns:
        int: Número de dependencias encontradas.
    """
    if not os.path.exists(requirements_path):
        return 0
    
    with open(requirements_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
        return len(lines)


async def resolve_dependencies_with_pipgrip_async(libraries: List[str]) -> str:
    """
    Versión asíncrona de resolve_dependencies_with_pipgrip que evita conflictos 
    con event loops existentes (como FastAPI).
    
    Args:
        libraries: Lista de librerías a analizar
        
    Returns:
        str: Contenido del requirements.txt con todas las dependencias
    """
    import asyncio
    import concurrent.futures
    
    def _sync_resolve():
        """Wrapper síncrono para ejecutar en ThreadPoolExecutor."""
        temp_dir, requirements_path = resolve_dependencies_with_pipgrip(libraries)
        try:
            with open(requirements_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        finally:
            # Limpiar directorio temporal
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Ejecutar en un hilo separado para evitar bloquear el event loop
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, _sync_resolve)
        return result
