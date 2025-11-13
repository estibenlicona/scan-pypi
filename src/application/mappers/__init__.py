"""
Application Mappers - Convert between domain models and DTOs.
Bridge between strict domain objects and flexible interface objects.
"""

from typing import Any, Dict, List
from datetime import datetime

# Domain models (strict typing)
from src.domain.models import (
    AnalysisRequest as DomainAnalysisRequest,
    PackageInfo as DomainPackageInfo,
    VulnerabilityInfo as DomainVulnerabilityInfo,
    AnalysisResult as DomainAnalysisResult,
    ConsolidatedReport as DomainConsolidatedReport
)

# Application DTOs (flexible typing)  
from src.application.dtos import (
    AnalysisRequest as DTOAnalysisRequest,
    PackageDTO,
    VulnerabilityDTO,
    AnalysisResultDTO,
    ReportDTO
)


class DomainToDTOMapper:
    """Maps from strict domain models to flexible DTOs."""
    
    @staticmethod
    def analysis_request_to_dto(domain_request: DomainAnalysisRequest) -> DTOAnalysisRequest:
        """Convert domain AnalysisRequest to DTO."""
        return DTOAnalysisRequest(
            libraries=domain_request.libraries,
            policy_name=domain_request.policy_name
        )
    
    @staticmethod
    def package_info_to_dto(domain_package: DomainPackageInfo) -> PackageDTO:
        """Convert domain PackageInfo to DTO."""
        return PackageDTO(
            name=domain_package.name,
            version=domain_package.version,
            license=domain_package.license,
            upload_time=domain_package.upload_time,
            summary=domain_package.summary,
            home_page=domain_package.home_page,
            author=domain_package.author,
            author_email=domain_package.author_email,
            maintainer=domain_package.maintainer,
            maintainer_email=domain_package.maintainer_email,
            keywords=domain_package.keywords,
            classifiers=domain_package.classifiers,
            requires_dist=domain_package.requires_dist,
            project_urls=domain_package.project_urls,
            github_url=domain_package.github_url,
            github_license=domain_package.github_license,
            dependencies=domain_package.dependencies,
            is_maintained=domain_package.is_maintained,
            license_rejected=domain_package.license_rejected,
            aprobada=domain_package.aprobada,
            motivo_rechazo=domain_package.motivo_rechazo,
            dependencias_directas=domain_package.dependencias_directas,
            dependencias_transitivas=domain_package.dependencias_transitivas
        )
    
    @staticmethod
    def vulnerability_info_to_dto(domain_vuln: DomainVulnerabilityInfo) -> VulnerabilityDTO:
        """Convert domain VulnerabilityInfo to DTO."""
        return VulnerabilityDTO(
            id=domain_vuln.id,
            title=domain_vuln.title,
            description=domain_vuln.description,
            severity=domain_vuln.severity.value,  # Convert enum to string
            package_name=domain_vuln.package_name,
            version=domain_vuln.version,
            license=None  # Not available in domain model
        )


class DTOToDomainMapper:
    """Maps from flexible DTOs to strict domain models."""
    
    @staticmethod
    def dto_to_analysis_request(dto_request: DTOAnalysisRequest) -> DomainAnalysisRequest:
        """Convert DTO AnalysisRequest to domain model."""
        return DomainAnalysisRequest(
            libraries=dto_request.libraries,
            policy_name=dto_request.policy_name
        )


class InterfaceMapper:
    """Maps between domain models and dynamic interface objects."""
    
    @staticmethod
    def domain_analysis_result_to_dict(domain_result: DomainAnalysisResult) -> Dict[str, Any]:
        """Convert domain AnalysisResult to flexible dict for HTTP response."""
        return {
            "timestamp": domain_result.timestamp.isoformat(),
            "vulnerabilities": [
                {
                    "id": v.id,
                    "title": v.title,
                    "description": v.description,
                    "severity": v.severity.value,
                    "package": v.package_name,
                    "version": v.version,
                    "cvss": v.cvss,
                    "fixed_in": v.fixed_in,
                    "is_high_severity": v.is_high_severity  # Include business logic
                }
                for v in domain_result.vulnerabilities
            ],
            "packages": [
                {
                    "name": p.name,
                    "version": p.version,
                    "license": p.license,
                    "upload_time": p.upload_time.isoformat() if p.upload_time else None,
                    "summary": p.summary,
                    "home_page": p.home_page,
                    "author": p.author,
                    "is_maintained": p.is_maintained,
                    "license_rejected": p.license_rejected,
                    "classifiers": p.classifiers,
                    "dependencies": p.dependencies
                }
                for p in domain_result.packages
            ],
            "filtered_packages": [
                {
                    "name": p.name,
                    "version": p.version,
                    "license": p.license,
                    "is_maintained": p.is_maintained,
                    "license_rejected": p.license_rejected
                }
                for p in domain_result.maintained_packages
            ],
            "summary": {
                "total_packages": domain_result.total_packages,
                "total_vulnerabilities": len(domain_result.vulnerabilities),
                "high_severity_vulnerabilities": len(domain_result.high_severity_vulnerabilities),
                "vulnerable_packages": len(domain_result.vulnerable_packages),
                "maintained_packages": len(domain_result.maintained_packages),
                "policy_applied": domain_result.policy_applied
            }
        }
    
    @staticmethod  
    def dict_to_domain_analysis_request(request_dict: Dict[str, Any]) -> DomainAnalysisRequest:
        """Convert flexible dict to strict domain AnalysisRequest."""
        return DomainAnalysisRequest(
            libraries=request_dict.get("libraries", []),
            organization=request_dict.get("organization"),
            policy_name=request_dict.get("policy_name")
        )