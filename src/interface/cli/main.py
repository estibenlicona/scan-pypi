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
from typing import List
from pathlib import Path

from src.application.dtos import AnalysisRequest
from src.application.bootstrap import ApplicationFactory
from src.infrastructure.adapters.markdown_report_adapter import MarkdownReportAdapter
from src.infrastructure.adapters.logger_adapter import LoggerAdapter
from src.infrastructure.config.settings import LoggingSettings


class RequirementsFileError(Exception):
    """Raised when the requirements file is missing or contains no packages."""


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


def add_scan_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add the scan arguments to a parser.

    Shared between the standalone scan parser (``python -m src.interface.cli``)
    and the ``run`` subcommand of the packaged executable, so both expose the
    exact same options.
    """
    parser.add_argument(
        "packages",
        nargs="*",
        metavar="paquete",
        help="Paquetes a escanear (ej: requests==2.28.0 flask)",
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        default=None,
        help="Leer paquetes desde un archivo de requirements",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Generar también reporte Markdown (packages.md)",
    )
    parser.add_argument(
        "--markdown-only",
        action="store_true",
        help="Solo generar Markdown desde consolidated_report.json",
    )
    parser.add_argument(
        "--report",
        type=str,
        default="consolidated_report.json",
        help="Ruta al JSON de reporte (para --markdown-only)",
    )
    return parser


def _build_parser() -> argparse.ArgumentParser:
    """Build the standalone argument parser for the scan command."""
    parser = argparse.ArgumentParser(
        prog="scan",
        description=(
            "PyPI Package Scanner — analiza dependencias, "
            "vulnerabilidades y licencias."
        ),
        usage="scan <paquete[==version]> [...] [opciones]",
        epilog=(
            "Ejemplos:\n"
            "  scan requests==2.28.0\n"
            "  scan flask django==4.2\n"
            "  scan -f requirements.scan.txt\n"
            "  scan requests --markdown\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    return add_scan_arguments(parser)


def _resolve_libraries(args: argparse.Namespace) -> List[str]:
    """Determine the list of libraries to scan from args.

    Priority:
    1. Positional ``packages`` on the command line.
    2. ``--file`` flag pointing to a requirements file.
    3. Default ``requirements.scan.txt`` if it exists.

    Raises:
        SystemExit: When no packages are provided.
    """
    # Positional packages take priority
    if args.packages:
        return args.packages

    # Explicit file flag
    if args.file:
        return read_requirements_file(args.file)

    # Fallback: default requirements file
    default_file = Path("requirements.scan.txt")
    if default_file.exists():
        return read_requirements_file(str(default_file))

    print(
        "[ERROR] No se indicaron paquetes.\n\n"
        "Uso:\n"
        "  scan <paquete[==version]> [...]\n"
        "  scan -f requirements.scan.txt\n",
        file=sys.stderr,
    )
    sys.exit(1)


def run_command(args: argparse.Namespace) -> None:
    """Execute the scan command from parsed arguments.

    Shared by the standalone CLI and the ``run`` subcommand so both behave
    identically once arguments are parsed.
    """
    # Report-only modes (no analysis)
    if args.markdown_only:
        generate_markdown_only(args.report)
        return

    try:
        libraries = _resolve_libraries(args)
        asyncio.run(run_analysis(libraries, generate_markdown=args.markdown))

    except KeyboardInterrupt:
        print("\n  Análisis interrumpido por el usuario")
        sys.exit(1)

    except RequirementsFileError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main CLI entry point for the standalone scan command."""
    args = _build_parser().parse_args()
    run_command(args)


if __name__ == "__main__":
    main()