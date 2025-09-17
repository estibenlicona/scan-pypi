import time
import os
from pipgrip_resolver import resolve_dependencies_with_pipgrip

# Configurar para estrategia de comando único optimizada
os.environ['PIPGRIP_GLOBAL_TIMEOUT'] = '90'   # Timeout para comando único
os.environ['PIPGRIP_MAX_WORKERS'] = '16'      # Fallback workers
os.environ['PIPGRIP_TASK_TIMEOUT'] = '60'     # Fallback timeout

# Test con librerías populares para medir mejora de rendimiento
libraries = [
    "requests", "flask", "django", "numpy", "pandas", 
    "pytest", "click", "jinja2", "sqlalchemy", "fastapi",
    "scipy", "matplotlib", "pillow", "boto3", "redis",
    "celery", "gunicorn", "psycopg2-binary", "aiohttp", "pydantic"
]

print(f"🚀 TEST DE RENDIMIENTO ULTRA-OPTIMIZADO")
print(f"📦 {len(libraries)} librerías populares")
print(f"⚙️  Estrategia: COMANDO ÚNICO + fallback por lotes")
print(f"⏱️  Timeout global: {os.environ['PIPGRIP_GLOBAL_TIMEOUT']}s")
print(f"� Fallback workers: {os.environ['PIPGRIP_MAX_WORKERS']}")
print("=" * 50)

start_time = time.time()

try:
    result = resolve_dependencies_with_pipgrip(libraries)
    end_time = time.time()
    
    total_time = end_time - start_time
    # Desempaquetar stdout y stderr si es necesario
    if len(result) >= 1:
        output = result[0]
    else:
        output = result
    lines: list[str] = [line for line in output.split('\n') if line.strip()]
    
    print("\n" + "=" * 50)
    print(f"🎯 RESULTADOS OPTIMIZADOS:")
    print(f"⚡ Tiempo total: {total_time:.2f} segundos")
    print(f"📦 Dependencias únicas: {len(lines)} paquetes")
    print(f"🏃 Promedio por librería: {total_time / len(libraries):.2f}s")
    print(f"💪 Paquetes por segundo: {len(libraries) / total_time:.1f}")
    
    # Calcular mejora estimada vs versión anterior (24.85s para 10 libs)
    previous_rate = 10 / 24.85  # librerías por segundo versión anterior
    current_rate = len(libraries) / total_time
    improvement = ((current_rate - previous_rate) / previous_rate) * 100
    
    print(f"📈 Mejora estimada: {improvement:.1f}% más rápido")
    
    if total_time < 8:  # Meta: menos de 8 segundos para 20 librerías
        print("✅ ¡META DE RENDIMIENTO ALCANZADA!")
    else:
        print(f"⚠️  Meta: <8s, actual: {total_time:.1f}s")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
