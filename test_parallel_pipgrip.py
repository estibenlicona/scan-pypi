from pipgrip_resolver import resolve_dependencies_with_pipgrip
import time

# Test con más librerías para verificar paralelismo
libraries = [
    "requests", "flask", "django", "numpy", "pandas", 
    "pytest", "click", "jinja2", "sqlalchemy", "fastapi"
]

print(f"Probando resolución paralela con {len(libraries)} librerías...")
start_time = time.time()

try:
    stdout, _ = resolve_dependencies_with_pipgrip(libraries)
    end_time = time.time()
    
    lines = [line for line in stdout.split('\n') if line.strip()]
    print(f"\n📊 Resultados:")
    print(f"⏱️  Tiempo total: {end_time - start_time:.2f} segundos")
    print(f"📦 Dependencias únicas resueltas: {len(lines)}")
    print(f"🏃 Promedio por librería: {(end_time - start_time) / len(libraries):.2f}s")
    
    print(f"\n🔍 Primeras 10 dependencias:")
    for line in lines[:10]:
        print(f"   {line}")
        
except Exception as e:
    print(f"❌ Error: {e}")
