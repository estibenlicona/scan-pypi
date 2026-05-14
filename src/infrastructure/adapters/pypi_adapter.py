"""
PyPI Client Adapter - Implements MetadataProviderPort using PyPI API.
"""

from __future__ import annotations
import re
import time
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List, Tuple, cast
from typing import Any as TypingAny
from datetime import datetime

from src.domain.entities import Package, License, LicenseType
from src.domain.ports import MetadataProviderPort, LoggerPort, CachePort
from src.domain.services.license_validator import LicenseValidator
from src.infrastructure.config.settings import APISettings
from src.infrastructure.utilities.retry_policy import RetryPolicy


class PyPIClientAdapter(MetadataProviderPort):
    """Adapter for PyPI API metadata enrichment."""
    
    # Cache TTL for version-specific PyPI data (immutable once published)
    _PYPI_METADATA_TTL = 7 * 24 * 3600  # 7 days
    _GITHUB_LICENSE_TTL = 7 * 24 * 3600  # 7 days

    def __init__(
        self,
        settings: APISettings,
        logger: LoggerPort,
        cache: Optional[CachePort] = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self._cache = cache
        # Cache performance counters
        self._pypi_cache_hits = 0
        self._pypi_cache_misses = 0
        self._github_cache_hits = 0
        self._github_cache_misses = 0
        # Initialize retry policy for resilient API calls
        self.retry_policy = RetryPolicy(
            max_retries=3,
            base_delay_seconds=1.0,
            max_delay_seconds=30.0,
            logger=logger
        )
        # GitHub rate-limit state: tracks when the limit resets (Unix timestamp)
        self._github_rate_limited_until: float = 0.0
        self._github_rate_limit_warned: bool = False
        # Semaphore limits concurrent GitHub requests to prevent burst rate-limiting
        self._github_semaphore = asyncio.Semaphore(5)
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Return current cache performance counters."""
        return {
            "pypi_hits": self._pypi_cache_hits,
            "pypi_misses": self._pypi_cache_misses,
            "github_hits": self._github_cache_hits,
            "github_misses": self._github_cache_misses,
        }

    def reset_cache_stats(self) -> None:
        """Reset all cache performance counters to zero."""
        self._pypi_cache_hits = 0
        self._pypi_cache_misses = 0
        self._github_cache_hits = 0
        self._github_cache_misses = 0

    # --- Helper normalization utilities ---------------------------------
    def _safe_str(self, value: TypingAny) -> Optional[str]:
        """Return a stripped string or None for non-string/empty values."""
        if isinstance(value, str):
            v = value.strip()
            return v if v else None
        return None

    def _safe_list(self, value: TypingAny) -> List[str]:
        """Return a list of strings or an empty list for other types."""
        if isinstance(value, (list, tuple)):
            cast_list = cast(List[TypingAny], value)
            return [str(x) for x in cast_list]
        return []

    def _safe_dict(self, value: TypingAny) -> Dict[str, str]:
        """Return a dict[str,str] or empty dict for other types."""
        if isinstance(value, dict):
            cast_dict = cast(Dict[TypingAny, TypingAny], value)
            return {str(k): str(v) for k, v in cast_dict.items() if v is not None}
        return {}

    def _safe_project_urls(self, info: Dict[str, Any]) -> Dict[str, str]:
        """Normalize project_urls from package info to Dict[str, str]."""
        raw = info.get("project_urls", {})
        return self._safe_dict(raw)

    def _normalize_spdx_license(self, license_str: str) -> str:
        """Normalize SPDX license identifier from lowercase to proper case.
        
        Examples:
            'mit' -> 'MIT'
            'apache-2.0' -> 'Apache-2.0'
            'bsd-3-clause' -> 'BSD-3-Clause'
            'gpl-3.0' -> 'GPL-3.0'
        """
        if not license_str:
            return license_str
        
        # Map of lowercase SPDX to properly formatted versions
        spdx_map = {
            'mit': 'MIT',
            'apache-2.0': 'Apache-2.0',
            'bsd-3-clause': 'BSD-3-Clause',
            'bsd-2-clause': 'BSD-2-Clause',
            'gpl-3.0': 'GPL-3.0',
            'gpl-2.0': 'GPL-2.0',
            'lgpl-2.1': 'LGPL-2.1',
            'lgpl-3.0': 'LGPL-3.0',
            'mpl-2.0': 'MPL-2.0',
            'isc': 'ISC',
            'unlicense': 'Unlicense',
        }
        
        lower = license_str.lower().strip()
        return spdx_map.get(lower, license_str)
    

    
    async def enrich_package_metadata(self, package: Package) -> Package:
        """Enrich package with metadata from PyPI and GitHub APIs."""
        self.logger.debug(f"Enriching package {package.identifier}")
        
        try:
            # Get PyPI metadata
            pypi_data = await self._fetch_pypi_metadata(package.identifier.name, package.identifier.version)
            
            if not pypi_data:
                self.logger.warning(f"No PyPI data found for {package.identifier}")
                return package
            
            # Update package with PyPI data
            enriched_package = self._merge_pypi_data(package, pypi_data)
            
            # Fetch latest version and its upload_time from PyPI
            latest_ver, latest_ut = await self._fetch_latest_version_info(
                package.identifier.name
            )
            if latest_ver:
                enriched_package.latest_version = latest_ver
            if latest_ut:
                enriched_package.latest_upload_time = latest_ut
            
            # Enrich with GitHub data if available
            if enriched_package.github_url:
                github_data = await self._fetch_github_metadata(
                    enriched_package.github_url
                )
                if github_data:
                    self._github_cache_misses += 1
                    # Cache license for fallback on future rate-limits
                    await self._cache_github_license(
                        enriched_package.github_url, github_data
                    )
                    enriched_package = self._merge_github_data(
                        enriched_package, github_data
                    )
                else:
                    # Fallback: cached license (no pushed_at)
                    cached_gh = await self._get_cached_github_license(
                        enriched_package.github_url
                    )
                    if cached_gh:
                        self._github_cache_hits += 1
                        enriched_package = self._merge_github_data(
                            enriched_package, cached_gh
                        )
            
            self.logger.debug(f"Successfully enriched {package.identifier}")
            return enriched_package
            
        except Exception as e:
            self.logger.error(f"Failed to enrich package {package.identifier}: {e}")
            return package  # Return original package if enrichment fails
    
    async def _fetch_pypi_metadata(self, package_name: str, version: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata from PyPI API with cache and automatic retries.

        Version-specific PyPI data is immutable once published, so results
        are cached to avoid redundant HTTP calls across scans.
        Tries specific version first, falls back to latest if not found.
        """
        # Check cache first (version-specific data is immutable)
        cache_key: Optional[str] = None
        if self._cache:
            cache_key = self._cache.generate_key(
                "pypi_metadata", package_name.lower(), version
            )
            cached = await self._cache.get(cache_key)
            if cached is not None:
                self._pypi_cache_hits += 1
                self.logger.debug(
                    f"Cache hit for PyPI metadata: "
                    f"{package_name}@{version}"
                )
                return cached
            self._pypi_cache_misses += 1

        # Helper function to fetch with retry
        async def fetch_with_retry() -> Optional[Dict[str, Any]]:
            # First, try to fetch the specific version
            url = f"{self.settings.pypi_base_url}/{package_name}/{version}/json"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout)) as session:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 404:
                            # Specific version not found, try fetching latest version metadata
                            self.logger.debug(f"Specific version {package_name}@{version} not found, trying latest")
                            url_latest = f"{self.settings.pypi_base_url}/{package_name}/json"
                            async with session.get(url_latest) as response_latest:
                                if response_latest.status == 200:
                                    return await response_latest.json()
                                else:
                                    self.logger.debug(f"PyPI API returned {response_latest.status} for {package_name} (may be unpublished or pre-release)")
                                    return None
                        else:
                            self.logger.debug(f"PyPI API returned {response.status} for {package_name}@{version}")
                            return None
                except asyncio.TimeoutError:
                    self.logger.debug(f"Timeout fetching {package_name}@{version}")
                    raise
        
        # Apply retry policy
        try:
            result = await self.retry_policy.execute(fetch_with_retry)
        except Exception as e:
            self.logger.warning(f"Failed to fetch {package_name}@{version} after retries: {e}")
            return None

        # Store in cache (immutable per version)
        if result is not None and self._cache and cache_key:
            await self._cache.set(
                cache_key, result,
                ttl_seconds=self._PYPI_METADATA_TTL
            )

        return result
    
    async def fetch_latest_version(self, package_name: str) -> Optional[str]:
        """Public method to fetch latest version of a package from PyPI."""
        return await self._fetch_latest_version(package_name)
    
    async def _fetch_latest_version(self, package_name: str) -> Optional[str]:
        """Fetch the latest version of a package from PyPI with automatic retries."""
        version, _ = await self._fetch_latest_version_info(package_name)
        return version

    async def _fetch_latest_version_info(
        self, package_name: str
    ) -> Tuple[Optional[str], Optional[datetime]]:
        """Fetch latest version and its upload_time from PyPI."""
        async def fetch_with_retry() -> Tuple[Optional[str], Optional[datetime]]:
            url = f"{self.settings.pypi_base_url}/{package_name}/json"

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout)
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        version = data.get("info", {}).get("version")
                        upload_time = self._parse_upload_time(data)
                        return version, upload_time
                    else:
                        self.logger.debug(
                            f"PyPI API returned {response.status} for "
                            f"{package_name} (may be pre-release)"
                        )
                        return None, None

        try:
            return await self.retry_policy.execute(fetch_with_retry)
        except Exception as e:
            self.logger.warning(
                f"Failed to fetch latest version for {package_name} "
                f"after retries: {e}"
            )
            return None, None

    @staticmethod
    def _parse_upload_time(pypi_data: Dict[str, Any]) -> Optional[datetime]:
        """Extract upload_time from PyPI JSON response."""
        urls = pypi_data.get("urls", [])
        if urls:
            ut_str = urls[0].get("upload_time")
            if ut_str:
                try:
                    return datetime.fromisoformat(
                        ut_str.replace('Z', '+00:00')
                    )
                except ValueError:
                    pass
        return None
    
    async def _fetch_github_metadata(self, github_url: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata from GitHub API with authentication support and automatic retries."""
        repo_match = re.match(r'https://github\.com/([^/]+)/([^/]+)', github_url)
        if not repo_match:
            return None

        owner, repo = repo_match.groups()
        api_url = f"{self.settings.github_base_url}/repos/{owner}/{repo}"

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Add authentication token if available (increases rate limit from 60 to 5000/hour)
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"

        # Early check to skip GitHub calls when rate limit is still active
        if time.time() < self._github_rate_limited_until:
            self.logger.debug("GitHub API rate limit active — skipping GitHub call")
            return None

        async def fetch_with_retry() -> Optional[Dict[str, Any]]:
            async with self._github_semaphore:
                # Re-check inside semaphore: another coroutine may have set the flag
                if time.time() < self._github_rate_limited_until:
                    self.logger.debug("GitHub API rate limit active — skipping GitHub call")
                    return None

                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout)
                ) as session:
                    async with session.get(api_url, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()

                        elif response.status in (403, 429):
                            remaining = response.headers.get("X-RateLimit-Remaining", "1")
                            retry_after = response.headers.get("Retry-After")
                            reset_ts = response.headers.get("X-RateLimit-Reset")

                            is_rate_limit = (
                                response.status == 429
                                or remaining == "0"
                                or retry_after is not None
                            )

                            if is_rate_limit:
                                # Retry-After takes precedence over X-RateLimit-Reset
                                if retry_after:
                                    self._github_rate_limited_until = (
                                        time.time() + float(retry_after) + 5
                                    )
                                elif reset_ts:
                                    self._github_rate_limited_until = float(reset_ts) + 5
                                else:
                                    self._github_rate_limited_until = time.time() + 3600

                                if not self._github_rate_limit_warned:
                                    self._github_rate_limit_warned = True
                                    self.logger.warning(
                                        f"GitHub API rate limit exceeded. "
                                        f"Remaining: {remaining}, Reset at: "
                                        f"{reset_ts or 'unknown'}. "
                                        f"GitHub calls paused until reset."
                                    )
                            else:
                                self.logger.warning(
                                    f"GitHub API 403 Forbidden for {owner}/{repo} "
                                    f"(not a rate limit — check token permissions)"
                                )
                            return None

                        elif response.status == 404:
                            self.logger.warning(f"GitHub repository not found: {owner}/{repo}")
                            return None

                        else:
                            self.logger.warning(
                                f"GitHub API returned {response.status} for {owner}/{repo}"
                            )
                            return None

        try:
            return await self.retry_policy.execute(fetch_with_retry)
        except Exception as e:
            self.logger.warning(
                f"Failed to fetch GitHub data for {owner}/{repo} after retries: {e}"
            )
            return None

    async def _cache_github_license(
        self, github_url: str, github_data: Dict[str, Any]
    ) -> None:
        """Cache only license-relevant fields from GitHub response."""
        if not self._cache:
            return
        cache_key = self._cache.generate_key(
            "github_license", github_url.lower()
        )
        license_data = {"license": github_data.get("license")}
        await self._cache.set(
            cache_key, license_data,
            ttl_seconds=self._GITHUB_LICENSE_TTL
        )

    async def _get_cached_github_license(
        self, github_url: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached GitHub license as fallback (no pushed_at)."""
        if not self._cache:
            return None
        cache_key = self._cache.generate_key(
            "github_license", github_url.lower()
        )
        return await self._cache.get(cache_key)
    
    def _merge_pypi_data(self, package: Package, pypi_data: Dict[str, Any]) -> Package:
        """Merge PyPI data into package."""
        info = pypi_data.get("info") or {}
        if not isinstance(info, dict):
            self.logger.warning(f"Invalid 'info' structure from PyPI for {package.identifier}: got {type(info)}")
            return package
        
        # Extract license using LicenseValidator (encapsulates all logic)
        license_obj = LicenseValidator.extract_license_from_sources(
            pypi_info=info,
            github_data=None  # GitHub data merged separately
        )
        
        # Parse upload time
        upload_time = self._parse_upload_time(pypi_data)
        
        # Extract GitHub URL from project URLs or description
        github_url = self._extract_github_url(cast(Dict[str, Any], info))

        # Normalize fields using helpers
        classifiers = self._safe_list(info.get("classifiers", []))
        summary_value = self._safe_str(info.get("summary"))
        home_page_value = self._safe_str(info.get("home_page"))
        author_value = self._safe_str(info.get("author"))
        author_email_value = self._safe_str(info.get("author_email"))
        maintainer_value = self._safe_str(info.get("maintainer"))
        maintainer_email_value = self._safe_str(info.get("maintainer_email"))
        keywords_value = self._safe_str(info.get("keywords"))
        requires_dist_value = self._safe_list(info.get("requires_dist", []))
        project_urls_value = self._safe_project_urls(cast(Dict[str, Any], info))

        return Package(
            identifier=package.identifier,
            license=license_obj,
            upload_time=upload_time,
            summary=summary_value,
            home_page=home_page_value,
            author=author_value,
            author_email=author_email_value,
            maintainer=maintainer_value,
            maintainer_email=maintainer_email_value,
            keywords=keywords_value,
            classifiers=classifiers,
            requires_dist=requires_dist_value,
            project_urls=project_urls_value,
            github_url=github_url,
            latest_version=package.latest_version,  # Preserve existing latest_version
            dependencies=package.dependencies  # Preserve existing dependencies
        )
    
    def _merge_github_data(self, package: Package, github_data: Dict[str, Any]) -> Package:
        """Merge GitHub data into package (license fallback + last commit date)."""
        # Use LicenseValidator to extract license from GitHub if PyPI license is missing
        final_license = package.license
        
        # Only try GitHub if PyPI didn't provide a valid license
        if final_license is None:
            github_license = LicenseValidator.extract_license_from_sources(
                pypi_info=None,
                github_data=github_data
            )
            if github_license:
                final_license = github_license

        # Extract last commit/push date from GitHub
        last_commit_date = self._parse_github_pushed_at(github_data)
        
        # Return updated package with merged GitHub data
        return Package(
            identifier=package.identifier,
            license=final_license,
            upload_time=package.upload_time,
            summary=package.summary,
            home_page=package.home_page,
            author=package.author,
            author_email=package.author_email,
            maintainer=package.maintainer,
            maintainer_email=package.maintainer_email,
            keywords=package.keywords,
            classifiers=package.classifiers,
            requires_dist=package.requires_dist,
            project_urls=package.project_urls,
            github_url=package.github_url,
            latest_version=package.latest_version,
            latest_upload_time=package.latest_upload_time,
            last_commit_date=last_commit_date or package.last_commit_date,
            dependencies=package.dependencies
        )

    @staticmethod
    def _parse_github_pushed_at(
        github_data: Dict[str, Any]
    ) -> Optional[datetime]:
        """Extract pushed_at datetime from GitHub API response."""
        pushed_at = github_data.get("pushed_at")
        if not pushed_at:
            return None
        try:
            return datetime.fromisoformat(
                pushed_at.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            return None
    
    def _extract_github_url(self, info: Dict[str, Any]) -> Optional[str]:
        """Extract GitHub URL from package info."""
        # Check project URLs first
        project_urls = info.get("project_urls") or {}
        if not isinstance(project_urls, dict):
            project_urls = {}
        for key, url in project_urls.items():
            if not isinstance(url, str):
                continue
            if "github.com" in url.lower():
                return url
        
        # Check home page
        home_page = info.get("home_page") or ""
        if not isinstance(home_page, str):
            home_page = ""
        if "github.com" in home_page:
            return home_page
        
        # Check summary/description
        summary = info.get("summary", "") or ""
        description = info.get("description", "") or ""
        combined_text = f"{summary} {description}"
        
        github_pattern = r'https://github\.com/[\w\-]+/[\w\-]+'
        github_urls = re.findall(github_pattern, combined_text)
        
        if github_urls:
            return min(github_urls, key=len)  # Return shortest URL (likely the main one)
        
        return None
    
    def _parse_license_type(self, license_name: str) -> Optional[LicenseType]:
        """Parse license type from license name, handling full text and various formats."""
        if not license_name:
            return None
        
        # Extract short name if it's full license text
        if len(license_name) > 100:
            license_name = self._extract_license_name_from_text(license_name)
        
        license_lower = license_name.lower()
        
        # Check for common SPDX identifiers and variations
        if "mit" in license_lower:
            return LicenseType.MIT
        elif "apache" in license_lower:
            return LicenseType.APACHE_2_0
        elif "bsd" in license_lower:
            # Check for specific BSD versions
            if "3" in license_lower or "3-clause" in license_lower:
                return LicenseType.BSD_3_CLAUSE
            return LicenseType.BSD_3_CLAUSE  # Default to 3-Clause
        elif ("gpl" in license_lower or "gnu" in license_lower) and ("3" in license_lower or "v3" in license_lower):
            return LicenseType.GPL_3_0
        elif "lgpl" in license_lower or ("lesser" in license_lower and "gpl" in license_lower):
            return LicenseType.LGPL_2_1
        elif "mpl" in license_lower or "mozilla" in license_lower:
            return LicenseType.MPL_2_0
        elif "isc" in license_lower:
            return LicenseType.UNKNOWN  # ISC not in enum, but valid license
        elif "unlicense" in license_lower or "public domain" in license_lower:
            return LicenseType.UNKNOWN
        else:
            return LicenseType.UNKNOWN
    
    def _extract_license_name_from_text(self, license_text: str) -> str:
        """Extract license name from full license text or short name."""
        if not license_text or len(license_text) < 5:
            return license_text
        
        # Normalize line endings
        license_text_normalized = license_text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Extract first line (usually the license name in full text)
        lines = license_text_normalized.split('\n')
        first_line = lines[0].strip()
        
        # If first line is empty, try to find a better line
        if not first_line or len(first_line) < 3:
            for line in lines:
                line = line.strip()
                if line and len(line) > 3 and not line.startswith('Copyright') and not line.startswith('License:'):
                    first_line = line
                    break
        
        # If still no valid line, try to find one with "License" keyword
        if not first_line or len(first_line) < 3:
            for line in lines:
                line = line.strip()
                if 'license' in line.lower():
                    first_line = line
                    break
        
        if not first_line:
            # If completely empty, return normalized stripped version (short text case)
            return license_text_normalized.strip()
        
        # If the extracted first line is short (< 50 chars) and it's the only substantive line,
        # it's likely just a name - return it as-is
        if len(first_line) < 50 and len(lines) > 1 and not lines[1].strip():
            # First line is short and followed by empty line - it's a name
            return first_line
        
        # If the entire normalized text is short (< 50 chars), it's already a name
        if len(license_text_normalized) < 50:
            return license_text_normalized.strip()
        
        # Common patterns for license names at start of text
        license_patterns = [
            # Match license name ending with "License", "License v1", or "v1"
            r"^([A-Za-z0-9\-\.\s]+?(?:License|v\d+))(?:\s|$)",
            # Match version patterns like "2.0", "3.0", "3-Clause"
            r"^([A-Za-z0-9\-\.\s]+?(?:2\.0|3\.0|3-Clause))(?:\s|$)",
            # Match v-style versions like "GPL v3"
            r"^([A-Za-z\s\-]+v?\d+)(?:\s|$)",
            # Fallback: take the whole first line if it's reasonably short
            r"^([A-Za-z0-9\s\-\.\(\)]+?)$",
        ]
        
        for pattern in license_patterns:
            match = re.match(pattern, first_line, re.IGNORECASE)
            if match:
                license_name = match.group(1).strip()
                if license_name and len(license_name) > 2:
                    return license_name
        
        # Final fallback: return first line if it's not too long
        if first_line and len(first_line) < 100:
            return first_line
        
        return license_text_normalized.strip()
