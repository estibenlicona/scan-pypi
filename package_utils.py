"""
package_utils.py
Funciones utilitarias para enriquecimiento de paquetes con info PyPI y dependencias.
"""

from pypi_info import get_dependency_pypi_info

def enrich_packages_with_pypi(dep_map):
    """
    Enriquecimiento de paquetes con info PyPI y dependencias.
    Args:
        dep_map (dict): Mapeo de dependencias por paquete@version.
    Returns:
        list: Lista de dicts con info PyPI y dependencias.
    """
    pypi_infos = {}

    def enrich_recursive(key):
        if key in pypi_infos:
            return
        pkg, ver = key.split("@", 1)
        info = get_dependency_pypi_info([[f"{pkg}@{ver}"]])
        if info:
            pkg_info = info[0]
            deps = dep_map.get(key, [])
            pkg_info["dependencies"] = deps
            pypi_infos[key] = pkg_info
            for dep_key in deps:
                enrich_recursive(dep_key)

    for key in dep_map.keys():
        enrich_recursive(key)

    return list(pypi_infos.values())