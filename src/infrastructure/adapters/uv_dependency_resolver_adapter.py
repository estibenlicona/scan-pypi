"""
UV Dependency Resolver Adapter - Implements DependencyResolverPort using uv-dep-resolver.

This adapter provides 10-100x faster dependency resolution compared to pipgrip
with intelligent caching to avoid redundant analysis.
"""

from __future__ import annotations
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any

from src.domain.entities import DependencyGraph
from src.domain.ports import DependencyResolverPort, LoggerPort, CachePort
from src.domain.services import GraphBuilder

try:
    from uv_dep_resolver import DependencyAnalyzer, ResolveResult
    UV_AVAILABLE = True
except ImportError:
    UV_AVAILABLE = False
    DependencyAnalyzer = None  # type: ignore
    ResolveResult = None  # type: ignore


class UvDepResolverAdapter(DependencyResolverPort):
    """Adapter for uv-based dependency resolution with intelligent caching."""
    
    def __init__(self, logger: LoggerPort, cache: CachePort, cache_dir: str = "./uv_cache") -> None:
        """
        Initialize UV dependency resolver adapter.
        
        Args:
            logger: Logger port for logging
            cache: Cache port (not used, uv-dep-resolver handles its own cache)
            cache_dir: Directory for uv-dep-resolver cache
            
        Raises:
            RuntimeError: If uv-dep-resolver is not installed
        """
        if not UV_AVAILABLE:
            raise RuntimeError(
                "uv-dep-resolver is not installed. Install it with: pip install uv-dep-resolver"
            )
        
        self.logger = logger
        self.cache = cache  # Keep for interface compatibility
        self.graph_builder = GraphBuilder()
        
        # Initialize uv-dep-resolver analyzer
        self.cache_dir = Path(cache_dir)
        self.analyzer = DependencyAnalyzer(
            cache_dir=str(self.cache_dir),
            auto_extract_subdeps=True
        )
        
        self.logger.info(f"UV Dependency Resolver initialized with cache at {self.cache_dir}")
    
    async def resolve_dependencies(self, packages: List[str]) -> DependencyGraph:
        """
        Resolve dependencies using uv with intelligent caching.
        
        Args:
            packages: List of package specifications (e.g., 'requests==2.31.0')
            
        Returns:
            DependencyGraph containing all resolved dependencies
            
        Raises:
            ValueError: If package list is invalid
            RuntimeError: If resolution fails
        """
        self.logger.info(f"Resolving dependencies for {len(packages)} packages using UV")
        
        try:
            # Validate packages
            self._validate_packages(packages)
            
            # Resolve dependencies using uv (with automatic caching)
            dependency_data = await self._run_uv_resolver(packages)
            
            # Build dependency graph from resolved requirements
            graph = self.graph_builder.build_dependency_graph(dependency_data)
            
            self.logger.info(f"Resolved {len(graph.get_all_packages())} total packages")
            return graph
            
        except Exception as e:
            self.logger.error(f"Dependency resolution failed: {e}")
            raise
    
    def _validate_packages(self, packages: List[str]) -> None:
        """
        Validate package list format.
        
        Args:
            packages: List of package specifications
            
        Raises:
            ValueError: If package list or format is invalid
        """
        if not packages:
            raise ValueError("Package list cannot be empty")
        
        for pkg in packages:
            pkg = pkg.strip()
            if not pkg:
                continue
            
            # Basic security check
            if ';' in pkg or '&' in pkg or '|' in pkg:
                raise ValueError(f"Invalid package format (shell characters not allowed): {pkg}")
    
    async def _run_uv_resolver(self, packages: List[str]) -> Dict[str, Any]:
        """
        Resolve dependencies using uv-dep-resolver with parallel execution.
        
        uv-dep-resolver handles its own caching automatically, so we don't need
        to implement cache logic here.
        
        Args:
            packages: List of package specifications
            
        Returns:
            Combined dependency structure for all packages
        """
        start_time = time.time()
        
        # Resolve packages in parallel using asyncio
        self.logger.debug(f"Resolving {len(packages)} packages in parallel with UV")
        
        # Create tasks for parallel resolution
        tasks = [
            self._resolve_single_package(pkg)
            for pkg in packages
        ]
        
        # Wait for all resolutions to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        all_dependencies = []
        cache_hits = 0
        cache_misses = 0
        
        for i, result in enumerate(results):
            package = packages[i]
            
            if isinstance(result, Exception):
                self.logger.warning(f"Failed to resolve package {package}: {result}")
                # Add empty entry for failed package
                all_dependencies.append({
                    "name": package.split("==")[0] if "==" in package else package,
                    "version": "unknown",
                    "dependencies": []
                })
                continue
            
            if result.from_cache:
                cache_hits += 1
            else:
                cache_misses += 1
            
            # Convert uv-dep-resolver result to internal format
            dependency_entry = self._convert_uv_result_to_internal(result)
            all_dependencies.append(dependency_entry)
        
        elapsed = time.time() - start_time
        self.logger.info(
            f"UV resolution completed in {elapsed:.2f}s "
            f"(Cache hits: {cache_hits}, Cache misses: {cache_misses})"
        )
        
        return {"dependencies": all_dependencies}
    
    async def _resolve_single_package(self, package: str) -> ResolveResult:
        """
        Resolve a single package using uv-dep-resolver.
        
        This runs in an executor to avoid blocking the async event loop
        since uv-dep-resolver's resolve() is synchronous.
        
        Args:
            package: Package specification (e.g., 'requests==2.31.0')
            
        Returns:
            ResolveResult from uv-dep-resolver
            
        Raises:
            RuntimeError: If resolution fails
        """
        loop = asyncio.get_event_loop()
        
        # Run synchronous resolve() in executor
        result = await loop.run_in_executor(
            None,
            lambda: self.analyzer.resolve(package, silent=True)
        )
        
        if not result.success:
            raise RuntimeError(f"UV resolution failed for {package}: {result.error}")
        
        return result
    
    def _convert_uv_result_to_internal(self, result: ResolveResult) -> Dict[str, Any]:
        """
        Convert uv-dep-resolver ResolveResult to internal dependency format.
        
        Args:
            result: ResolveResult from uv-dep-resolver
            
        Returns:
            Dependency entry in internal format
        """
        # Extract package name and version from the tree
        tree = result.tree
        
        return {
            "name": tree.name,
            "version": tree.version,
            "dependencies": self._convert_tree_nodes(tree.dependencies)
        }
    
    def _convert_tree_nodes(self, nodes: List[Any]) -> List[Dict[str, Any]]:
        """
        Recursively convert uv-dep-resolver PackageNode tree to internal format.
        
        Args:
            nodes: List of PackageNode objects
            
        Returns:
            List of dependency dictionaries
        """
        dependencies = []
        
        for node in nodes:
            dep_entry = {
                "name": node.name,
                "version": node.version,
                "dependencies": self._convert_tree_nodes(node.dependencies)
            }
            dependencies.append(dep_entry)
        
        return dependencies
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics from uv-dep-resolver.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            stats = self.analyzer.cache_stats()
            return {
                "total_packages": stats.get("total_packages", 0),
                "total_dependencies": stats.get("total_dependencies", 0),
                "cache_size_bytes": stats.get("size_bytes", 0),
                "cache_dir": str(self.cache_dir)
            }
        except Exception as e:
            self.logger.warning(f"Failed to get cache stats: {e}")
            return {
                "total_packages": 0,
                "total_dependencies": 0,
                "cache_size_bytes": 0,
                "cache_dir": str(self.cache_dir)
            }
    
    def clear_cache(self) -> int:
        """
        Clear uv-dep-resolver cache.
        
        Returns:
            Number of files deleted
        """
        try:
            deleted = self.analyzer.clear_cache()
            self.logger.info(f"Cleared UV cache: {deleted} files deleted")
            return deleted
        except Exception as e:
            self.logger.warning(f"Failed to clear cache: {e}")
            return 0
