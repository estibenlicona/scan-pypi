"""Unit tests for uv compile command argument construction."""

from __future__ import annotations

from typing import Any, List

import pytest

from src.infrastructure.adapters import uv_dependency_resolver_adapter as uv_module
from src.infrastructure.adapters.uv_dependency_resolver_adapter import (
    UvDepResolverAdapter,
)
from src.infrastructure.config.settings import APISettings


class _FakeProcess:
    """Minimal async subprocess stub used for command capture."""

    returncode = 0

    async def communicate(self, input: bytes | None = None):
        _ = input
        return b"requests==2.31.0\n", b""


def _make_adapter(uv_allow_prerelease: bool) -> UvDepResolverAdapter:
    """Create an adapter instance bypassing __init__ for isolated testing."""
    adapter = UvDepResolverAdapter.__new__(UvDepResolverAdapter)
    adapter.api_settings = APISettings(uv_allow_prerelease=uv_allow_prerelease)
    return adapter


@pytest.mark.asyncio
async def test_compile_adds_prerelease_flag_when_enabled(monkeypatch):
    seen_cmd: List[str] = []

    async def _fake_create_subprocess_exec(*cmd: Any, **kwargs: Any):
        _ = kwargs
        seen_cmd.extend(str(part) for part in cmd)
        return _FakeProcess()

    adapter = _make_adapter(uv_allow_prerelease=True)
    monkeypatch.setattr(uv_module, "_UV_BIN", "uv")
    monkeypatch.setattr(
        uv_module.asyncio, "create_subprocess_exec", _fake_create_subprocess_exec
    )
    parse_output = lambda requested, _output: {"name": requested}
    monkeypatch.setattr(
        adapter, "_parse_compile_output", parse_output
    )

    await adapter._compile_with_uv("requests==2.31.0")

    assert "--prerelease=allow" in seen_cmd


@pytest.mark.asyncio
async def test_compile_skips_prerelease_flag_when_disabled(monkeypatch):
    seen_cmd: List[str] = []

    async def _fake_create_subprocess_exec(*cmd: Any, **kwargs: Any):
        _ = kwargs
        seen_cmd.extend(str(part) for part in cmd)
        return _FakeProcess()

    adapter = _make_adapter(uv_allow_prerelease=False)
    monkeypatch.setattr(uv_module, "_UV_BIN", "uv")
    monkeypatch.setattr(
        uv_module.asyncio, "create_subprocess_exec", _fake_create_subprocess_exec
    )
    parse_output = lambda requested, _output: {"name": requested}
    monkeypatch.setattr(
        adapter, "_parse_compile_output", parse_output
    )

    await adapter._compile_with_uv("requests==2.31.0")

    assert "--prerelease=allow" not in seen_cmd
