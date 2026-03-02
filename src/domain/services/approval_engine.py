"""
Approval Engine - Business rules for package approval evaluation.

Evaluates packages based on license, maintenance status, and
vulnerabilities.  Operates directly on domain entities (Package,
Vulnerability) and returns ApprovalResult value objects.
"""

from __future__ import annotations
from typing import List, Optional, Dict

from src.domain.entities import (
    Package,
    Vulnerability,
    DependencyInfo,
    ApprovalStatus,
    ApprovalResult,
)
from src.domain.services.license_validator import LicenseValidator


class ApprovalEngine:
    """Domain service for evaluating package approval status."""

    # ── Single-package evaluation ────────────────────────────────────

    def evaluate_package(
        self,
        package: Package,
        vulnerabilities: List[Vulnerability],
        dependencies_map: Dict[str, List[str]],
        all_approvals: Dict[str, ApprovalResult],
    ) -> ApprovalResult:
        """Evaluate approval status for a single package.

        Rules (in order):
        1. License must exist and be recognised.
        2. License must not be rejected by policy.
        3. Package must be maintained (recent activity).
        4. No known vulnerabilities for this exact version.
        5. All dependencies must be approved (checked in two-pass).

        Args:
            package: The Package entity to evaluate.
            vulnerabilities: All known vulnerabilities.
            dependencies_map: ``{pkg_name: ["dep==ver", ...]}``
            all_approvals: Results already computed for other packages.

        Returns:
            An ``ApprovalResult`` value object.
        """
        # Critical info gate
        if not package.name or not package.version:
            return ApprovalResult(
                status=ApprovalStatus.UNDER_REVIEW,
                rejection_reason="Datos básicos incompletos",
            )

        rejection_reasons: List[str] = []
        warnings: List[str] = []

        # Secondary warnings (non-blocking)
        if not package.home_page and not package.github_url:
            warnings.append("Falta URL del Proyecto")
        if not package.upload_time:
            warnings.append("Falta Fecha de Publicación")

        direct_deps = dependencies_map.get(package.name, [])

        # Rule 1 — License must exist and be valid
        license_name = LicenseValidator.extract_from_package(package)
        if not license_name:
            rejection_reasons.append("Falta Licencia")

        # Rule 2 — License not blocked by policy
        if package.license and package.license.is_rejected:
            rejection_reasons.append("Licencia rechazada por política")

        # Rule 3 — Maintenance
        if not package.is_maintained():
            rejection_reasons.append(
                "Sin mantenimiento (última actualización > 2 años)"
            )

        # Rule 4 — Vulnerabilities for *this* exact version
        pkg_vulns = [
            v
            for v in vulnerabilities
            if (
                v.package_name.lower() == package.name.lower()
                and v.version == package.version
            )
        ]
        if pkg_vulns:
            rejection_reasons.append(
                f"Contiene {len(pkg_vulns)} vulnerabilidad(es)"
            )

        # Build dependency lists
        transitive_deps = self._get_transitive_dependencies(
            package.name, dependencies_map, direct_deps
        )
        direct_infos = [self._parse_dep(d) for d in direct_deps]
        transitive_infos = [self._parse_dep(d) for d in transitive_deps]

        if rejection_reasons:
            unique = _dedupe(rejection_reasons + warnings)
            return ApprovalResult(
                status=ApprovalStatus.REJECTED,
                rejection_reason=", ".join(unique),
                direct_dependencies=direct_infos,
                transitive_dependencies=transitive_infos,
            )

        # Rule 5 — All (recursive) dependencies must be approved
        rejected_dep_names = self._collect_rejected_deps(
            package.name, dependencies_map, all_approvals
        )
        if rejected_dep_names:
            unique = _dedupe(["Dependencias rechazadas"] + warnings)
            return ApprovalResult(
                status=ApprovalStatus.REJECTED,
                rejection_reason=", ".join(unique),
                direct_dependencies=direct_infos,
                transitive_dependencies=transitive_infos,
                rejected_dependencies=rejected_dep_names,
            )

        # All rules pass
        return ApprovalResult(
            status=ApprovalStatus.APPROVED,
            rejection_reason=", ".join(warnings) if warnings else None,
            direct_dependencies=direct_infos,
            transitive_dependencies=transitive_infos,
        )

    # ── Batch evaluation (two-pass) ─────────────────────────────────

    def evaluate_all_packages(
        self,
        packages: List[Package],
        vulnerabilities: List[Vulnerability],
        dependencies_map: Dict[str, List[str]],
    ) -> Dict[str, ApprovalResult]:
        """Evaluate all packages in two passes.

        Pass 1 — evaluate each package on its own merits.
        Pass 2 — cascade rejections to parents of rejected deps.

        Returns:
            ``{package_name: ApprovalResult}``
        """
        approvals: Dict[str, ApprovalResult] = {}

        # Pass 1
        for pkg in packages:
            result = self.evaluate_package(
                pkg, vulnerabilities, dependencies_map, approvals
            )
            approvals[pkg.name] = result

        # Pass 2 — cascade
        for pkg in packages:
            current = approvals[pkg.name]
            rejected_deps = self._collect_rejected_deps(
                pkg.name, dependencies_map, approvals
            )
            if not rejected_deps:
                continue

            if current.status == ApprovalStatus.APPROVED:
                approvals[pkg.name] = ApprovalResult(
                    status=ApprovalStatus.REJECTED,
                    rejection_reason="Dependencias rechazadas",
                    direct_dependencies=current.direct_dependencies,
                    transitive_dependencies=current.transitive_dependencies,
                    rejected_dependencies=rejected_deps,
                )
            elif not current.rejected_dependencies:
                approvals[pkg.name] = ApprovalResult(
                    status=current.status,
                    rejection_reason=current.rejection_reason,
                    direct_dependencies=current.direct_dependencies,
                    transitive_dependencies=current.transitive_dependencies,
                    rejected_dependencies=rejected_deps,
                )

        return approvals

    # ── Helpers ──────────────────────────────────────────────────────

    def _collect_rejected_deps(
        self,
        package_name: str,
        dependencies_map: Dict[str, List[str]],
        all_approvals: Dict[str, ApprovalResult],
    ) -> List[str]:
        """Recursively collect names of rejected dependencies."""
        rejected: List[str] = []
        visited: set[str] = set()

        def _walk(name: str) -> None:
            if name in visited:
                return
            visited.add(name)

            for dep_entry in dependencies_map.get(name, []):
                dep_name = _extract_name(dep_entry)
                if dep_name in all_approvals:
                    if (
                        all_approvals[dep_name].status
                        == ApprovalStatus.REJECTED
                    ):
                        if dep_name not in rejected:
                            rejected.append(dep_name)
                _walk(dep_name)

        _walk(package_name)
        return rejected

    def _get_transitive_dependencies(
        self,
        package_name: str,
        dependencies_map: Dict[str, List[str]],
        direct_deps: List[str],
    ) -> List[str]:
        """Return transitive deps (deps-of-deps, excluding directs)."""
        transitive: List[str] = []
        visited: set[str] = set()

        for dep in direct_deps:
            visited.add(_extract_name(dep))

        def _collect(pkg: str) -> None:
            for dep_entry in dependencies_map.get(pkg, []):
                dep_name = _extract_name(dep_entry)
                if dep_name not in visited:
                    visited.add(dep_name)
                    transitive.append(dep_entry)
                    _collect(dep_name)

        for dep in direct_deps:
            _collect(_extract_name(dep))

        return transitive

    @staticmethod
    def _parse_dep(dep_str: str) -> DependencyInfo:
        """Parse ``"name==version"`` into a ``DependencyInfo``."""
        if "==" in dep_str:
            name, version = dep_str.split("==", 1)
            return DependencyInfo(
                name=name.strip(), version=version.strip()
            )
        return DependencyInfo(name=dep_str.strip(), version="*")

    def _separate_production_and_dev_deps(
        self,
        requires_dist: List[str],
        all_direct_deps: List[str],
    ) -> tuple[List[str], List[str]]:
        """Separate production deps from dev/optional extras.

        Uses PEP 508 ``extra ==`` markers to identify optional deps.

        Returns:
            ``(production_deps, dev_and_optional_deps)``
        """
        optional_names: set[str] = set()

        for req in requires_dist:
            if "; extra ==" in req:
                pkg_name = (
                    req.split(";")[0]
                    .split(">=")[0]
                    .split("==")[0]
                    .split("<")[0]
                    .split(">")[0]
                    .split("~")[0]
                    .split("!")[0]
                    .strip()
                )
                optional_names.add(pkg_name.lower())

        production: List[str] = []
        dev: List[str] = []

        for dep in all_direct_deps:
            if dep.lower() in optional_names:
                dev.append(dep)
            else:
                production.append(dep)

        return production, dev


# ── Module-level helpers ─────────────────────────────────────────────


def _extract_name(dep_entry: str) -> str:
    """Extract package name from a versioned string like ``name==1.0``."""
    return (
        dep_entry.split("==")[0]
        .split(">=")[0]
        .split("<")[0]
        .strip()
    )


def _dedupe(items: List[str]) -> List[str]:
    """Deduplicate preserving order (case-insensitive)."""
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
