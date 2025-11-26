"""Test to verify packages without license are rejected"""
from datetime import datetime
from src.domain.models import PackageInfo
from src.domain.services.approval_engine import ApprovalEngine

def test_package_without_license_should_be_rejected():
    """Verify that a package without license is rejected"""
    
    # Create a package without license (like 'arch' in the screenshot)
    package = PackageInfo(
        name="test-package",
        version="1.0.0",
        latest_version="1.0.0",
        license=None,  # NO LICENSE
        upload_time=datetime.now(),
        summary="Test package",
        home_page="https://example.com",
        author="Test",
        is_maintained=True,  # Package is maintained
    )
    
    engine = ApprovalEngine()
    
    # Evaluate package
    aprobada, motivo, deps_dir, deps_trans, deps_rech = engine.evaluate_package_approval(
        package=package,
        vulnerabilities=[],
        dependencies_map={},
        all_packages={}
    )
    
    print(f"\nPackage: {package.name}")
    print(f"License: {package.license}")
    print(f"Aprobada: {aprobada}")
    print(f"Motivo: {motivo}")
    
    # Assertion
    if aprobada == "No":
        print("\n✅ PASS: Package without license is correctly REJECTED")
        return True
    else:
        print(f"\n❌ FAIL: Package without license is APPROVED (should be rejected)")
        print(f"   Expected: 'No'")
        print(f"   Got: '{aprobada}'")
        return False

def test_package_with_empty_license_should_be_rejected():
    """Verify that a package with empty/whitespace license is rejected"""
    
    package = PackageInfo(
        name="test-package-2",
        version="1.0.0",
        latest_version="1.0.0",
        license="  ",  # EMPTY/WHITESPACE LICENSE
        upload_time=datetime.now(),
        summary="Test package",
        home_page="https://example.com",
        author="Test",
        is_maintained=True,
    )
    
    engine = ApprovalEngine()
    
    aprobada, motivo, deps_dir, deps_trans, deps_rech = engine.evaluate_package_approval(
        package=package,
        vulnerabilities=[],
        dependencies_map={},
        all_packages={}
    )
    
    print(f"\nPackage: {package.name}")
    print(f"License: '{package.license}'")
    print(f"Aprobada: {aprobada}")
    print(f"Motivo: {motivo}")
    
    if aprobada == "No":
        print("\n✅ PASS: Package with empty license is correctly REJECTED")
        return True
    else:
        print(f"\n❌ FAIL: Package with empty license is APPROVED (should be rejected)")
        return False

def test_package_with_valid_license_should_be_approved():
    """Verify that a package with valid license is approved"""
    
    package = PackageInfo(
        name="test-package-3",
        version="1.0.0",
        latest_version="1.0.0",
        license="MIT",  # VALID LICENSE
        upload_time=datetime.now(),
        summary="Test package",
        home_page="https://example.com",
        author="Test",
        is_maintained=True,
    )
    
    engine = ApprovalEngine()
    
    aprobada, motivo, deps_dir, deps_trans, deps_rech = engine.evaluate_package_approval(
        package=package,
        vulnerabilities=[],
        dependencies_map={},
        all_packages={}
    )
    
    print(f"\nPackage: {package.name}")
    print(f"License: {package.license}")
    print(f"Aprobada: {aprobada}")
    print(f"Motivo: {motivo}")
    
    if aprobada == "Sí":
        print("\n✅ PASS: Package with valid license is correctly APPROVED")
        return True
    else:
        print(f"\n❌ FAIL: Package with valid license is REJECTED (should be approved)")
        return False

if __name__ == "__main__":
    print("="*80)
    print("TESTING LICENSE VALIDATION IN APPROVAL ENGINE")
    print("="*80)
    
    results = []
    
    results.append(test_package_without_license_should_be_rejected())
    results.append(test_package_with_empty_license_should_be_rejected())
    results.append(test_package_with_valid_license_should_be_approved())
    
    print("\n" + "="*80)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("="*80)
    
    if all(results):
        print("\n✅ All tests PASSED")
    else:
        print("\n❌ Some tests FAILED - license validation needs fixing")
