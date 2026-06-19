"""
UV Dependency Resolver Adapter - Implements DependencyResolverPort using uv CLI.

Uses ``uv pip compile`` as a subprocess to resolve dependency trees.
No external Python package required — only the ``uv`` binary on PATH.
"""

from __future__ import annotations
import asyncio
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from typing import List, Dict, Any, Optional, cast

import aiohttp

from src.domain.entities import DependencyGraph
from src.domain.ports import DependencyResolverPort, LoggerPort, CachePort
from src.infrastructure.config.settings import APISettings
from src.domain.services import GraphBuilder
from src.infrastructure.adapters.http_session import make_client_session


def _resolve_uv_bin() -> Optional[str]:
    """Locate the ``uv`` binary, preferring the one bundled by PyInstaller.

    When running as a frozen executable, ``uv`` is shipped inside the bundle
    (see ``pyscan.spec``) so the program is self-contained. In development
    (non-frozen) we fall back to the ``uv`` on PATH.
    """
    if getattr(sys, "frozen", False):
        bundled = os.path.join(
            getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)),
            "uv.exe" if os.name == "nt" else "uv",
        )
        if os.path.exists(bundled):
            return bundled
    return shutil.which("uv")


_UV_BIN: Optional[str] = _resolve_uv_bin()


class UvDepResolverAdapter(DependencyResolverPort):
    """Adapter for uv-based dependency resolution via CLI subprocess."""

    def __init__(
        self,
        logger: LoggerPort,
        cache: CachePort,
        cache_dir: str = "./uv_cache",
        api_settings: Optional[APISettings] = None,
    ) -> None:
        """
        Initialize UV dependency resolver adapter.

        Args:
            logger: Logger port for logging.
            cache: Cache port for per-package caching.
            cache_dir: Directory for uv internal cache (unused, kept
                       for signature compatibility).
            api_settings: Optional API settings for PyPI fallback.

        Raises:
            RuntimeError: If the ``uv`` binary is not found on PATH.
        """
        if _UV_BIN is None:
            raise RuntimeError(
                "uv is not installed or not on PATH. "
                "Install it with: pip install uv"
            )

        self.logger = logger
        self.cache = cache
        self.graph_builder = GraphBuilder()
        self.api_settings = api_settings or APISettings()

        # Grab version for logging
        version = self._get_uv_version()
        self.logger.info(f"UV Dependency Resolver initialized ({version})")
    
    # ── Public API ─────────────────────────────────────────────────

    async def resolve_dependencies(
        self, packages: List[str]
    ) -> DependencyGraph:
        """
        Resolve dependencies using ``uv pip compile``.

        Args:
            packages: Package specifications (e.g. ``['requests==2.31.0']``).

        Returns:
            DependencyGraph with all resolved dependencies.

        Raises:
            ValueError: If the package list is invalid.
            RuntimeError: If resolution fails.
        """
        self.logger.info(
            f"Resolving dependencies for {len(packages)} packages using UV"
        )
        try:
            self._validate_packages(packages)
            dependency_data = await self._run_uv_resolver(packages)
            graph = self.graph_builder.build_dependency_graph(dependency_data)
            self.logger.info(
                f"Resolved {len(graph.get_all_packages())} total packages"
            )
            return graph
        except Exception as e:
            self.logger.error(f"Dependency resolution failed: {e}")
            raise

    # ── Internals ────────────────────────────────────────────────────

    @staticmethod
    def _get_uv_version() -> str:
        """Return the ``uv --version`` string."""
        try:
            proc = subprocess.run(
                [_UV_BIN, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return proc.stdout.strip() or "uv (unknown version)"
        except Exception:
            return "uv (version check failed)"

    def _validate_packages(self, packages: List[str]) -> None:
        """Validate package list format."""
        if not packages:
            raise ValueError("Package list cannot be empty")
        for pkg in packages:
            pkg = pkg.strip()
            if not pkg:
                continue
            if ";" in pkg or "&" in pkg or "|" in pkg:
                raise ValueError(
                    f"Invalid package format "
                    f"(shell characters not allowed): {pkg}"
                )

    # ── Resolution logic ─────────────────────────────────────────────

    async def _run_uv_resolver(
        self, packages: List[str]
    ) -> Dict[str, Any]:
        """Resolve each package in parallel via ``uv pip compile``."""
        start_time = time.time()
        self.logger.debug(
            f"Resolving {len(packages)} packages in parallel with UV"
        )

        tasks = [
            self._resolve_single_package(pkg) for pkg in packages
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_dependencies: List[Dict[str, Any]] = []
        cache_hits = 0
        cache_misses = 0

        for i, result in enumerate(results):
            package = packages[i]

            if isinstance(result, Exception):
                self.logger.warning(
                    f"Failed to resolve package {package}: {result}"
                )
                parts = package.split("==", 1)
                pkg_name = parts[0]
                pkg_version = parts[1] if len(parts) == 2 else "unknown"

                fallback_deps = await self._fetch_dependencies_from_pypi(
                    pkg_name, pkg_version
                )
                if fallback_deps:
                    self.logger.info(
                        f"PyPI fallback resolved {len(fallback_deps)} "
                        f"dependencies for {package}"
                    )
                else:
                    self.logger.warning(
                        f"PyPI fallback found no dependencies for {package}"
                    )
                all_dependencies.append({
                    "name": pkg_name,
                    "version": pkg_version,
                    "dependencies": fallback_deps,
                })
                continue

            # result is (dependency_entry, from_cache)
            dependency_entry, from_cache = result
            if from_cache:
                cache_hits += 1
            else:
                cache_misses += 1
            all_dependencies.append(dependency_entry)

        elapsed = time.time() - start_time
        self.logger.info(
            f"UV resolution completed in {elapsed:.2f}s "
            f"(Cache hits: {cache_hits}, Cache misses: {cache_misses})"
        )
        return {"dependencies": all_dependencies}

    async def _resolve_single_package(
        self, package: str
    ) -> tuple[Dict[str, Any], bool]:
        """
        Resolve a single package, checking the cache first.

        Returns:
            Tuple of (dependency_entry, from_cache).
        """
        cache_key = self._cache_key(package)
        cached = await self.cache.get(cache_key)
        if cached is not None:
            self.logger.debug(f"Cache hit for {package}")
            return cast(Dict[str, Any], cached), True

        self.logger.debug(f"Cache miss for {package} — running uv")
        entry = await self._compile_with_uv(package)

        await self.cache.set(cache_key, entry, ttl_seconds=3600)
        return entry, False

    async def _compile_with_uv(
        self, package: str, timeout_sec: int = 120
    ) -> Dict[str, Any]:
        """
        Run ``uv pip compile`` for *package* and parse the output.

        Args:
            package: Package spec (e.g. ``requests==2.31.0``).
            timeout_sec: Maximum time to wait for the process.

        Returns:
            Dict ``{"name", "version", "dependencies": [...]}``.
        """
        cmd = [
            _UV_BIN, "pip", "compile",
            "--no-header",
            "--annotation-style=line",
            "--quiet",
        ]

        if self.api_settings.uv_allow_prerelease:
            cmd.append("--prerelease=allow")

        # Add private index when configured
        if self.api_settings.private_index_url and self.api_settings.private_index_pat:
            url = self.api_settings.private_index_url.rstrip("/")
            pat = self.api_settings.private_index_pat
            # Embed PAT as password in the URL (Azure DevOps accepts any username)
            if "://" in url:
                scheme, rest = url.split("://", 1)
                url_with_creds = f"{scheme}://VssSessionToken:{pat}@{rest}"
            else:
                url_with_creds = url
            cmd += ["--extra-index-url", url_with_creds]
        elif self.api_settings.private_index_url:
            cmd += ["--extra-index-url", self.api_settings.private_index_url]

        cmd.append("-")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=package.encode()),
                timeout=timeout_sec,
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(
                f"uv pip compile timed out for {package} "
                f"after {timeout_sec}s"
            )

        if proc.returncode != 0:
            err = (stderr or b"").decode(errors="ignore").strip()
            raise RuntimeError(
                f"uv pip compile failed for {package}: {err}"
            )

        return self._parse_compile_output(package, stdout.decode())

    # ── Output parsing ───────────────────────────────────────────────

    def _parse_compile_output(
        self, requested: str, output: str
    ) -> Dict[str, Any]:
        """
        Parse ``uv pip compile --annotation-style=line`` output into a
        dependency tree.

        Example output::

            certifi==2024.2.2    # via requests
            charset-normalizer==3.3.2  # via requests
            requests==2.31.0
            urllib3==2.2.0       # via requests
        """
        # 1. Parse all resolved packages and their "via" parents
        packages: Dict[str, str] = {}          # normalised name → version
        children_of: Dict[str, List[str]] = {} # parent → [child, ...]

        current_pkg: Optional[str] = None

        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # "# via <parent>" annotation (may appear on its own line)
            via_match = re.match(r"^#\s*via\s+(.+)$", line)
            if via_match and current_pkg:
                parent = self._normalise(via_match.group(1).strip())
                if parent not in ("-r", "-", "stdin", "-r -"):
                    children_of.setdefault(parent, []).append(current_pkg)
                continue

            # Inline annotation: "pkg==ver   # via parent"
            inline_match = re.match(
                r"^([A-Za-z0-9_.@-]+)==([^\s#]+)\s*(?:#\s*via\s+(.+))?$",
                line,
            )
            if inline_match:
                name = self._normalise(inline_match.group(1))
                version = inline_match.group(2)
                packages[name] = version
                current_pkg = name

                via_raw = (inline_match.group(3) or "").strip()
                if via_raw:
                    parent = self._normalise(via_raw)
                    if parent not in ("-r", "-", "stdin", "-r -"):
                        children_of.setdefault(parent, []).append(name)
                continue

        # 2. Identify the root package
        req_name = self._normalise(requested.split("==")[0])
        req_version = packages.get(
            req_name,
            requested.split("==")[1]
            if "==" in requested
            else "unknown",
        )

        # 3. Build tree recursively
        visited: set[str] = set()

        def _build(name: str) -> Dict[str, Any]:
            visited.add(name)
            deps: List[Dict[str, Any]] = []
            for child in sorted(children_of.get(name, [])):
                if child not in visited:
                    deps.append(_build(child))
            return {
                "name": name,
                "version": packages.get(name, "unknown"),
                "dependencies": deps,
            }

        return _build(req_name)

    @staticmethod
    def _normalise(name: str) -> str:
        """PEP 503 normalisation: lowercase, hyphens/underscores → dash."""
        return re.sub(r"[-_.]+", "-", name.strip().lower())

    @staticmethod
    def _cache_key(package: str) -> str:
        """SHA-256 cache key for a package spec."""
        data = f"uv:pkg:{package.strip().lower()}".encode()
        return hashlib.sha256(data).hexdigest()

    # ── PyPI fallback for unresolvable packages ──────────────────────

    async def _fetch_dependencies_from_pypi(
        self, package_name: str, version: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch dependency list from PyPI metadata as fallback.

        When UV cannot compile a package (e.g. missing C toolchain),
        PyPI ``requires_dist`` still lists declared dependencies without
        needing to build the wheel.  For each dependency whose version is
        not pinned, we query PyPI again to resolve the latest release.

        Args:
            package_name: Name of the package.
            version: Requested version.

        Returns:
            List of dependency dicts ``{"name", "version", "dependencies"}``.
        """
        requires_dist = await self._get_requires_dist_from_pypi(
            package_name, version
        )
        if not requires_dist:
            return []

        parsed_deps: List[Dict[str, Any]] = []
        for req_str in requires_dist:
            parsed = self._parse_requires_dist_entry(req_str)
            if parsed:
                parsed_deps.append(parsed)

        deps_to_resolve = [d for d in parsed_deps if d["version"] == "*"]
        if deps_to_resolve:
            self.logger.debug(
                f"Resolving exact versions for {len(deps_to_resolve)} "
                f"dependencies of {package_name}"
            )
            resolve_tasks = [
                self._resolve_latest_version_from_pypi(dep["name"])
                for dep in deps_to_resolve
            ]
            resolved_versions = await asyncio.gather(
                *resolve_tasks, return_exceptions=True
            )
            for dep, ver_result in zip(deps_to_resolve, resolved_versions):
                if isinstance(ver_result, str) and ver_result:
                    dep["version"] = ver_result
                else:
                    self.logger.debug(
                        f"Could not resolve version for {dep['name']}"
                    )

        return parsed_deps

    async def _resolve_latest_version_from_pypi(
        self, package_name: str
    ) -> Optional[str]:
        """Fetch the latest stable version of a package from PyPI."""
        base_url = self.api_settings.pypi_base_url
        url = f"{base_url}/{package_name}/json"
        timeout = aiohttp.ClientTimeout(
            total=self.api_settings.request_timeout
        )
        try:
            async with make_client_session(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("info", {}).get("version")
        except Exception as exc:
            self.logger.debug(
                f"Failed to resolve latest version for "
                f"{package_name}: {exc}"
            )
        return None

    async def _get_requires_dist_from_pypi(
        self, package_name: str, version: str
    ) -> List[str]:
        """Query PyPI JSON API and return the ``requires_dist`` list."""
        base_url = self.api_settings.pypi_base_url
        timeout = aiohttp.ClientTimeout(
            total=self.api_settings.request_timeout
        )
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for url in (
                f"{base_url}/{package_name}/{version}/json",
                f"{base_url}/{package_name}/json",
            ):
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            info = data.get("info", {})
                            requires = info.get("requires_dist")
                            if isinstance(requires, list) and requires:
                                return requires
                except Exception as exc:
                    self.logger.debug(
                        f"PyPI fallback request failed ({url}): {exc}"
                    )
        return []

    @staticmethod
    def _parse_requires_dist_entry(
        entry: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single ``requires_dist`` string into a dependency dict.

        Environment markers (after ``;``) are ignored — we list ALL
        declared dependencies regardless of platform.
        """
        spec = entry.split(";")[0].strip()
        if not spec:
            return None
        match = re.match(
            r"^([A-Za-z0-9_.-]+)\s*(?:\(([^)]*)\)|([<>=!~].*))?", spec
        )
        if not match:
            return None
        name = match.group(1).strip()
        version_raw = (match.group(2) or match.group(3) or "").strip()
        exact = re.search(r"==\s*([A-Za-z0-9_.]+)", version_raw)
        version = exact.group(1) if exact else "*"
        return {"name": name, "version": version, "dependencies": []}
