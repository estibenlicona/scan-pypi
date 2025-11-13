import json

with open('consolidated_report.json', encoding='utf-8') as f:
    data = json.load(f)

# Check ipython
ipython = next((p for p in data['packages'] if p.get('package') == 'ipython'), None)
if ipython:
    print("ipython:")
    print(f"  aprobada: {ipython.get('aprobada')}")
    print(f"  motivo_rechazo: {ipython.get('motivo_rechazo')}")
    print(f"  dependencias_rechazadas: {ipython.get('dependencias_rechazadas')}")
    print(f"  type: {type(ipython.get('dependencias_rechazadas'))}")
