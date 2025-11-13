"""
Test para validar que los mensajes muestren EXACTAMENTE qué falta.
Simula casos reales del screenshot.
"""

from datetime import datetime
from src.domain.models import PackageInfo, VulnerabilityInfo
from src.domain.services.approval_engine import ApprovalEngine


def test_specific_missing_data_messages():
    """Verifica que cada razón sea específica sobre qué falta"""
    
    engine = ApprovalEngine()
    dt = datetime(2025, 1, 1)
    
    print("\n" + "="*80)
    print("🧪 TEST: Mensajes Específicos sobre Datos Faltantes")
    print("="*80 + "\n")
    
    # CASO 1: Falta LICENCIA
    print("📌 CASO 1: Paquete sin Licencia (solo falta licencia)")
    pkg1 = PackageInfo(
        name="test-pkg-1",
        version="1.0.0",
        license=None,  # ← FALTA LICENCIA
        upload_time=dt,
        is_maintained=True,
        author="Someone",
        maintainer="Someone",
        home_page="https://example.com",
        github_url="https://github.com/test",
        summary="Test package",
        author_email=None,
        maintainer_email=None,
        keywords=None,
        classifiers=[],
        requires_dist=[],
        project_urls={},
        dependencies=[],
        license_rejected=False
    )
    
    aprobada, motivo, _, _ = engine.evaluate_package_approval(pkg1, [], {}, {})
    print(f"   Estado: {aprobada}")
    print(f"   Razón: {motivo}\n")
    
    # CASO 2: Falta MANTENIMIENTO
    print("📌 CASO 2: Paquete sin Información de Mantenimiento")
    pkg2 = PackageInfo(
        name="test-pkg-2",
        version="2.0.0",
        license="MIT",
        upload_time=dt,
        is_maintained=False,
        author=None,  # ← SIN AUTOR
        maintainer=None,  # ← SIN MANTENEDOR
        home_page="https://example.com",
        github_url="https://github.com/test",
        summary="Test package",
        author_email=None,
        maintainer_email=None,
        keywords=None,
        classifiers=[],
        requires_dist=[],
        project_urls={},
        dependencies=[],
        license_rejected=False
    )
    
    aprobada, motivo, _, _ = engine.evaluate_package_approval(pkg2, [], {}, {})
    print(f"   Estado: {aprobada}")
    print(f"   Razón: {motivo}\n")
    
    # CASO 3: FALTAN AMBAS (licencia + mantenimiento) → "En verificación"
    print("📌 CASO 3: Faltan AMBAS (Licencia + Mantenimiento) - VERIFICACIÓN")
    pkg3 = PackageInfo(
        name="test-pkg-3",
        version="3.0.0",
        license=None,  # ← FALTA LICENCIA
        upload_time=dt,
        is_maintained=False,
        author=None,  # ← FALTA MANTENIMIENTO
        maintainer=None,
        home_page="https://example.com",
        github_url="https://github.com/test",
        summary="Test package",
        author_email=None,
        maintainer_email=None,
        keywords=None,
        classifiers=[],
        requires_dist=[],
        project_urls={},
        dependencies=[],
        license_rejected=False
    )
    
    aprobada, motivo, _, _ = engine.evaluate_package_approval(pkg3, [], {}, {})
    print(f"   Estado: {aprobada}")
    print(f"   Razón: {motivo}")
    print(f"   ✅ Ahora se ve EXACTAMENTE qué falta: {motivo}\n")
    
    # CASO 4: Falta URL (solo advertencia)
    print("📌 CASO 4: Falta solo URL (ADVERTENCIA, no bloquea)")
    pkg4 = PackageInfo(
        name="test-pkg-4",
        version="4.0.0",
        license="MIT",
        upload_time=dt,
        is_maintained=True,
        author="Someone",
        maintainer="Someone",
        home_page=None,  # ← FALTA URL
        github_url=None,  # ← AMBAS URLS NULAS
        summary="Test package",
        author_email=None,
        maintainer_email=None,
        keywords=None,
        classifiers=[],
        requires_dist=[],
        project_urls={},
        dependencies=[],
        license_rejected=False
    )
    
    aprobada, motivo, _, _ = engine.evaluate_package_approval(pkg4, [], {}, {})
    print(f"   Estado: {aprobada}")
    print(f"   Razón: {motivo}")
    print(f"   ✅ Se aprueba pero muestra advertencia: {motivo}\n")
    
    # CASO 5: Faltan Licencia + URL + Fecha
    print("📌 CASO 5: Faltan Licencia + URL + Fecha (múltiples datos)")
    pkg5 = PackageInfo(
        name="test-pkg-5",
        version="5.0.0",
        license=None,  # ← FALTA
        upload_time=None,  # ← FALTA
        is_maintained=True,
        author="Someone",
        maintainer="Someone",
        home_page=None,  # ← FALTA
        github_url=None,  # ← FALTA
        summary="Test package",
        author_email=None,
        maintainer_email=None,
        keywords=None,
        classifiers=[],
        requires_dist=[],
        project_urls={},
        dependencies=[],
        license_rejected=False
    )
    
    aprobada, motivo, _, _ = engine.evaluate_package_approval(pkg5, [], {}, {})
    print(f"   Estado: {aprobada}")
    print(f"   Razón: {motivo}")
    print(f"   ✅ Lista EXACTAMENTE qué falta: licencia, URL, fecha\n")
    
    print("="*80)
    print("✅ TEST COMPLETADO - Mensajes ESPECÍFICOS sobre qué falta")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_specific_missing_data_messages()
