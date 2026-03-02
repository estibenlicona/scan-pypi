"""Tests to verify packages without license are rejected."""

from datetime import datetime, timezone

from src.domain.entities import (
    ApprovalStatus,
    License,
    Package,
    PackageIdentifier,
)
from src.domain.services.approval_engine import ApprovalEngine


def _make_package(
    name: str = "test-package",
    version: str = "1.0.0",
    license_name: str | None = "MIT",
) -> Package:
    """Create a Package entity with sensible defaults."""
    lic = License(name=license_name) if license_name is not None else None
    return Package(
        identifier=PackageIdentifier(name=name, version=version),
        license=lic,
        upload_time=datetime.now(timezone.utc),
        summary="Test package",
        home_page="https://example.com",
        author="Test",
        latest_version=version,
    )


def test_package_without_license_should_be_rejected():
    """Verify that a package without license is rejected."""
    package = _make_package(license_name=None)
    engine = ApprovalEngine()

    result = engine.evaluate_package(
        package=package,
        vulnerabilities=[],
        dependencies_map={},
        all_approvals={},
    )

    assert result.status == ApprovalStatus.REJECTED
    assert "Falta Licencia" in (result.rejection_reason or "")


def test_package_with_empty_license_should_be_rejected():
    """Verify that a package with empty/whitespace license is rejected."""
    package = _make_package(license_name="  ")
    engine = ApprovalEngine()

    result = engine.evaluate_package(
        package=package,
        vulnerabilities=[],
        dependencies_map={},
        all_approvals={},
    )

    assert result.status == ApprovalStatus.REJECTED
    assert "Falta Licencia" in (result.rejection_reason or "")


def test_package_with_valid_license_should_be_approved():
    """Verify that a package with valid license is approved."""
    package = _make_package(license_name="MIT")
    engine = ApprovalEngine()

    result = engine.evaluate_package(
        package=package,
        vulnerabilities=[],
        dependencies_map={},
        all_approvals={},
    )

    assert result.status == ApprovalStatus.APPROVED
