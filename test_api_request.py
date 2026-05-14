#!/usr/bin/env python3
"""
Script de prueba para testear la API FastAPI y verificar que no hay errores de asyncio.
"""

import requests
import json
import time

def test_api():
    """Probar la API con una petición simple."""
    
    url = "http://localhost:8000/scan/"
    headers = {"Content-Type": "application/json"}
    data = {"libraries": ["requests"]}
    
    print("🚀 Enviando petición a la API...")
    print(f"URL: {url}")
    print(f"Datos: {json.dumps(data, indent=2)}")
    
    try:
        # Realizar la petición POST
        start_time = time.time()
        response = requests.post(url, headers=headers, json=data, timeout=120, verify=False)
        end_time = time.time()
        
        print(f"\n✅ Respuesta recibida en {end_time - start_time:.2f} segundos")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📊 Reporte generado exitosamente")
            print(f"Número de vulnerabilidades: {len(result.get('vulnerabilities', []))}")
            print(f"Número de paquetes analizados: {len(result.get('packages', []))}")
            print(f"Reporte disponible: consolidated_report.json")
            return True
        else:
            print(f"❌ Error en la API: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar a la API. ¿Está ejecutándose en localhost:8000?")
        return False
    except requests.exceptions.Timeout:
        print("❌ Error: Timeout en la petición")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    success = test_api()
    if success:
        print("\n🎉 ¡Prueba de API exitosa! No hay errores de asyncio.")
    else:
        print("\n💥 Prueba de API falló.")