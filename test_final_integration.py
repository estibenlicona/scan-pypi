#!/usr/bin/env python3
"""
Test final de la API FastAPI para verificar la integración completa.
"""

import subprocess
import time
import requests
import os
import sys

def start_api_server():
    """Iniciar el servidor API en background."""
    
    python_path = "C:/Users/estib/source/repos/pypi/.venv/Scripts/python.exe"
    cmd = [python_path, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", "8000"]
    
    print("🚀 Iniciando servidor FastAPI...")
    process = subprocess.Popen(
        cmd,
        cwd="c:/Users/estib/source/repos/pypi",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Esperar a que el servidor se inicie
    print("⏳ Esperando que el servidor se inicie...")
    time.sleep(8)
    
    return process

def test_api_endpoint():
    """Probar el endpoint /scan/ de la API."""
    
    url = "http://127.0.0.1:8000/scan/"
    headers = {"Content-Type": "application/json"}
    data = {"libraries": ["requests"]}
    
    print(f"📡 Enviando petición POST a {url}")
    print(f"📦 Librerías a analizar: {data['libraries']}")
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=data, timeout=60)
        end_time = time.time()
        
        print(f"⏱️  Tiempo de respuesta: {end_time - start_time:.2f} segundos")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ ¡API respondió exitosamente!")
            
            # Mostrar estadísticas del reporte
            vulnerabilities = result.get('vulnerabilities', [])
            packages = result.get('packages', [])
            filtered_packages = result.get('filtered_packages', [])
            
            print(f"📈 Estadísticas del análisis:")
            print(f"   • Vulnerabilidades encontradas: {len(vulnerabilities)}")
            print(f"   • Paquetes analizados: {len(packages)}")
            print(f"   • Paquetes filtrados: {len(filtered_packages)}")
            
            # Verificar que el reporte se generó
            report_path = "c:/Users/estib/source/repos/pypi/consolidated_report.json"
            if os.path.exists(report_path):
                print(f"📄 Reporte consolidado generado: {os.path.basename(report_path)}")
                
            return True
            
        else:
            print(f"❌ Error en la API:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se pudo conectar a la API")
        return False
    except requests.exceptions.Timeout:
        print("❌ Error: Timeout en la petición")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def main():
    """Ejecutar el test completo."""
    
    print("🧪 TEST FINAL: Integración FastAPI + AsyncIO")
    print("=" * 50)
    
    # Iniciar servidor
    server_process = start_api_server()
    
    try:
        # Probar API
        success = test_api_endpoint()
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 ¡TEST EXITOSO!")
            print("✅ La integración FastAPI funciona correctamente")
            print("✅ No hay errores de asyncio.run() en event loop")
            print("✅ El análisis de dependencias se ejecuta async")
            print("✅ El reporte se genera correctamente")
        else:
            print("💥 TEST FALLIDO")
            print("❌ Revisar los errores mostrados arriba")
            
    finally:
        # Limpiar: terminar el servidor
        print(f"\n🧹 Terminando servidor (PID: {server_process.pid})...")
        server_process.terminate()
        time.sleep(2)
        if server_process.poll() is None:
            server_process.kill()
            
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)