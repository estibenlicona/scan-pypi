"""
package_utils.py
Funciones utilitarias para enriquecimiento de paquetes con info PyPI y dependencias.
"""

from typing import Dict, List
from pypi_info import get_dependency_pypi_info
from models import PackageInfo

def enrich_packages_with_pypi(dep_map: Dict[str, List[str]]) -> List[PackageInfo]:
    """
    Enriquecimiento de paquetes con info PyPI y dependencias.
    
    Args:
        dep_map: Mapeo de dependencias por paquete@version.
        
    Returns:
        Lista de objetos PackageInfo con info PyPI y dependencias.
    """
    pypi_infos: Dict[str, PackageInfo] = {}

    def enrich_recursive(key: str) -> None:
        if key in pypi_infos:
            return
        pkg, ver = key.split("@", 1)
        info = get_dependency_pypi_info([[f"{pkg}@{ver}"]])
        if info:
            pkg_info = info[0]
            deps = dep_map.get(key, [])
            # Agregar las dependencias al modelo PackageInfo
            pkg_info.dependencies = deps
            pypi_infos[key] = pkg_info
            for dep_key in deps:
                enrich_recursive(dep_key)

    for key in dep_map.keys():
        enrich_recursive(key)

    return list(pypi_infos.values())