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
            
            # Fetch latest version from PyPI
            latest_version = await self._fetch_latest_version(package.identifier.name)
            if latest_version:
                enriched_package.latest_version = latest_version
            
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
        """Fetch metadata from PyPI API.
        
        Tries to fetch specific version first, falls back to latest version if not found.
        """
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
                self.logger.debug(f"Timeout fetching PyPI data for {package_name}@{version}")
                return None
            except Exception as e:
                self.logger.debug(f"Error fetching PyPI data for {package_name}@{version}: {e}")
                return None
    
    async def fetch_latest_version(self, package_name: str) -> Optional[str]:
        """Public method to fetch latest version of a package from PyPI."""
        return await self._fetch_latest_version(package_name)
    
    async def _fetch_latest_version(self, package_name: str) -> Optional[str]:
        """Fetch the latest version of a package from PyPI."""
        url = f"{self.settings.pypi_base_url}/{package_name}/json"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout)) as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # PyPI returns latest version in info.version
                        return data.get("info", {}).get("version")
                    else:
                        self.logger.debug(f"PyPI API returned {response.status} for {package_name} (may be pre-release or local version)")
                        return None
            except asyncio.TimeoutError:
                self.logger.debug(f"Timeout fetching latest version for {package_name}")
                return None
            except Exception as e:
                self.logger.debug(f"Error fetching latest version for {package_name}: {e}")
                return None
    
    async def _fetch_github_metadata(self, github_url: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata from GitHub API with authentication support."""
        # Extract repo info from GitHub URL
        repo_match = re.match(r'https://github\.com/([^/]+)/([^/]+)', github_url)
        if not repo_match:
            return None
        
        owner, repo = repo_match.groups()
        api_url = f"{self.settings.github_base_url}/repos/{owner}/{repo}"
        
        # Build headers with authentication if token available
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        # Add authentication token if available (increases rate limit from 60 to 5000 requests/hour)
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout)) as session:
            try:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 403:
                        # Rate limit exceeded
                        remaining = response.headers.get("X-RateLimit-Remaining", "0")
                        reset_timestamp = response.headers.get("X-RateLimit-Reset", "unknown")
                        self.logger.warning(
                            f"GitHub API rate limit exceeded for {owner}/{repo}. "
                            f"Remaining: {remaining}, Reset: {reset_timestamp}"
                        )
                        return None
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
        
        # Normalize and extract license name
        license_name = self._safe_str(license_name)  # Clean up whitespace
        
        # If license is empty, try license_expression as fallback
        if not license_name:
            license_expression = info.get("license_expression")
            license_name = self._safe_str(license_expression)
        
        # If still empty, try to extract from classifiers
        if not license_name:
            classifiers = info.get("classifiers", [])
            if isinstance(classifiers, list):
                for classifier in classifiers:
                    if isinstance(classifier, str) and "License ::" in classifier:
                        # Extract license name from classifier like "License :: OSI Approved :: BSD License"
                        parts = classifier.split("::")
                        if len(parts) >= 3:
                            license_name = parts[-1].strip()
                            break
        
        # Extract proper license name from full text if necessary
        if license_name:
            license_name = self._extract_license_name_from_text(license_name)
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
            latest_version=package.latest_version,  # Preserve existing latest_version
            dependencies=package.dependencies  # Preserve existing dependencies
        )
    
    def _merge_github_data(self, package: Package, github_data: Dict[str, Any]) -> Package:
        """Merge GitHub data into package."""
        # Extract license from GitHub: try 'key' (SPDX) then 'name' as fallback
        github_license_str = None
        if "license" in github_data:
            license_obj = github_data.get("license")
            if isinstance(license_obj, dict) and license_obj:
                # Try SPDX identifier first (e.g., "mit", "apache-2.0")
                github_license_str = license_obj.get("key")
                # Fallback to full name if key not available (e.g., "MIT License")
                if not github_license_str:
                    github_license_str = license_obj.get("name")
        
        # Normalize license to string or None
        github_license_str = self._safe_str(github_license_str)
        
        # Normalize SPDX license format (lowercase → proper case)
        if github_license_str:
            github_license_str = self._normalize_spdx_license(github_license_str)
        
        # Determine final license: use package.license if available, else create from github_license_str
        final_license = package.license
        if final_license is None and github_license_str:
            # Create License object from GitHub data if PyPI license was not found
            final_license = License(
                name=github_license_str,
                license_type=self._parse_license_type(github_license_str)
            )
        
        # Create updated package
        result = Package(
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
            latest_version=package.latest_version,  # Preserve latest_version
            dependencies=package.dependencies
        )

        return result
    
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
