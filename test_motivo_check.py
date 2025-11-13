import json

with open('consolidated_report.json', encoding='utf-8') as f:
    data = json.load(f)

# Find ipython and check its motivo and dependencias_rechazadas
ipython = next((p for p in data['packages'] if p.get('package') == 'ipython'), None)
if ipython:
    print(f"ipython motivo: {ipython.get('motivo_rechazo')}")
    print(f"ipython aprobada: {ipython.get('aprobada')}")
    print(f"ipython dependencias_rechazadas: {ipython.get('dependencias_rechazadas')}")
    
    # Extract the names from motivo if present
    motivo = ipython.get('motivo_rechazo', '')
    if 'Dependencias rechazadas:' in motivo:
        rejected_str = motivo.split('Dependencias rechazadas:')[1].split(';')[0].strip()
        print(f"Extracted from motivo: {rejected_str}")
