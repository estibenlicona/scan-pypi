import json

data = json.load(open('consolidated_report.json', encoding='utf-8'))
packages = data.get('packages', [])

# Find colorama and its details
colorama = next((p for p in packages if p.get('package') == 'colorama'), None)

if colorama:
    print(f"Package: {colorama['package']}")
    print(f"Aprobada: {colorama.get('aprobada')}")
    print(f"\nDependencias Directas:")
    for dep in colorama.get('dependencias_directas', [])[:5]:
        print(f"  {dep}")
    
    print(f"\nDependencias Transitivas:")
    transitivas = colorama.get('dependencias_transitivas', [])
    print(f"  Total: {len(transitivas)}")
    for dep in transitivas[:5]:
        print(f"  {dep}")
else:
    print("colorama not found in report")
