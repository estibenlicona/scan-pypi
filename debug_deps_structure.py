import json

# Let's check what ipykernel reports - it should have colorama as transitive
data = json.load(open('consolidated_report.json', encoding='utf-8'))
packages = data.get('packages', [])

ipykernel = next((p for p in packages if p.get('package') == 'ipykernel'), None)
ipython = next((p for p in packages if p.get('package') == 'ipython'), None)

print("=== IPYKERNEL ===")
if ipykernel:
    print(f"Aprobada: {ipykernel.get('aprobada')}")
    print(f"Dependencias Rechazadas: {ipykernel.get('dependencias_rechazadas')}")
    print(f"Direct deps: {len(ipykernel.get('dependencias_directas', []))}")
    print(f"Transitive deps: {len(ipykernel.get('dependencias_transitivas', []))}")
    
    # Show which packages depend on ipykernel as direct
    print(f"\nFirst 3 direct deps:")
    for dep in ipykernel.get('dependencias_directas', [])[:3]:
        print(f"  {dep.get('name')}")

print("\n=== IPYTHON ===")
if ipython:
    print(f"Aprobada: {ipython.get('aprobada')}")
    print(f"Dependencias Rechazadas: {ipython.get('dependencias_rechazadas')}")
    print(f"Direct deps: {len(ipython.get('dependencias_directas', []))}")
    print(f"Transitive deps: {len(ipython.get('dependencias_transitivas', []))}")
    
    print(f"\nFirst 3 direct deps:")
    for dep in ipython.get('dependencias_directas', [])[:3]:
        print(f"  {dep.get('name')}")

print("\n=== COLORAMA ===")
colorama = next((p for p in packages if p.get('package') == 'colorama'), None)
if colorama:
    print(f"Aprobada: {colorama.get('aprobada')}")
    print(f"Direct deps: {len(colorama.get('dependencias_directas', []))}")
    print(f"Transitive deps: {len(colorama.get('dependencias_transitivas', []))}")
    print(f"Dependencias Rechazadas: {colorama.get('dependencias_rechazadas')}")
