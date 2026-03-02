"""Unit tests for AnalyzePackagesUseCase – orchestration with fully mocked ports.

Verifies that the use case correctly sequences: resolve deps → scan vulns →
enrich metadata → apply policies → approval engine → build report.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.entities import (
    Package, PackageIdentifier, DependencyGraph, DependencyNode,
    License, Vulnerability, SeverityLevel, DependencyInfo, Policy,
)
from src.application.dtos import (
    AnalysisRequest, AnalysisResultDTO, PackageDTO,
)
from src.application.use_cases import AnalyzePackagesUseCase


# ── Helpers ──────────────────────────────────────────────────────────


def _pkg(name: str, version: str = "1.0.0", **kw) -> Package:
    return Package(
        identifier=PackageIdentifier(name, version),
        license=License(name="MIT"),
        upload_time=datetime.now(timezone.utc) - timedelta(days=30),
        summary=f"{name} summary",
        home_page=f"https://example.com/{name}",
        **kw,
    )


def _graph(*packages: Package) -> DependencyGraph:
    """Create a flat graph (each package is a root with no sub-deps)."""
    nodes = [DependencyNode(package=p) for p in packages]
    return DependencyGraph(root_packages=nodes)


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def logger():
    m = MagicMock()
    for method in ("debug", "info", "warning", "error"):
        setattr(m, method, MagicMock())
    return m


@pytest.fixture
def resolver():
    m = AsyncMock()
    return m


@pytest.fixture
def scanner():
    m = AsyncMock()
    m.scan_vulnerabilities = AsyncMock(return_value={"results": []})
    return m


@pytest.fixture
def metadata_provider():
    m = AsyncMock()
    # By default, enrich returns the same package (identity enrichment)
    m.enrich_package_metadata = AsyncMock(side_effect=lambda pkg: pkg)
    m.fetch_latest_version = AsyncMock(return_value=None)
    # These are sync methods on the real adapter; expose as plain attributes
    # so hasattr() checks in use_case work correctly with non-coroutine values
    m.get_cache_stats = MagicMock(return_value={
        "pypi_hits": 0, "pypi_misses": 0,
        "github_hits": 0, "github_misses": 0,
    })
    m.reset_cache_stats = MagicMock()
    return m


@pytest.fixture
def cache():
    m = AsyncMock()
    m.get = AsyncMock(return_value=None)
    m.set = AsyncMock()
    m.exists = AsyncMock(return_value=False)
    m.delete = AsyncMock()
    m.generate_key = MagicMock(return_value="key")
    return m


@pytest.fixture
def policy():
    return Policy(
        name="test",
        description="Test policy",
        blocked_licenses=[],
        maintainability_years_threshold=2,
        max_vulnerability_severity=None,
    )


@pytest.fixture
def use_case(resolver, scanner, metadata_provider, cache, logger, policy):
    return AnalyzePackagesUseCase(
        dependency_resolver=resolver,
        vulnerability_scanner=scanner,
        metadata_provider=metadata_provider,
        cache=cache,
        logger=logger,
        policy=policy,
    )


# ── Tests ────────────────────────────────────────────────────────────


class TestAnalyzePackagesUseCase:
    """Tests for the main orchestration use case."""

    @pytest.mark.asyncio
    async def test_execute_returns_dto(self, use_case, resolver, scanner):
        """Happy path: execute should return an AnalysisResultDTO."""
        pkg = _pkg("requests", "2.31.0")
        resolver.resolve_dependencies = AsyncMock(return_value=_graph(pkg))
        scanner.scan_vulnerabilities = AsyncMock(return_value={"results": []})

        request = AnalysisRequest(libraries=["requests==2.31.0"])
        result = await use_case.execute(request)

        assert isinstance(result, AnalysisResultDTO)
        assert len(result.packages) >= 1

    @pytest.mark.asyncio
    async def test_resolver_called_with_libraries(self, use_case, resolver):
        pkg = _pkg("flask")
        resolver.resolve_dependencies = AsyncMock(return_value=_graph(pkg))

        request = AnalysisRequest(libraries=["flask==3.0.0"])
        await use_case.execute(request)

        resolver.resolve_dependencies.assert_called_once_with(["flask==3.0.0"])

    @pytest.mark.asyncio
    async def test_vulnerability_scanner_called(self, use_case, resolver, scanner):
        pkg = _pkg("flask")
        resolver.resolve_dependencies = AsyncMock(return_value=_graph(pkg))

        request = AnalysisRequest(libraries=["flask==3.0.0"])
        await use_case.execute(request)

        scanner.scan_vulnerabilities.assert_called_once()

    @pytest.mark.asyncio
    async def test_metadata_enrichment_called_per_package(
        self, use_case, resolver, metadata_provider
    ):
        """Each package in the graph should be enriched."""
        pkgs = [_pkg("a"), _pkg("b"), _pkg("c")]
        resolver.resolve_dependencies = AsyncMock(return_value=_graph(*pkgs))

        request = AnalysisRequest(libraries=["a==1.0.0", "b==1.0.0", "c==1.0.0"])
        await use_case.execute(request)

        assert metadata_provider.enrich_package_metadata.await_count == 3

    @pytest.mark.asyncio
    async def test_resolver_failure_propagates(self, use_case, resolver):
        resolver.resolve_dependencies = AsyncMock(
            side_effect=RuntimeError("resolution failed")
        )
        request = AnalysisRequest(libraries=["bad==1.0.0"])
        with pytest.raises(RuntimeError, match="resolution failed"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_scanner_failure_propagates(self, use_case, resolver, scanner):
        pkg = _pkg("flask")
        resolver.resolve_dependencies = AsyncMock(return_value=_graph(pkg))
        scanner.scan_vulnerabilities = AsyncMock(
            side_effect=RuntimeError("scan failed")
        )

        request = AnalysisRequest(libraries=["flask==3.0.0"])
        with pytest.raises(RuntimeError, match="scan failed"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_result_contains_correct_package_names(
        self, use_case, resolver
    ):
        pkgs = [_pkg("flask", "3.0.0"), _pkg("click", "8.1.0")]
        resolver.resolve_dependencies = AsyncMock(return_value=_graph(*pkgs))

        request = AnalysisRequest(libraries=["flask==3.0.0", "click==8.1.0"])
        result = await use_case.execute(request)

        names = {p.name for p in result.packages}
        assert "flask" in names
        assert "click" in names


# ── AnalysisRequest validation ───────────────────────────────────────


class TestAnalysisRequestValidation:
    """Tests for AnalysisRequest DTO creation validation."""

    def test_empty_libraries_raises(self):
        with pytest.raises(ValueError, match="empty"):
            AnalysisRequest(libraries=[])

    def test_blank_library_name_raises(self):
        with pytest.raises(ValueError, match="empty"):
            AnalysisRequest(libraries=["flask==1.0", ""])

    def test_valid_request(self):
        req = AnalysisRequest(libraries=["flask==3.0.0"])
        assert req.libraries == ["flask==3.0.0"]
