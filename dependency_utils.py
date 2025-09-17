from typing import Dict, List, Any


def extract_dependencies_tree(dep_obj: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Extrae el mapeo de dependencias directas para cada paquete del objeto 'dependencies' de Snyk.
    
    Args:
        dep_obj: Objeto 'dependencies' del JSON de Snyk.
        
    Returns:
        Diccionario donde cada clave es 'package@version' y el valor es una lista
        de dependencias directas en formato 'dep@version'.
    """
    dependencies_obj = dep_obj.get("dependencies", {})
    dep_map: Dict[str, List[str]] = {}

    def get_key(pkg: Dict[str, Any]) -> str:
        return f"{pkg['name']}@{pkg['version']}"

    def traverse(pkg_info: Dict[str, Any]) -> None:
        key = get_key(pkg_info)
        if key in dep_map:
            return
        direct_deps: List[str] = []
        for _, dep_info in pkg_info.get('dependencies', {}).items():
            dep_key = get_key(dep_info)
            direct_deps.append(dep_key)
            traverse(dep_info)
        dep_map[key] = direct_deps

    for _, pkg_info in dependencies_obj.items():
        traverse(pkg_info)

    return dep_map
