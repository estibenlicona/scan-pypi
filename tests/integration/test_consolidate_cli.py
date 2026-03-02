"""Integration tests for the consolidate CLI (``py consolidate``).

Tests report discovery, merging, XLSX generation, and the full
subprocess invocation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.interface.cli.consolidate import (
    ConsolidationError,
    find_all_report_jsons,
    generate_consolidated_xlsx,
    load_and_merge_packages,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ── Helpers ──────────────────────────────────────────────────────────


def _write_report(
    directory: Path,
    packages: list[dict],
    subfolder: str = "20260101_120000",
) -> Path:
    """Create a minimal consolidated_report.json in a timestamped dir."""
    ts_dir = directory / subfolder
    ts_dir.mkdir(parents=True, exist_ok=True)
    report = {"packages": packages}
    path = ts_dir / "consolidated_report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


# ── Report discovery ─────────────────────────────────────────────────


class TestFindAllReportJsons:
    """Test find_all_report_jsons discovery logic."""

    def test_finds_reports(self, tmp_path: Path):
        base = tmp_path / "history"
        _write_report(base, [{"package": "a", "version": "1.0"}])
        _write_report(
            base,
            [{"package": "b", "version": "2.0"}],
            subfolder="20260102_120000",
        )
        result = find_all_report_jsons(base)
        assert len(result) == 2

    def test_missing_directory_raises(self, tmp_path: Path):
        with pytest.raises(ConsolidationError):
            find_all_report_jsons(tmp_path / "nonexistent")

    def test_empty_directory_raises(self, tmp_path: Path):
        base = tmp_path / "empty"
        base.mkdir()
        with pytest.raises(ConsolidationError):
            find_all_report_jsons(base)


# ── Package merging ──────────────────────────────────────────────────


class TestLoadAndMergePackages:
    """Test deduplication and merge logic."""

    def test_deduplicates_by_name_version(self, tmp_path: Path):
        base = tmp_path / "history"
        _write_report(
            base,
            [
                {"package": "requests", "version": "2.28.0"},
                {"package": "flask", "version": "2.0.0"},
            ],
        )
        _write_report(
            base,
            [
                {"package": "requests", "version": "2.28.0"},  # duplicate
                {"package": "django", "version": "4.2.0"},
            ],
            subfolder="20260102_120000",
        )
        paths = find_all_report_jsons(base)
        merged = load_and_merge_packages(paths)
        assert len(merged) == 3  # requests, flask, django

    def test_skips_packages_without_name(self, tmp_path: Path):
        base = tmp_path / "history"
        _write_report(
            base,
            [
                {"package": "", "version": "1.0"},
                {"package": "valid", "version": "1.0"},
            ],
        )
        paths = find_all_report_jsons(base)
        merged = load_and_merge_packages(paths)
        assert len(merged) == 1


# ── XLSX generation ──────────────────────────────────────────────────


class TestGenerateConsolidatedXlsx:
    """Test XLSX output file creation."""

    def test_creates_xlsx_file(self, tmp_path: Path):
        packages = {
            ("requests", "2.28.0"): {
                "package": "requests",
                "version": "2.28.0",
                "aprobada": "Sí",
            },
        }
        output = tmp_path / "out.xlsx"
        generate_consolidated_xlsx(packages, output)
        assert output.exists()
        assert output.stat().st_size > 0

    def test_empty_packages_raises(self, tmp_path: Path):
        with pytest.raises(ConsolidationError):
            generate_consolidated_xlsx({}, tmp_path / "empty.xlsx")


# ── Subprocess smoke test ────────────────────────────────────────────


class TestConsolidateSubprocess:
    """Verify that ``py consolidate`` runs as a subprocess."""

    def test_missing_history_exits_nonzero(self, tmp_path: Path):
        result = subprocess.run(
            [sys.executable, "-c",
             "from src.interface.cli.consolidate import main; main()"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(tmp_path),
            env={**__import__('os').environ, "PYTHONPATH": str(_PROJECT_ROOT)},
        )
        assert result.returncode != 0

    def test_with_valid_history_exits_zero(self, tmp_path: Path):
        base = tmp_path / "reports_history"
        _write_report(
            base,
            [
                {
                    "package": "requests",
                    "version": "2.28.0",
                    "aprobada": "Sí",
                    "licencia": "Apache-2.0",
                },
            ],
        )
        result = subprocess.run(
            [sys.executable, "-c",
             "from src.interface.cli.consolidate import main; main()"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(tmp_path),
            env={**__import__('os').environ, "PYTHONPATH": str(_PROJECT_ROOT)},
        )
        assert result.returncode == 0
        assert "consolidated" in result.stdout.lower()
        assert (tmp_path / "consolidated.xlsx").exists()
