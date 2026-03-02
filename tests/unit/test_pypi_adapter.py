"""Unit tests for PyPIClientAdapter – enrich_package_metadata, cache stats,
GitHub fallback, error handling.

Uses mocks for all HTTP calls (aiohttp) and CachePort.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.domain.entities import Package, PackageIdentifier, License
from src.infrastructure.adapters.pypi_adapter import PyPIClientAdapter
from src.infrastructure.config.settings import APISettings


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def logger():
    m = MagicMock()
    for method in ("debug", "info", "warning", "error"):
        setattr(m, method, MagicMock())
    return m


@pytest.fixture
def cache():
    """Async mock implementing CachePort interface."""
    c = AsyncMock()
    c.get = AsyncMock(return_value=None)
    c.set = AsyncMock()
    c.exists = AsyncMock(return_value=False)
    c.delete = AsyncMock()
    c.generate_key = MagicMock(side_effect=lambda *args: "|".join(str(a) for a in args))
    return c


@pytest.fixture
def settings():
    return APISettings(
        pypi_base_url="https://pypi.org/pypi",
        github_base_url="https://api.github.com",
        request_timeout=10,
    )


@pytest.fixture
def adapter(settings, logger, cache):
    return PyPIClientAdapter(settings, logger, cache=cache)


@pytest.fixture
def adapter_no_cache(settings, logger):
    return PyPIClientAdapter(settings, logger, cache=None)


def _make_package(name="requests", version="2.31.0", **kwargs) -> Package:
    return Package(identifier=PackageIdentifier(name, version), **kwargs)


FAKE_PYPI_RESPONSE = {
    "info": {
        "name": "requests",
        "version": "2.31.0",
        "license": "Apache 2.0",
        "summary": "HTTP library",
        "home_page": "https://github.com/psf/requests",
        "author": "Kenneth Reitz",
        "author_email": "me@kennethreitz.org",
        "maintainer": None,
        "maintainer_email": None,
        "keywords": "http,requests",
        "classifiers": [
            "License :: OSI Approved :: Apache Software License",
        ],
        "requires_dist": ["charset-normalizer>=2"],
        "project_urls": {
            "Source": "https://github.com/psf/requests",
        },
    },
    "urls": [
        {"upload_time": "2023-05-22T15:12:00"}
    ],
}


# ── enrich_package_metadata ──────────────────────────────────────────


class TestEnrichPackageMetadata:
    """Tests for the main enrichment orchestration."""

    @pytest.mark.asyncio
    async def test_enrich_with_pypi_data(self, adapter):
        """Enrichment should populate license, summary, etc."""
        pkg = _make_package()

        with patch.object(
            adapter, "_fetch_pypi_metadata", new_callable=AsyncMock
        ) as mock_pypi, patch.object(
            adapter, "_fetch_latest_version_info", new_callable=AsyncMock
        ) as mock_latest, patch.object(
            adapter, "_fetch_github_metadata", new_callable=AsyncMock
        ) as mock_gh:
            mock_pypi.return_value = FAKE_PYPI_RESPONSE
            mock_latest.return_value = ("2.32.0", datetime(2024, 1, 1, tzinfo=timezone.utc))
            mock_gh.return_value = None

            result = await adapter.enrich_package_metadata(pkg)

        assert result.license is not None
        assert result.summary == "HTTP library"
        assert result.latest_version == "2.32.0"

    @pytest.mark.asyncio
    async def test_enrich_returns_original_on_no_pypi_data(self, adapter):
        pkg = _make_package()

        with patch.object(
            adapter, "_fetch_pypi_metadata", new_callable=AsyncMock
        ) as mock_pypi:
            mock_pypi.return_value = None
            result = await adapter.enrich_package_metadata(pkg)

        assert result is pkg  # exact same object

    @pytest.mark.asyncio
    async def test_enrich_returns_original_on_exception(self, adapter):
        pkg = _make_package()

        with patch.object(
            adapter, "_fetch_pypi_metadata", new_callable=AsyncMock
        ) as mock_pypi:
            mock_pypi.side_effect = RuntimeError("network error")
            result = await adapter.enrich_package_metadata(pkg)

        assert result is pkg

    @pytest.mark.asyncio
    async def test_enrich_calls_github_when_url_available(self, adapter):
        pkg = _make_package()

        with patch.object(
            adapter, "_fetch_pypi_metadata", new_callable=AsyncMock
        ) as mock_pypi, patch.object(
            adapter, "_fetch_latest_version_info", new_callable=AsyncMock
        ) as mock_latest, patch.object(
            adapter, "_fetch_github_metadata", new_callable=AsyncMock
        ) as mock_gh:
            mock_pypi.return_value = FAKE_PYPI_RESPONSE
            mock_latest.return_value = (None, None)
            mock_gh.return_value = {
                "license": {"key": "apache-2.0", "name": "Apache 2.0"},
                "pushed_at": "2024-06-01T00:00:00Z",
            }

            result = await adapter.enrich_package_metadata(pkg)

        mock_gh.assert_called_once()
        assert result.last_commit_date is not None

    @pytest.mark.asyncio
    async def test_github_fallback_uses_cached_license(self, adapter):
        """When GitHub returns None (rate-limit), cached license is used."""
        pkg = _make_package()

        # Pre-populate the cache with a license
        adapter._cache.get = AsyncMock(side_effect=lambda key: (
            {"license": {"key": "mit", "name": "MIT License"}}
            if "github_license" in key else None
        ))

        with patch.object(
            adapter, "_fetch_pypi_metadata", new_callable=AsyncMock
        ) as mock_pypi, patch.object(
            adapter, "_fetch_latest_version_info", new_callable=AsyncMock
        ) as mock_latest, patch.object(
            adapter, "_fetch_github_metadata", new_callable=AsyncMock
        ) as mock_gh:
            mock_pypi.return_value = FAKE_PYPI_RESPONSE
            mock_latest.return_value = (None, None)
            mock_gh.return_value = None  # Simulate rate-limit

            result = await adapter.enrich_package_metadata(pkg)

        # GitHub cache hit counter should increment
        assert adapter._github_cache_hits >= 1


# ── Cache stats ──────────────────────────────────────────────────────


class TestCacheStats:
    """Tests for cache hit/miss counters."""

    def test_initial_stats_zero(self, adapter):
        stats = adapter.get_cache_stats()
        assert all(v == 0 for v in stats.values())

    def test_reset_stats(self, adapter):
        adapter._pypi_cache_hits = 5
        adapter._github_cache_misses = 3
        adapter.reset_cache_stats()
        stats = adapter.get_cache_stats()
        assert all(v == 0 for v in stats.values())

    @pytest.mark.asyncio
    async def test_pypi_cache_hit_increments(self, adapter):
        """When cache has data, hit counter increments."""
        adapter._cache.get = AsyncMock(return_value=FAKE_PYPI_RESPONSE)

        result = await adapter._fetch_pypi_metadata("requests", "2.31.0")
        assert result == FAKE_PYPI_RESPONSE
        assert adapter._pypi_cache_hits == 1
        assert adapter._pypi_cache_misses == 0

    @pytest.mark.asyncio
    async def test_pypi_cache_miss_increments(self, adapter):
        """When cache is empty, miss counter increments."""
        adapter._cache.get = AsyncMock(return_value=None)

        with patch.object(
            adapter.retry_policy, "execute", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.return_value = FAKE_PYPI_RESPONSE
            await adapter._fetch_pypi_metadata("requests", "2.31.0")

        assert adapter._pypi_cache_misses == 1
        assert adapter._pypi_cache_hits == 0


# ── No cache adapter ─────────────────────────────────────────────────


class TestNoCacheAdapter:
    """Tests when adapter is created without CachePort (cache=None)."""

    @pytest.mark.asyncio
    async def test_fetch_works_without_cache(self, adapter_no_cache):
        """Adapter without cache should still work (no errors)."""
        with patch.object(
            adapter_no_cache.retry_policy, "execute", new_callable=AsyncMock
        ) as mock_retry:
            mock_retry.return_value = FAKE_PYPI_RESPONSE
            result = await adapter_no_cache._fetch_pypi_metadata("requests", "2.31.0")

        assert result == FAKE_PYPI_RESPONSE
        assert adapter_no_cache._pypi_cache_hits == 0
        assert adapter_no_cache._pypi_cache_misses == 0


# ── _merge_pypi_data ─────────────────────────────────────────────────


class TestMergePypiData:
    """Tests for _merge_pypi_data helper."""

    def test_merges_basic_fields(self, adapter):
        pkg = _make_package()
        result = adapter._merge_pypi_data(pkg, FAKE_PYPI_RESPONSE)
        assert result.summary == "HTTP library"
        assert result.author == "Kenneth Reitz"
        assert result.github_url is not None

    def test_preserves_dependencies(self, adapter):
        """Existing dependencies should not be lost during merge."""
        from src.domain.entities import DependencyInfo
        deps = [DependencyInfo(name="urllib3", version="2.0.0")]
        pkg = _make_package(dependencies=deps)
        result = adapter._merge_pypi_data(pkg, FAKE_PYPI_RESPONSE)
        assert result.dependencies == deps

    def test_handles_invalid_info_structure(self, adapter):
        """If 'info' is not a dict, should return original package."""
        pkg = _make_package()
        result = adapter._merge_pypi_data(pkg, {"info": "not_a_dict"})
        assert result is pkg


# ── _merge_github_data ───────────────────────────────────────────────


class TestMergeGithubData:
    """Tests for _merge_github_data helper."""

    def test_extracts_pushed_at(self, adapter):
        pkg = _make_package(github_url="https://github.com/psf/requests")
        github_data = {
            "license": {"key": "mit", "name": "MIT License"},
            "pushed_at": "2024-06-15T12:00:00Z",
        }
        result = adapter._merge_github_data(pkg, github_data)
        assert result.last_commit_date is not None
        assert result.last_commit_date.year == 2024

    def test_github_license_fallback_when_pypi_none(self, adapter):
        """If PyPI didn't detect license, GitHub should fill it in."""
        pkg = _make_package(github_url="https://github.com/psf/requests")
        # No license from PyPI
        github_data = {
            "license": {"key": "mit", "name": "MIT License"},
        }
        result = adapter._merge_github_data(pkg, github_data)
        assert result.license is not None
        assert "mit" in result.license.name.lower()

    def test_preserves_pypi_license_over_github(self, adapter):
        """PyPI license should not be overwritten by GitHub."""
        license_obj = License(name="Apache-2.0")
        pkg = _make_package(
            license=license_obj,
            github_url="https://github.com/psf/requests",
        )
        github_data = {
            "license": {"key": "mit", "name": "MIT License"},
        }
        result = adapter._merge_github_data(pkg, github_data)
        assert "Apache" in result.license.name


# ── _parse_github_pushed_at ──────────────────────────────────────────


class TestParseGithubPushedAt:
    def test_valid_iso_with_z(self):
        result = PyPIClientAdapter._parse_github_pushed_at(
            {"pushed_at": "2024-06-15T12:00:00Z"}
        )
        assert result is not None
        assert result.year == 2024

    def test_none_when_missing(self):
        assert PyPIClientAdapter._parse_github_pushed_at({}) is None

    def test_none_when_invalid(self):
        assert PyPIClientAdapter._parse_github_pushed_at(
            {"pushed_at": "not-a-date"}
        ) is None
