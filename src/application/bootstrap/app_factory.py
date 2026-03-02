"""
Application Factory - Bootstrap layer for creating configured application instances.

This module provides factory functions to create fully configured application 
services using dependency injection. Follows Clean Architecture by keeping 
the application layer pure and delegating infrastructure concerns.
"""

from __future__ import annotations

from src.application.use_cases import AnalyzePackagesUseCase, BuildConsolidatedReportUseCase, PipelineOrchestrator
from src.domain.entities import Policy, SeverityLevel
from src.infrastructure.di.dependency_container import DependencyContainer


def _build_policy_from_settings(container: DependencyContainer) -> Policy:
    """Convert infrastructure PolicySettings into a domain Policy entity."""
    ps = container.settings.policy
    max_sev = None
    if ps.max_vulnerability_severity:
        try:
            max_sev = SeverityLevel(
                ps.max_vulnerability_severity.lower()
            )
        except (ValueError, AttributeError):
            max_sev = None
    return Policy(
        name="default",
        description="Default analysis policy",
        maintainability_years_threshold=ps.maintainability_years_threshold,
        blocked_licenses=ps.blocked_licenses,
        max_vulnerability_severity=max_sev,
    )


class ApplicationFactory:
    """
    Factory for creating configured application services.
    
    This class encapsulates the complexity of wiring together use cases,
    orchestrators, and dependencies following Clean Architecture principles.
    """
    
    def __init__(self, container: DependencyContainer) -> None:
        """
        Initialize factory with dependency container.
        
        Args:
            container: Configured dependency injection container
        """
        self.container = container
    
    def create_analyze_packages_use_case(self) -> AnalyzePackagesUseCase:
        """
        Create configured package analysis use case.
        
        Returns:
            Fully configured AnalyzePackagesUseCase
        """
        return AnalyzePackagesUseCase(
            dependency_resolver=self.container.dependency_resolver,
            vulnerability_scanner=self.container.vulnerability_scanner,
            metadata_provider=self.container.metadata_provider,
            cache=self.container.cache,
            logger=self.container.logger,
            policy=_build_policy_from_settings(self.container),
        )
    
    def create_report_use_case(self) -> BuildConsolidatedReportUseCase:
        """
        Create configured report building use case.
        
        Returns:
            Fully configured BuildConsolidatedReportUseCase
        """
        return BuildConsolidatedReportUseCase(
            report_sink=self.container.report_sink,
            logger=self.container.logger
        )
    
    def create_pipeline_orchestrator(self) -> PipelineOrchestrator:
        """
        Create configured pipeline orchestrator.
        
        This is the main entry point for the complete analysis workflow.
        
        Returns:
            Fully configured PipelineOrchestrator
        """
        analyze_use_case = self.create_analyze_packages_use_case()
        report_use_case = self.create_report_use_case()
        
        return PipelineOrchestrator(
            analyze_use_case=analyze_use_case,
            report_use_case=report_use_case,
            report_sink=self.container.report_sink,
            logger=self.container.logger
        )

    @classmethod
    def create_application(cls) -> tuple[PipelineOrchestrator, DependencyContainer]:
        """
        Class method to create a fully configured application.
        
        Single Responsibility: Complete application bootstrap.
        This is the main entry point for interface layers.
        
        Returns:
            Tuple of (configured_orchestrator, dependency_container)
            
        Example:
            orchestrator, container = ApplicationFactory.create_application()
            try:
                result = await orchestrator.run(request)
            finally:
                container.close()  # Clean up resources
        """
        container = DependencyContainer()
        factory = cls(container)
        orchestrator = factory.create_pipeline_orchestrator()
        
        return orchestrator, container