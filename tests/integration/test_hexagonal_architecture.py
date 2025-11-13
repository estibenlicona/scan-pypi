"""
Integration test for the new Hexagonal Architecture.
Tests the complete flow from interface to domain to infrastructure.
"""

from __future__ import annotations
import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from typing import TypedDict
from src.application.services import SettingsService
from src.domain.entities import PackageIdentifier, Package
from src.infrastructure.adapters import LoggerAdapter, CacheDiskAdapter, SystemClockAdapter
from src.infrastructure.config import CacheSettings

class Dependency(TypedDict):
            name: str
            version: str
            dependencies: list["Dependency"]


class TestHexagonalArchitecture:
    """Integration tests for hexagonal architecture."""

    def test_settings_loading(self) -> None:
        """Test that settings load correctly from environment."""
        settings_service = SettingsService()
        settings = settings_service.load_settings()
        
        assert settings is not None
        assert settings.cache.enabled is True
        assert settings.policy.maintainability_years_threshold == 2

    def test_domain_entities_creation(self) -> None:
        """Test domain entities can be created and work correctly."""
        from src.domain.entities import Package, PackageIdentifier
        from datetime import datetime, timezone, timedelta
        
        pkg_id = PackageIdentifier(name="test-package", version="1.0.0")
        package = Package(
            identifier=pkg_id,
            upload_time=datetime.now(timezone.utc) - timedelta(days=30)
        )
        
        assert package.identifier.name == "test-package"
        assert package.identifier.version == "1.0.0"
        assert package.is_maintained(years_threshold=2) is True

    @pytest.mark.asyncio
    async def test_cache_adapter_async(self) -> None:
        """Test cache adapter works with async operations."""
        settings_service = SettingsService()
        settings = settings_service.load_settings()
        
        logger = LoggerAdapter(settings=settings.logging)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create new cache settings with temp directory
            cache_settings = CacheSettings(
                enabled=True,
                directory=temp_dir,
                ttl_hours=1
            )
            
            cache = CacheDiskAdapter(settings=cache_settings, logger=logger)
            
            # Test set and get
            test_key = "test:key"
            test_data: dict[str, str | int] = {"message": "hello", "count": 42}
            
            await cache.set(test_key, test_data)
            retrieved = await cache.get(test_key)
            
            assert retrieved == test_data

    def test_policy_creation_from_settings(self) -> None:
        """Test policy entity creation from settings."""
        settings_service = SettingsService()
        settings = settings_service.load_settings()
        
        policy = settings_service.create_policy(settings)
        
        assert policy.name == "Default Policy"
        assert policy.maintainability_years_threshold == 2
        assert isinstance(policy.blocked_licenses, list)

    def test_domain_services(self) -> None:
        """Test domain services work correctly."""
        from src.domain.services import PolicyEngine, GraphBuilder, ReportBuilder
        from src.domain.entities import Policy, Package, PackageIdentifier
        from datetime import datetime, timezone, timedelta
        
        # Create policy
        policy = Policy(
            name="Test Policy",
            description="Test policy for integration",
            maintainability_years_threshold=1,
            blocked_licenses=["GPL-3.0"]
        )
        
        # Test PolicyEngine
        engine = PolicyEngine(policy)
        
        recent_package = Package(
            identifier=PackageIdentifier(name="recent", version="1.0.0"),
            upload_time=datetime.now(timezone.utc) - timedelta(days=30)
        )
        
        old_package = Package(
            identifier=PackageIdentifier(name="old", version="1.0.0"), 
            upload_time=datetime.now(timezone.utc) - timedelta(days=400)
        )
        
        maintained = engine.filter_maintained_packages([recent_package, old_package])
        assert len(maintained) == 1
        assert maintained[0] == recent_package
        
        # Test GraphBuilder
        graph_builder = GraphBuilder()

        dependency_data: dict[str, list[Dependency]] = {
            "dependencies": [
            {
                "name": "test-pkg",
                "version": "1.0.0",
                "dependencies": []
            }
            ]
        }        
        graph = graph_builder.build_dependency_graph(dependency_data)
        assert len(graph.root_packages) == 1
        
        # Test ReportBuilder
        report_builder = ReportBuilder()
        result = report_builder.build_analysis_result(
            dependency_graph=graph,
            vulnerabilities=[],
            maintained_packages=maintained,
            policy=policy
        )
        
        assert result is not None
        assert result.dependency_graph == graph
        assert result.policy_applied == policy

    def test_complete_architecture_integration(self) -> None:
        """Test that all architecture layers work together."""
        # This is the integration test we ran manually before
        settings_service = SettingsService()
        settings = settings_service.load_settings()
        
        # 2. Domain layer 
        pkg_id = PackageIdentifier(name="requests", version="2.31.0")
        package = Package(
            identifier=pkg_id,
            upload_time=datetime.now(timezone.utc) - timedelta(days=30)
        )
        
        policy = settings_service.create_policy(settings)
        is_maintained = package.is_maintained(years_threshold=policy.maintainability_years_threshold)
        
        # 3. Infrastructure layer
        logger = LoggerAdapter(settings=settings.logging)
        clock = SystemClockAdapter()
        
        # Assertions
        assert package.identifier.name == "requests"
        assert is_maintained is True
        assert policy.name == "Default Policy"
        assert logger is not None
        assert clock.now() is not None
        
        print("[Ok] Complete hexagonal architecture integration test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])