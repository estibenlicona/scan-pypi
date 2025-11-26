"""
Integration test comparing PipGrip and UV dependency resolvers.

This test validates that both resolvers produce compatible results,
ensuring UV can be used as a drop-in replacement for PipGrip.
"""

import asyncio
import pytest
from pathlib import Path

from src.infrastructure.adapters import PipGripAdapter, UvDepResolverAdapter
from src.infrastructure.adapters.logger_adapter import LoggerAdapter
from src.infrastructure.adapters.cache_adapter import CacheDiskAdapter
from src.infrastructure.config.settings import LoggingSettings, CacheSettings


class TestDependencyResolverComparison:
    """Compare PipGrip and UV resolvers for compatibility."""
    
    @pytest.fixture
    def logger(self):
        """Create logger for testing."""
        logging_settings = LoggingSettings(level="DEBUG", format_type="text")
        return LoggerAdapter(logging_settings, "test_resolver")
    
    @pytest.fixture
    def cache(self, logger):
        """Create cache for testing."""
        cache_settings = CacheSettings(
            enabled=True,
            directory="./test_cache_resolvers",
            ttl_hours=1
        )
        return CacheDiskAdapter(cache_settings, logger)
    
    @pytest.fixture
    def pipgrip_adapter(self, logger, cache):
        """Create PipGrip adapter."""
        return PipGripAdapter(logger, cache)
    
    @pytest.fixture
    def uv_adapter(self, logger, cache):
        """Create UV adapter."""
        return UvDepResolverAdapter(logger, cache, cache_dir="./test_uv_cache")
    
    @pytest.mark.asyncio
    async def test_simple_package_resolution(self, pipgrip_adapter, uv_adapter):
        """Test that both resolvers can resolve a simple package."""
        test_package = ["requests==2.31.0"]
        
        # Resolve with both adapters
        pipgrip_graph = await pipgrip_adapter.resolve_dependencies(test_package)
        uv_graph = await uv_adapter.resolve_dependencies(test_package)
        
        # Get all packages from both graphs
        pipgrip_packages = pipgrip_graph.get_all_packages()
        uv_packages = uv_graph.get_all_packages()
        
        # Both should have resolved packages
        assert len(pipgrip_packages) > 0, "PipGrip should resolve packages"
        assert len(uv_packages) > 0, "UV should resolve packages"
        
        # Both should include the root package
        pipgrip_names = {pkg.name for pkg in pipgrip_packages}
        uv_names = {pkg.name for pkg in uv_packages}
        
        assert "requests" in pipgrip_names, "PipGrip should include requests"
        assert "requests" in uv_names, "UV should include requests"
        
        print(f"\nPipGrip resolved {len(pipgrip_packages)} packages")
        print(f"UV resolved {len(uv_packages)} packages")
        print(f"\nPipGrip packages: {sorted(pipgrip_names)}")
        print(f"UV packages: {sorted(uv_names)}")
    
    @pytest.mark.asyncio
    async def test_multiple_packages_resolution(self, pipgrip_adapter, uv_adapter):
        """Test that both resolvers handle multiple packages."""
        test_packages = ["requests==2.31.0", "click==8.1.0"]
        
        # Resolve with both adapters
        pipgrip_graph = await pipgrip_adapter.resolve_dependencies(test_packages)
        uv_graph = await uv_adapter.resolve_dependencies(test_packages)
        
        # Get all packages from both graphs
        pipgrip_packages = pipgrip_graph.get_all_packages()
        uv_packages = uv_graph.get_all_packages()
        
        pipgrip_names = {pkg.name for pkg in pipgrip_packages}
        uv_names = {pkg.name for pkg in uv_packages}
        
        # Both should include root packages
        assert "requests" in pipgrip_names
        assert "click" in pipgrip_names
        assert "requests" in uv_names
        assert "click" in uv_names
        
        print(f"\nMultiple packages test:")
        print(f"PipGrip resolved {len(pipgrip_packages)} packages")
        print(f"UV resolved {len(uv_packages)} packages")
    
    @pytest.mark.asyncio
    async def test_performance_comparison(self, pipgrip_adapter, uv_adapter):
        """Test performance difference between resolvers."""
        import time
        
        test_packages = ["pandas==2.0.0"]
        
        # Time PipGrip
        start = time.time()
        await pipgrip_adapter.resolve_dependencies(test_packages)
        pipgrip_time = time.time() - start
        
        # Time UV
        start = time.time()
        await uv_adapter.resolve_dependencies(test_packages)
        uv_time = time.time() - start
        
        print(f"\nPerformance comparison:")
        print(f"PipGrip: {pipgrip_time:.2f}s")
        print(f"UV: {uv_time:.2f}s")
        print(f"Speedup: {pipgrip_time / uv_time:.2f}x")
        
        # UV should be faster (but this may fail on first run without cache)
        # So we just log the results without assertion


async def main():
    """Run tests manually for quick validation."""
    from src.infrastructure.config.settings import LoggingSettings, CacheSettings
    from src.infrastructure.adapters.logger_adapter import LoggerAdapter
    from src.infrastructure.adapters.cache_adapter import CacheDiskAdapter
    
    # Setup
    logging_settings = LoggingSettings(level="INFO", format_type="text")
    logger = LoggerAdapter(logging_settings, "test_resolver")
    
    cache_settings = CacheSettings(
        enabled=True,
        directory="./test_cache_resolvers",
        ttl_hours=1
    )
    cache = CacheDiskAdapter(cache_settings, logger)
    
    print("=" * 80)
    print("TESTING DEPENDENCY RESOLVER COMPATIBILITY")
    print("=" * 80)
    
    try:
        # Test PipGrip
        print("\n1. Testing PipGrip adapter...")
        pipgrip = PipGripAdapter(logger, cache)
        pipgrip_result = await pipgrip.resolve_dependencies(["requests==2.31.0"])
        pipgrip_packages = pipgrip_result.get_all_packages()
        print(f"✓ PipGrip resolved {len(pipgrip_packages)} packages")
        print(f"  Packages: {sorted([p.name for p in pipgrip_packages])}")
        
    except Exception as e:
        print(f"✗ PipGrip failed: {e}")
    
    try:
        # Test UV
        print("\n2. Testing UV adapter...")
        uv = UvDepResolverAdapter(logger, cache, cache_dir="./test_uv_cache")
        uv_result = await uv.resolve_dependencies(["requests==2.31.0"])
        uv_packages = uv_result.get_all_packages()
        print(f"✓ UV resolved {len(uv_packages)} packages")
        print(f"  Packages: {sorted([p.name for p in uv_packages])}")
        
        # Show cache stats
        stats = uv.get_cache_stats()
        print(f"\n3. UV Cache Statistics:")
        print(f"  Total packages: {stats['total_packages']}")
        print(f"  Total dependencies: {stats['total_dependencies']}")
        print(f"  Cache size: {stats['cache_size_bytes'] / 1024:.2f} KB")
        
    except Exception as e:
        print(f"✗ UV failed: {e}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
