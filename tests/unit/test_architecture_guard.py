"""Architecture guard tests — enforce hexagonal dependency rules.

These tests statically verify that forbidden cross-layer imports do not
exist in the codebase.  They catch architecture regressions early,
ensuring:

* **domain/** never imports from application/ or infrastructure/
* **application/use_cases/** never imports from infrastructure/
  (except via bootstrap/)
* **application/dtos/** never imports from infrastructure/
* **application/mappers/** never imports from infrastructure/
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import List, Tuple

import pytest

# Repo root is two levels up from this test file
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"


# ── Helpers ──────────────────────────────────────────────────────────


def _collect_python_files(directory: Path) -> List[Path]:
    """Recursively collect all .py files under *directory*."""
    return sorted(directory.rglob("*.py"))


def _extract_imports(filepath: Path) -> List[str]:
    """Return all import module strings from a Python file."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    except SyntaxError:
        return []

    modules: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _violations(
    files: List[Path],
    forbidden_prefixes: List[str],
) -> List[Tuple[str, str]]:
    """Return ``[(relative_path, offending_import), ...]``."""
    hits: List[Tuple[str, str]] = []
    for f in files:
        for imp in _extract_imports(f):
            if any(imp.startswith(prefix) for prefix in forbidden_prefixes):
                rel = f.relative_to(_REPO_ROOT).as_posix()
                hits.append((rel, imp))
    return hits


# ── Tests ────────────────────────────────────────────────────────────


class TestDomainIsolation:
    """Domain layer must not depend on application or infrastructure."""

    def test_domain_does_not_import_application(self):
        files = _collect_python_files(_SRC / "domain")
        bad = _violations(files, ["src.application"])
        assert bad == [], (
            f"Domain layer imports application: {bad}"
        )

    def test_domain_does_not_import_infrastructure(self):
        files = _collect_python_files(_SRC / "domain")
        bad = _violations(files, ["src.infrastructure"])
        assert bad == [], (
            f"Domain layer imports infrastructure: {bad}"
        )


class TestApplicationIsolation:
    """Application use-cases / dtos / mappers must not import infrastructure."""

    def _app_files(self, *subdirs: str) -> List[Path]:
        result: List[Path] = []
        for sub in subdirs:
            d = _SRC / "application" / sub
            if d.exists():
                result.extend(_collect_python_files(d))
        return result

    def test_use_cases_do_not_import_infrastructure(self):
        files = self._app_files("use_cases")
        bad = _violations(files, ["src.infrastructure"])
        assert bad == [], (
            f"Use-cases import infrastructure: {bad}"
        )

    def test_dtos_do_not_import_infrastructure(self):
        files = self._app_files("dtos")
        bad = _violations(files, ["src.infrastructure"])
        assert bad == [], (
            f"DTOs import infrastructure: {bad}"
        )

    def test_mappers_do_not_import_infrastructure(self):
        files = self._app_files("mappers")
        bad = _violations(files, ["src.infrastructure"])
        assert bad == [], (
            f"Mappers import infrastructure: {bad}"
        )

    def test_application_does_not_import_interface(self):
        """Application should not know about interface layer."""
        files = _collect_python_files(_SRC / "application")
        bad = _violations(files, ["src.interface"])
        assert bad == [], (
            f"Application layer imports interface: {bad}"
        )


class TestInfrastructureIsolation:
    """Infrastructure must not import from interface layer."""

    def test_infrastructure_does_not_import_interface(self):
        files = _collect_python_files(_SRC / "infrastructure")
        bad = _violations(files, ["src.interface"])
        assert bad == [], (
            f"Infrastructure imports interface: {bad}"
        )
