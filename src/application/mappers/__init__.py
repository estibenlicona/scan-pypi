"""
Application Mappers — Convert between domain entities and DTOs.

With domain/models eliminated, these mappers bridge domain entities
directly to application DTOs without an intermediate layer.
"""

from __future__ import annotations
from typing import Any, Dict, List

from src.domain.entities import (
    AnalysisResult,
    Package,
    Vulnerability,
    ApprovalResult,
    ApprovalStatus,
)
from src.application.dtos import (
    AnalysisRequest,
    PackageDTO,
    VulnerabilityDTO,
    AnalysisResultDTO,
)
from src.domain.services.license_validator import LicenseValidator


class EntityToDTOMapper:
    """Maps from domain entities to application DTOs."""

    @staticmethod
    def vulnerability_to_dto(vuln: Vulnerability) -> VulnerabilityDTO:
        """Convert Vulnerability entity to DTO."""
        return VulnerabilityDTO(
            id=vuln.id,
            title=vuln.title,
            description=vuln.description,
            severity=vuln.severity.value,
            package_name=vuln.package_name,
            version=vuln.version,
            license=None,
        )

    @staticmethod
    def package_to_dto(
        package: Package,
        approval: ApprovalResult | None = None,
    ) -> PackageDTO:
        """Convert Package entity + optional ApprovalResult to DTO."""
        license_name = LicenseValidator.extract_from_package(package)

        return PackageDTO(
            name=package.name,
            version=package.version,
            latest_version=package.latest_version,
            license=license_name,
            upload_time=package.upload_time,
            summary=package.summary,
            home_page=package.home_page,
            author=package.author,
            author_email=package.author_email,
            maintainer=package.maintainer,
            maintainer_email=package.maintainer_email,
            keywords=package.keywords,
            classifiers=(package.classifiers or []).copy(),
            requires_dist=(package.requires_dist or []).copy(),
            project_urls=(package.project_urls or {}).copy(),
            github_url=package.github_url,
            dependencies=package.dependencies,
            is_maintained=package.is_maintained(),
            latest_upload_time=package.latest_upload_time,
            last_commit_date=package.last_commit_date,
            license_rejected=(
                package.license.is_rejected if package.license else False
            ),
            aprobada=(
                approval.status.value
                if approval
                else ApprovalStatus.UNDER_REVIEW.value
            ),
            motivo_rechazo=(
                approval.rejection_reason if approval else None
            ),
            dependencias_directas=(
                list(approval.direct_dependencies) if approval else []
            ),
            dependencias_transitivas=(
                list(approval.transitive_dependencies) if approval else []
            ),
            dependencias_rechazadas=(
                list(approval.rejected_dependencies) if approval else []
            ),
        )


class InterfaceMapper:
    """Maps domain entities to plain dicts for HTTP responses."""

    @staticmethod
    def analysis_result_to_dict(
        result: AnalysisResult,
    ) -> Dict[str, Any]:
        """Convert AnalysisResult entity to a JSON-ready dictionary."""
        return {
            "timestamp": result.timestamp.isoformat(),
            "vulnerabilities": [
                {
                    "id": v.id,
                    "title": v.title,
                    "description": v.description,
                    "severity": v.severity.value,
                    "package": v.package_name,
                    "version": v.version,
                    "is_high_severity": v.is_high_severity,
                }
                for v in result.vulnerabilities
            ],
            "packages": [
                {
                    "name": p.name,
                    "version": p.version,
                    "license": (
                        p.license.name if p.license else None
                    ),
                    "upload_time": (
                        p.upload_time.isoformat()
                        if p.upload_time
                        else None
                    ),
                    "summary": p.summary,
                    "home_page": p.home_page,
                    "author": p.author,
                    "is_maintained": p.is_maintained(),
                    "license_rejected": (
                        p.license.is_rejected if p.license else False
                    ),
                }
                for p in result.get_all_packages()
            ],
            "filtered_packages": [
                {
                    "name": p.name,
                    "version": p.version,
                    "is_maintained": p.is_maintained(),
                }
                for p in result.maintained_packages
            ],
            "summary": {
                "total_packages": len(result.get_all_packages()),
                "total_vulnerabilities": len(result.vulnerabilities),
                "maintained_packages": len(result.maintained_packages),
                "policy_applied": (
                    result.policy_applied.name
                    if result.policy_applied
                    else None
                ),
            },
        }
