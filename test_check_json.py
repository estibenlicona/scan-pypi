import json

try:
    f = open('consolidated_report.json', encoding='utf-8')
    data = json.load(f)

    ipython = next((p for p in data['packages'] if p.get('package') == 'ipython'), None)
    if ipython:
        print(f"ipython.dependencias_rechazadas = {repr(ipython['dependencias_rechazadas'])}")
    else:
        print("ipython not found")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()


