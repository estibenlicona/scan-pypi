"""
Domain services - Pure business logic without external dependencies.
"""

from __future__ import annotations
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timezone

from src.domain.entities import (
    Package, PackageIdentifier, DependencyGraph, DependencyNode, 
    Vulnerability, Policy, SeverityLevel, AnalysisResult
)


class PolicyEngine:
    """Pure domain service for applying business policies."""
    
    def __init__(self, policy: Policy) -> None:
        self.policy = policy
    
    def filter_maintained_packages(self, packages: List[Package]) -> List[Package]:
        """Filter packages based on maintainability policy."""
        maintained = []
        
        for package in packages:
            if self._is_package_maintained(package):
                maintained.append(package)
        
        return maintained
    
    def _is_package_maintained(self, package: Package) -> bool:
        """Check if a package meets maintainability criteria."""
        return package.is_maintained(self.policy.maintainability_years_threshold)
    
    def evaluate_vulnerabilities(self, vulnerabilities: List[Vulnerability]) -> List[Vulnerability]:
        """Filter vulnerabilities based on policy."""
        if not self.policy.max_vulnerability_severity:
            return vulnerabilities
        
        # Use string values for robust comparisons in case enums differ
        severity_order = {
            SeverityLevel.LOW.value: 1,
            SeverityLevel.MEDIUM.value: 2,
            SeverityLevel.HIGH.value: 3,
            SeverityLevel.CRITICAL.value: 4
        }

        def sev_key(s):
            if isinstance(s, SeverityLevel):
                return s.value
            if isinstance(s, str):
                return s
            try:
                return str(s)
            except Exception:
                return SeverityLevel.LOW.value

        max_level = severity_order.get(sev_key(self.policy.max_vulnerability_severity), 4)

        return [
            vuln for vuln in vulnerabilities
            if severity_order.get(sev_key(vuln.severity), 1) <= max_level
        ]
    
    def evaluate_licenses(self, packages: List[Package]) -> List[Package]:
        """Mark packages with blocked licenses."""
        for package in packages:
            if package.license and package.license.name:
                if package.license.name in self.policy.blocked_licenses:
                    # Create new license with rejection flag
                    from domain.entities import License
                    package.license = License(
                        name=package.license.name,
                        license_type=package.license.license_type,
                        url=package.license.url,
                        is_rejected=True
                    )
        
        return packages


class GraphBuilder:
    """Pure domain service for building dependency graphs."""
    
    def build_dependency_graph(self, dependency_data: Dict[str, Any]) -> DependencyGraph:
        """Build a DependencyGraph from raw dependency data."""
        # This would need to be adapted based on the actual structure of dependency_data
        # For now, creating a simple implementation
        
        root_nodes = []
        
        # Extract root dependencies (packages directly requested)
        dependencies = dependency_data.get("dependencies", [])
        
        for dep_data in dependencies:
            node = self._build_dependency_node(dep_data)
            if node:
                root_nodes.append(node)
        
        return DependencyGraph(root_packages=root_nodes)
    
    def _build_dependency_node(self, dep_data: Dict[str, Any]) -> DependencyNode:
        """Build a single dependency node from data."""
        # Extract package information
        name = dep_data.get("name", "")
        version = dep_data.get("version", "")
        
        if not name or not version:
            raise ValueError("Invalid dependency data: missing name or version")
        
        # Create package identifier and basic package
        identifier = PackageIdentifier(name=name, version=version)
        package = Package(identifier=identifier)
        
        # Create node
        node = DependencyNode(package=package)
        
        # Add sub-dependencies recursively
        sub_deps = dep_data.get("dependencies", [])
        for sub_dep in sub_deps:
            sub_node = self._build_dependency_node(sub_dep)
            node.add_dependency(sub_node)
        
        return node
    
    def merge_package_data_into_graph(
        self, 
        graph: DependencyGraph, 
        enriched_packages: List[Package]
    ) -> DependencyGraph:
        """Merge enriched package data back into the dependency graph."""
        # Create a lookup dictionary for enriched packages
        package_lookup = {
            f"{pkg.identifier.name}@{pkg.identifier.version}": pkg
            for pkg in enriched_packages
        }
        
        # Update all packages in the graph
        for root_node in graph.root_packages:
            self._update_node_packages(root_node, package_lookup)
        
        return graph
    
    def _update_node_packages(
        self, 
        node: DependencyNode, 
        package_lookup: Dict[str, Package]
    ) -> None:
        """Recursively update packages in dependency nodes."""
        package_key = f"{node.package.identifier.name}@{node.package.identifier.version}"
        
        if package_key in package_lookup:
            node.package = package_lookup[package_key]
        
        # Update sub-dependencies recursively
        for dep_node in node.dependencies:
            self._update_node_packages(dep_node, package_lookup)


class ReportBuilder:
    """Pure domain service for building analysis reports."""
    
    def __init__(self, clock_provider: Optional[Callable[[], datetime]] = None) -> None:
        """Initialize with optional clock provider for testing."""
        self._get_now = clock_provider or self._default_now
    
    def _default_now(self) -> datetime:
        """Default implementation for getting current time."""
        return datetime.now(timezone.utc)
    
    def build_analysis_result(
        self,
        dependency_graph: DependencyGraph,
        vulnerabilities: List[Vulnerability],
        maintained_packages: List[Package],
        policy: Policy
    ) -> AnalysisResult:
        """Build a complete analysis result."""
        return AnalysisResult(
            dependency_graph=dependency_graph,
            vulnerabilities=vulnerabilities,
            maintained_packages=maintained_packages,
            timestamp=self._get_now(),
            policy_applied=policy
        )