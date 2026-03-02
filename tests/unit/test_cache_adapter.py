"""Unit tests for CacheDiskAdapter – TTL expiry, exists, delete, generate_key,
disabled cache, corrupt data handling."""

import pytest
import json
import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock

from src.infrastructure.adapters.cache_adapter import CacheDiskAdapter
from src.infrastructure.config.settings import CacheSettings


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def cache_dir(tmp_path):
    return str(tmp_path / "test_cache")


@pytest.fixture
def logger():
    m = MagicMock()
    m.debug = MagicMock()
    m.warning = MagicMock()
    return m


@pytest.fixture
def cache(cache_dir, logger):
    settings = CacheSettings(enabled=True, directory=cache_dir, ttl_hours=1)
    return CacheDiskAdapter(settings, logger)


@pytest.fixture
def disabled_cache(cache_dir, logger):
    settings = CacheSettings(enabled=False, directory=cache_dir, ttl_hours=1)
    return CacheDiskAdapter(settings, logger)


# ── Helper ───────────────────────────────────────────────────────────


def _run(coro):
    """Run async in sync test."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Tests ────────────────────────────────────────────────────────────


class TestCacheSetGet:
    """Basic set/get operations."""

    def test_set_and_get(self, cache):
        key = cache.generate_key("test", "data")
        _run(cache.set(key, {"foo": "bar"}))
        result = _run(cache.get(key))
        assert result == {"foo": "bar"}

    def test_get_nonexistent_returns_none(self, cache):
        key = cache.generate_key("nonexistent")
        result = _run(cache.get(key))
        assert result is None

    def test_overwrite_value(self, cache):
        key = cache.generate_key("overwrite")
        _run(cache.set(key, "v1"))
        _run(cache.set(key, "v2"))
        assert _run(cache.get(key)) == "v2"


class TestCacheTTL:
    """TTL expiration tests."""

    def test_expired_entry_returns_none(self, cache_dir, logger):
        """Set a very short global TTL and verify expiry."""
        # Use a global TTL of 1 second (1/3600 hours ≈ 0.000278 hours)
        # CacheDiskAdapter.get() checks against self.ttl_seconds (global)
        settings = CacheSettings(
            enabled=True,
            directory=cache_dir,
            ttl_hours=1,  # Will be overridden below
        )
        cache = CacheDiskAdapter(settings, logger)
        # Override global TTL to 1 second for fast test
        cache.ttl_seconds = 1
        key = cache.generate_key("ttl_test")

        _run(cache.set(key, "temp"))

        # Should exist immediately
        assert _run(cache.get(key)) == "temp"

        # Wait for expiry
        time.sleep(1.5)
        assert _run(cache.get(key)) is None

    def test_exists_returns_false_after_expiry(self, cache_dir, logger):
        settings = CacheSettings(enabled=True, directory=cache_dir, ttl_hours=1)
        cache = CacheDiskAdapter(settings, logger)
        key = cache.generate_key("exists_ttl")

        _run(cache.set(key, "data", ttl_seconds=1))
        assert _run(cache.exists(key)) is True

        time.sleep(1.5)
        assert _run(cache.exists(key)) is False


class TestCacheDelete:
    """Delete operations."""

    def test_delete_removes_entry(self, cache):
        key = cache.generate_key("del_test")
        _run(cache.set(key, "value"))
        assert _run(cache.exists(key)) is True

        _run(cache.delete(key))
        assert _run(cache.exists(key)) is False
        assert _run(cache.get(key)) is None

    def test_delete_nonexistent_no_error(self, cache):
        key = cache.generate_key("no_such_key")
        _run(cache.delete(key))  # Should not raise


class TestCacheDisabled:
    """When cache is disabled, all operations are no-ops."""

    def test_get_returns_none(self, disabled_cache):
        key = disabled_cache.generate_key("anything")
        _run(disabled_cache.set(key, "data"))
        assert _run(disabled_cache.get(key)) is None

    def test_exists_returns_false(self, disabled_cache):
        key = disabled_cache.generate_key("anything")
        assert _run(disabled_cache.exists(key)) is False


class TestGenerateKey:
    """Key generation tests."""

    def test_deterministic(self, cache):
        k1 = cache.generate_key("a", "b", "c")
        k2 = cache.generate_key("a", "b", "c")
        assert k1 == k2

    def test_different_args_different_keys(self, cache):
        k1 = cache.generate_key("pkg", "1.0")
        k2 = cache.generate_key("pkg", "2.0")
        assert k1 != k2

    def test_handles_complex_types(self, cache):
        k = cache.generate_key("prefix", {"nested": True}, [1, 2, 3])
        assert isinstance(k, str)
        assert len(k) == 64  # SHA256 hex digest


class TestCacheCorruption:
    """Graceful handling of corrupt cached data."""

    def test_corrupt_data_file_returns_none(self, cache):
        key = cache.generate_key("corrupt")
        _run(cache.set(key, "good_data"))

        # Corrupt the data file
        data_file = cache._get_cache_file(key)
        data_file.write_text("NOT VALID JSON {{{")

        result = _run(cache.get(key))
        assert result is None  # Should handle gracefully

    def test_corrupt_metadata_file_returns_none(self, cache):
        key = cache.generate_key("corrupt_meta")
        _run(cache.set(key, "good_data"))

        # Corrupt the metadata file
        meta_file = cache._get_metadata_file(key)
        meta_file.write_text("BROKEN")

        result = _run(cache.get(key))
        assert result is None
