import time
import os
from pipgrip_resolver import resolve_dependencies_with_pipgrip

# Test más pequeño para validar si alcanzamos la meta de 70% reducción
os.environ['PIPGRIP_GLOBAL_TIMEOUT'] = '60'
os.environ['PIPGRIP_MAX_WORKERS'] = '16'
os.environ['PIPGRIP_TASK_TIMEOUT'] = '45'

# Test con las 10 librerías originales (baseline: 24.85s)
libraries = [
    "requests", "flask", "django", "numpy", "pandas", 
    "pytest", "click", "jinja2", "sqlalchemy", "fastapi"
]

print(f"⚡ TEST DE VALIDACIÓN - META 70% REDUCCIÓN")
print(f"📊 Baseline original: 24.85s para 10 librerías")
print(f"🎯 Meta: ≤7.45s (70% reducción)")
print(f"📦 Librerías: {len(libraries)}")
print("=" * 50)

start_time = time.time()

try:
    result = resolve_dependencies_with_pipgrip(libraries)
    end_time = time.time()
    
    total_time = end_time - start_time
    stdout, _ = result  # Unpack tuple directly
    lines = [line for line in stdout.split('\n') if line.strip()]
    
    baseline = 24.85
    reduction = ((baseline - total_time) / baseline) * 100
    
    print("\n" + "=" * 50)
    print(f"🎯 RESULTADO FINAL:")
    print(f"⏱️  Tiempo actual: {total_time:.2f}s")
    print(f"📈 Tiempo baseline: {baseline}s")
    print(f"📊 Reducción lograda: {reduction:.1f}%")
    print(f"📦 Dependencias: {len(lines)} paquetes")
    
    if reduction >= 70:
        print(f"✅ ¡META ALCANZADA! {reduction:.1f}% ≥ 70%")
    elif reduction >= 50:
        print(f"🟡 Progreso significativo: {reduction:.1f}%")
    else:
        print(f"🔴 Meta no alcanzada: {reduction:.1f}% < 70%")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
