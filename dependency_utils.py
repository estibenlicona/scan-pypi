def extract_dependencies_tree(dep_obj):
    """
    Extrae el mapeo de dependencias directas para cada paquete del objeto 'dependencies' de Snyk.
    Args:
        dependencies_obj (dict): Objeto 'dependencies' del JSON de Snyk.
    Returns:
        dict: { 'package@version': [dep1@ver, dep2@ver, ...] }
    """
    dependencies_obj = dep_obj.get("dependencies", {})
    dep_map = {}

    def get_key(pkg):
        return f"{pkg['name']}@{pkg['version']}"

    def traverse(pkg_info):
        key = get_key(pkg_info)
        if key in dep_map:
            return
        direct_deps = []
        for dep_name, dep_info in pkg_info.get('dependencies', {}).items():
            dep_key = get_key(dep_info)
            direct_deps.append(dep_key)
            traverse(dep_info)
        dep_map[key] = direct_deps

    for pkg_name, pkg_info in dependencies_obj.items():
        traverse(pkg_info)

    return dep_map
