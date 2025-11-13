"""
Approval Engine - Business rules for package approval evaluation.
Evaluates packages based on license, maintenance status, and vulnerabilities.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Tuple
from src.domain.models import PackageInfo, VulnerabilityInfo
from src.domain.entities import DependencyInfo


class ApprovalEngine:
    """Domain service for evaluating package approval status based on business rules."""
    
    def __init__(self) -> None:
        pass
    
    def evaluate_package_approval(
        self,
        package: PackageInfo,
        vulnerabilities: List[VulnerabilityInfo],
        dependencies_map: Dict[str, List[str]],  # Maps package name to its direct dependencies
        all_packages: Dict[str, PackageInfo]  # All packages by name for lookup
    ) -> Tuple[str, Optional[str], List[str], List[str]]:
        """
        Evaluate package approval status according to business rules.
        
        Rules:
        1. license_rejected must be False
        2. is_maintained should be True (but absence doesn't block approval)
        3. No vulnerabilities reported by Snyk
        4. For main packages: no direct dependency should be rejected
        5. Critical missing info (name, version) → "En verificación"
        6. Warnings are documented but don't block approval
        
        Returns:
            (aprobada, motivo_rechazo, dependencias_directas, dependencias_transitivas)
        """
        # Check for CRITICAL missing information (name, version only)
        if not package.name or not package.version:
            return ("En verificación", "Datos básicos incompletos", [], [])
        
        # Collect warnings about incomplete info (doesn't block approval)
        warnings: List[str] = []
        missing_critical: List[str] = []  # Critical data that's missing
        missing_secondary: List[str] = []  # Secondary data that's missing (just warnings)
        
        # CRÍTICO: Licencia es dato importante
        # Check if license exists and is not empty/whitespace
        if not (package.license and package.license.strip()):
            missing_critical.append("Falta Licencia")
        
        # SECUNDARIO: URL y fecha son útiles pero no críticas
        if not package.home_page and not package.github_url:
            missing_secondary.append("Falta URL del Proyecto")
        if not package.upload_time:
            missing_secondary.append("Falta Fecha de Publicación")
        
        # If we have TOO MUCH critical missing data, mark as "En verificación"
        # (Require at least 50% of critical data)
        if len(missing_critical) > 1:
            missing_items = missing_critical + missing_secondary
            motivo = "Datos incompletos para evaluar: " + "; ".join(missing_items)
            return ("En verificación", motivo, [], [])
        
        # Single missing data point becomes warning
        for item in missing_critical:
            warnings.append(f"⚠ {item}")
        
        # Add secondary missing data as warnings too
        for item in missing_secondary:
            warnings.append(f"⚠ {item}")
        
        # Check individual package rules (these DO block approval)
        rejection_reasons: List[str] = []
        
        # Rule 1: license must not be rejected
        if package.license_rejected:
            rejection_reasons.append("Licencia rechazada")
        
        # Rule 2: package should be maintained (validated only by upload_time, >= 2 years)
        if not package.is_maintained:
            rejection_reasons.append("Sin mantenimiento (última actualización > 2 años)")
        
        # Rule 3: no vulnerabilities
        pkg_vulnerabilities = [v for v in vulnerabilities if v.package_name == package.name]
        if pkg_vulnerabilities:
            rejection_reasons.append(f"Contiene {len(pkg_vulnerabilities)} vulnerabilidad(es)")
        
        # If individual rules are violated, package is rejected
        if rejection_reasons:
            all_reasons = rejection_reasons + warnings
            motivo = "; ".join(all_reasons)
            return ("No", motivo, [], [])
        
        # Get direct dependencies for this package
        direct_deps = dependencies_map.get(package.name, [])
        
        # Rule 4: Check if any direct dependency is rejected
        rejected_deps: List[str] = []
        for dep_name in direct_deps:
            if dep_name in all_packages:
                dep_package = all_packages[dep_name]
                # If dependency is marked as rejected, collect it
                if dep_package.aprobada == "No":
                    rejected_deps.append(dep_name)
        
        if rejected_deps:
            all_reasons = [f"Dependencias directas rechazadas: {', '.join(rejected_deps)}"] + warnings
            motivo = "; ".join(all_reasons)
            return ("No", motivo, direct_deps, [])
        
        # All critical rules passed: package is approved
        # Separate production deps from dev/optional deps using requires_dist
        production_deps, dev_and_optional_deps = self._separate_production_and_dev_deps(
            package.requires_dist,
            direct_deps
        )
        
        # Include warnings in approval message if any
        motivo_final = None
        if warnings:
            motivo_final = "; ".join(warnings)
        
        # Return: (aprobada, motivo, production_deps, dev_and_optional_deps)
        return ("Sí", motivo_final, production_deps, dev_and_optional_deps)
    
    def _has_required_info(self, package: PackageInfo, vulnerabilities: List[VulnerabilityInfo]) -> bool:
        """Check if all CRITICAL information is available to evaluate approval.
        
        Note: This method is now less strict. Only name and version are truly required.
        License and maintenance info are warnings if missing, not blockers.
        """
        # Only truly critical: name and version
        if not package.name or not package.version:
            return False
        
        return True
    
    def _get_transitive_dependencies(
        self,
        package_name: str,
        dependencies_map: Dict[str, List[str]],
        direct_deps: List[str]
    ) -> List[str]:
        """
        Get transitive dependencies (dependencies of dependencies).
        For now, returns all other dependencies not in direct_deps.
        """
        transitive: List[str] = []
        visited = set(direct_deps)
        
        def collect_transitive(pkg: str) -> None:
            for dep in dependencies_map.get(pkg, []):
                if dep not in visited:
                    visited.add(dep)
                    transitive.append(dep)
                    collect_transitive(dep)
        
        # Start from direct dependencies
        for direct_dep in direct_deps:
            collect_transitive(direct_dep)
        
        return transitive
    
    def _separate_production_and_dev_deps(
        self,
        requires_dist: List[str],
        all_direct_deps: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Separate production dependencies from development/optional dependencies.
        
        Uses requires_dist to identify dev/optional deps via PEP 508 markers:
        - Dependencies with 'extra ==' marker are considered optional/dev
        - If a dep is in requires_dist with extra marker, it's dev/optional
        - Otherwise it's production
        
        Args:
            requires_dist: List of PEP 508 requirement strings from PyPI
            all_direct_deps: List of direct dependency names from dependency graph
            
        Returns:
            (production_deps, dev_and_optional_deps)
        """
        production_deps = []
        dev_and_optional_deps = []
        
        # Create a lookup of which deps are extras/optional
        optional_package_names = set()
        
        for req in requires_dist:
            # PEP 508 format examples:
            # - "numpy>=1.0"                          → production
            # - "pytest; extra == 'dev'"              → dev
            # - "sphinx; extra == 'docs'"             → optional
            # - "typing-extensions; python_version < '3.8'" → production (env marker only)
            
            # Check if this requirement has an extra marker
            if "; extra ==" in req:
                # This is an optional extra (dev, docs, tests, etc)
                # Extract package name (before any version specifier)
                pkg_name = req.split(";")[0].split(">=")[0].split("==")[0].split("<")[0].split(">")[0].split("~")[0].split("!")[0].strip()
                optional_package_names.add(pkg_name.lower())
        
        # Now categorize the direct dependencies
        for dep_name in all_direct_deps:
            if dep_name.lower() in optional_package_names:
                dev_and_optional_deps.append(dep_name)
            else:
                production_deps.append(dep_name)
        
        return production_deps, dev_and_optional_deps
    
    def evaluate_all_packages(
        self,
        packages: List[PackageInfo],
        vulnerabilities: List[VulnerabilityInfo],
        dependencies_map: Dict[str, List[str]]  # Maps package name to direct dependencies
    ) -> List[PackageInfo]:
        """
        Evaluate approval status for all packages and return updated list.
        """
        # Create lookup dictionary
        all_packages = {pkg.name: pkg for pkg in packages}
        
        updated_packages: List[PackageInfo] = []
        
        for package in packages:
            aprobada, motivo_rechazo, direct_deps, transitive_deps = self.evaluate_package_approval(
                package,
                vulnerabilities,
                dependencies_map,
                all_packages
            )
            
            # Create new PackageInfo with updated approval status
            updated_pkg = self._update_package_approval(
                package,
                aprobada,
                motivo_rechazo,
                direct_deps,
                transitive_deps
            )
            updated_packages.append(updated_pkg)
        
        return updated_packages
    
    def _update_package_approval(
        self,
        package: PackageInfo,
        aprobada: str,
        motivo_rechazo: Optional[str],
        dependencias_directas: List[str],
        dependencias_transitivas: List[str]
    ) -> PackageInfo:
        """Create an updated PackageInfo with new approval status fields."""
        # Convert string dependency names to DependencyInfo objects
        # For now, use name only (version/latest_version will be enriched later)
        direct_deps_info = [DependencyInfo(name=dep, version="*") for dep in dependencias_directas]
        transitive_deps_info = [DependencyInfo(name=dep, version="*") for dep in dependencias_transitivas]
        
        # Since PackageInfo is frozen, create a new instance with updated fields
        return PackageInfo(
            name=package.name,
            version=package.version,
            latest_version=package.latest_version,
            license=package.license,
            upload_time=package.upload_time,
            summary=package.summary,
            home_page=package.home_page,
            author=package.author,
            author_email=package.author_email,
            maintainer=package.maintainer,
            maintainer_email=package.maintainer_email,
            keywords=package.keywords,
            classifiers=package.classifiers,
            requires_dist=package.requires_dist,
            project_urls=package.project_urls,
            github_url=package.github_url,
            dependencies=package.dependencies,
            is_maintained=package.is_maintained,
            license_rejected=package.license_rejected,
            aprobada=aprobada,
            motivo_rechazo=motivo_rechazo,
            dependencias_directas=direct_deps_info,
            dependencias_transitivas=transitive_deps_info
        )
