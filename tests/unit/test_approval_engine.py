"""Unit tests for ApprovalEngine – evaluate_package,
transitive deps, two-pass rejection cascade, production/dev separation."""

import pytest
from datetime import datetime, timezone, timedelta

from src.domain.entities import (
    ApprovalResult,
    ApprovalStatus,
    DependencyInfo,
    License,
    Package,
    PackageIdentifier,
    SeverityLevel,
    Vulnerability,
)
from src.domain.services.approval_engine import ApprovalEngine


# ── Helpers ──────────────────────────────────────────────────────────

_RECENT = datetime.now(timezone.utc)
_OLD = datetime.now(timezone.utc) - timedelta(days=3 * 365)


def _pkg(
    name: str = "pkg",
    version: str = "1.0.0",
    license_name: str | None = "MIT",
    is_maintained: bool = True,
    license_rejected: bool = False,
    **kwargs,
) -> Package:
    """Create a minimal Package entity for testing."""
    lic: License | None = None
    if license_name is not None:
        lic = License(name=license_name, is_rejected=license_rejected)
    elif license_rejected:
        lic = License(name=None, is_rejected=True)

    return Package(
        identifier=PackageIdentifier(name=name, version=version),
        license=lic,
        upload_time=_RECENT if is_maintained else _OLD,
        **kwargs,
    )


def _vuln(
    pkg_name: str = "pkg",
    version: str = "1.0.0",
    vuln_id: str = "CVE-2024-0001",
) -> Vulnerability:
    """Create a minimal Vulnerability entity for testing."""
    return Vulnerability(
        id=vuln_id,
        title="Test vuln",
        description=None,
        severity=SeverityLevel.HIGH,
        package_name=pkg_name,
        version=version,
    )


# ── evaluate_package ─────────────────────────────────────────────────


class TestEvaluatePackage:
    """Tests for single-package evaluation logic."""

    def setup_method(self):
        self.engine = ApprovalEngine()

    def test_approved_when_all_rules_pass(self):
        pkg = _pkg()
        result = self.engine.evaluate_package(pkg, [], {}, {})
        assert result.status == ApprovalStatus.APPROVED
        assert result.rejected_dependencies == []

    def test_rejected_missing_license(self):
        pkg = _pkg(license_name=None)
        result = self.engine.evaluate_package(pkg, [], {}, {})
        assert result.status == ApprovalStatus.REJECTED
        assert "Falta Licencia" in result.rejection_reason

    def test_rejected_empty_license(self):
        pkg = _pkg(license_name="")
        result = self.engine.evaluate_package(pkg, [], {}, {})
        assert result.status == ApprovalStatus.REJECTED
        assert "Falta Licencia" in result.rejection_reason

    def test_rejected_invalid_license(self):
        """Unrecognised license text is equivalent to missing license."""
        pkg = _pkg(license_name="my-custom-unknown-license")
        result = self.engine.evaluate_package(pkg, [], {}, {})
        assert result.status == ApprovalStatus.REJECTED
        assert "Falta Licencia" in result.rejection_reason

    def test_rejected_license_rejected_by_policy(self):
        pkg = _pkg(license_name="GPL v3", license_rejected=True)
        result = self.engine.evaluate_package(pkg, [], {}, {})
        assert result.status == ApprovalStatus.REJECTED
        assert "política" in result.rejection_reason.lower()

    def test_rejected_not_maintained(self):
        pkg = _pkg(is_maintained=False)
        result = self.engine.evaluate_package(pkg, [], {}, {})
        assert result.status == ApprovalStatus.REJECTED
        assert "mantenimiento" in result.rejection_reason.lower()

    def test_rejected_has_vulnerabilities(self):
        pkg = _pkg(name="flask", version="2.0.0")
        vuln = _vuln(pkg_name="flask", version="2.0.0")
        result = self.engine.evaluate_package(pkg, [vuln], {}, {})
        assert result.status == ApprovalStatus.REJECTED
        assert "vulnerabilidad" in result.rejection_reason.lower()

    def test_vuln_different_version_no_rejection(self):
        """Vulnerabilities for a different version do not affect this pkg."""
        pkg = _pkg(name="flask", version="3.0.0")
        vuln = _vuln(pkg_name="flask", version="2.0.0")
        result = self.engine.evaluate_package(pkg, [vuln], {}, {})
        assert result.status == ApprovalStatus.APPROVED

    def test_blank_name_raises_value_error(self):
        """PackageIdentifier with empty name should raise ValueError."""
        with pytest.raises(ValueError):
            PackageIdentifier(name="", version="1.0.0")

    def test_rejected_dependency_causes_rejection(self):
        """Package A depends on B. If B already rejected, A rejected too."""
        parent = _pkg(name="parent")
        deps_map = {"parent": ["bad-dep==1.0.0"], "bad-dep": []}
        all_approvals: dict[str, ApprovalResult] = {
            "bad-dep": ApprovalResult(
                status=ApprovalStatus.REJECTED,
                rejection_reason="Falta Licencia",
            ),
        }

        result = self.engine.evaluate_package(
            parent, [], deps_map, all_approvals
        )
        assert result.status == ApprovalStatus.REJECTED
        assert "bad-dep" in result.rejected_dependencies


# ── Transitive dependencies ──────────────────────────────────────────


class TestTransitiveDependencies:
    """Tests for _get_transitive_dependencies method."""

    def setup_method(self):
        self.engine = ApprovalEngine()

    def test_basic_transitive(self):
        """a → b → c.  Direct=[b], transitive=[c]."""
        deps_map = {
            "a": ["b==1.0"],
            "b": ["c==1.0"],
        }
        direct = ["b==1.0"]
        result = self.engine._get_transitive_dependencies(
            "a", deps_map, direct
        )
        dep_names = [d.split("==")[0] for d in result]
        assert "c" in dep_names

    def test_no_transitives(self):
        deps_map = {"a": ["b==1.0"]}
        direct = ["b==1.0"]
        result = self.engine._get_transitive_dependencies(
            "a", deps_map, direct
        )
        assert result == []

    def test_no_cycle(self):
        """Cyclic deps should not cause infinite loop."""
        deps_map = {
            "a": ["b==1.0"],
            "b": ["a==1.0"],
        }
        direct = ["b==1.0"]
        result = self.engine._get_transitive_dependencies(
            "a", deps_map, direct
        )
        assert isinstance(result, list)

    def test_diamond_dependency(self):
        """a → b, a → c, b → d, c → d.  d appears once."""
        deps_map = {
            "a": ["b==1.0", "c==1.0"],
            "b": ["d==1.0"],
            "c": ["d==1.0"],
        }
        direct = ["b==1.0", "c==1.0"]
        result = self.engine._get_transitive_dependencies(
            "a", deps_map, direct
        )
        dep_names = [d.split("==")[0] for d in result]
        assert dep_names.count("d") == 1


# ── Two-pass cascade (evaluate_all_packages) ────────────────────────


class TestTwoPassCascade:
    """Tests for evaluate_all_packages two-pass algorithm."""

    def setup_method(self):
        self.engine = ApprovalEngine()

    def test_second_pass_rejects_parent_of_rejected(self):
        """If dep rejected in pass 1, parent rejected in pass 2."""
        parent = _pkg(
            name="parent", license_name="MIT", is_maintained=True
        )
        child = _pkg(
            name="child", license_name=None, is_maintained=True
        )
        deps_map = {"parent": ["child==1.0.0"], "child": []}

        approvals = self.engine.evaluate_all_packages(
            [parent, child], [], deps_map
        )

        assert approvals["child"].status == ApprovalStatus.REJECTED
        assert approvals["parent"].status == ApprovalStatus.REJECTED
        assert "child" in approvals["parent"].rejected_dependencies

    def test_all_approved_when_no_issues(self):
        a = _pkg(name="a", license_name="MIT")
        b = _pkg(name="b", license_name="Apache-2.0")
        deps_map = {"a": ["b==1.0.0"], "b": []}

        approvals = self.engine.evaluate_all_packages(
            [a, b], [], deps_map
        )
        for result in approvals.values():
            assert result.status == ApprovalStatus.APPROVED

    def test_deep_cascade_rejection(self):
        """a → b → c.  c rejected → b rejected → a rejected."""
        a = _pkg(name="a")
        b = _pkg(name="b")
        c = _pkg(name="c", license_name=None)
        deps_map = {"a": ["b==1.0"], "b": ["c==1.0"], "c": []}

        approvals = self.engine.evaluate_all_packages(
            [a, b, c], [], deps_map
        )

        assert approvals["c"].status == ApprovalStatus.REJECTED
        assert approvals["b"].status == ApprovalStatus.REJECTED
        assert approvals["a"].status == ApprovalStatus.REJECTED


# ── Production/dev dependency separation ─────────────────────────────


class TestSeparateProductionDevDeps:
    """Tests for _separate_production_and_dev_deps."""

    def setup_method(self):
        self.engine = ApprovalEngine()

    def test_all_production(self):
        requires_dist = ["numpy>=1.0", "pandas>=2.0"]
        all_deps = ["numpy", "pandas"]
        prod, dev = self.engine._separate_production_and_dev_deps(
            requires_dist, all_deps
        )
        assert prod == ["numpy", "pandas"]
        assert dev == []

    def test_extra_marker_is_dev(self):
        requires_dist = [
            "numpy>=1.0",
            "pytest; extra == 'dev'",
            "sphinx; extra == 'docs'",
        ]
        all_deps = ["numpy", "pytest", "sphinx"]
        prod, dev = self.engine._separate_production_and_dev_deps(
            requires_dist, all_deps
        )
        assert "numpy" in prod
        assert "pytest" in dev
        assert "sphinx" in dev

    def test_env_marker_is_production(self):
        """python_version markers are NOT extras → production."""
        requires_dist = [
            "typing-extensions; python_version < '3.8'",
        ]
        all_deps = ["typing-extensions"]
        prod, dev = self.engine._separate_production_and_dev_deps(
            requires_dist, all_deps
        )
        assert "typing-extensions" in prod
