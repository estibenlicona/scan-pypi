import json

data = json.load(open('consolidated_report.json', encoding='utf-8'))
packages = data.get('packages', [])

# Find packages with rejected dependencies
rejected_pkgs = [p for p in packages if p.get('dependencias_rechazadas')]

print(f"Packages with rejected dependencies: {len(rejected_pkgs)}\n")

for pkg in rejected_pkgs[:5]:
    pkg_name = pkg.get('package')
    motivo = pkg.get('motivo_rechazo', '')
    rechazadas = pkg.get('dependencias_rechazadas', [])
    
    print(f"{pkg_name}:")
    print(f"  Motivo: {motivo}")
    print(f"  Dependencias rechazadas: {rechazadas}")
    print()
