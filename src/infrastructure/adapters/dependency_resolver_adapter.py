"""
PipGrip Dependency Resolver Adapter - Implements DependencyResolverPort using pipgrip with caching.
"""

from __future__ import annotations
import asyncio
import os
import subprocess
import json
import hashlib
import re
from pathlib import Path
import time
from typing import List, Dict, Any, cast

from src.domain.entities import DependencyGraph
from src.domain.ports import DependencyResolverPort, LoggerPort, CachePort
from src.domain.services import GraphBuilder


class PipGripAdapter(DependencyResolverPort):
    """Adapter for pipgrip dependency resolution with caching support."""
    
    def __init__(self, logger: LoggerPort, cache: CachePort) -> None:
        self.logger = logger
        self.cache = cache
        self.graph_builder = GraphBuilder()
    
    async def resolve_dependencies(self, packages: List[str]) -> DependencyGraph:
        """Resolve dependencies using pipgrip with caching."""
        self.logger.info(f"Resolving dependencies for {len(packages)} packages")
        
        try:
            # Validate packages
            self._validate_packages(packages)
            
            # Use pipgrip to resolve dependencies (with caching)
            dependency_data = await self._run_pipgrip(packages)
            
            # Build dependency graph from resolved requirements
            graph = self.graph_builder.build_dependency_graph(dependency_data)
            
            self.logger.info(f"Resolved {len(graph.get_all_packages())} total packages")
            return graph
            
        except Exception as e:
            self.logger.error(f"Dependency resolution failed: {e}")
            raise
    
    def _validate_packages(self, packages: List[str]) -> None:
        """Validate package list."""
        if not packages:
            raise ValueError("Package list cannot be empty")
        
        for pkg in packages:
            pkg = pkg.strip()
            if not pkg:
                continue
            
            # Check for truly problematic characters (semicolons can indicate command injection)
            if ';' in pkg:
                raise ValueError(f"Invalid package format (semicolon not allowed): {pkg}")
            
            # Basic format validation - only allow exact versions (==) or no version
            # Should match: package-name, package-name==1.0.0
            # Should reject: package-name>=1.0, package-name~=1.0, etc.
            exact_pattern = r'^[A-Za-z0-9_.-]+(?:==[A-Za-z0-9_.-]+)?$'
            range_pattern = r'^[A-Za-z0-9_.-]+[<>!~]'
            
            if re.match(range_pattern, pkg):
                raise ValueError(
                    f"Range version specifiers not supported: '{pkg}'. "
                    f"Only exact versions (==) or unspecified versions are allowed."
                )
            
            if not re.match(exact_pattern, pkg):
                raise ValueError(f"Invalid package format: '{pkg}'")

    async def _run_pipgrip(self, packages: List[str]) -> Dict[str, Any]:
        """
        Resolve dependencies using pipgrip with per-package caching.
        
        Each package is cached individually to maximize cache reuse across different
        analysis requests. If some packages are cached and others aren't, only the
        missing ones are resolved and the results are merged.
        """
        # Separate packages into cached and uncached
        cached_results: Dict[str, Dict[str, Any]] = {}
        uncached_packages: List[str] = []
        
        for package in packages:
            cache_key = self._generate_package_cache_key(package)
            cached_data = await self.cache.get(cache_key)
            
            if cached_data is not None:
                self.logger.debug(f"Cache hit for package: {package}")
                cached_results[package] = cast(Dict[str, Any], cached_data)
            else:
                self.logger.debug(f"Cache miss for package: {package}")
                uncached_packages.append(package)
        
        # Resolve uncached packages if any
        uncached_results: Dict[str, Dict[str, Any]] = {}
        if uncached_packages:
            self.logger.debug(f"Resolving {len(uncached_packages)} uncached packages in parallel")
            
            # Resolve each package individually in parallel for better performance
            start = time.time()
            
            # Create tasks for parallel execution
            tasks = []
            for package in uncached_packages:
                task = asyncio.create_task(
                    self._resolve_and_cache_package(package),
                    name=f"resolve_{package}"
                )
                tasks.append((package, task))
            
            # Wait for all tasks to complete
            for package, task in tasks:
                try:
                    package_data = await task
                    uncached_results[package] = package_data
                    self.logger.debug(f"Successfully resolved and cached package: {package}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to resolve package {package}: {e}")
                    # Create empty result for failed package
                    uncached_results[package] = {
                        "package": package,
                        "dependencies": []
                    }
            
            end = time.time()
            self.logger.info(f"Resolved {len(uncached_packages)} packages in parallel in {end - start:.2f} seconds")
        
        # Merge cached and newly resolved results
        all_results: Dict[str, Dict[str, Any]] = {**cached_results, **uncached_results}
        
        # Combine individual package results into final dependency structure
        return self._combine_package_results(all_results, packages)
    
    def _generate_package_cache_key(self, package: str) -> str:
        """
        Generate cache key for individual package.
        
        Args:
            package: Package name (e.g., 'requests', 'flask==2.0.1')
            
        Returns:
            Cache key for the specific package
        """
        # Normalize package name and add prefix for namespacing
        normalized_package = package.strip().lower()
        key_data = f"pkg:{normalized_package}".encode('utf-8')
        return hashlib.sha256(key_data).hexdigest()
    
    async def _resolve_and_cache_package(self, package: str) -> Dict[str, Any]:
        """
        Resolve a single package and cache the result.
        
        This method combines resolution and caching in a single async operation,
        making it suitable for parallel execution.
        
        Args:
            package: Package name to resolve
            
        Returns:
            Dependency data for the package
            
        Raises:
            Exception: If resolution fails (caught by caller)
        """
        # Resolve the package
        package_data = await self._resolve_single_package_with_pipgrip(package)
        
        # Cache the result
        cache_key = self._generate_package_cache_key(package)
        cache_ttl_seconds = 3600  # 1 hour
        await self.cache.set(cache_key, package_data, ttl_seconds=cache_ttl_seconds)
        
        return package_data
    
    def _combine_package_results(self, package_results: Dict[str, Dict[str, Any]], requested_packages: List[str]) -> Dict[str, Any]:
        """
        Combine individual package results into final dependency structure.
        
        Args:
            package_results: Dictionary of package name to its dependency data
            requested_packages: Original list of requested packages
            
        Returns:
            Combined dependency structure expected by graph builder
        """
        # Since each package was resolved individually, we need to combine them
        # into a single dependency tree structure
        all_dependencies = []
        
        for package in requested_packages:
            if package in package_results:
                package_data = package_results[package]
                
                # Each package_data should already be in the format from map_dependencies
                # Extract the root package info
                if "package" in package_data:
                    pkg_name = package_data["package"]
                    dependencies = package_data.get("dependencies", [])
                    
                    # Convert to the format expected by graph builder
                    if isinstance(pkg_name, str) and "==" in pkg_name:
                        name, version = pkg_name.split("==", 1)
                    else:
                        name = str(pkg_name)
                        version = "unknown"
                    
                    dependency_item = {
                        "name": name.strip(),
                        "version": version.strip(),
                        "dependencies": self._convert_dependencies_format(dependencies)
                    }
                    all_dependencies.append(dependency_item)
                else:
                    # Fallback: create minimal dependency entry
                    all_dependencies.append({
                        "name": package,
                        "version": "unknown",
                        "dependencies": []
                    })
        
        return {"dependencies": all_dependencies}
    
    def _convert_dependencies_format(self, dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert dependencies from pipgrip format to internal format.
        
        Args:
            dependencies: Dependencies in pipgrip format
            
        Returns:
            Dependencies in internal format
        """
        converted = []
        
        for dep in dependencies:
            if isinstance(dep, dict):
                if "package" in dep:
                    pkg_name = dep["package"]
                    if isinstance(pkg_name, str) and "==" in pkg_name:
                        name, version = pkg_name.split("==", 1)
                    else:
                        name = str(pkg_name)
                        version = "unknown"
                    
                    converted_dep = {
                        "name": name.strip(),
                        "version": version.strip(),
                        "dependencies": self._convert_dependencies_format(dep.get("dependencies", []))
                    }
                    converted.append(converted_dep)
        
        return converted

    async def _resolve_single_package_with_pipgrip(self, package: str, timeout_sec: int = 300) -> Dict[str, Any]:
        """
        Resolve a single package using pipgrip.
        
        Args:
            package: Package name to resolve
            
        Returns:
            Dependency data for the single package
            
        Raises:
            RuntimeError: If pipgrip execution fails
        """
        try:
            env = os.environ.copy()
            env["PIP_PREFER_BINARY"] = "1"                 # modo A (rápido)
            env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

            cmd = ["pipgrip", "--tree-json-exact", package]
            self.logger.debug(f"Running pipgrip for package: {package}")
            
            # Run subprocess in executor to avoid blocking
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path.cwd()),
                env=env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            except asyncio.TimeoutError:
                proc.kill()
                raise RuntimeError(f"pipgrip timeout for package {package} after {timeout_sec}s")

            if proc.returncode != 0:
                err = (stderr or b"").decode(errors="ignore").strip()
                raise RuntimeError(f"pipgrip failed for package {package}: {err}")

            # json.loads es CPU-bound pero muy corto; si quisieras aislarlo:
            # data = await asyncio.to_thread(json.loads, stdout.decode())
            data: Dict[str, Any] = json.loads(stdout.decode())
            return self.map_dependencies(data)

        except FileNotFoundError:
            raise RuntimeError("pipgrip is not available - ensure it's installed")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"pipgrip resolution timed out for package {package}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse pipgrip JSON output for package {package}: {e}")
        except Exception as e:
            raise RuntimeError(f"Dependency resolution failed for package {package}: {e}")

    async def _resolve_with_pipgrip(self, packages: List[str]) -> Dict[str, Any]:
        """
        Execute pipgrip to resolve dependencies.
        
        Args:
            packages: List of package names to resolve
            
        Returns:
            Parsed dependency data from pipgrip output
            
        Raises:
            RuntimeError: If pipgrip execution fails
        """       
        # Use pipgrip --tree-json-exact for structured output
        try:
            cmd = ["pipgrip", "--tree-json-exact"] + packages
            self.logger.debug(f"Running pipgrip: {' '.join(cmd)}")
            
            # Run subprocess in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(Path.cwd())
                )
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"pipgrip failed: {result.stderr}")

            data: Dict[str, Any] = json.loads(result.stdout)
            return self.map_dependencies(data)

        except FileNotFoundError:
            raise RuntimeError("pipgrip is not available - ensure it's installed")
        except subprocess.TimeoutExpired:
            raise RuntimeError("pipgrip resolution timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse pipgrip JSON output: {e}")
        except Exception as e:
            raise RuntimeError(f"Dependency resolution failed: {e}")    
        
    def transform(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = []
        for package, deps in node.items():
            result.append({
                "package": package,
                "dependencies": self.transform(deps)
            })
        return result

    def map_dependencies(self, tree: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte un diccionario en formato pipgrip --tree-json-exact a un
        diccionario con las claves 'package' y 'dependencies'.

        Args:
            tree (Dict[str, Any]): Diccionario de dependencias en formato pipgrip.

        Returns:
            Dict[str, Any]: Diccionario transformado al nuevo formato.
        """

        # pipgrip siempre devuelve un dict con un único root
        root_package, root_deps = next(iter(tree.items()))
        return {
            "package": root_package,
            "dependencies": self.transform(root_deps)
        }
    
    def _parse_requirements_to_dependency_data(self, requirements_output: str) -> Dict[str, Any]:
        """Parse pipgrip output to dependency data structure."""
        # This is a simplified parser - the real implementation would need
        # to handle pipgrip's tree format properly
        dependencies = []
        
        for line in requirements_output.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse package==version format
            if '==' in line:
                name, version = line.split('==', 1)
                name = name.strip()
                version = version.strip()
                
                dependencies.append({
                    "name": name,
                    "version": version,
                    "dependencies": []  # Simplified - would need tree parsing
                })
        
        return {"dependencies": dependencies}