"""
Domain entities - Pure business objects without external dependencies.
"""

from __future__ import annotations
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum


class SeverityLevel(Enum):
    """Severity levels for vulnerabilities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LicenseType(Enum):
    """Common license types."""
    MIT = "MIT"
    APACHE_2_0 = "Apache-2.0"
    BSD_3_CLAUSE = "BSD-3-Clause"
    GPL_3_0 = "GPL-3.0"
    LGPL_2_1 = "LGPL-2.1"
    MPL_2_0 = "MPL-2.0"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class PackageIdentifier:
    """Value object representing a package name and version."""
    name: str
    version: str
    
    def __post_init__(self) -> None:
        if not self.name or not self.version:
            raise ValueError("Package name and version cannot be empty")
    
    def __str__(self) -> str:
        return f"{self.name}@{self.version}"


@dataclass(frozen=True)
class DependencyInfo:
    """Value object representing a package dependency with version information."""
    name: str
    version: str  # Exact version required
    latest_version: Optional[str] = None  # Latest version available on PyPI


@dataclass(frozen=True)
class License:
    """Value object representing a software license."""
    name: Optional[str] = None
    license_type: Optional[LicenseType] = None
    url: Optional[str] = None
    is_rejected: bool = False


@dataclass(frozen=True)
class Vulnerability:
    """Domain entity representing a security vulnerability."""
    id: str
    title: str
    description: Optional[str]
    severity: SeverityLevel
    package_name: str
    version: str
    license: Optional[License] = None
    
    def __post_init__(self) -> None:
        # Only require ID and package_name/version to be non-empty
        # Title and description can be generated/placeholder values
        if not self.id or not self.package_name or not self.version:
            raise ValueError("Required vulnerability fields (id, package_name, version) cannot be empty")


@dataclass
class Package:
    """Domain entity representing a software package."""
    identifier: PackageIdentifier
    license: Optional[License] = None
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
    latest_version: Optional[str] = None  # Latest version available on PyPI
    dependencies: List[DependencyInfo] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        pass  # Fields are initialized by field(default_factory)
    
    @property
    def name(self) -> str:
        """Get package name."""
        return self.identifier.name
    
    @property
    def version(self) -> str:
        """Get package version."""
        return self.identifier.version
    
    def is_maintained(self, years_threshold: int = 2) -> bool:
        """Check if package is maintained based on upload time."""
        if not self.upload_time:
            return False
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=years_threshold * 365)
        
        # Ensure upload_time has timezone info
        upload_time = self.upload_time
        if upload_time.tzinfo is None:
            upload_time = upload_time.replace(tzinfo=timezone.utc)
        
        return upload_time >= cutoff_date


@dataclass
class DependencyNode:
    """Domain entity representing a node in the dependency tree."""
    package: Package
    dependencies: List[DependencyNode] = field(default_factory=list)
    
    def add_dependency(self, dependency: DependencyNode) -> None:
        """Add a dependency to this node."""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)
    
    def get_all_packages(self) -> List[Package]:
        """Get all packages in the dependency tree recursively."""
        packages = [self.package]
        for dep in self.dependencies:
            packages.extend(dep.get_all_packages())
        return packages


@dataclass
class DependencyGraph:
    """Domain entity representing the complete dependency graph."""
    root_packages: List[DependencyNode]
    
    def __post_init__(self) -> None:
        if not self.root_packages:
            self.root_packages = []
    
    def get_all_packages(self) -> List[Package]:
        """Get all packages in the entire dependency graph (deduplicated by name@version)."""
        seen: Dict[str, Package] = {}
        for root in self.root_packages:
            for package in root.get_all_packages():
                key = f"{package.identifier.name}@{package.identifier.version}"
                if key not in seen:
                    seen[key] = package
        return list(seen.values())
    
    def find_package(self, identifier: PackageIdentifier) -> Optional[Package]:
        """Find a specific package in the graph."""
        all_packages = self.get_all_packages()
        for package in all_packages:
            if package.identifier == identifier:
                return package
        return None


@dataclass
class Policy:
    """Domain entity representing business policy for package analysis."""
    name: str
    description: str
    maintainability_years_threshold: int = 2
    blocked_licenses: List[str] = field(default_factory=list)
    max_vulnerability_severity: Optional[SeverityLevel] = None


@dataclass
class AnalysisResult:
    """Domain entity representing the complete analysis result."""
    dependency_graph: DependencyGraph
    vulnerabilities: List[Vulnerability]
    maintained_packages: List[Package]
    timestamp: datetime
    policy_applied: Optional[Policy] = None
    
    def get_all_packages(self) -> List[Package]:
        """Get all analyzed packages."""
        return self.dependency_graph.get_all_packages()
    
    def get_vulnerabilities_for_package(self, package_identifier: PackageIdentifier) -> List[Vulnerability]:
        """Get vulnerabilities for a specific package."""
        return [
            vuln for vuln in self.vulnerabilities
            if vuln.package_name == package_identifier.name and vuln.version == package_identifier.version
        ]