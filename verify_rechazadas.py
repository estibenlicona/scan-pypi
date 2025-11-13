import json

data = json.load(open('consolidated_report.json', encoding='utf-8'))
packages = data.get('packages', [])
rejected_pkgs = [p for p in packages if p.get('dependencias_rechazadas')]

print(f'Total packages: {len(packages)}')
print(f'Packages with rejected dependencies: {len(rejected_pkgs)}')
print()

for p in rejected_pkgs[:10]:
    pkg_name = p.get('package_name') or p.get('nombre')
    print(f"{pkg_name}: {p['dependencias_rechazadas']}")
