#!/usr/bin/env python3
"""
Test to verify that EVERY approval status has a clear reason.
This ensures the user will never see unclear "En verificación" messages.
"""

from datetime import datetime
from src.domain.models import PackageInfo, VulnerabilityInfo
from src.domain.services.approval_engine import ApprovalEngine
from src.domain.entities import SeverityLevel

def test_all_statuses_have_reasons():
    """Verify that EVERY status (Sí, No, En verificación) has a reason."""
    print("🧪 Testing that all statuses have clear reasons...\n")
    
    packages = [
        # ✅ CASO 1: Aprobada (Sí) - Sin problemas
        PackageInfo(
            name="good-lib",
            version="1.0.0",
            license="MIT",
            is_maintained=True,
            license_rejected=False,
            author="Author",
            home_page="https://example.com",
            upload_time=datetime(2023, 1, 1),
            dependencies=[]
        ),
        
        # ✅ CASO 2: Aprobada (Sí) - Con advertencias menores
        PackageInfo(
            name="ok-lib",
            version="1.0.0",
            license=None,  # Missing license
            is_maintained=True,
            license_rejected=False,
            author="Author",
            home_page="https://example.com",
            upload_time=datetime(2023, 1, 1),
            dependencies=[]
        ),
        
        # ❌ CASO 3: Rechazada (No) - Tiene vulnerabilidades
        PackageInfo(
            name="vulnerable-lib",
            version="1.0.0",
            license="MIT",
            is_maintained=True,
            license_rejected=False,
            author="Author",
            home_page="https://example.com",
            upload_time=datetime(2023, 1, 1),
            dependencies=[]
        ),
        
        # ❌ CASO 4: Rechazada (No) - Sin mantenimiento
        PackageInfo(
            name="abandoned-lib",
            version="1.0.0",
            license="MIT",
            is_maintained=False,
            license_rejected=False,
            # No author/maintainer
            dependencies=[]
        ),
        
        # 🔲 CASO 5: En verificación - Datos críticos faltantes
        PackageInfo(
            name="incomplete-lib",
            version="1.0.0",
            license=None,  # Missing
            is_maintained=False,  # Missing
            license_rejected=False,
            # No author/maintainer
            dependencies=[]
        ),
    ]
    
    vulnerabilities = [
        VulnerabilityInfo(
            id="CVE-2023-1234",
            title="Critical vulnerability",
            description="Test vuln",
            severity=SeverityLevel.HIGH,
            package_name="vulnerable-lib",
            version="1.0.0"
        ),
    ]
    
    dependencies_map = {
        "good-lib": [],
        "ok-lib": [],
        "vulnerable-lib": [],
        "abandoned-lib": [],
        "incomplete-lib": [],
    }
    
    engine = ApprovalEngine()
    approved = engine.evaluate_all_packages(packages, vulnerabilities, dependencies_map)
    
    print("📊 Results:\n")
    
    test_results = []
    
    for pkg in approved:
        status = pkg.aprobada
        reason = pkg.motivo_rechazo
        
        # Print result
        print(f"  {pkg.name:20} → {status:18} | Razón: {reason or '(sin problemas)'}")
        
        # VALIDACIÓN: Siempre debe haber una razón EXCEPTO cuando es "Sí" sin problemas
        if status in ["No", "En verificación"]:
            if not reason:
                print(f"    ❌ ERROR: {status} sin motivo!")
                test_results.append(False)
            else:
                print(f"    ✅ Razón clara")
                test_results.append(True)
        elif status == "Sí":
            if reason:
                print(f"    ✅ Aprobada con advertencias")
                test_results.append(True)
            else:
                print(f"    ✅ Aprobada sin problemas")
                test_results.append(True)
    
    print(f"\n{'='*70}")
    print(f"Resultados: {sum(test_results)}/{len(test_results)} PASARON")
    print(f"{'='*70}\n")
    
    if all(test_results):
        print("✅ TODAS LAS VALIDACIONES PASARON - Cada estado tiene razón clara!")
    else:
        print("❌ ALGUNAS VALIDACIONES FALLARON")
        raise AssertionError("Some statuses don't have clear reasons")

if __name__ == "__main__":
    try:
        test_all_statuses_have_reasons()
        print("🎉 Test completado exitosamente!")
    except Exception as e:
        print(f"❌ Test falló: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
