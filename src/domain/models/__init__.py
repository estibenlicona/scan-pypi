"""
Domain Models - Pure business objects with strict typing and validation.
"""

from __future__ import annotations
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from src.domain.entities import SeverityLevel, DependencyInfo


@dataclass(frozen=True)
class AnalysisRequest:
    """Domain model for package analysis requests."""
    libraries: List[str]
    organization: Optional[str] = None
    policy_name: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Strict business validation."""
        if not self.libraries:
            raise ValueError("Libraries list cannot be empty")
        if any(not lib.strip() for lib in self.libraries):
            raise ValueError("Library names cannot be empty")
        if any(" " in lib for lib in self.libraries):
            raise ValueError("Library names cannot contain spaces")


@dataclass(frozen=True) 
class PackageInfo:
    """Domain model for package information with approval status and dependency tracking."""
    name: str
    version: str
    latest_version: Optional[str] = None  # Latest version available on PyPI
    license: Optional[str] = None
    upload_time: Optional[datetime] = None
    summary: Optional[str] = None
    home_page: Optional[str] = None
    author: Optional[str] = None
    author_email: Optional[str] = None
    maintainer: Optional[str] = None
    maintainer_email: Optional[str] = None
    keywords: Optional[str] = None
    classifiers: List[str] = field(default_factory=list)
    requires_dist: List[str] = field(default_factory=list)
    project_urls: dict[str, str] = field(default_factory=dict)
    github_url: Optional[str] = None
    dependencies: List[DependencyInfo] = field(default_factory=list)
    is_maintained: bool = False
    license_rejected: bool = False
    # Business rule fields (calculated by domain services)
    aprobada: str = "En verificación"  # "Sí", "No", "En verificación"
    motivo_rechazo: Optional[str] = None  # Reason for rejection if aprobada="No"
    dependencias_rechazadas: List[str] = field(default_factory=list)  # Dependencies that caused rejection
    dependencias_directas: List[DependencyInfo] = field(default_factory=list)  # Direct dependencies
    dependencias_transitivas: List[DependencyInfo] = field(default_factory=list)  # Transitive/dev dependencies
    
    def __post_init__(self) -> None:
        """Strict business validation."""
        if not self.name or not self.name.strip():
            raise ValueError("Package name is required")
        if not self.version or not self.version.strip():
            raise ValueError("Package version is required")


@dataclass(frozen=True)
class VulnerabilityInfo:
    """Domain model for vulnerability information."""
    id: str
    title: str
    description: Optional[str]
    severity: SeverityLevel
    package_name: str
    version: str
    cvss: Optional[str] = None
    fixed_in: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Strict business validation."""
        if not self.id or not self.id.strip():
            raise ValueError("Vulnerability ID is required")
        if not self.title or not self.title.strip():
            raise ValueError("Vulnerability title is required")
        if not self.package_name or not self.package_name.strip():
            raise ValueError("Package name is required")
        if not self.version or not self.version.strip():
            raise ValueError("Package version is required")
    
    @property
    def is_high_severity(self) -> bool:
        """Business logic: Check if vulnerability is high severity."""
        return self.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
    
    def affects_version(self, version: str) -> bool:
        """Business logic: Check if vulnerability affects given version.
        
        Handles version comparison logic. The version field in VulnerabilityInfo
        can be stored in different formats depending on the vulnerability source:
        - Exact version: "2.32.1" matches "2.32.1"
        - Wildcard/range: "*" matches any version
        - Version range indicators (handled by OSV integration)
        
        For simplicity, we do direct version matching. If OSV provides range info,
        it should be reflected in the version field during vulnerability parsing.
        """
        if self.version == "*" or version == "*":
            # Wildcard means all versions are affected (for this vulnerability)
            return True
        
        # Direct version comparison
        return self.version == version


@dataclass(frozen=True)
class AnalysisResult:
    """Domain model for complete analysis results."""
    timestamp: datetime
    vulnerabilities: List[VulnerabilityInfo]
    packages: List[PackageInfo]
    maintained_packages: List[PackageInfo] 
    policy_applied: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Strict business validation."""
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")
    
    @property
    def total_packages(self) -> int:
        """Business logic: Total packages analyzed."""
        return len(self.packages)
    
    @property
    def high_severity_vulnerabilities(self) -> List[VulnerabilityInfo]:
        """Business logic: Filter high severity vulnerabilities."""
        return [v for v in self.vulnerabilities if v.is_high_severity]
    
    @property
    def vulnerable_packages(self) -> set[str]:
        """Business logic: Get unique set of vulnerable package names."""
        return {v.package_name for v in self.vulnerabilities}


@dataclass(frozen=True)
class ConsolidatedReport:
    """Domain model for consolidated report with business validation."""
    timestamp: str
    analysis_result: AnalysisResult
    
    def __post_init__(self) -> None:
        """Strict business validation."""
        if not self.timestamp:
            raise ValueError("Report timestamp is required")
        if not self.analysis_result:
            raise ValueError("Analysis result is required")
    
    @property
    def summary_stats(self) -> dict[str, int]:
        """Business logic: Generate summary statistics."""
        return {
            "total_packages": self.analysis_result.total_packages,
            "total_vulnerabilities": len(self.analysis_result.vulnerabilities),
            "high_severity_vulnerabilities": len(self.analysis_result.high_severity_vulnerabilities),
            "vulnerable_packages": len(self.analysis_result.vulnerable_packages),
            "maintained_packages": len(self.analysis_result.maintained_packages)
        }