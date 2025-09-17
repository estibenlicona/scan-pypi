"""
pypi_info.py
Módulo para consultar información de paquetes desde PyPI API y GitHub API.
Enriquece metadatos de dependencias con licencias, fechas de publicación y URLs.
Versión mejorada con validación estricta de tipos usando Pydantic.
"""

import re
import requests
from typing import Dict, List, Optional, Any, Set, cast
from models import PackageInfo
from cache_manager import get_cache, is_cache_enabled

# Constantes de configuración
PYPI_BASE_URL = "https://pypi.org/pypi"
GITHUB_API_BASE_URL = "https://api.github.com/repos"
REQUEST_TIMEOUT = 10


def extract_github_url_from_description(description: Optional[str]) -> Optional[str]:
    """
    Extrae la URL principal de GitHub desde la descripción del paquete.
    
    Args:
        description: Texto de la descripción del paquete.
        
    Returns:
        URL principal del repositorio GitHub si se encuentra, None en caso contrario.
    """
    if not description:
        return None
        
    github_pattern = r'https://github\.com/[\w\-]+/[\w\-]+'
    github_urls = re.findall(github_pattern, description)
    
    if github_urls:
        # Retorna la URL más corta (usualmente la principal)
        return min(github_urls, key=len)
    
    return None


def get_github_license(repo_url: str) -> Optional[str]:
    """
    Obtiene información de licencia desde GitHub API.
    
    Args:
        repo_url: URL del repositorio GitHub.
        
    Returns:
        Nombre de la licencia si se encuentra, None en caso contrario.
    """
    if not repo_url or "github.com" not in repo_url:
        return None
        
    try:
        # Extraer owner y repo de la URL
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            return None
            
        owner = parts[-2]
        repo = parts[-1]
        
        api_url = f"{GITHUB_API_BASE_URL}/{owner}/{repo}/license"
        response = requests.get(api_url, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            license_info = data.get("license")
            
            if license_info:
                # Priorizar SPDX ID sobre nombre
                return (license_info.get("spdx_id") or 
                       license_info.get("name"))
                       
    except Exception:
        # Fallar silenciosamente para no interrumpir el flujo principal
        pass
        
    return None
def _extract_license_from_classifiers(classifiers: List[str]) -> Optional[str]:
    """
    Extrae información de licencia desde classifiers de PyPI.
    
    Args:
        classifiers: Lista de clasificadores del paquete.
        
    Returns:
        Licencias encontradas separadas por coma, None si no hay.
    """
    if not classifiers:
        return None
        
    found_licenses: List[str] = []
    license_prefix = "License ::"
    
    for classifier in classifiers:
        if classifier.startswith(license_prefix):
            parts = classifier.split("::")
            if len(parts) > 2:
                license_name = parts[-1].strip()
                found_licenses.append(license_name)
                
    return ", ".join(found_licenses) if found_licenses else None


def _get_github_repo_from_package_info(package_info: Dict[str, Any]) -> Optional[str]:
    """
    Extrae URL de repositorio GitHub desde información del paquete.
    
    Args:
        package_info: Información del paquete desde PyPI.
        
    Returns:
        URL del repositorio GitHub si se encuentra, None en caso contrario.
    """
    # Buscar en project_urls usando cast para eliminar ambigüedad de tipos
    project_urls_raw = package_info.get("project_urls", {})
    
    # Usar cast para indicar al type checker que esperamos Dict[str, str]
    if isinstance(project_urls_raw, dict):
        project_urls = cast(Dict[str, str], project_urls_raw)
        
        # Buscar URLs de GitHub en project_urls
        for url_type in ["Homepage", "Source", "Repository"]:
            url: Optional[str] = project_urls.get(url_type)
            if url and "github.com" in url:
                return url
    
    # Buscar en campos directos
    for field in ["project_url", "home_page", "Homepage"]:
        url = package_info.get(field)
        if url and "github.com" in str(url):
            return url
    
    # Buscar en descripción como último recurso
    description = package_info.get("description", "")
    return extract_github_url_from_description(description)


def _get_license_info(package_info: Dict[str, Any]) -> Optional[str]:
    """
    Obtiene información de licencia desde múltiples fuentes.
    
    Args:
        package_info: Información del paquete desde PyPI.
        
    Returns:
        Información de licencia encontrada, None si no hay.
    """
    # Intentar obtener licencia directamente
    license_info = (package_info.get("license") or 
                   package_info.get("license_expression"))
    
    # Si la licencia es muy larga o vacía, buscar en classifiers
    if not license_info or len(license_info) > 40:
        classifiers = package_info.get("classifiers", [])
        license_info = _extract_license_from_classifiers(classifiers)
    
    # Si aún no hay licencia, intentar GitHub
    if not license_info or not license_info.strip():
        github_url = _get_github_repo_from_package_info(package_info)
        if github_url:
            license_info = get_github_license(github_url)
    
    return license_info


def _get_upload_time_from_files(files: List[Dict[str, Any]]) -> Optional[str]:
    """
    Extrae tiempo de subida desde lista de archivos.
    
    Args:
        files: Lista de archivos del paquete.
        
    Returns:
        Tiempo de subida ISO format si se encuentra, None en caso contrario.
    """
    if not files:
        return None
        
    # Priorizar archivos wheel
    for file_info in files:
        if file_info.get("packagetype") == "bdist_wheel":
            return file_info.get("upload_time_iso_8601")
    
    return None


def get_wheel_url(files: List[Dict[str, Any]]) -> Optional[str]:
    """
    Obtiene la URL del archivo wheel de una lista de archivos.
    
    Args:
        files: Lista de diccionarios con información de archivos.
        
    Returns:
        URL del archivo wheel si existe, None en caso contrario.
    """
    if not files:
        return None
        
    for file_info in files:
        if file_info.get("packagetype") == "bdist_wheel":
            return file_info.get("url")
    
    return None


def get_pypi_package_info(package: str, version: str) -> PackageInfo:
    """
    Consulta la API de PyPI para obtener información completa del paquete.
    Incluye caché inteligente para evitar consultas repetidas.
    
    Args:
        package: Nombre del paquete.
        version: Versión del paquete.
        
    Returns:
        Objeto PackageInfo validado con información del paquete.
    """
    # Intentar obtener desde caché
    if is_cache_enabled():
        cache = get_cache()
        cached_data = cache.get_pypi_cache(package, version)
        if cached_data:
            try:
                # Convertir dict de caché a PackageInfo
                return PackageInfo(**cached_data)
            except Exception as e:
                print(f"⚠️  Error convirtiendo caché PyPI {package}: {e}")
    
    url = f"{PYPI_BASE_URL}/{package}/{version}/json"
    
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return _create_error_package_info(package, version, f"HTTP {response.status_code}")
        
        data = response.json()
        info = data.get("info", {})
        
        # Obtener información de licencia
        license_info = _get_license_info(info)
        
        # Obtener archivos y tiempo de subida
        upload_time = None
        
        # Intentar desde releases primero
        releases = data.get("releases", {})
        files = releases.get(version, [])
        
        if files:
            upload_time = _get_upload_time_from_files(files)
        else:
            # Fallback a urls
            files = data.get("urls", [])
            if files:
                upload_time = _get_upload_time_from_files(files)
        
        # Crear y validar objeto PackageInfo
        package_info = PackageInfo(
            package=package,
            version=version,
            license=license_info,
            upload_time=upload_time,
            summary=info.get("summary"),
            home_page=info.get("home_page"),
            author=info.get("author"),
            author_email=info.get("author_email"),
            maintainer=info.get("maintainer"),
            maintainer_email=info.get("maintainer_email"),
            keywords=info.get("keywords"),
            classifiers=info.get("classifiers", []) or [],
            requires_dist=info.get("requires_dist", []) or [],
            project_urls=info.get("project_urls", {}) or {}
        )
        
        # Guardar en caché si está habilitado
        if is_cache_enabled():
            cache = get_cache()
            # Convertir PackageInfo a dict para caché
            cache_data = package_info.model_dump()
            cache.set_pypi_cache(package, version, cache_data)
        
        return package_info
        
    except Exception as e:
        return _create_error_package_info(package, version, str(e))


def _create_error_package_info(package: str, version: str, error_msg: str) -> PackageInfo:
    """
    Crea objeto PackageInfo de error estandarizado.
    
    Args:
        package: Nombre del paquete.
        version: Versión del paquete.
        error_msg: Mensaje de error.
        
    Returns:
        Objeto PackageInfo con información de error.
    """
    return PackageInfo(
        package=package,
        version=version,
        summary=f"Error: {error_msg}"
    )

def get_dependency_pypi_info(dependency_trees: List[List[str]]) -> List[PackageInfo]:
    """
    Consulta información de PyPI para cada paquete en los árboles de dependencias.
    
    Args:
        dependency_trees: Lista de listas con dependencias en formato [package@version, ...]
        
    Returns:
        Lista de objetos PackageInfo con información de PyPI por paquete y versión.
    """
    results: List[PackageInfo] = []
    seen: Set[str] = set()
    
    for tree in dependency_trees:
        for dependency in tree:
            if '@' in dependency:
                package_name, version = dependency.split('@', 1)
                key = f"{package_name}@{version}"
                
                if key not in seen:
                    package_info = get_pypi_package_info(package_name, version)
                    results.append(package_info)
                    seen.add(key)
                    
    return results
