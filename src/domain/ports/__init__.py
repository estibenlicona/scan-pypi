"""
Domain ports - Interfaces that define contracts for external dependencies.
"""

from __future__ import annotations
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities import AnalysisResult
    from src.application.dtos import ReportDTO
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from src.domain.entities import (
    Package, PackageIdentifier, DependencyGraph, 
    AnalysisResult
)


class PackageFetcherPort(ABC):
    """Port for fetching basic package metadata."""
    
    @abstractmethod
    async def fetch_package(self, identifier: PackageIdentifier) -> Optional[Package]:
        """Fetch basic package information."""
        pass


class DependencyResolverPort(ABC):
    """Port for resolving package dependencies."""
    
    @abstractmethod
    async def resolve_dependencies(self, packages: List[str]) -> DependencyGraph:
        """Resolve dependencies for a list of package requirements."""
        pass


class VulnerabilityscannerPort(ABC):
    """Port for scanning vulnerabilities using external tools."""
    
    @abstractmethod
    async def scan_vulnerabilities(self, requirements_content: str) -> Dict[str, Any]:
        """
        Scan vulnerabilities and return vulnerabilities data.
        
        Organization and other tool-specific configuration is handled internally
        by the adapter implementation, keeping the domain clean.
        """
        pass


class MetadataProviderPort(ABC):
    """Port for enriching packages with external metadata (PyPI, GitHub, etc)."""
    
    @abstractmethod
    async def enrich_package_metadata(self, package: Package) -> Package:
        """Enrich package with additional metadata from external sources."""
        pass
    
    @abstractmethod
    async def fetch_latest_version(self, package_name: str) -> Optional[str]:
        """Fetch the latest version of a package from PyPI."""
        pass


class CachePort(ABC):
    """Port for caching results to improve performance."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    def generate_key(self, *args: Any) -> str:
        """Generate deterministic cache key from arguments."""
        pass


class ReportSinkPort(ABC):
    """Port for persisting analysis reports."""
    
    @abstractmethod
    async def save_report(self, result: Union[AnalysisResult, ReportDTO], format_type: str = "json") -> str:
        """Save analysis result or report to storage and return location.
        
        Accepts either an AnalysisResult (domain entity) or a ReportDTO (application DTO).
        """
        pass
    
    @abstractmethod
    async def load_report(self, location: str) -> Optional[AnalysisResult]:
        """Load analysis result from storage."""
        pass


class LoggerPort(ABC):
    """Port for structured logging."""
    
    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        pass
    
    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        pass
    
    @abstractmethod
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        pass


class ClockPort(ABC):
    """Port for time operations (useful for testing)."""
    
    @abstractmethod
    def now(self) -> datetime:
        """Get current datetime."""
        pass