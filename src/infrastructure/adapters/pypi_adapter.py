"""
PyPI Client Adapter - Implements MetadataProviderPort using PyPI API.
"""

from __future__ import annotations
import re
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List, cast
from typing import Any as TypingAny
from datetime import datetime

from src.domain.entities import Package, License, LicenseType
from src.domain.ports import MetadataProviderPort, LoggerPort
from src.infrastructure.config.settings import APISettings


class PyPIClientAdapter(MetadataProviderPort):
    """Adapter for PyPI API metadata enrichment."""
    
    def __init__(self, settings: APISettings, logger: LoggerPort) -> None:
        self.settings = settings
        self.logger = logger
    
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
            
            # Enrich with GitHub data if available
            if enriched_package.github_url:
                github_data = await self._fetch_github_metadata(enriched_package.github_url)
                if github_data:
                    enriched_package = self._merge_github_data(enriched_package, github_data)
            
            self.logger.debug(f"Successfully enriched {package.identifier}")
            return enriched_package
            
        except Exception as e:
            self.logger.error(f"Failed to enrich package {package.identifier}: {e}")
            return package  # Return original package if enrichment fails
    
    async def _fetch_pypi_metadata(self, package_name: str, version: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata from PyPI API."""
        url = f"{self.settings.pypi_base_url}/{package_name}/{version}/json"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout)) as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.warning(f"PyPI API returned {response.status} for {package_name}@{version}")
                        return None
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout fetching PyPI data for {package_name}@{version}")
                return None
            except Exception as e:
                self.logger.warning(f"Error fetching PyPI data for {package_name}@{version}: {e}")
                return None
    
    async def _fetch_github_metadata(self, github_url: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata from GitHub API."""
        # Extract repo info from GitHub URL
        repo_match = re.match(r'https://github\.com/([^/]+)/([^/]+)', github_url)
        if not repo_match:
            return None
        
        owner, repo = repo_match.groups()
        api_url = f"{self.settings.github_base_url}/repos/{owner}/{repo}"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout)) as session:
            try:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.warning(f"GitHub API returned {response.status} for {owner}/{repo}")
                        return None
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout fetching GitHub data for {owner}/{repo}")
                return None
            except Exception as e:
                self.logger.warning(f"Error fetching GitHub data for {owner}/{repo}: {e}")
                return None
    
    def _merge_pypi_data(self, package: Package, pypi_data: Dict[str, Any]) -> Package:
        """Merge PyPI data into package."""
        info = pypi_data.get("info") or {}
        if not isinstance(info, dict):
            self.logger.warning(f"Invalid 'info' structure from PyPI for {package.identifier}: got {type(info)}")
            return package
        
        # Parse license information
        license_name = info.get("license")
        license_type = None
        license_obj = None
        # Ensure license_name is a non-empty string before parsing to satisfy type checkers
        if isinstance(license_name, str) and license_name.strip():
            license_type = self._parse_license_type(license_name)
            license_obj = License(name=license_name, license_type=license_type)
        
        # Parse upload time
        upload_time = None
        if "urls" in pypi_data and pypi_data["urls"]:
            # Get upload time from first URL entry
            upload_time_str = pypi_data["urls"][0].get("upload_time")
            if upload_time_str:
                try:
                    upload_time = datetime.fromisoformat(upload_time_str.replace('Z', '+00:00'))
                except ValueError:
                    pass
        
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
            dependencies=package.dependencies  # Preserve existing dependencies
        )
    
    def _merge_github_data(self, package: Package, github_data: Dict[str, Any]) -> Package:
        """Merge GitHub data into package."""
        # Get license from GitHub
        github_license = None
        if "license" in github_data and github_data["license"]:
            github_license = github_data["license"].get("name")
        
        # Create updated package
        return Package(
            identifier=package.identifier,
            license=package.license,
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
            github_license=github_license,
            dependencies=package.dependencies
        )
    
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
        """Parse license type from license name."""
        if not license_name:
            return None
        
        license_lower = license_name.lower()
        
        if "mit" in license_lower:
            return LicenseType.MIT
        elif "apache" in license_lower:
            return LicenseType.APACHE_2_0
        elif "bsd" in license_lower:
            return LicenseType.BSD_3_CLAUSE
        elif "gpl" in license_lower and "3" in license_lower:
            return LicenseType.GPL_3_0
        elif "lgpl" in license_lower:
            return LicenseType.LGPL_2_1
        elif "mpl" in license_lower or "mozilla" in license_lower:
            return LicenseType.MPL_2_0
        else:
            return LicenseType.UNKNOWN
