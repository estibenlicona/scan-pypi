"""
Application DTOs - Data Transfer Objects for application layer.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, TypedDict
from dataclasses import dataclass, field
from datetime import datetime
from src.domain.entities import DependencyInfo


# HTTP Request/Response DTOs - TypedDict for JSON payloads
class AnalysisRequestDTO(TypedDict):
    """HTTP Request DTO for package analysis."""
    libraries: List[str]
    policy_name: Optional[str]


# Alias for backward compatibility - TODO: Migrate to use AnalysisRequestDTO directly
@dataclass(frozen=True)
class AnalysisRequest:
    """
    Request for package analysis - Business object with validation.
    
    Organization is handled internally by security scanners (Snyk, Kiuwan, etc.)
    keeping domain clean from implementation details.
    """
    libraries: List[str]
    policy_name: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate request data."""
        if not self.libraries:
            raise ValueError("Libraries list cannot be empty")
        if any(not lib.strip() for lib in self.libraries):
            raise ValueError("Library names cannot be empty")


class VulnerabilityResponseDTO(TypedDict):
    """HTTP Response DTO for vulnerability data."""
    id: str
    title: str
    severity: str
    package: str
    version: str
    cvss: Optional[str]
    description: Optional[str]
    fixed_in: Optional[List[str]]


class PackageResponseDTO(TypedDict):
    """HTTP Response DTO for package data."""
    name: str
    version: str
    license: Optional[str]
    upload_time: Optional[str]  # ISO string for JSON
    summary: Optional[str]
    home_page: Optional[str]
    author: Optional[str]
    is_maintained: bool
    license_rejected: bool


class AnalysisResponseDTO(TypedDict):
    """HTTP Response DTO for complete analysis results."""
    timestamp: str
    vulnerabilities: List[VulnerabilityResponseDTO]
    packages: List[PackageResponseDTO]
    filtered_packages: List[PackageResponseDTO]
    summary: Dict[str, Any]


@dataclass(frozen=True)
class PackageDTO:
    """DTO for package information."""
    name: str
    version: str
    latest_version: Optional[str] = None
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
    project_urls: Dict[str, str] = field(default_factory=dict)
    github_url: Optional[str] = None
    github_license: Optional[str] = None
    dependencies: List[DependencyInfo] = field(default_factory=list)
    is_maintained: bool = False
    license_rejected: bool = False
    # Business rule fields (approval status tracking)
    aprobada: str = "En verificación"  # "Sí", "No", "En verificación"
    motivo_rechazo: Optional[str] = None  # Reason for rejection if aprobada="No"
    dependencias_directas: List[DependencyInfo] = field(default_factory=list)  # Direct dependencies
    dependencias_transitivas: List[DependencyInfo] = field(default_factory=list)  # Transitive/dev dependencies


@dataclass(frozen=True)
class VulnerabilityDTO:
    """DTO for vulnerability information."""
    id: str
    title: str
    description: Optional[str]
    severity: str
    package_name: str
    version: str
    license: Optional[str] = None


# ========================================
# Application/Domain DTOs - @dataclass for business objects
# ========================================

@dataclass(frozen=True)
class AnalysisResultDTO:
    """DTO for complete analysis results - Business object with behavior."""
    timestamp: datetime
    vulnerabilities: List[VulnerabilityDTO]
    packages: List[PackageDTO]
    maintained_packages: List[PackageDTO]
    policy_applied: Optional[str] = None


@dataclass(frozen=True)
class ReportDTO:
    """DTO for consolidated report - Business object with validation."""
    timestamp: str
    vulnerabilities: List[Dict[str, Any]]  # Will be mapped from VulnerabilityDTO
    packages: List[Dict[str, Any]]         # Will be mapped from PackageDTO
    filtered_packages: List[Dict[str, Any]]
    summary: Dict[str, Any] = field(default_factory=lambda: {})
    
    def __post_init__(self) -> None:
        """Validate report data."""
        if not self.timestamp:
            raise ValueError("Timestamp is required")