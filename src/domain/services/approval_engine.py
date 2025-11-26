"""
Approval Engine - Business rules for package approval evaluation.
Evaluates packages based on license, maintenance status, and vulnerabilities.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Tuple
from src.domain.models import PackageInfo, VulnerabilityInfo
from src.domain.entities import DependencyInfo
from src.domain.services.license_validator import LicenseValidator


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
    ) -> Tuple[str, Optional[str], List[str], List[str], List[str]]:
        """
        Evaluate package approval status according to business rules.
        
        Rules:
        1. license_rejected must be False
        2. is_maintained should be True (but absence doesn't block approval)
        3. No vulnerabilities reported
        4. All dependencies (recursive) must be approved
        5. Critical missing info (name, version) → "En verificación"
        6. Warnings are documented but don't block approval
        
        Returns:
            (aprobada, motivo_rechazo, dependencias_directas, dependencias_transitivas, dependencias_rechazadas)
        """
        # Check for CRITICAL missing information (name, version only)
        if not package.name or not package.version:
            return ("En verificación", "Datos básicos incompletos", [], [], [])
        
        # Collect warnings about incomplete info (doesn't block approval)
        warnings: List[str] = []
        missing_critical: List[str] = []  # Critical data that's missing
        missing_secondary: List[str] = []  # Secondary data that's missing (just warnings)
        
        # NOTE: License is now handled as a rejection reason (see Rule 1 below)
        # It's no longer just a warning
        
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
            return ("En verificación", motivo, [], [], [])
        
        # Single missing data point becomes warning
        for item in missing_critical:
            warnings.append(item)
        
        # Add secondary missing data as warnings too
        for item in missing_secondary:
            warnings.append(item)
        
        # Check individual package rules (these DO block approval)
        rejection_reasons: List[str] = []
        
        # Get direct dependencies EARLY (needed for all outcomes)
        direct_deps = dependencies_map.get(package.name, [])
        
        # Rule 1: License MUST exist and be valid
        # First check if license exists (not None or empty/whitespace)
        has_license = package.license and package.license.strip()
        
        if not has_license:
            # Missing license is a rejection reason, not just a warning
            rejection_reasons.append("Falta Licencia")
        else:
            # License exists, now check if it's valid
            license_is_valid = LicenseValidator.is_valid_license(package.license)
            if not license_is_valid:
                rejection_reasons.append("Licencia no válida o no reconocida")
        
        # Rule 2: if license is explicitly rejected by policy
        if package.license_rejected:
            rejection_reasons.append("Licencia rechazada por política")
        
        # Rule 2: package should be maintained (validated only by upload_time, >= 2 years)
        if not package.is_maintained:
            rejection_reasons.append("Sin mantenimiento (última actualización > 2 años)")
        
        # Rule 3: no vulnerabilities for this specific version
        # Check if this exact package version has any reported vulnerabilities
        pkg_vulnerabilities = [
            v for v in vulnerabilities 
            if v.package_name.lower() == package.name.lower() and v.version == package.version
        ]
        
        if pkg_vulnerabilities:
            rejection_reasons.append(f"Contiene {len(pkg_vulnerabilities)} vulnerabilidad(es)")
        
        # If individual rules are violated, package is rejected but show its dependencies
        if rejection_reasons:
            # Combine and deduplicate reasons
            all_reasons = rejection_reasons + warnings
            unique_reasons = []
            seen_reasons = set()
            for reason in all_reasons:
                if reason.lower() not in seen_reasons:
                    unique_reasons.append(reason)
                    seen_reasons.add(reason.lower())
            motivo = ", ".join(unique_reasons)
            # Calculate dependencies even for rejected packages so user can see what they depend on
            transitive_deps = self._get_transitive_dependencies(package.name, dependencies_map, direct_deps)
            return ("No", motivo, direct_deps, transitive_deps, [])
        
        # Rule 4: Check if ANY dependency (direct or transitive) is rejected
        # Collect all rejected dependencies recursively
        rejected_deps: List[str] = []
        rejected_dep_names: List[str] = []
        
        def collect_rejected_deps(pkg_name: str, visited: set[str] | None = None) -> None:
            """Recursively collect all rejected dependencies."""
            if visited is None:
                visited = set()
            if pkg_name in visited:
                return
            visited.add(pkg_name)
            
            # Check direct dependencies
            for dep_entry in dependencies_map.get(pkg_name, []):
                # Extract package name from versioned format (e.g., "colorama==0.4.6" -> "colorama")
                dep_name = dep_entry.split("==")[0].split(">=")[0].split("<")[0].strip()
                if dep_name in all_packages:
                    dep_package = all_packages[dep_name]
                    if dep_package.aprobada == "No":
                        if dep_name not in rejected_dep_names:
                            rejected_dep_names.append(dep_name)
                    # Recurse into this dependency
                    collect_rejected_deps(dep_name, visited)
        
        # Collect all rejected dependencies starting from this package
        collect_rejected_deps(package.name)
        
        if rejected_dep_names:
            # Combine and deduplicate reasons
            all_reasons_list = ["Dependencias rechazadas"] + warnings
            unique_reasons_list = []
            seen_reasons_set = set()
            for reason in all_reasons_list:
                if reason.lower() not in seen_reasons_set:
                    unique_reasons_list.append(reason)
                    seen_reasons_set.add(reason.lower())
            motivo = ", ".join(unique_reasons_list)
            # Calculate transitive dependencies even for rejected packages
            transitive_deps = self._get_transitive_dependencies(package.name, dependencies_map, direct_deps)
            return ("No", motivo, direct_deps, transitive_deps, rejected_dep_names)
        
        # All critical rules passed: package is approved
        # Get all direct dependencies for this package
        direct_dep_names = direct_deps
        
        # Calculate transitive dependencies (dependencies of dependencies)
        transitive_deps = self._get_transitive_dependencies(package.name, dependencies_map, direct_deps)
        
        # Include warnings in approval message if any
        motivo_final = None
        if warnings:
            motivo_final = ", ".join(warnings)
        
        # Return: (aprobada, motivo, direct_deps, transitive_deps, dependencias_rechazadas)
        return ("Sí", motivo_final, direct_dep_names, transitive_deps, [])
    
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
        Returns all dependencies not in direct_deps.
        
        Args:
            package_name: The package to get transitives for
            dependencies_map: Maps package name to list of versioned dependency strings
            direct_deps: List of direct dependency strings (e.g., "colorama==0.4.6")
        
        Returns:
            List of transitive dependency strings
        """
        transitive: List[str] = []
        # Create a set of direct dependency names (without versions) to avoid duplicates
        visited = set()
        for dep in direct_deps:
            dep_name = dep.split("==")[0].split(">=")[0].split("<")[0].strip()
            visited.add(dep_name)
        
        def collect_transitive(pkg: str) -> None:
            """Recursively collect transitive dependencies."""
            for dep_entry in dependencies_map.get(pkg, []):
                # Extract package name from versioned string (e.g., "colorama==0.4.6" -> "colorama")
                dep_name = dep_entry.split("==")[0].split(">=")[0].split("<")[0].strip()
                if dep_name not in visited:
                    visited.add(dep_name)
                    transitive.append(dep_entry)
                    collect_transitive(dep_name)
        
        # Start from direct dependencies
        for dep_entry in direct_deps:
            dep_name = dep_entry.split("==")[0].split(">=")[0].split("<")[0].strip()
            collect_transitive(dep_name)
        
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
        
        This is done in TWO PASSES:
        1. First pass: Evaluate each package based on its own criteria
        2. Second pass: Re-evaluate packages with rejected dependencies
        
        This ensures that if a package depends on a rejected package, it too is rejected.
        """
        # PASS 1: Initial evaluation of all packages
        all_packages = {pkg.name: pkg for pkg in packages}
        
        updated_packages: List[PackageInfo] = []
        
        for package in packages:
            aprobada, motivo_rechazo, direct_deps, transitive_deps, rejected_deps = self.evaluate_package_approval(
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
                transitive_deps,
                rejected_deps,
            )
            updated_packages.append(updated_pkg)
        
        # PASS 2: Re-evaluate packages that have rejected dependencies
        # Update the lookup dictionary with first-pass results
        all_packages = {pkg.name: pkg for pkg in updated_packages}
        
        final_packages: List[PackageInfo] = []
        
        for package in updated_packages:
            # Check if this package depends on any rejected packages
            rejected_dep_names: List[str] = []
            
            def collect_rejected_deps_from_final(pkg_name: str, visited: set[str] | None = None) -> None:
                """Recursively collect rejected dependencies using final pass results."""
                if visited is None:
                    visited = set()
                if pkg_name in visited:
                    return
                visited.add(pkg_name)
                
                for dep_entry in dependencies_map.get(pkg_name, []):
                    dep_name = dep_entry.split("==")[0].split(">=")[0].split("<")[0].strip()
                    if dep_name in all_packages:
                        dep_package = all_packages[dep_name]
                        if dep_package.aprobada == "No":
                            if dep_name not in rejected_dep_names:
                                rejected_dep_names.append(dep_name)
                        collect_rejected_deps_from_final(dep_name, visited)
            
            collect_rejected_deps_from_final(package.name)
            
            # If this package has rejected dependencies and is currently approved, reject it
            if rejected_dep_names and package.aprobada == "Sí":
                direct_deps_names = [d.name for d in package.dependencias_directas]
                transitive_deps_names = [d.name for d in package.dependencias_transitivas]
                final_pkg = self._update_package_approval(
                    package,
                    "No",
                    "Dependencias rechazadas",
                    direct_deps_names,
                    transitive_deps_names,
                    rejected_dep_names,
                )
                final_packages.append(final_pkg)
            elif rejected_dep_names and package.aprobada != "Sí":
                # Already rejected, but update rejected_dep_names if empty
                if not package.dependencias_rechazadas:
                    direct_deps_names = [d.name for d in package.dependencias_directas]
                    transitive_deps_names = [d.name for d in package.dependencias_transitivas]
                    final_pkg = self._update_package_approval(
                        package,
                        package.aprobada,
                        package.motivo_rechazo,
                        direct_deps_names,
                        transitive_deps_names,
                        rejected_dep_names,
                    )
                    final_packages.append(final_pkg)
                else:
                    final_packages.append(package)
            else:
                final_packages.append(package)
        
        return final_packages
    
    def _update_package_approval(
        self,
        package: PackageInfo,
        aprobada: str,
        motivo_rechazo: Optional[str],
        dependencias_directas: List[str],
        dependencias_transitivas: List[str],
        dependencias_rechazadas: List[str],
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
            dependencias_transitivas=transitive_deps_info,
            dependencias_rechazadas=dependencias_rechazadas,
        )
