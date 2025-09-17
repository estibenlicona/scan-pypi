#!/usr/bin/env python3
"""
test_cache_system.py
Test completo del sistema de caché para validar mejoras de rendimiento.
"""

import time
import os
from typing import Dict, Any
from cache_manager import get_cache, is_cache_enabled
from pipgrip_resolver import resolve_dependencies_with_pipgrip
from pypi_info import get_pypi_package_info

def test_pipgrip_cache():
    """Test del caché de pipgrip."""
    print("🧪 Testing caché de pipgrip...")
    
    libraries = ["requests", "click"]
    
    # Primera llamada (sin caché)
    print("  📋 Primera llamada (sin caché)...")
    start_time = time.time()
    temp_dir1, req_path1 = resolve_dependencies_with_pipgrip(libraries)
    first_call_time = time.time() - start_time
    
    # Segunda llamada (con caché)
    print("  💾 Segunda llamada (con caché)...")
    start_time = time.time()
    temp_dir2, req_path2 = resolve_dependencies_with_pipgrip(libraries)
    second_call_time = time.time() - start_time
    
    # Verificar que ambos tienen el mismo contenido
    with open(req_path1, 'r') as f1, open(req_path2, 'r') as f2:
        content1 = f1.read()
        content2 = f2.read()
    
    success = content1 == content2 and second_call_time < first_call_time
    
    print(f"  ⏱️  Primera llamada: {first_call_time:.2f}s")
    print(f"  ⏱️  Segunda llamada: {second_call_time:.2f}s")
    print(f"  📈 Mejora: {((first_call_time - second_call_time) / first_call_time * 100):.1f}%")
    print(f"  {'✅' if success else '❌'} Cache pipgrip: {'FUNCIONANDO' if success else 'FALLO'}")
    
    # Limpiar
    import shutil
    shutil.rmtree(temp_dir1, ignore_errors=True)
    shutil.rmtree(temp_dir2, ignore_errors=True)
    
    return success

def test_pypi_cache():
    """Test del caché de PyPI."""
    print("\n🧪 Testing caché de PyPI...")
    
    package, version = "requests", "2.31.0"
    
    # Primera llamada (sin caché)
    print("  📋 Primera consulta (sin caché)...")
    start_time = time.time()
    pkg_info1 = get_pypi_package_info(package, version)
    first_call_time = time.time() - start_time
    
    # Segunda llamada (con caché)
    print("  💾 Segunda consulta (con caché)...")
    start_time = time.time()
    pkg_info2 = get_pypi_package_info(package, version)
    second_call_time = time.time() - start_time
    
    # Verificar que ambos tienen la misma información
    success = (pkg_info1.package == pkg_info2.package and 
              pkg_info1.version == pkg_info2.version and
              pkg_info1.license == pkg_info2.license and
              second_call_time < first_call_time)
    
    print(f"  ⏱️  Primera consulta: {first_call_time:.2f}s")
    print(f"  ⏱️  Segunda consulta: {second_call_time:.2f}s")
    print(f"  📈 Mejora: {((first_call_time - second_call_time) / first_call_time * 100):.1f}%")
    print(f"  {'✅' if success else '❌'} Cache PyPI: {'FUNCIONANDO' if success else 'FALLO'}")
    
    return success

def test_snyk_cache():
    """Test del caché de Snyk (simulado)."""
    print("\n🧪 Testing caché de Snyk...")
    
    try:
        cache = get_cache()
        
        # Crear requirements.txt de prueba
        test_requirements = "requests==2.31.0\nclick==8.1.0"
        
        # Simular datos de Snyk
        mock_dependencies: Dict[str, Any] = {"dependencies": {"requests": {"version": "2.31.0"}}}
        mock_vulnerabilities: Dict[str, Any] = {"vulnerabilities": []}
        
        # Guardar en caché
        cache.set_snyk_cache(test_requirements, mock_dependencies, mock_vulnerabilities)
        
        # Obtener desde caché
        cached_result = cache.get_snyk_cache(test_requirements)
        
        success = (cached_result is not None and 
                  cached_result[0] == mock_dependencies and
                  cached_result[1] == mock_vulnerabilities)
        
        print(f"  {'✅' if success else '❌'} Cache Snyk: {'FUNCIONANDO' if success else 'FALLO'}")
        return success
        
    except Exception as e:
        print(f"  ❌ Error en test Snyk cache: {e}")
        return False

def test_cache_stats():
    """Test de estadísticas del caché."""
    print("\n📊 Estadísticas del caché...")
    
    try:
        cache = get_cache()
        stats = cache.get_cache_stats()
        
        print(f"  📋 Pipgrip: {stats.get('pipgrip', {}).get('valid_files', 0)} archivos válidos")
        print(f"  🔍 Snyk: {stats.get('snyk', {}).get('valid_files', 0)} archivos válidos")  
        print(f"  📦 PyPI: {stats.get('pypi', {}).get('valid_files', 0)} archivos válidos")
        print(f"  💾 Tamaño total: {stats.get('total', {}).get('size_mb', 0)} MB")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error obteniendo estadísticas: {e}")
        return False

def test_cache_cleanup():
    """Test de limpieza de caché."""
    print("\n🧹 Testing limpieza de caché...")
    
    try:
        cache = get_cache()
        cleared_stats = cache.clear_expired_cache()
        
        total_cleared = sum(cleared_stats.values())
        print(f"  🗑️  Archivos limpiados: {total_cleared}")
        print(f"  📋 Pipgrip: {cleared_stats.get('pipgrip', 0)}")
        print(f"  🔍 Snyk: {cleared_stats.get('snyk', 0)}")
        print(f"  📦 PyPI: {cleared_stats.get('pypi', 0)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error en limpieza: {e}")
        return False

def main():
    """Ejecutar todos los tests de caché."""
    print("🚀 INICIANDO TESTS DE SISTEMA DE CACHÉ")
    print("=" * 50)
    
    # Verificar que el caché está habilitado
    if not is_cache_enabled():
        print("⚠️  El caché está deshabilitado. Habilitando para tests...")
        os.environ['ENABLE_CACHE'] = 'true'
    
    test_results: list[bool] = []
    
    try:
        # Test 1: Caché de pipgrip
        test_results.append(test_pipgrip_cache())
        
        # Test 2: Caché de PyPI  
        test_results.append(test_pypi_cache())
        
        # Test 3: Caché de Snyk
        test_results.append(test_snyk_cache())
        
        # Test 4: Estadísticas
        test_results.append(test_cache_stats())
        
        # Test 5: Limpieza
        test_results.append(test_cache_cleanup())
        
    except Exception as e:
        print(f"\n❌ Error durante los tests: {e}")
        return False
    
    # Resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE TESTS DE CACHÉ:")
    
    tests_passed = sum(test_results)
    total_tests = len(test_results)
    
    test_names = [
        "Caché Pipgrip",
        "Caché PyPI", 
        "Caché Snyk",
        "Estadísticas",
        "Limpieza"
    ]
    
    for test_name, result in zip(test_names, test_results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n🎯 RESULTADO: {tests_passed}/{total_tests} tests pasaron")
    
    if tests_passed == total_tests:
        print("🎉 ¡TODOS LOS TESTS DE CACHÉ PASARON!")
        print("✅ El sistema de caché está funcionando correctamente")
        print("⚡ Las llamadas API subsecuentes serán significativamente más rápidas")
        return True
    else:
        print("💥 Algunos tests fallaron. Revisar implementación del caché.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)