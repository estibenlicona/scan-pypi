import json

with open('consolidated_report.json', encoding='utf-8') as f:
    data = json.load(f)

# Print ipython's direct dependencies from the report
ipython = next((p for p in data['packages'] if p.get('package') == 'ipython'), None)
if ipython and ipython.get('dependencias_directas'):
    print("ipython's direct dependencies:")
    for dep in ipython['dependencias_directas']:
        print(f"  - {dep['name']}")
        # Find this dependency and check its approval status
        found_dep = next((p for p in data['packages'] if p.get('package') == dep['name'].split('==')[0]), None)
        if found_dep:
            print(f"    Status: aprobada={found_dep.get('aprobada')}")
        else:
            print(f"    Status: NOT FOUND in packages")
