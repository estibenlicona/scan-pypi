"""
CLI Interface - Main entry point for command line usage.

This module handles only CLI-specific concerns: argument parsing, 
user interaction, and error presentation. Business logic and 
dependency injection are handled by other layers.
"""

from __future__ import annotations
import asyncio
import sys
import re
import argparse
import shutil
from datetime import datetime
from typing import List
from pathlib import Path

from src.application.dtos import AnalysisRequest
from src.application.bootstrap import ApplicationFactory
from src.infrastructure.adapters.markdown_report_adapter import MarkdownReportAdapter
from src.infrastructure.adapters.xlsx_report_adapter import XLSXReportAdapter
from src.infrastructure.adapters.logger_adapter import LoggerAdapter
from src.infrastructure.config.settings import LoggingSettings


def generate_xlsx_only(report_path: str = "consolidated_report.json") -> None:
    """Generate XLSX report from existing consolidated report."""
    logging_settings = LoggingSettings()
    logger = LoggerAdapter(logging_settings)
    xlsx_adapter = XLSXReportAdapter(logger)

    if xlsx_adapter.generate_xlsx(report_path, "packages.xlsx"):
        print("[OK] XLSX report generated: packages.xlsx")
        archive_reports(report_path, "packages.xlsx")
        sys.exit(0)
    else:
        print("[ERROR] Failed to generate XLSX report", file=sys.stderr)
        sys.exit(1)


class RequirementsFileError(Exception):
    """Raised when the requirements file is missing or contains no packages."""


def archive_reports(
    json_report_path: str | Path,
    xlsx_report_path: str | Path,
    base_directory: str | Path = "reports_history",
) -> Path | None:
    """Copy generated reports into a timestamped folder for historical tracking."""

    json_path = Path(json_report_path)
    xlsx_path = Path(xlsx_report_path)

    if not json_path.exists():
        print(f"[ARCHIVE] Skipped: JSON report not found at {json_path}")
        return None

    if not xlsx_path.exists():
        print(f"[ARCHIVE] Skipped: XLSX report not found at {xlsx_path}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(base_directory)
    archive_dir = base_dir / timestamp

    if archive_dir.exists():
        # Extremely rare collision (same second). Append microseconds to avoid overwrite.
        unique_suffix = datetime.now().strftime("%f")
        archive_dir = base_dir / f"{timestamp}_{unique_suffix}"

    archive_dir.mkdir(parents=True, exist_ok=False)

    shutil.copy2(json_path, archive_dir / json_path.name)
    shutil.copy2(xlsx_path, archive_dir / xlsx_path.name)

    print(f"[ARCHIVE] Reports copied to: {archive_dir}")
    return archive_dir


def read_requirements_file(path: str | Path = "requirements.scan.txt") -> List[str]:
    """Read a requirements file and return a list of exact package specifications.

    The function ignores blank lines and comments. Only allows exact version
    specifications with '==' or package names without version specifiers.
    Rejects range specifiers like >=, <=, !=, ~= as they cannot be analyzed precisely.
    
    Returns:
        List of package specifications (e.g. ["requests==2.28.0", "flask"])
        
    Raises:
        RequirementsFileError: If file is missing or contains invalid version specifiers
    """
    p = Path(path)
    if not p.exists():
        raise RequirementsFileError("No packages found in requirements.scan.txt")

    packages: List[str] = []
    # Matches package name with optional exact version (==) only
    exact_spec_re = re.compile(r"^\s*([A-Za-z0-9_.-]+(?:==[A-Za-z0-9_.-]+)?)\s*$")
    # Detects range version specifiers that are not allowed
    range_spec_re = re.compile(r"^\s*[A-Za-z0-9_.-]+[<>!~]")

    with p.open("r", encoding="utf-8") as fh:
        for line_num, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            # Check for forbidden range specifiers first
            if range_spec_re.match(line):
                raise RequirementsFileError(
                    f"Line {line_num}: Range version specifiers not supported: '{line}'\n"
                    f"Only exact versions (==) or unspecified versions are allowed.\n"
                    f"Example: 'requests==2.28.0' or 'requests'"
                )

            # Check if it matches our allowed pattern
            m = exact_spec_re.match(line)
            if m:
                packages.append(m.group(1))
            else:
                raise RequirementsFileError(
                    f"Line {line_num}: Invalid package specification: '{line}'\n"
                    f"Only package names and exact versions (==) are allowed.\n"
                    f"Example: 'requests==2.28.0' or 'requests'"
                )
    
    if not packages:
        raise RequirementsFileError("No valid packages found in requirements file")
    
    return packages


async def run_analysis(libraries: List[str], generate_markdown: bool = False) -> None:
    """
    Run the complete package analysis pipeline.
    
    This function orchestrates the analysis but delegates all business
    logic to the application layer. Clean separation of concerns.
    
    Args:
        libraries: List of libraries to analyze
        generate_markdown: Whether to generate markdown report after analysis
        
    Raises:
        Exception: If analysis pipeline fails
    """
    # Create application using factory (Clean Architecture)
    orchestrator, container = ApplicationFactory.create_application()
    
    # Create domain request object
    request = AnalysisRequest(libraries=libraries)
    
    try:
        # Execute business logic through application layer
        report = await orchestrator.run(request)
        
        # Present results to user (CLI responsibility)
        print(f"[OK] Analysis complete: {len(report.packages)} packages analyzed")
        print(f"[REPORT] Report saved to: {container.settings.report.output_path}")
        
        # Auto-generate XLSX report
        xlsx_adapter = XLSXReportAdapter(container.logger)
        if xlsx_adapter.generate_xlsx(
            container.settings.report.output_path,
            "packages.xlsx",
            root_libraries=libraries,
        ):
            print("[XLSX] Report generated: packages.xlsx")
            archive_reports(
                container.settings.report.output_path,
                "packages.xlsx",
            )
        
        # Generate markdown if requested
        if generate_markdown:
            markdown_adapter = MarkdownReportAdapter(container.logger)
            if markdown_adapter.generate_markdown(container.settings.report.output_path):
                print("[OK] Markdown report generated: packages.md")
            else:
                print("[WARNING] Failed to generate Markdown report", file=sys.stderr)
        
    except Exception as e:
        # Handle and present errors appropriately for CLI
        print(f"[ERROR] Analysis failed: {e}", file=sys.stderr)
        raise
    finally:
        # Clean up resources
        container.close()


def generate_markdown_only(report_path: str = "consolidated_report.json") -> None:
    """Generate markdown report from existing consolidated report."""
    logging_settings = LoggingSettings()
    logger = LoggerAdapter(logging_settings)
    markdown_adapter = MarkdownReportAdapter(logger)
    
    if markdown_adapter.generate_markdown(report_path):
        print("[OK] Markdown report generated: packages.md")
        sys.exit(0)
    else:
        print("[ERROR] Failed to generate Markdown report", file=sys.stderr)
        sys.exit(1)

## CSV adapter removed


def main() -> None:
    """
    Main CLI entry point.
    
    Handles only CLI orchestration: argument parsing, async execution,
    and error presentation. Follows Single Responsibility Principle.
    """
    parser = argparse.ArgumentParser(
        description="PyPI Package Analysis Tool - Analyze dependencies and generate reports"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Generate Markdown report (packages.md) after analysis"
    )
    parser.add_argument(
        "--markdown-only",
        action="store_true",
        help="Generate Markdown report from existing consolidated_report.json (no analysis)"
    )
## CSV adapter removed
    parser.add_argument(
        "--xlsx",
        action="store_true",
        help="Generate Excel report (packages.xlsx) from existing consolidated_report.json (no analysis)"
    )
    parser.add_argument(
        "--report",
        type=str,
        default="consolidated_report.json",
        help="Path to consolidated report (used with --markdown-only)"
    )
    
    args = parser.parse_args()
    
    # Handle markdown-only mode
    if args.markdown_only:
        generate_markdown_only(args.report)
        return
    ## CSV adapter removed
    # Handle xlsx-only mode
    if args.xlsx:
        generate_xlsx_only(args.report)
        return
    
    try:
        # Read libraries to analyze from requirements.scan.txt
        libraries = read_requirements_file()

        # Execute analysis pipeline
        asyncio.run(run_analysis(libraries, generate_markdown=args.markdown))

    except KeyboardInterrupt:
        print("\n  Analysis interrupted by user")
        sys.exit(1)

    except RequirementsFileError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()