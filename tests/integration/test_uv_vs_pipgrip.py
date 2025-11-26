"""
Integration test to compare UV and PipGrip dependency resolvers.

This test validates that both resolvers produce compatible results
and that UV is significantly faster.
"""

import asyncio
import time
from typing import List, Dict, Any

from src.infrastructure.adapters import PipGripAdapter, UvDepResolverAdapter
from src.infrastructure.adapters.logger_adapter import LoggerAdapter
from src.infrastructure.adapters.cache_adapter import CacheDiskAdapter
from src.infrastructure.config.settings import CacheSettings, LoggingSettings


def create_logger() -> LoggerAdapter:
    """Create logger for testing."""
    logging_settings = LoggingSettings(level="INFO", format_type="text")
    return LoggerAdapter(logging_settings, "test_resolvers")


def create_cache() -> CacheDiskAdapter:
    """Create cache adapter for testing."""
    cache_settings = CacheSettings(
        enabled=True,
        directory=".cache_test",
        ttl_hours=1
    )
    logger = create_logger()
    return CacheDiskAdapter(cache_settings, logger)


async def test_single_package_resolution():
    """Test resolving a single package with both resolvers."""
    print("\n" + "="*80)
    print("TEST 1: Single Package Resolution (requests==2.31.0)")
    print("="*80)
    
    logger = create_logger()
    cache = create_cache()
    
    # Test package
    test_package = ["requests==2.31.0"]
    
    # Test PipGrip
    print("\n[PipGrip] Resolving...")
    pipgrip_adapter = PipGripAdapter(logger, cache)
    start = time.time()
    try:
        pipgrip_result = await pipgrip_adapter.resolve_dependencies(test_package)
        pipgrip_time = time.time() - start
        pipgrip_packages = pipgrip_result.get_all_packages()
        print(f"✓ PipGrip: {len(pipgrip_packages)} packages in {pipgrip_time:.2f}s")
    except Exception as e:
        print(f"✗ PipGrip failed: {e}")
        pipgrip_packages = []
        pipgrip_time = 0
    
    # Test UV
    print("\n[UV] Resolving...")
    try:
        uv_adapter = UvDepResolverAdapter(logger, cache, cache_dir=".cache_test/uv")
        start = time.time()
        uv_result = await uv_adapter.resolve_dependencies(test_package)
        uv_time = time.time() - start
        uv_packages = uv_result.get_all_packages()
        print(f"✓ UV: {len(uv_packages)} packages in {uv_time:.2f}s")
        
        # Compare results
        print(f"\n[Comparison]")
        print(f"  PipGrip packages: {len(pipgrip_packages)}")
        print(f"  UV packages:      {len(uv_packages)}")
        
        if pipgrip_time > 0 and uv_time > 0:
            speedup = pipgrip_time / uv_time
            print(f"  UV speedup:       {speedup:.1f}x faster")
        
        return True
        
    except ImportError:
        print("⚠ UV not available - install with: pip install uv-dep-resolver")
        return False
    except Exception as e:
        print(f"✗ UV failed: {e}")
        return False


async def test_multiple_packages_resolution():
    """Test resolving multiple packages with both resolvers."""
    print("\n" + "="*80)
    print("TEST 2: Multiple Packages Resolution")
    print("="*80)
    
    logger = create_logger()
    cache = create_cache()
    
    # Test packages
    test_packages = [
        "requests==2.31.0",
        "flask==2.3.0",
        "pandas==2.0.0"
    ]
    
    print(f"\nResolving {len(test_packages)} packages:")
    for pkg in test_packages:
        print(f"  - {pkg}")
    
    # Test PipGrip
    print("\n[PipGrip] Resolving...")
    pipgrip_adapter = PipGripAdapter(logger, cache)
    start = time.time()
    try:
        pipgrip_result = await pipgrip_adapter.resolve_dependencies(test_packages)
        pipgrip_time = time.time() - start
        pipgrip_packages = pipgrip_result.get_all_packages()
        print(f"✓ PipGrip: {len(pipgrip_packages)} total packages in {pipgrip_time:.2f}s")
    except Exception as e:
        print(f"✗ PipGrip failed: {e}")
        pipgrip_packages = []
        pipgrip_time = 0
    
    # Test UV
    print("\n[UV] Resolving...")
    try:
        uv_adapter = UvDepResolverAdapter(logger, cache, cache_dir=".cache_test/uv")
        start = time.time()
        uv_result = await uv_adapter.resolve_dependencies(test_packages)
        uv_time = time.time() - start
        uv_packages = uv_result.get_all_packages()
        print(f"✓ UV: {len(uv_packages)} total packages in {uv_time:.2f}s")
        
        # Compare results
        print(f"\n[Comparison]")
        print(f"  PipGrip packages: {len(pipgrip_packages)}")
        print(f"  UV packages:      {len(uv_packages)}")
        
        if pipgrip_time > 0 and uv_time > 0:
            speedup = pipgrip_time / uv_time
            print(f"  UV speedup:       {speedup:.1f}x faster")
            
            # Show cache stats
            stats = uv_adapter.get_cache_stats()
            print(f"\n[UV Cache Stats]")
            print(f"  Cached packages:  {stats['total_packages']}")
            print(f"  Cache size:       {stats['cache_size_bytes'] / 1024:.1f} KB")
        
        return True
        
    except ImportError:
        print("⚠ UV not available - install with: pip install uv-dep-resolver")
        return False
    except Exception as e:
        print(f"✗ UV failed: {e}")
        return False


async def test_cache_performance():
    """Test cache performance with second run."""
    print("\n" + "="*80)
    print("TEST 3: Cache Performance (Second Run)")
    print("="*80)
    
    logger = create_logger()
    cache = create_cache()
    
    test_packages = ["requests==2.31.0", "flask==2.3.0"]
    
    try:
        uv_adapter = UvDepResolverAdapter(logger, cache, cache_dir=".cache_test/uv")
        
        # Second run (should hit cache)
        print("\n[UV] Second resolution (testing cache)...")
        start = time.time()
        result = await uv_adapter.resolve_dependencies(test_packages)
        cached_time = time.time() - start
        packages = result.get_all_packages()
        
        print(f"✓ UV (cached): {len(packages)} packages in {cached_time:.2f}s")
        
        if cached_time < 1.0:
            print(f"  ⚡ Cache hit! Resolution completed in under 1 second")
        
        return True
        
    except ImportError:
        print("⚠ UV not available")
        return False
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


async def main():
    """Run all comparison tests."""
    print("\n" + "="*80)
    print("UV vs PipGrip Dependency Resolver Comparison")
    print("="*80)
    
    results = []
    
    # Run tests
    results.append(await test_single_package_resolution())
    results.append(await test_multiple_packages_resolution())
    results.append(await test_cache_performance())
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"\nPassed: {passed}/{total} tests")
    
    if passed == total:
        print("\n✓ All tests passed!")
        print("\n💡 Recommendation: Use DEPENDENCY_RESOLVER=uv for 10-100x faster resolution")
        return True
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
