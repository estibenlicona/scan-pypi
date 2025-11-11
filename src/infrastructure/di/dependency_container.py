"""
Dependency Injection Container - Infrastructure layer.

This module centralizes all dependency creation and injection following 
Clean Architecture principles. It's infrastructure-level concern that 
can be reused by any interface (CLI, HTTP, etc.).
"""

from __future__ import annotations

from src.domain.ports import (
    VulnerabilityscannerPort, MetadataProviderPort, DependencyResolverPort,
    CachePort, LoggerPort, ClockPort, ReportSinkPort
)
from src.infrastructure.adapters import (
    LoggerAdapter, SnykCLIAdapter, PyPIClientAdapter, CacheDiskAdapter, 
    PipGripAdapter, SystemClockAdapter, FileReportSinkAdapter
)
from src.infrastructure.config.settings import get_settings, Settings


class DependencyContainer:
    """
    Dependency Injection Container following Clean Architecture.
    
    Centralizes object creation and lifecycle management.
    Can be used by any interface layer (CLI, HTTP, testing).
    """
    
    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize container with configuration.
        
        Args:
            settings: Optional settings override (useful for testing)
        """
        self.settings = settings or get_settings()
        
        # Lazy initialization - objects created only when needed
        self._logger: LoggerPort | None = None
        self._cache: CachePort | None = None
        self._clock: ClockPort | None = None
        self._vulnerability_scanner: VulnerabilityscannerPort | None = None
        self._metadata_provider: MetadataProviderPort | None = None
        self._dependency_resolver: DependencyResolverPort | None = None
        self._report_sink: ReportSinkPort | None = None
    
    @property
    def logger(self) -> LoggerPort:
        """Get or create logger adapter."""
        if self._logger is None:
            self._logger = LoggerAdapter(
                self.settings.logging, 
                "pypi_scanner.infrastructure"
            )
        return self._logger
    
    @property
    def cache(self) -> CachePort:
        """Get or create cache adapter."""
        if self._cache is None:
            self._cache = CacheDiskAdapter(self.settings.cache, self.logger)
        return self._cache
    
    @property
    def clock(self) -> ClockPort:
        """Get or create clock adapter."""
        if self._clock is None:
            self._clock = SystemClockAdapter()
        return self._clock
    
    @property
    def vulnerability_scanner(self) -> VulnerabilityscannerPort:
        """Get or create vulnerability scanner adapter."""
        if self._vulnerability_scanner is None:
            self._vulnerability_scanner = SnykCLIAdapter(
                self.settings.snyk, 
                self.logger
            )
        return self._vulnerability_scanner
    
    @property
    def metadata_provider(self) -> MetadataProviderPort:
        """Get or create metadata provider adapter."""
        if self._metadata_provider is None:
            self._metadata_provider = PyPIClientAdapter(
                self.settings.api, 
                self.logger
            )
        return self._metadata_provider
    
    @property
    def dependency_resolver(self) -> DependencyResolverPort:
        """Get or create dependency resolver adapter."""
        if self._dependency_resolver is None:
            self._dependency_resolver = PipGripAdapter(
                logger=self.logger,
                cache=self.cache
            )
        return self._dependency_resolver
    
    @property
    def report_sink(self) -> ReportSinkPort:
        """Get or create report sink adapter."""
        if self._report_sink is None:
            self._report_sink = FileReportSinkAdapter(
                self.settings.report, 
                self.logger
            )
        return self._report_sink
    
    def close(self) -> None:
        """Clean up resources if needed."""
        # Close connections, flush caches, etc.
        if self._cache:
            # Assuming cache has a close method
            pass