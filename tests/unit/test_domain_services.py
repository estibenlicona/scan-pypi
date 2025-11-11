"""
Unit tests for domain services.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from src.domain.entities import Package, PackageIdentifier, Policy, SeverityLevel, Vulnerability, License, LicenseType
from src.domain.services import PolicyEngine, GraphBuilder, ReportBuilder


class TestPolicyEngine:
    """Test cases for PolicyEngine."""
    
    def test_filter_maintained_packages_recent(self) -> None:
        """Test that recent packages are considered maintained."""
        policy = Policy(
            name="test",
            description="Test policy",
            maintainability_years_threshold=2
        )
        engine = PolicyEngine(policy)
        
        # Recent package
        recent_time = datetime.now(timezone.utc) - timedelta(days=30)
        recent_package = Package(
            identifier=PackageIdentifier(name="test", version="1.0.0"),
            upload_time=recent_time
        )
        
        maintained = engine.filter_maintained_packages([recent_package])
        assert len(maintained) == 1
        assert maintained[0] == recent_package
    
    def test_filter_maintained_packages_old(self) -> None:
        """Test that old packages are filtered out."""
        policy = Policy(
            name="test",
            description="Test policy", 
            maintainability_years_threshold=2
        )
        engine = PolicyEngine(policy)
        
        # Old package
        old_time = datetime.now(timezone.utc) - timedelta(days=3*365)
        old_package = Package(
            identifier=PackageIdentifier(name="test", version="1.0.0"),
            upload_time=old_time
        )
        
        maintained = engine.filter_maintained_packages([old_package])
        assert len(maintained) == 0
    
    def test_evaluate_vulnerabilities_filter_by_severity(self) -> None:
        """Test vulnerability filtering by severity."""
        policy = Policy(
            name="test",
            description="Test policy",
            max_vulnerability_severity=SeverityLevel.MEDIUM
        )
        engine = PolicyEngine(policy)
        
        vulnerabilities = [
            Vulnerability(
                id="1", title="Low vuln", description="", severity=SeverityLevel.LOW,
                package_name="test", version="1.0.0"
            ),
            Vulnerability(
                id="2", title="Medium vuln", description="", severity=SeverityLevel.MEDIUM,
                package_name="test", version="1.0.0"
            ),
            Vulnerability(
                id="3", title="High vuln", description="", severity=SeverityLevel.HIGH,
                package_name="test", version="1.0.0"
            ),
        ]
        
        filtered = engine.evaluate_vulnerabilities(vulnerabilities)
        assert len(filtered) == 2
        assert filtered[0].severity == SeverityLevel.LOW
        assert filtered[1].severity == SeverityLevel.MEDIUM
    
    def test_evaluate_licenses_blocks_rejected(self) -> None:
        """Test license evaluation blocks rejected licenses."""
        policy = Policy(
            name="test",
            description="Test policy",
            blocked_licenses=["GPL-3.0"]
        )
        engine = PolicyEngine(policy)
        
        package = Package(
            identifier=PackageIdentifier(name="test", version="1.0.0"),
            license=License(name="GPL-3.0", license_type=LicenseType.GPL_3_0)
        )
        
        evaluated = engine.evaluate_licenses([package])
        assert len(evaluated) == 1
        assert evaluated[0].license is not None
        assert evaluated[0].license.name == "GPL-3.0"


class TestGraphBuilder:
    """Test cases for GraphBuilder."""
    
    def test_build_dependency_graph_simple(self) -> None:
        """Test building a simple dependency graph."""
        builder = GraphBuilder()
        
        dependency_data: Dict[str, Any] = {
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.28.0", 
                    "dependencies": [
                        {
                            "name": "urllib3",
                            "version": "1.26.0",
                            "dependencies": []
                        }
                    ]
                }
            ]
        }
        
        graph = builder.build_dependency_graph(dependency_data)
        
        assert len(graph.root_packages) == 1
        root_node = graph.root_packages[0]
        assert root_node.package.identifier.name == "requests"
        assert root_node.package.identifier.version == "2.28.0"
        assert len(root_node.dependencies) == 1
        
        sub_dep = root_node.dependencies[0]
        assert sub_dep.package.identifier.name == "urllib3"
        assert sub_dep.package.identifier.version == "1.26.0"


class TestReportBuilder:
    """Test cases for ReportBuilder."""
    
    def test_build_analysis_result(self) -> None:
        """Test building analysis result."""
        # Mock clock
        test_time = datetime.now(timezone.utc)
        clock_mock = lambda: test_time
        
        builder = ReportBuilder(clock_mock)
        
        # Create test data
        from src.domain.entities import DependencyGraph
        graph = DependencyGraph(root_packages=[])
        vulnerabilities: List[Vulnerability] = []
        maintained_packages: List[Package] = []
        policy = Policy(name="test", description="Test policy")
        
        result = builder.build_analysis_result(
            graph, vulnerabilities, maintained_packages, policy
        )
        
        assert result.timestamp == test_time
        assert result.dependency_graph == graph
        assert result.vulnerabilities == vulnerabilities
        assert result.maintained_packages == maintained_packages
        assert result.policy_applied == policy