"""
Application Use Cases - Orchestrate domain services and coordinate with external systems.
"""

from __future__ import annotations
import asyncio
from typing import List, Dict, Any

from src.application.dtos import AnalysisRequest, AnalysisResultDTO, PackageDTO, VulnerabilityDTO, ReportDTO
from src.domain.entities import (
    Package, DependencyGraph, Vulnerability,
    Policy, AnalysisResult, SeverityLevel
)
from src.domain.services import PolicyEngine, GraphBuilder, ReportBuilder
from src.domain.ports import (
    DependencyResolverPort, VulnerabilityscannerPort, MetadataProviderPort,
    CachePort, ReportSinkPort, LoggerPort
)
class AnalyzePackagesUseCase:
    """Use case for analyzing packages with dependencies and vulnerabilities."""
    
    def __init__(
        self,
        dependency_resolver: DependencyResolverPort,
        vulnerability_scanner: VulnerabilityscannerPort,
        metadata_provider: MetadataProviderPort,
        cache: CachePort,
        logger: LoggerPort
    ) -> None:
        self.dependency_resolver = dependency_resolver
        self.vulnerability_scanner = vulnerability_scanner
        self.metadata_provider = metadata_provider
        self.cache = cache
        self.logger = logger
    
    async def execute(self, request: AnalysisRequest) -> AnalysisResultDTO:
        """Execute the complete package analysis."""
        self.logger.info("Starting package analysis", libraries=request.libraries)
        
        try:
            # Step 1: Resolve dependencies
            dependency_graph = await self.dependency_resolver.resolve_dependencies(request.libraries)
            self.logger.info(f"Resolved {len(dependency_graph.get_all_packages())} packages")
            
            # Step 2: Scan vulnerabilities
            # We need to convert the graph to requirements format for scanning
            requirements_content = self._graph_to_requirements(dependency_graph)
            dep_data, vuln_data = await self.vulnerability_scanner.scan_vulnerabilities(
                requirements_content
            )
            
            # Step 3: Extract vulnerabilities
            vulnerabilities = self._extract_vulnerabilities(vuln_data)
            self.logger.info(f"Found {len(vulnerabilities)} vulnerabilities")
            
            # Step 4: Enrich packages with metadata (run in parallel)
            all_packages = dependency_graph.get_all_packages()
            enriched_packages = await asyncio.gather(
                *(self.metadata_provider.enrich_package_metadata(pkg) for pkg in all_packages)
            )
            
            self.logger.info(f"Enriched {len(enriched_packages)} packages with metadata")
            
            # Step 5: Apply business policies
            policy = Policy(
                name="default",
                description="Default analysis policy",
                maintainability_years_threshold=2,
                blocked_licenses=[],
                max_vulnerability_severity=None
            )
            
            policy_engine = PolicyEngine(policy)
            maintained_packages = policy_engine.filter_maintained_packages(enriched_packages)
            evaluated_vulns = policy_engine.evaluate_vulnerabilities(vulnerabilities)
            
            self.logger.info(f"Policy filtered to {len(maintained_packages)} maintained packages")
            
            # Step 6: Build result
            graph_builder = GraphBuilder()
            updated_graph = graph_builder.merge_package_data_into_graph(dependency_graph, enriched_packages)
            
            report_builder = ReportBuilder()
            result = report_builder.build_analysis_result(
                updated_graph, evaluated_vulns, maintained_packages, policy
            )
            
            # Convert to DTO
            return self._to_dto(result)
            
        except Exception as e:
            self.logger.error("Analysis failed", error=str(e))
            raise
    
    def _graph_to_requirements(self, graph: DependencyGraph) -> str:
        """Convert dependency graph to requirements.txt format."""
        lines = []
        for package in graph.get_all_packages():
            lines.append(f"{package.identifier.name}=={package.identifier.version}")
        return "\n".join(lines)
    
    def _extract_vulnerabilities(self, vuln_data: Dict[str, Any]) -> List[Vulnerability]:
        """Extract vulnerabilities from Snyk data."""
        vulnerabilities = []
        
        for vuln in vuln_data.get("vulnerabilities", []):
            try:
                severity_str = vuln.get("severity", "low").lower()
                severity = SeverityLevel.LOW  # default
                
                if severity_str == "medium":
                    severity = SeverityLevel.MEDIUM
                elif severity_str == "high":
                    severity = SeverityLevel.HIGH
                elif severity_str == "critical":
                    severity = SeverityLevel.CRITICAL
                
                vulnerability = Vulnerability(
                    id=vuln.get("id", ""),
                    title=vuln.get("title", ""),
                    description=vuln.get("description"),
                    severity=severity,
                    package_name=vuln.get("packageName", ""),
                    version=vuln.get("version", "")
                )
                vulnerabilities.append(vulnerability)
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Failed to parse vulnerability: {e}")
                continue
        
        return vulnerabilities
    
    def _to_dto(self, result: AnalysisResult) -> AnalysisResultDTO:
        """Convert domain result to DTO."""
        vulnerability_dtos = [
            VulnerabilityDTO(
                id=v.id,
                title=v.title,
                description=v.description,
                severity=v.severity.value,
                package_name=v.package_name,
                version=v.version,
                license=v.license.name if v.license else None
            )
            for v in result.vulnerabilities
        ]
        
        package_dtos = [self._package_to_dto(p) for p in result.get_all_packages()]
        maintained_dtos = [self._package_to_dto(p) for p in result.maintained_packages]
        
        return AnalysisResultDTO(
            timestamp=result.timestamp,
            vulnerabilities=vulnerability_dtos,
            packages=package_dtos,
            maintained_packages=maintained_dtos,
            policy_applied=result.policy_applied.name if result.policy_applied else None
        )
    
    def _package_to_dto(self, package: Package) -> PackageDTO:
        """Convert domain package to DTO."""
        return PackageDTO(
            name=package.identifier.name,
            version=package.identifier.version,
            license=package.license.name if package.license else None,
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
            github_license=package.github_license,
            dependencies=[str(dep) for dep in package.dependencies],
            is_maintained=package.is_maintained(),
            license_rejected=package.license.is_rejected if package.license else False
        )


class BuildConsolidatedReportUseCase:
    """Use case for building the final consolidated report."""
    
    def __init__(self, report_sink: ReportSinkPort, logger: LoggerPort) -> None:
        self.report_sink = report_sink
        self.logger = logger
    
    async def execute(self, analysis_result: AnalysisResultDTO) -> ReportDTO:
        """Build and optionally persist the consolidated report."""
        self.logger.info("Building consolidated report")
        
        # Convert DTOs to dictionaries for report format
        vulnerabilities = [self._vulnerability_to_dict(v) for v in analysis_result.vulnerabilities]
        packages = [self._package_to_dict(p) for p in analysis_result.packages]
        filtered_packages = [self._package_to_dict(p) for p in analysis_result.maintained_packages]
        
        report = ReportDTO(
            timestamp=analysis_result.timestamp.isoformat(),
            vulnerabilities=vulnerabilities,
            packages=packages,
            filtered_packages=filtered_packages,
            summary={
                "total_packages": len(packages),
                "total_vulnerabilities": len(vulnerabilities),
                "maintained_packages": len(filtered_packages),
                "policy_applied": analysis_result.policy_applied
            }
        )
        
        return report
    
    def _vulnerability_to_dict(self, vuln: VulnerabilityDTO) -> Dict[str, Any]:
        """Convert vulnerability DTO to dictionary."""
        return {
            "id": vuln.id,
            "title": vuln.title,
            "description": vuln.description,
            "severity": vuln.severity,
            "packageName": vuln.package_name,
            "version": vuln.version,
            "license": vuln.license
        }
    
    def _package_to_dict(self, pkg: PackageDTO) -> Dict[str, Any]:
        """Convert package DTO to dictionary."""
        return {
            "package": pkg.name,
            "version": pkg.version,
            "license": pkg.license,
            "upload_time": pkg.upload_time.isoformat() if pkg.upload_time else None,
            "summary": pkg.summary,
            "home_page": pkg.home_page,
            "author": pkg.author,
            "author_email": pkg.author_email,
            "maintainer": pkg.maintainer,
            "maintainer_email": pkg.maintainer_email,
            "keywords": pkg.keywords,
            "classifiers": pkg.classifiers,
            "requires_dist": pkg.requires_dist,
            "project_urls": pkg.project_urls,
            "github_url": pkg.github_url,
            "github_license": pkg.github_license,
            "dependencies": pkg.dependencies,
            "is_maintained": pkg.is_maintained,
            "license_rejected": pkg.license_rejected
        }


class PipelineOrchestrator:
    """Main orchestrator for the complete analysis pipeline."""
    
    def __init__(
        self,
        analyze_use_case: AnalyzePackagesUseCase,
        report_use_case: BuildConsolidatedReportUseCase,
        report_sink: ReportSinkPort,
        logger: LoggerPort
    ) -> None:
        self.analyze_use_case = analyze_use_case
        self.report_use_case = report_use_case
        self.report_sink = report_sink
        self.logger = logger
    
    async def run(self, request: AnalysisRequest) -> ReportDTO:
        """Run the complete analysis pipeline."""
        self.logger.info("Starting analysis pipeline", libraries=request.libraries)
        
        try:
            # Step 1: Analyze packages
            analysis_result = await self.analyze_use_case.execute(request)
            
            # Step 2: Build consolidated report
            report = await self.report_use_case.execute(analysis_result)

            # Step 3: Persist report using configured report sink (adapter accepts dataclass ReportDTO)
            try:
                saved_location = await self.report_sink.save_report(report)
                self.logger.info("Report generated successfully", location=saved_location)
            except Exception as e:
                # Non-fatal: log failure to persist but continue returning report
                self.logger.warning("Failed to persist report", error=str(e))

            return report
            
        except Exception as e:
            self.logger.error("Pipeline failed", error=str(e))
            raise