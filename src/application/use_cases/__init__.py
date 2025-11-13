"""
Application Use Cases - Orchestrate domain services and coordinate with external systems.
"""

from __future__ import annotations
import asyncio
import re
from typing import List, Dict, Any

from src.application.dtos import AnalysisRequest, AnalysisResultDTO, PackageDTO, VulnerabilityDTO, ReportDTO
from src.domain.entities import DependencyInfo
from src.domain.entities import (
    Package, DependencyGraph, Vulnerability, DependencyNode,
    Policy, AnalysisResult, SeverityLevel
)
from src.domain.services import PolicyEngine, GraphBuilder, ReportBuilder
from src.domain.services.approval_engine import ApprovalEngine
from src.domain.models import PackageInfo, VulnerabilityInfo
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
        self.approval_map = {}  # Store approval info for use in DTOs
        self._last_result: AnalysisResult | None = None  # Keep last domain result
    
    async def execute(self, request: AnalysisRequest) -> AnalysisResultDTO:
        """Execute the complete package analysis."""
        self.logger.info("Starting package analysis", libraries=request.libraries)
        
        try:
            # Step 1: Resolve dependencies
            dependency_graph = await self.dependency_resolver.resolve_dependencies(request.libraries)
            self.logger.info(f"Resolved {len(dependency_graph.get_all_packages())} packages")
            
            # Extract dependency map from the graph BEFORE enrichment
            # (the graph structure contains the real dependency relationships)
            dependencies_map = self._extract_dependencies_map_from_graph(dependency_graph)
            self.logger.debug(f"Built dependencies map with {len(dependencies_map)} packages")
            
            # Step 2: Scan vulnerabilities
            # We need to convert the graph to requirements format for scanning
            requirements_content = self._graph_to_requirements(dependency_graph)
            vuln_data = await self.vulnerability_scanner.scan_vulnerabilities(
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
            
            # Step 5: Apply approval engine business rules
            # Convert Vulnerability entities to VulnerabilityInfo domain models
            vulnerability_infos: List[VulnerabilityInfo] = []
            for vuln in vulnerabilities:
                vuln_info = VulnerabilityInfo(
                    id=vuln.id,
                    title=vuln.title,
                    description=vuln.description,
                    severity=vuln.severity,
                    package_name=vuln.package_name,
                    version=vuln.version,
                    cvss=None,
                    fixed_in=[]
                )
                vulnerability_infos.append(vuln_info)
            
            # Convert enriched packages to PackageInfo for approval engine
            package_info_list: List[PackageInfo] = []
            for pkg in enriched_packages:
                # Get dependencies from the map we built from the graph
                pkg_deps = dependencies_map.get(pkg.identifier.name, [])
                
                # Extract license using proper cascading: license → classifiers → github_license → None
                extracted_license = self._extract_license_cascade(pkg)
                
                package_info = PackageInfo(
                    name=pkg.identifier.name,
                    version=pkg.identifier.version,
                    latest_version=pkg.latest_version,
                    license=extracted_license,
                    upload_time=pkg.upload_time,
                    summary=pkg.summary,
                    home_page=pkg.home_page,
                    author=pkg.author,
                    author_email=pkg.author_email,
                    maintainer=pkg.maintainer,
                    maintainer_email=pkg.maintainer_email,
                    keywords=pkg.keywords,
                    classifiers=pkg.classifiers.copy() if pkg.classifiers else [],
                    requires_dist=pkg.requires_dist.copy() if pkg.requires_dist else [],
                    project_urls=pkg.project_urls.copy() if pkg.project_urls else {},
                    github_url=pkg.github_url,
                    dependencies=self._convert_dep_strings_to_dependency_info(pkg_deps),
                    is_maintained=pkg.is_maintained(),
                    license_rejected=pkg.license.is_rejected if pkg.license else False
                )
                package_info_list.append(package_info)
            
            # Apply approval rules using domain service
            approval_engine = ApprovalEngine()
            approved_packages_info = approval_engine.evaluate_all_packages(
                package_info_list,
                vulnerability_infos,
                dependencies_map
            )
            
            self.logger.info(f"Approval engine evaluated {len(approved_packages_info)} packages")
            
            # Step 5b: Enrich dependencies with latest versions from PyPI
            enriched_approved_packages = await self._enrich_dependencies_with_latest_version(
                approved_packages_info
            )
            self.logger.info("Enriched dependencies with latest version information")
            
            # Create a mapping of package name to approval info for quick lookup
            self.approval_map = {pkg.name: pkg for pkg in enriched_approved_packages}
            
            # Step 6: Apply business policies
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
            
            # Store domain result and convert to DTO
            self._last_result = result
            return self._to_dto(result)
            return self._to_dto(result)
            
        except Exception as e:
            self.logger.error("Analysis failed", error=str(e))
            raise
    
    def _extract_license_cascade(self, pkg: Package) -> str | None:
        """
        Extract license using 3-level cascade:
        1. pkg.license.name (from PyPI 'license' field)
        2. Classifiers (License :: classifiers)
        3. None if not found anywhere
        """
        # Level 1: Direct license field
        if pkg.license and pkg.license.name:
            return pkg.license.name
        
        # Level 2: Classifiers - look for License :: ... lines
        if pkg.classifiers:
            license_classifiers = [
                c for c in pkg.classifiers 
                if c.startswith("License ::")
            ]
            if license_classifiers:
                # Extract the license name from first matching classifier
                # Format: "License :: OSI Approved :: MIT License"
                classifier = license_classifiers[0]
                parts = classifier.split(" :: ")
                if len(parts) >= 3:
                    return parts[-1]
        
        # Level 3: Not found
        self.logger.debug(
            f"License not found in cascade for {pkg.identifier.name}@{pkg.identifier.version}",
            has_license_obj=pkg.license is not None,
            has_classifiers=len(pkg.classifiers or []) > 0
        )
        return None
    
    def _extract_dependencies_map_from_graph(
        self, graph: DependencyGraph
    ) -> Dict[str, List[str]]:
        """
        Extract dependency map from the dependency graph structure.
        
        The DependencyGraph contains the true dependency relationships in its
        DependencyNode tree. This method traverses that tree to build a map
        of package name -> list of direct dependency names with versions.
        
        Args:
            graph: The DependencyGraph with root_packages and nested dependencies
            
        Returns:
            Dictionary mapping package name to list of direct dependencies (format: "name==version")
        """
        dependencies_map: Dict[str, List[str]] = {}
        visited: set = set()
        
        def traverse_node(node: DependencyNode) -> None:
            """Recursively traverse dependency tree."""
            pkg_name = node.package.identifier.name
            
            # Avoid cycles
            if pkg_name in visited:
                return
            visited.add(pkg_name)
            
            # Get direct dependencies of this package with versions
            direct_deps = [
                f"{dep.package.identifier.name}=={dep.package.identifier.version}"
                for dep in node.dependencies
            ]
            dependencies_map[pkg_name] = direct_deps
            
            # Recursively process sub-dependencies
            for dep_node in node.dependencies:
                traverse_node(dep_node)
        
        # Traverse from all root packages
        for root_node in graph.root_packages:
            traverse_node(root_node)
        
        return dependencies_map
    
    def _graph_to_requirements(self, graph: DependencyGraph) -> str:
        """Convert dependency graph to requirements.txt format."""
        lines = []
        for package in graph.get_all_packages():
            lines.append(f"{package.identifier.name}=={package.identifier.version}")
        return "\n".join(lines)
    
    def _extract_vulnerabilities(self, vuln_data: Dict[str, Any]) -> List[Vulnerability]:
        """Extract vulnerabilities from OSV.dev data.
        
        OSV format:
        {
            "vulnerabilities": {
                "package@version": [
                    {
                        "id": "GHSA-...",
                        "summary": "...",
                        "severity": [{"type": "CVSS_V3", "score": "..."}],
                        "database_specific": {"severity": "MODERATE"}
                    }
                ]
            }
        }
        """
        vulnerabilities = []
        
        vulnerabilities_map = vuln_data.get("vulnerabilities", {})
        
        # OSV returns vulnerabilities grouped by package@version
        for package_version_key, vulns_list in vulnerabilities_map.items():
            # Parse package@version format
            parts = package_version_key.split("@")
            if len(parts) != 2:
                continue
            
            package_name, version = parts[0], parts[1]
            
            for vuln in vulns_list:
                try:
                    # Extract severity from OSV format
                    severity_str = vuln.get("database_specific", {}).get("severity", "low").lower()
                    severity = SeverityLevel.LOW  # default
                    
                    if severity_str == "medium":
                        severity = SeverityLevel.MEDIUM
                    elif severity_str == "high":
                        severity = SeverityLevel.HIGH
                    elif severity_str == "critical":
                        severity = SeverityLevel.CRITICAL
                    
                    vulnerability = Vulnerability(
                        id=vuln.get("id", ""),
                        title=vuln.get("summary", ""),
                        description=vuln.get("details"),
                        severity=severity,
                        package_name=package_name,
                        version=version
                    )
                    vulnerabilities.append(vulnerability)
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"Failed to parse OSV vulnerability: {e}")
                    continue
        
        return vulnerabilities
    
    def _convert_dep_strings_to_dependency_info(
        self, dep_strings: List[str]
    ) -> List[DependencyInfo]:
        """
        Convert dependency strings (format: "name==version") to DependencyInfo objects.
        
        Args:
            dep_strings: List of dependency strings in format "name==version"
            
        Returns:
            List of DependencyInfo objects with version extracted and latest_version set to None
        """
        dependency_infos: List[DependencyInfo] = []
        
        for dep_str in dep_strings:
            # Parse "name==version" format
            if "==" in dep_str:
                name, version = dep_str.split("==", 1)
                dependency_infos.append(
                    DependencyInfo(
                        name=name.strip(),
                        version=version.strip(),
                        latest_version=None  # Will be enriched later if needed
                    )
                )
            else:
                # If no version specified, use the string as name
                dependency_infos.append(
                    DependencyInfo(
                        name=dep_str.strip(),
                        version="*",  # Unknown version
                        latest_version=None
                    )
                )
        
        return dependency_infos
    
    async def _enrich_dependencies_with_latest_version(
        self, 
        packages: List[PackageInfo]
    ) -> List[PackageInfo]:
        """
        Enrich all dependency DependencyInfo objects with latest_version from PyPI.
        
        Args:
            packages: List of PackageInfo objects with dependencies
            
        Returns:
            List of PackageInfo objects with enriched dependencies
        """
        enriched_packages: List[PackageInfo] = []
        
        for pkg in packages:
            # Enrich each list of dependencies
            enriched_deps = await self._enrich_dep_list(pkg.dependencies)
            enriched_direct = await self._enrich_dep_list(pkg.dependencias_directas)
            enriched_transitive = await self._enrich_dep_list(pkg.dependencias_transitivas)
            
            # Create new PackageInfo with enriched dependencies (using dataclass evolution)
            enriched_pkg = PackageInfo(
                name=pkg.name,
                version=pkg.version,
                latest_version=pkg.latest_version,
                license=pkg.license,
                upload_time=pkg.upload_time,
                summary=pkg.summary,
                home_page=pkg.home_page,
                author=pkg.author,
                author_email=pkg.author_email,
                maintainer=pkg.maintainer,
                maintainer_email=pkg.maintainer_email,
                keywords=pkg.keywords,
                classifiers=pkg.classifiers,
                requires_dist=pkg.requires_dist,
                project_urls=pkg.project_urls,
                github_url=pkg.github_url,
                dependencies=enriched_deps,
                is_maintained=pkg.is_maintained,
                license_rejected=pkg.license_rejected,
                aprobada=pkg.aprobada,
                motivo_rechazo=pkg.motivo_rechazo,
                dependencias_directas=enriched_direct,
                dependencias_transitivas=enriched_transitive,
                dependencias_rechazadas=pkg.dependencias_rechazadas
            )
            enriched_packages.append(enriched_pkg)
        
        return enriched_packages
    
    async def _enrich_dep_list(
        self,
        deps: List[DependencyInfo]
    ) -> List[DependencyInfo]:
        """
        Enrich a single list of dependencies with latest_version.
        
        Queries PyPI for each dependency's latest version.
        """
        enriched_deps: List[DependencyInfo] = []
        
        for dep in deps:
            try:
                # Fetch latest version from PyPI
                latest_ver = await self.metadata_provider.fetch_latest_version(dep.name)
                
                # Create new DependencyInfo with latest_version enriched
                enriched_dep = DependencyInfo(
                    name=dep.name,
                    version=dep.version,
                    latest_version=latest_ver
                )
                enriched_deps.append(enriched_dep)
            except Exception as e:
                self.logger.warning(f"Failed to enrich dependency {dep.name}: {e}")
                # Keep original if enrichment fails
                enriched_deps.append(dep)
        
        return enriched_deps
    
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
        """Convert domain package to DTO, enriched with approval info."""
        pkg_name = package.identifier.name
        
        # Get approval info if available
        approval_info = self.approval_map.get(pkg_name)
        
        aprobada = approval_info.aprobada if approval_info else "En verificación"
        motivo_rechazo = approval_info.motivo_rechazo if approval_info else None
        dependencias_directas = approval_info.dependencias_directas if approval_info else []
        dependencias_transitivas = approval_info.dependencias_transitivas if approval_info else []
        dependencias_rechazadas = approval_info.dependencias_rechazadas if approval_info else []
        
        return PackageDTO(
            name=package.identifier.name,
            version=package.identifier.version,
            latest_version=package.latest_version,
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
            dependencies=package.dependencies,  # Already List[DependencyInfo]
            is_maintained=package.is_maintained(),
            license_rejected=package.license.is_rejected if package.license else False,
            aprobada=aprobada,
            motivo_rechazo=motivo_rechazo,
            dependencias_directas=dependencias_directas,
            dependencias_transitivas=dependencias_transitivas,
            dependencias_rechazadas=dependencias_rechazadas,
        )
    
    def _package_info_to_dto(self, package_info: PackageInfo) -> PackageDTO:
        """Convert PackageInfo domain model to DTO."""
        # Transform license to short format
        short_license = self._short_license(
            package_info.license or "—"
        )
        
        return PackageDTO(
            name=package_info.name,
            version=package_info.version,
            latest_version=package_info.latest_version,
            license=short_license,
            upload_time=package_info.upload_time,
            summary=package_info.summary,
            home_page=package_info.home_page,
            author=package_info.author,
            author_email=package_info.author_email,
            maintainer=package_info.maintainer,
            maintainer_email=package_info.maintainer_email,
            keywords=package_info.keywords,
            classifiers=package_info.classifiers.copy(),
            requires_dist=package_info.requires_dist.copy(),
            project_urls=package_info.project_urls.copy(),
            github_url=package_info.github_url,
            dependencies=package_info.dependencies.copy(),
            is_maintained=package_info.is_maintained,
            license_rejected=package_info.license_rejected,
            aprobada=package_info.aprobada,
            motivo_rechazo=package_info.motivo_rechazo,
            dependencias_directas=package_info.dependencias_directas.copy(),
            dependencias_transitivas=package_info.dependencias_transitivas.copy(),
            dependencias_rechazadas=package_info.dependencias_rechazadas.copy(),
        )
    
    def _short_license(self, raw_license: str) -> str:
        """Transform raw license string to short, readable format using regex patterns.
        
        Handles both PyPI and GitHub license formats, standardizing to SPDX identifiers.
        Returns "—" for missing/invalid licenses.
        """
        # Handle None, empty, or dash
        if raw_license is None or not raw_license or raw_license == "—":
            return "—"
        
        if not isinstance(raw_license, str):
            return "—"
        
        # Clean up GitHub markdown/quotes noise
        text = raw_license.lower().strip()
        text = re.sub(r'["\\\']', '', text)  # Remove quotes and backslashes
        text = re.sub(r'\b(new|revised|or)\b', '', text)  # Remove noise words
        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        
        # License pattern mapping: (regex_pattern, spdx_identifier)
        license_patterns = [
            (r'\bmit\b(?!\w)', 'MIT'),
            (r'\bbsd[- ]?3', 'BSD-3-Clause'),
            (r'\bbsd[- ]?2', 'BSD-2-Clause'),
            (r'\bbsd\b', 'BSD'),
            (r'\bapache[- ]?2', 'Apache-2.0'),
            (r'\bapache\b', 'Apache'),
            (r'\bgpl[- ]?3', 'GPL-3.0'),
            (r'\bgpl[- ]?2', 'GPL-2.0'),
            (r'\bgpl\b', 'GPL'),
            (r'\blgpl\b', 'LGPL'),
            (r'\bmpl\b', 'MPL'),
            (r'\bepl\b', 'EPL'),
            (r'\b(unlicense|public\s+domain)\b', 'Public Domain'),
            (r'\b(proprietary|all\s+rights\s+reserved)\b', 'Proprietary'),
        ]
        
        # Try pattern matching first
        for pattern, identifier in license_patterns:
            if re.search(pattern, text):
                return identifier
        
        # Fallback: try to extract SPDX identifier from first line
        first_line = next((ln.strip() for ln in raw_license.splitlines() if ln.strip()), raw_license)
        spdx_match = re.match(r'^([A-Za-z0-9.+\-]+(?:\-[0-9.]+)?)(?:\s|$)', first_line)
        if spdx_match:
            candidate = spdx_match.group(1)
            if len(candidate) <= 40:
                return candidate
        
        # Last resort: truncate first line
        first_line_stripped = first_line.strip()
        return first_line_stripped[:120] if first_line_stripped else "—"
    
    def get_last_domain_result(self) -> AnalysisResult:
        """Return the last domain AnalysisResult produced by execute()."""
        if self._last_result is None:
            raise RuntimeError("No analysis result available. Execute analysis first.")
        return self._last_result


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
        # Build enriched motivo field for reporting
        motivo_final = pkg.motivo_rechazo or ""
        if not motivo_final:
            # Generate default message based on approval status
            if pkg.aprobada == "Sí":
                motivo_final = "Sin problemas detectados"
            elif pkg.aprobada == "No":
                motivo_final = "Rechazado por criterios de seguridad"
            else:  # "En verificación"
                motivo_final = "Datos insuficientes para evaluar"
        
        # Ensure license is never None in the report
        license_value = pkg.license or "—"
        
        return {
            "package": pkg.name,
            "version": pkg.version,
            "latest_version": pkg.latest_version,
            "license": license_value,
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
            "dependencies": [
                {"name": dep.name, "version": dep.version, "latest_version": dep.latest_version}
                for dep in pkg.dependencies
            ],
            "is_maintained": pkg.is_maintained,
            "license_rejected": pkg.license_rejected,
            "aprobada": pkg.aprobada,
            "motivo_rechazo": motivo_final,
            "dependencias_directas": [
                {"name": dep.name, "version": dep.version, "latest_version": dep.latest_version}
                for dep in pkg.dependencias_directas
            ],
            "dependencias_transitivas": [
                {"name": dep.name, "version": dep.version, "latest_version": dep.latest_version}
                for dep in pkg.dependencias_transitivas
            ],
            "dependencias_rechazadas": pkg.dependencias_rechazadas,
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
        """Execute the complete analysis pipeline."""
        try:
            # Step 1: Analyze packages (returns DTO)
            analysis_result_dto = await self.analyze_use_case.execute(request)
            
            # Step 2: Build consolidated report
            report = await self.report_use_case.execute(analysis_result_dto)

            # Step 3: Persist report using configured report sink
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