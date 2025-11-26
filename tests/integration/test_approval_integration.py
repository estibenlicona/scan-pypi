#!/usr/bin/env python3
"""
Test script for approval engine integration validation.
Tests that all approval fields are correctly calculated and persisted.
"""

import json
from pathlib import Path
from src.domain.models import PackageInfo, VulnerabilityInfo
from src.domain.services.approval_engine import ApprovalEngine
from src.domain.entities import SeverityLevel

def test_approval_engine():
    """Test ApprovalEngine basic functionality."""
    print("🧪 Testing ApprovalEngine...")
    
    # Create test packages
    packages = [
        PackageInfo(
            name="requests",
            version="2.28.0",
            license="Apache-2.0",
            is_maintained=True,
            license_rejected=False,
            dependencies=["urllib3", "certifi"]
        ),
        PackageInfo(
            name="flask",
            version="2.0.0",
            license="BSD-3-Clause",
            is_maintained=False,  # Not maintained
            license_rejected=False,
            # No author or maintainer info - truly abandoned
            dependencies=["click", "itsdangerous", "jinja2", "werkzeug"]
        ),
        PackageInfo(
            name="django",
            version="3.2.0",
            license="BSD-3-Clause",
            is_maintained=True,
            license_rejected=False,
            author="Django Team",
            dependencies=[]
        ),
        PackageInfo(
            name="incomplete-pkg",
            version="1.0.0",
            license=None,  # Missing license (now just a warning, not a blocker)
            is_maintained=True,  # But is maintained
            license_rejected=False,
            author="Some Author",
            dependencies=[]
        ),
    ]
    
    # Create test vulnerabilities
    vulnerabilities = [
        VulnerabilityInfo(
            id="CVE-2021-1234",
            title="SQL Injection in requests",
            description="SQL injection vulnerability",
            severity=SeverityLevel.HIGH,
            package_name="requests",
            version="2.28.0"
        ),
    ]
    
    # Create dependencies map
    dependencies_map = {
        "requests": ["urllib3", "certifi"],
        "flask": ["click", "itsdangerous", "jinja2", "werkzeug"],
        "django": [],
        "urllib3": [],
        "certifi": []
    }
    
    # Run approval engine
    engine = ApprovalEngine()
    approved_packages = engine.evaluate_all_packages(
        packages,
        vulnerabilities,
        dependencies_map
    )
    
    # Validate results
    print("\n📊 Approval Engine Results:")
    for pkg in approved_packages:
        print(f"\n  📦 {pkg.name} v{pkg.version}")
        print(f"     Status: {pkg.aprobada}")
        print(f"     Reason: {pkg.motivo_rechazo}")
        print(f"     Direct: {pkg.dependencias_directas}")
        print(f"     Transitive: {pkg.dependencias_transitivas}")
    
    # Assertions
    requests_pkg = next((p for p in approved_packages if p.name == "requests"), None)
    assert requests_pkg is not None, "requests package not found"
    assert requests_pkg.aprobada == "No", f"requests should be rejected, got {requests_pkg.aprobada}"
    assert "vulnerabilidad" in (requests_pkg.motivo_rechazo or "").lower(), \
        f"Expected vulnerability reason, got: {requests_pkg.motivo_rechazo}"
    
    flask_pkg = next((p for p in approved_packages if p.name == "flask"), None)
    assert flask_pkg is not None, "flask package not found"
    assert flask_pkg.aprobada == "No", f"flask should be rejected (not maintained), got {flask_pkg.aprobada}"
    assert "mantenimiento" in (flask_pkg.motivo_rechazo or "").lower(), \
        f"Expected maintenance reason, got: {flask_pkg.motivo_rechazo}"
    
    django_pkg = next((p for p in approved_packages if p.name == "django"), None)
    assert django_pkg is not None, "django package not found"
    assert django_pkg.aprobada == "Sí", \
        f"django should be approved, got {django_pkg.aprobada}"
    
    incomplete_pkg = next((p for p in approved_packages if p.name == "incomplete-pkg"), None)
    assert incomplete_pkg is not None, "incomplete-pkg not found"
    assert incomplete_pkg.aprobada == "Sí", \
        f"incomplete-pkg should be approved (has author, no vulnerabilities), got {incomplete_pkg.aprobada}"
    assert "licencia no documentada" in (incomplete_pkg.motivo_rechazo or "").lower(), \
        f"Expected warning about missing license, got: {incomplete_pkg.motivo_rechazo}"
    
    print("\n✅ ApprovalEngine tests passed!")

def test_json_serialization():
    """Test that approval fields are serializable to JSON."""
    print("\n🧪 Testing JSON serialization...")
    
    package = PackageInfo(
        name="test-pkg",
        version="1.0.0",
        license="MIT",
        is_maintained=True,
        license_rejected=False,
        aprobada="Sí",
        motivo_rechazo=None,
        dependencias_directas=["dep1", "dep2"],
        dependencias_transitivas=["dep3", "dep4"]
    )
    
    # Simulate DTO conversion
    package_dict = {
        "package": package.name,
        "version": package.version,
        "license": package.license,
        "is_maintained": package.is_maintained,
        "license_rejected": package.license_rejected,
        "aprobada": package.aprobada,
        "motivo_rechazo": package.motivo_rechazo,
        "dependencias_directas": package.dependencias_directas,
        "dependencias_transitivas": package.dependencias_transitivas
    }
    
    # Try to serialize
    json_str = json.dumps(package_dict, indent=2)
    print(f"\n✅ Serialized:\n{json_str}")
    
    # Deserialize
    deserialized = json.loads(json_str)
    assert deserialized["aprobada"] == "Sí"
    assert deserialized["dependencias_directas"] == ["dep1", "dep2"]
    print("\n✅ JSON serialization tests passed!")

if __name__ == "__main__":
    try:
        test_approval_engine()
        test_json_serialization()
        print("\n🎉 All integration tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
