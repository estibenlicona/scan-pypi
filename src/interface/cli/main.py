"""
CLI Interface - Main entry point for command line usage.

This module handles only CLI-specific concerns: argument parsing, 
user interaction, and error presentation. Business logic and 
dependency injection are handled by other layers.
"""

from __future__ import annotations
import asyncio
import sys
from typing import List
from pathlib import Path
import re

from src.application.dtos import AnalysisRequest
from src.application.bootstrap import ApplicationFactory


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


async def run_analysis(libraries: List[str]) -> None:
    """
    Run the complete package analysis pipeline.
    
    This function orchestrates the analysis but delegates all business
    logic to the application layer. Clean separation of concerns.
    
    Args:
        libraries: List of libraries to analyze
        
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
        print(f"✅ Analysis complete: {len(report.packages)} packages analyzed")
        print(f"📊 Report saved to: {container.settings.report.output_path}")
        
    except Exception as e:
        # Handle and present errors appropriately for CLI
        print(f"❌ Analysis failed: {e}", file=sys.stderr)
        raise
    finally:
        # Clean up resources
        container.close()


def main() -> None:
    """
    Main CLI entry point.
    
    Handles only CLI orchestration: argument parsing, async execution,
    and error presentation. Follows Single Responsibility Principle.
    """
    try:
        # Read libraries to analyze from requirements.scan.txt
        libraries = read_requirements_file()

        # Execute analysis pipeline
        asyncio.run(run_analysis(libraries))

    except KeyboardInterrupt:
        print("\n  Analysis interrupted by user")
        sys.exit(1)

    except RequirementsFileError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f" Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()