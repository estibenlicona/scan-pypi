"""Integration tests for the scan CLI (``py scan ...``).

Tests argument parsing, library resolution logic, and the full
subprocess invocation of ``py scan --help``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from src.interface.cli.main import (
    RequirementsFileError,
    _build_parser,
    _resolve_libraries,
    read_requirements_file,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ── Argument parser ──────────────────────────────────────────────────


class TestBuildParser:
    """Verify that the CLI parser is correctly configured."""

    def test_parser_accepts_positional_packages(self):
        parser = _build_parser()
        args = parser.parse_args(["requests==2.28.0"])
        assert args.packages == ["requests==2.28.0"]

    def test_parser_accepts_multiple_packages(self):
        parser = _build_parser()
        args = parser.parse_args(["flask", "django==4.2", "numpy"])
        assert args.packages == ["flask", "django==4.2", "numpy"]

    def test_parser_accepts_file_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["-f", "my_reqs.txt"])
        assert args.file == "my_reqs.txt"
        assert args.packages == []

    def test_parser_accepts_markdown_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["requests", "--markdown"])
        assert args.markdown is True

    def test_parser_defaults(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.packages == []
        assert args.file is None
        assert args.markdown is False
        assert args.markdown_only is False
        assert args.report == "consolidated_report.json"


# ── Library resolution ───────────────────────────────────────────────


class TestResolveLibraries:
    """Test the _resolve_libraries priority logic."""

    def test_positional_packages_take_priority(self):
        parser = _build_parser()
        args = parser.parse_args(["requests==2.28.0", "flask"])
        result = _resolve_libraries(args)
        assert result == ["requests==2.28.0", "flask"]

    def test_file_flag_reads_from_file(self, tmp_path: Path):
        req_file = tmp_path / "reqs.txt"
        req_file.write_text("django==4.2\nnumpy\n")
        parser = _build_parser()
        args = parser.parse_args(["-f", str(req_file)])
        result = _resolve_libraries(args)
        assert result == ["django==4.2", "numpy"]

    def test_fallback_to_default_requirements(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """When no args and no --file, reads requirements.scan.txt."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "requirements.scan.txt").write_text("celery==5.3.0\n")
        parser = _build_parser()
        args = parser.parse_args([])
        result = _resolve_libraries(args)
        assert result == ["celery==5.3.0"]

    def test_no_packages_exits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """When no args and no default file, should exit with code 1."""
        monkeypatch.chdir(tmp_path)
        parser = _build_parser()
        args = parser.parse_args([])
        with pytest.raises(SystemExit) as exc_info:
            _resolve_libraries(args)
        assert exc_info.value.code == 1


# ── Requirements file reader ────────────────────────────────────────


class TestReadRequirementsFile:
    """Test read_requirements_file validation."""

    def test_reads_valid_file(self, tmp_path: Path):
        f = tmp_path / "req.txt"
        f.write_text("requests==2.28.0\nflask\n# comment\n\n")
        result = read_requirements_file(str(f))
        assert result == ["requests==2.28.0", "flask"]

    def test_rejects_range_specifiers(self, tmp_path: Path):
        f = tmp_path / "req.txt"
        f.write_text("requests>=2.0\n")
        with pytest.raises(RequirementsFileError):
            read_requirements_file(str(f))

    def test_missing_file_raises(self):
        with pytest.raises(RequirementsFileError):
            read_requirements_file("/nonexistent/path.txt")

    def test_empty_file_raises(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("# only comments\n\n")
        with pytest.raises(RequirementsFileError):
            read_requirements_file(str(f))


# ── Subprocess smoke test ────────────────────────────────────────────


class TestScanSubprocess:
    """Verify that ``scan`` entry point runs as a subprocess."""

    def test_help_returns_zero(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.interface.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(_PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "paquete" in result.stdout.lower()

    def test_no_args_with_missing_requirements_exits_nonzero(
        self, tmp_path: Path
    ):
        result = subprocess.run(
            [sys.executable, "-m", "src.interface.cli"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(tmp_path),
        )
        assert result.returncode != 0
        assert "no se indicaron" in result.stderr.lower()
