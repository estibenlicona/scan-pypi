"""Integration tests for ApprovalEngine with realistic package scenarios."""

from datetime import datetime, timezone, timedelta

from src.domain.entities import (
    ApprovalStatus,
    License,
    Package,
    PackageIdentifier,
    SeverityLevel,
    Vulnerability,
)
from src.domain.services.approval_engine import ApprovalEngine


_RECENT = datetime.now(timezone.utc)
_OLD = datetime.now(timezone.utc) - timedelta(days=3 * 365)


def test_approval_engine():
    """Test ApprovalEngine with a realistic set of packages."""
    packages = [
        Package(
            identifier=PackageIdentifier(
                name="requests", version="2.28.0"
            ),
            license=License(name="Apache-2.0"),
            upload_time=_RECENT,
            dependencies=[],
        ),
        Package(
            identifier=PackageIdentifier(
                name="flask", version="2.0.0"
            ),
            license=License(name="BSD-3-Clause"),
            upload_time=_OLD,  # Not maintained
            dependencies=[],
        ),
        Package(
            identifier=PackageIdentifier(
                name="django", version="3.2.0"
            ),
            license=License(name="BSD-3-Clause"),
            upload_time=_RECENT,
            author="Django Team",
            dependencies=[],
        ),
        Package(
            identifier=PackageIdentifier(
                name="incomplete-pkg", version="1.0.0"
            ),
            license=None,  # Missing license
            upload_time=_RECENT,
            author="Some Author",
            dependencies=[],
        ),
    ]

    vulnerabilities = [
        Vulnerability(
            id="CVE-2021-1234",
            title="SQL Injection in requests",
            description="SQL injection vulnerability",
            severity=SeverityLevel.HIGH,
            package_name="requests",
            version="2.28.0",
        ),
    ]

    dependencies_map = {
        "requests": ["urllib3", "certifi"],
        "flask": [
            "click", "itsdangerous", "jinja2", "werkzeug"
        ],
        "django": [],
        "incomplete-pkg": [],
        "urllib3": [],
        "certifi": [],
    }

    engine = ApprovalEngine()
    approvals = engine.evaluate_all_packages(
        packages, vulnerabilities, dependencies_map
    )

    # requests → rejected (vulnerability)
    assert approvals["requests"].status == ApprovalStatus.REJECTED
    assert "vulnerabilidad" in (
        approvals["requests"].rejection_reason or ""
    ).lower()

    # flask → rejected (not maintained)
    assert approvals["flask"].status == ApprovalStatus.REJECTED
    assert "mantenimiento" in (
        approvals["flask"].rejection_reason or ""
    ).lower()

    # django → approved
    assert approvals["django"].status == ApprovalStatus.APPROVED

    # incomplete-pkg → rejected (missing license)
    assert approvals["incomplete-pkg"].status == ApprovalStatus.REJECTED
    assert "falta licencia" in (
        approvals["incomplete-pkg"].rejection_reason or ""
    ).lower()
