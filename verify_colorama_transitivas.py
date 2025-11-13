import json

data = json.load(open('consolidated_report.json', encoding='utf-8'))
packages = data.get('packages', [])

ipykernel = next((p for p in packages if p.get('package') == 'ipykernel'), None)
ipython = next((p for p in packages if p.get('package') == 'ipython'), None)

print("=== IPYKERNEL - Checking if colorama is in transitives ===")
if ipykernel:
    transitivas = ipykernel.get('dependencias_transitivas', [])
    print(f"Total transitive deps: {len(transitivas)}")
    
    colorama_in_transitivas = any(dep.get('name', '').startswith('colorama') for dep in transitivas)
    print(f"colorama in transitivas: {colorama_in_transitivas}")
    
    if colorama_in_transitivas:
        colorama_dep = next(d for d in transitivas if d.get('name', '').startswith('colorama'))
        print(f"  Found: {colorama_dep}")
    else:
        print("  colorama NOT found in ipykernel's transitives")
        print(f"  First 5 transitive deps:")
        for dep in transitivas[:5]:
            print(f"    {dep}")

print("\n=== IPYTHON - Checking if colorama is in directs (not transitives) ===")
if ipython:
    directas = ipython.get('dependencias_directas', [])
    transitivas = ipython.get('dependencias_transitivas', [])
    
    colorama_in_directas = any(dep.get('name', '').startswith('colorama') for dep in directas)
    colorama_in_transitivas = any(dep.get('name', '').startswith('colorama') for dep in transitivas)
    
    print(f"colorama in directas (should be True): {colorama_in_directas}")
    print(f"colorama in transitivas (should be False): {colorama_in_transitivas}")
    
    if colorama_in_directas:
        colorama_dep = next(d for d in directas if d.get('name', '').startswith('colorama'))
        print(f"  Direct: {colorama_dep}")
