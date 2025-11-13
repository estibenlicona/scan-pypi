import json

with open('consolidated_report.json', encoding='utf-8') as f:
    data = json.load(f)

# Find colorama
colorama = next((p for p in data['packages'] if p.get('package') == 'colorama'), None)
if colorama:
    print(f"colorama: aprobada={colorama.get('aprobada')}, motivo={colorama.get('motivo_rechazo')}")
    print(f"dependencias_rechazadas field exists: {'dependencias_rechazadas' in colorama}")
    if 'dependencias_rechazadas' in colorama:
        print(f"  dependencias_rechazadas: {colorama.get('dependencias_rechazadas')}")
else:
    print("colorama not found")

# Find ipython  
ipython = next((p for p in data['packages'] if p.get('package') == 'ipython'), None)
if ipython:
    print(f"\nipython: aprobada={ipython.get('aprobada')}, motivo={ipython.get('motivo_rechazo')}")
    print(f"dependencias_rechazadas field exists: {'dependencias_rechazadas' in ipython}")
    if 'dependencias_rechazadas' in ipython:
        print(f"  dependencias_rechazadas: {ipython.get('dependencias_rechazadas')}")
else:
    print("ipython not found")

# Find ipykernel
ipykernel = next((p for p in data['packages'] if p.get('package') == 'ipykernel'), None)
if ipykernel:
    print(f"\nipykernel: aprobada={ipykernel.get('aprobada')}, motivo={ipykernel.get('motivo_rechazo')}")
    print(f"dependencias_rechazadas field exists: {'dependencias_rechazadas' in ipykernel}")
    if 'dependencias_rechazadas' in ipykernel:
        print(f"  dependencias_rechazadas: {ipykernel.get('dependencias_rechazadas')}")
else:
    print("ipykernel not found")
