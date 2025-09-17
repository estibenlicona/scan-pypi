#!/usr/bin/env python3
"""
Test directo de las funciones async para verificar que no hay errores de asyncio.
"""

import asyncio
from pipgrip_resolver import resolve_dependencies_with_pipgrip_async
from main import run_snyk_analysis_async

async def test_pipgrip_async():
    """Probar la función pipgrip asíncrona."""
    print("🧪 Probando resolve_dependencies_with_pipgrip_async...")
    
    try:
        libraries = ["requests"]
        result = await resolve_dependencies_with_pipgrip_async(libraries)
        print(f"✅ Pipgrip async exitoso. Dependencias resueltas:")
        print(result[:200] + "..." if len(result) > 200 else result)
        return True
    except Exception as e:
        print(f"❌ Error en pipgrip async: {e}")
        return False

async def test_main_async():
    """Probar la función principal asíncrona."""
    print("\n🧪 Probando run_snyk_analysis_async...")
    
    try:
        libraries = ["requests"]
        await run_snyk_analysis_async(libraries)
        print("✅ Análisis async exitoso. Verificar consolidated_report.json")
        return True
    except Exception as e:
        print(f"❌ Error en análisis async: {e}")
        return False

async def main():
    """Ejecutar todos los tests."""
    print("🚀 Iniciando tests de funciones asíncronas...\n")
    
    # Test 1: Pipgrip async
    pipgrip_ok = await test_pipgrip_async()
    
    # Test 2: Main async (solo si pipgrip funcionó)
    if pipgrip_ok:
        main_ok = await test_main_async()
    else:
        main_ok = False
        print("⏩ Saltando test principal porque pipgrip falló")
    
    # Resumen
    print("\n📊 Resumen de tests:")
    print(f"  - Pipgrip async: {'✅' if pipgrip_ok else '❌'}")
    print(f"  - Main async: {'✅' if main_ok else '❌'}")
    
    if pipgrip_ok and main_ok:
        print("\n🎉 ¡Todas las funciones async funcionan correctamente!")
        print("✅ No hay errores de 'asyncio.run() cannot be called from a running event loop'")
        return True
    else:
        print("\n💥 Algunos tests fallaron. Revisar los errores arriba.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)