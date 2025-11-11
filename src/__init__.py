"""
Main package initialization for hexagonal architecture.
"""

# Package version
__version__ = "2.0.0"

# Make key classes available at package level
from .domain.entities import Package, PackageIdentifier, DependencyGraph, Vulnerability
from .application.dtos import AnalysisRequest, AnalysisResultDTO
from .infrastructure.config.settings import get_settings

__all__ = [
    "Package",
    "PackageIdentifier", 
    "DependencyGraph",
    "Vulnerability",
    "AnalysisRequest",
    "AnalysisResultDTO",
    "get_settings"
]