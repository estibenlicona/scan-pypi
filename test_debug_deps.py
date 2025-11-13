import json

# Read the report and build reverse mapping
with open('consolidated_report.json', encoding='utf-8') as f:
    data = json.load(f)

# Create dependency map from report
deps_map = {}
for pkg in data['packages']:
    pkg_name = pkg.get('package')
    deps_list = []
    for dep in pkg.get('dependencias_directas', []):
        deps_list.append(dep['name'] if isinstance(dep, dict) else str(dep))
    deps_map[pkg_name] = deps_list

print("ipython dependencies_map:")
for dep in deps_map.get('ipython', []):
    print(f"  {dep}")
    # Extract base name
    base_name = dep.split('==')[0].split('>=')[0].split('<')[0].strip()
    found = next((p for p in data['packages'] if p.get('package') == base_name), None)
    if found:
        print(f"    -> {base_name}: aprobada={found.get('aprobada')}")
    else:
        print(f"    -> NOT FOUND: {base_name}")
