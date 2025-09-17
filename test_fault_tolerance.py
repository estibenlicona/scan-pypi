from pipgrip_resolver import resolve_dependencies_with_pipgrip

# Test de tolerancia a fallos
libraries = [
    "requests",  # Existe
    "nonexistent-package-12345",  # No existe
    "flask",  # Existe
    "another-fake-package",  # No existe
    "click"  # Existe
]

print(f"Probando tolerancia a fallos con {len(libraries)} librerías (algunas no existen)...")

try:
    result, _ = resolve_dependencies_with_pipgrip(libraries)
    lines: list[str] = [line for line in result.split('\n') if line.strip()]
    
    print(f"\n📊 Resultado final:")
    print(f"📦 Dependencias resueltas: {len(lines)}")
    print(f"✅ El sistema continuó a pesar de errores en paquetes individuales")
    
    print(f"\n🔍 Dependencias encontradas:")
    for line in lines[:15]:
        print(f"   {line}")
        
except Exception as e:
    print(f"❌ Error general: {e}")
