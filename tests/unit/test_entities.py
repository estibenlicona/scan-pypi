"""Unit tests for domain entities – Package, PackageIdentifier,
DependencyGraph, Vulnerability, etc."""

import pytest
from datetime import datetime, timezone, timedelta

from src.domain.entities import (
    Package,
    PackageIdentifier,
    DependencyGraph,
    DependencyNode,
    DependencyInfo,
    Vulnerability,
    License,
    LicenseType,
    SeverityLevel,
    Policy,
    AnalysisResult,
)


# ── PackageIdentifier ───────────────────────────────────────────────


class TestPackageIdentifier:
    """Tests for the PackageIdentifier value object."""

    def test_valid_creation(self):
        pid = PackageIdentifier(name="requests", version="2.31.0")
        assert pid.name == "requests"
        assert pid.version == "2.31.0"

    def test_str_representation(self):
        pid = PackageIdentifier(name="flask", version="3.0.0")
        assert str(pid) == "flask@3.0.0"

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            PackageIdentifier(name="", version="1.0.0")

    def test_empty_version_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            PackageIdentifier(name="requests", version="")

    def test_both_empty_raises(self):
        with pytest.raises(ValueError):
            PackageIdentifier(name="", version="")

    def test_frozen_hashable(self):
        a = PackageIdentifier("pkg", "1.0")
        b = PackageIdentifier("pkg", "1.0")
        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_different_versions_not_equal(self):
        a = PackageIdentifier("pkg", "1.0")
        b = PackageIdentifier("pkg", "2.0")
        assert a != b


# ── Vulnerability ────────────────────────────────────────────────────


class TestVulnerability:
    """Tests for the Vulnerability entity."""

    def test_valid_creation(self):
        v = Vulnerability(
            id="CVE-2024-0001",
            title="XSS",
            description="Cross-site scripting",
            severity=SeverityLevel.HIGH,
            package_name="flask",
            version="2.0.0",
        )
        assert v.id == "CVE-2024-0001"
        assert v.severity == SeverityLevel.HIGH

    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            Vulnerability(
                id="",
                title="XSS",
                description=None,
                severity=SeverityLevel.LOW,
                package_name="flask",
                version="2.0.0",
            )

    def test_empty_package_name_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            Vulnerability(
                id="CVE-1",
                title="t",
                description=None,
                severity=SeverityLevel.LOW,
                package_name="",
                version="1.0",
            )

    def test_empty_version_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            Vulnerability(
                id="CVE-1",
                title="t",
                description=None,
                severity=SeverityLevel.LOW,
                package_name="pkg",
                version="",
            )


# ── Package.is_maintained ────────────────────────────────────────────


class TestPackageIsMaintained:
    """Tests for the Package.is_maintained() method – all 3 signals."""

    @staticmethod
    def _make_package(**kwargs) -> Package:
        return Package(
            identifier=PackageIdentifier("test-pkg", "1.0.0"),
            **kwargs,
        )

    def test_recent_upload_time(self):
        pkg = self._make_package(
            upload_time=datetime.now(timezone.utc) - timedelta(days=30)
        )
        assert pkg.is_maintained() is True

    def test_old_upload_time(self):
        pkg = self._make_package(
            upload_time=datetime.now(timezone.utc) - timedelta(days=800)
        )
        assert pkg.is_maintained() is False

    def test_latest_upload_time_overrides_old_upload(self):
        """latest_upload_time is checked first; even if upload_time is old,
        a recent latest_upload_time means maintained."""
        pkg = self._make_package(
            upload_time=datetime.now(timezone.utc) - timedelta(days=900),
            latest_upload_time=datetime.now(timezone.utc) - timedelta(days=10),
        )
        assert pkg.is_maintained() is True

    def test_last_commit_date_overrides_old_upload(self):
        """last_commit_date (signal 2) is checked before upload_time."""
        pkg = self._make_package(
            upload_time=datetime.now(timezone.utc) - timedelta(days=900),
            last_commit_date=datetime.now(timezone.utc) - timedelta(days=5),
        )
        assert pkg.is_maintained() is True

    def test_all_dates_none_returns_false(self):
        pkg = self._make_package()
        assert pkg.is_maintained() is False

    def test_all_dates_old_returns_false(self):
        old = datetime.now(timezone.utc) - timedelta(days=1000)
        pkg = self._make_package(
            upload_time=old,
            latest_upload_time=old,
            last_commit_date=old,
        )
        assert pkg.is_maintained() is False

    def test_naive_datetime_treated_as_utc(self):
        """Naive datetimes should work (treated as UTC internally)."""
        pkg = self._make_package(
            upload_time=datetime.now() - timedelta(days=30)
        )
        assert pkg.is_maintained() is True

    def test_custom_years_threshold(self):
        pkg = self._make_package(
            upload_time=datetime.now(timezone.utc) - timedelta(days=400)
        )
        # Default 2 years → maintained.  1 year → not maintained.
        assert pkg.is_maintained(years_threshold=2) is True
        assert pkg.is_maintained(years_threshold=1) is False


# ── DependencyGraph ──────────────────────────────────────────────────


class TestDependencyGraph:
    """Tests for DependencyGraph deduplication and find_package."""

    @staticmethod
    def _pkg(name: str, version: str = "1.0.0") -> Package:
        return Package(identifier=PackageIdentifier(name, version))

    def test_get_all_packages_deduplicates(self):
        shared = self._pkg("shared-lib")
        node_a = DependencyNode(
            package=self._pkg("a"),
            dependencies=[DependencyNode(package=shared)],
        )
        node_b = DependencyNode(
            package=self._pkg("b"),
            dependencies=[DependencyNode(package=shared)],
        )
        graph = DependencyGraph(root_packages=[node_a, node_b])
        all_pkgs = graph.get_all_packages()
        names = [p.name for p in all_pkgs]
        assert names.count("shared-lib") == 1
        assert len(all_pkgs) == 3  # a, b, shared-lib

    def test_find_package_existing(self):
        pkg = self._pkg("flask", "3.0.0")
        graph = DependencyGraph(root_packages=[DependencyNode(package=pkg)])
        found = graph.find_package(PackageIdentifier("flask", "3.0.0"))
        assert found is not None
        assert found.name == "flask"

    def test_find_package_missing(self):
        pkg = self._pkg("flask", "3.0.0")
        graph = DependencyGraph(root_packages=[DependencyNode(package=pkg)])
        found = graph.find_package(PackageIdentifier("django", "5.0"))
        assert found is None

    def test_empty_graph(self):
        graph = DependencyGraph(root_packages=[])
        assert graph.get_all_packages() == []

    def test_deep_tree_deduplication(self):
        """Chain: a → b → c.  c appears once."""
        c = DependencyNode(package=self._pkg("c"))
        b = DependencyNode(package=self._pkg("b"), dependencies=[c])
        a = DependencyNode(package=self._pkg("a"), dependencies=[b])
        graph = DependencyGraph(root_packages=[a])
        assert len(graph.get_all_packages()) == 3


# ── AnalysisResult ───────────────────────────────────────────────────


class TestAnalysisResult:
    """Tests for AnalysisResult helper methods."""

    def test_get_vulnerabilities_for_package(self):
        pid = PackageIdentifier("pkg", "1.0")
        vuln_match = Vulnerability(
            id="V1", title="t", description=None,
            severity=SeverityLevel.HIGH,
            package_name="pkg", version="1.0",
        )
        vuln_other = Vulnerability(
            id="V2", title="t2", description=None,
            severity=SeverityLevel.LOW,
            package_name="other", version="2.0",
        )
        graph = DependencyGraph(
            root_packages=[DependencyNode(package=Package(identifier=pid))]
        )
        result = AnalysisResult(
            dependency_graph=graph,
            vulnerabilities=[vuln_match, vuln_other],
            maintained_packages=[],
            timestamp=datetime.now(timezone.utc),
        )
        filtered = result.get_vulnerabilities_for_package(pid)
        assert len(filtered) == 1
        assert filtered[0].id == "V1"
