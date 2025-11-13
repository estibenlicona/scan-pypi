"""
Markdown Report Adapter - Generates dependency tree and package table in Markdown format.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, cast

from src.domain.ports import LoggerPort


class MarkdownReportAdapter:
    """Generates a Markdown file with dependency tree and package summary table."""

    # Development and testing dependency markers to filter
    DEV_KEYWORDS = {
        "test", "dev", "lint", "format", "black", "mypy", "pylint", "pytest",
        "sphinx", "doc", "build", "flake8", "isort", "pre-commit", "tox",
        "coverage", "mock", "typing", "stub", "wheel", "setuptools"
    }

    def __init__(self, logger: LoggerPort) -> None:
        self.logger = logger

    def _is_dev_dependency(self, pkg_name: str) -> bool:
        """Check if package name indicates it's a development/testing dependency."""
        lower_name = pkg_name.lower()
        return any(keyword in lower_name for keyword in self.DEV_KEYWORDS)

    def _extract_package_name(self, dep_string: str) -> str:
        """
        Extract clean package name from dependency string.
        
        Handles formats like:
        - "numpy>=1.0"
        - "scipy[sparse]>=1.5"
        - "pandas!=1.0.*,>=1.2"
        """
        match = re.match(r"^([a-zA-Z0-9_.-]+)", dep_string)
        if match:
            return match.group(1)
        return dep_string.strip()

    def _normalize_license(self, license_val: Any) -> str:
        """
        Normalize license value. Extract short license name from full text.
        
        Args:
            license_val: License value (can be None, string, or dict)
            
        Returns:
            Short license identifier or "—" if not available
        """
        if license_val is None:
            return "—"

        # If it's a dict (from license object)
        if isinstance(license_val, dict):
            name = license_val.get("name")
            if name:
                license_val = name
            else:
                return "—"

        # Convert to string
        license_str = str(cast(Any, license_val)).strip()

        if not license_str:
            return "—"

        # If it's very long (full license text), try to extract the license name
        if len(license_str) > 100:
            # Try to extract SPDX identifier or common licenses
            if "MIT" in license_str:
                return "MIT"
            elif "Apache" in license_str:
                return "Apache 2.0"
            elif "GPL" in license_str:
                if "3" in license_str:
                    return "GPL 3.0"
                elif "2" in license_str:
                    return "GPL 2.0"
                return "GPL"
            elif "BSD" in license_str:
                if "3" in license_str:
                    return "BSD 3-Clause"
                elif "2" in license_str:
                    return "BSD 2-Clause"
                return "BSD"
            elif "MPL" in license_str or "Mozilla" in license_str:
                return "MPL 2.0"
            elif "ISC" in license_str:
                return "ISC"
            else:
                # Return first line of license text if it seems like a name
                first_line = license_str.split("\n")[0].strip()
                if len(first_line) < 50:
                    return first_line[:50]
                return "Custom License"

        # For short strings, return as-is (already a license name)
        return license_str[:50]

    def generate_markdown(self, report_path: str, output_path: str = "packages.md") -> bool:
        """
        Generate Markdown report from consolidated JSON report.
        
        Args:
            report_path: Path to consolidated_report.json
            output_path: Path where packages.md will be saved
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not Path(report_path).exists():
                self.logger.error(f"Report file not found: {report_path}")
                return False

            with open(report_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            packages = data.get("packages", [])
            if not packages:
                self.logger.warning("No packages found in report")
                return False

            # Build dependency map (cleaned)
            dep_map = self._build_dependency_map(packages)

            # Generate markdown content
            markdown_content = self._generate_markdown_content(packages, dep_map)

            # Save to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            self.logger.info(f"✅ Markdown report generated: {output_path}")
            return True

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in report file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to generate Markdown report: {e}")
            return False

    def _build_dependency_map(self, packages: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build a map of package name -> production dependencies (cleaned, no dev)."""
        dep_map: Dict[str, List[str]] = {}

        for pkg in packages:
            name = pkg.get("package", "")
            if not name:
                continue

            raw_deps = pkg.get("requires_dist") or []
            cleaned_deps = []
            seen = set()

            for dep in raw_deps:
                if not isinstance(dep, str):
                    continue

                # Extract clean package name
                pkg_name = self._extract_package_name(dep)

                # Skip if already seen (avoid duplicates) or if it's a dev dependency
                if pkg_name in seen or self._is_dev_dependency(pkg_name):
                    continue

                seen.add(pkg_name)
                cleaned_deps.append(pkg_name)

            dep_map[name] = cleaned_deps

        return dep_map

    def _generate_tree_for_package(
        self, name: str, dep_map: Dict[str, List[str]], level: int = 0, seen: Optional[Set[str]] = None, max_depth: int = 3
    ) -> List[str]:
        """Recursively generate dependency tree rows (depth-limited, cycle-aware)."""
        seen = seen or set()

        # Stop at max depth to avoid huge trees
        if level >= max_depth:
            return []

        if name in seen:
            return []

        seen.add(name)
        rows = [("  " * level) + name]  # Use 2 spaces for indentation

        for dep in dep_map.get(name, []):
            rows.extend(self._generate_tree_for_package(dep, dep_map, level + 1, seen.copy(), max_depth))

        return rows

    def _generate_markdown_content(self, packages: List[Dict[str, Any]], dep_map: Dict[str, List[str]]) -> str:
        """Generate complete Markdown report content."""
        lines: List[str] = []

        # Header
        lines.append("# 📦 Árbol de dependencias (Reporte Markdown)")
        lines.append("")
        lines.append("Generado automáticamente desde `consolidated_report.json`")
        lines.append("")
        lines.append("> **Nota:** Solo se muestran dependencias de producción (se filtran dependencias de desarrollo/testing)")
        lines.append("")

        # Top-level packages
        lines.append("## Paquetes principales analizados")
        lines.append("")
        lines.append("| # | Paquete | Versión | Licencia | Estado |")
        lines.append("|---|----------|----------|-----------|----------|")

        counter = 1
        for pkg in packages:
            name = pkg.get("package", "")
            if not name:
                continue

            version = pkg.get("version", "—")
            # Get license field
            license_val = pkg.get("license", None)
            license_normalized = self._normalize_license(license_val)
            is_maintained = pkg.get("is_maintained", True)
            status = "✅ Activo" if is_maintained else "⚠️ Inactivo"

            lines.append(f"| {counter} | `{name}` | {version} | {license_normalized} | {status} |")
            counter += 1

        lines.append("")
        lines.append("## Árbol de dependencias")
        lines.append("")

        # Dependency trees (only for top-level packages with dependencies)
        for pkg in packages:
            pkg_name = pkg.get("package", "")
            if not pkg_name:
                continue

            tree = self._generate_tree_for_package(pkg_name, dep_map, max_depth=3)

            if len(tree) > 1:  # Only show if has dependencies
                lines.append(f"### {pkg_name}")
                lines.append("")
                lines.append("```")
                lines.extend(tree)
                lines.append("```")
                lines.append("")

        # Summary statistics
        lines.append("## Estadísticas")
        lines.append("")

        total_packages = len(packages)
        total_unique_deps = len(dep_map)
        maintained_count = sum(1 for pkg in packages if pkg.get("is_maintained", True))

        lines.append(f"- **Total de paquetes principales:** {total_packages}")
        lines.append(f"- **Paquetes mantenidos:** {maintained_count}")
        lines.append(f"- **Paquetes inactivos:** {total_packages - maintained_count}")
        lines.append(f"- **Total de dependencias únicas:** {total_unique_deps}")
        lines.append("")

        # Table with all packages details
        lines.append("## Tabla detallada de paquetes")
        lines.append("")
        lines.append("| Paquete | Versión | Licencia | Estado | Propósito |")
        lines.append("|----------|----------|-----------|----------|-------------|")

        for pkg in packages:
            name = pkg.get("package", "")
            version = pkg.get("version", "—")
            # Use normalized license
            license_val = pkg.get("license", None)
            license_normalized = self._normalize_license(license_val)
            is_maintained = pkg.get("is_maintained", True)
            status = "✅ Activo" if is_maintained else "⚠️ Inactivo"

            # Get summary, ensure it's a string
            raw_summary = pkg.get("summary")
            if raw_summary is None:
                summary = "—"
            else:
                summary = str(raw_summary).replace("\n", " ").strip() or "—"
                # Truncate long summaries and escape pipes
                if len(summary) > 80:
                    summary = summary[:77] + "..."
                summary = summary.replace("|", "\\|")

            lines.append(f"| `{name}` | {version} | {license_normalized} | {status} | {summary} |")

        lines.append("")

        return "\n".join(lines)
