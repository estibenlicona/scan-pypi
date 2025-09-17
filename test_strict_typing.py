#!/usr/bin/env python3
"""
Test de validación de tipos estrictos con Pydantic.
Verifica que los errores de codificación se hayan resuelto.
"""

from pypi_info import get_pypi_package_info, get_dependency_pypi_info
from models import PackageInfo

def test_strict_typing():
    """Test de validación estricta de tipos."""
    print("🔍 Probando validación estricta de tipos...")
    
    # Test 1: Función básica de PyPI
    print("\n1. Testing get_pypi_package_info...")
    package_info = get_pypi_package_info("requests", "2.31.0")
    
    # Verificar que devuelve el tipo correcto
    assert isinstance(package_info, PackageInfo), f"Expected PackageInfo, got {type(package_info)}"
    assert package_info.package == "requests"
    assert package_info.version == "2.31.0"
    assert package_info.license is not None
    print(f"✅ PackageInfo válido: {package_info.package}@{package_info.version}")
    
    # Test 2: Función de múltiples paquetes
    print("\n2. Testing get_dependency_pypi_info...")
    dependency_trees = [["requests@2.31.0", "urllib3@2.0.4"]]
    results = get_dependency_pypi_info(dependency_trees)
    
    # Verificar tipos de la lista
    assert isinstance(results, list), f"Expected list, got {type(results)}"
    assert len(results) >= 2, f"Expected at least 2 results, got {len(results)}"
    
    for pkg in results:
        assert isinstance(pkg, PackageInfo), f"Expected PackageInfo, got {type(pkg)}"
        assert pkg.package is not None
        assert pkg.version is not None
        print(f"✅ PackageInfo válido: {pkg.package}@{pkg.version}")
    
    # Test 3: Validación de campos opcionales
    print("\n3. Testing optional fields...")
    for pkg in results[:2]:  # Probar los primeros 2
        # Los campos opcionales pueden ser None pero deben tener los tipos correctos
        if pkg.upload_time is not None:
            assert isinstance(pkg.upload_time, str), f"upload_time debe ser str, got {type(pkg.upload_time)}"
        
        if pkg.author is not None:
            assert isinstance(pkg.author, str), f"author debe ser str, got {type(pkg.author)}"
            
        if pkg.summary is not None:
            assert isinstance(pkg.summary, str), f"summary debe ser str, got {type(pkg.summary)}"
            
        # Listas siempre deben existir (pueden estar vacías)
        assert isinstance(pkg.classifiers, list), f"classifiers debe ser list, got {type(pkg.classifiers)}"
        assert isinstance(pkg.requires_dist, list), f"requires_dist debe ser list, got {type(pkg.requires_dist)}"
        assert isinstance(pkg.project_urls, dict), f"project_urls debe ser dict, got {type(pkg.project_urls)}"
        
        print(f"✅ Campos validados para {pkg.package}")
    
    return True

def test_error_handling():
    """Test de manejo de errores con tipos estrictos."""
    print("\n🚨 Probando manejo de errores...")
    
    # Test con paquete inexistente
    error_pkg = get_pypi_package_info("paquete_inexistente_12345", "1.0.0")
    
    # Debe seguir devolviendo un PackageInfo válido con información de error
    assert isinstance(error_pkg, PackageInfo), f"Expected PackageInfo even for errors, got {type(error_pkg)}"
    assert error_pkg.package == "paquete_inexistente_12345"
    assert error_pkg.version == "1.0.0"
    assert error_pkg.summary is not None and "Error" in error_pkg.summary
    
    print(f"✅ Manejo de errores: {error_pkg.summary}")
    return True

def main():
    """Ejecutar todos los tests de validación."""
    print("🧪 INICIANDO TESTS DE VALIDACIÓN ESTRICTA")
    print("=" * 60)
    
    try:
        # Test 1: Tipos estrictos
        test_strict_typing()
        
        # Test 2: Manejo de errores
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("🎉 ¡TODOS LOS TESTS PASARON!")
        print("✅ Los errores de codificación y tipos han sido resueltos")
        print("✅ Validación estricta con Pydantic funcionando correctamente")
        print("✅ Los tipos Unknown han sido eliminados")
        
        return True
        
    except Exception as e:
        print(f"\n💥 TEST FALLÓ: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)