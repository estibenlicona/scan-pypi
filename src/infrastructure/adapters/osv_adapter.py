"""
OSV.dev API Adapter - Implements VulnerabilityScannerPort using OSV.dev API.

Queries the OSV.dev API (api.osv.dev) for vulnerabilities in Python packages.
"""

from __future__ import annotations
import json
from typing import Dict, Any, List, Optional
import aiohttp

from src.domain.ports import VulnerabilityscannerPort, LoggerPort
from src.domain.entities import Vulnerability, SeverityLevel


class OSVAdapter(VulnerabilityscannerPort):
    """Adapter for OSV.dev vulnerability scanning."""
    
    def __init__(self, logger: LoggerPort) -> None:
        """Initialize OSV adapter."""
        self.logger = logger
        self.api_url = "https://api.osv.dev/v1/query"
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def scan_vulnerabilities(
        self, 
        requirements_content: str,
        organization: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scan vulnerabilities using OSV.dev API.
        
        Parses requirements.txt format and queries OSV for each package.
        
        Args:
            requirements_content: Content of requirements.txt file
            organization: Organization name (unused for OSV, kept for compatibility)
            
        Returns:
            Dictionary with vulnerabilities and dependency information
        """
        self.logger.info("Starting OSV vulnerability scan")
        
        # Parse requirements
        packages = self._parse_requirements(requirements_content)
        
        if not packages:
            self.logger.warning("No packages found in requirements")
            return {"vulnerabilities": {}}
        
        self.logger.info(f"Querying OSV for {len(packages)} packages")
        
        # Query OSV for each package
        vulnerabilities_map: Dict[str, List[Dict[str, Any]]] = {}
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for package_name, version in packages:
                try:
                    vulns = await self._query_osv(
                        session, 
                        package_name, 
                        version
                    )
                    if vulns:
                        vulnerabilities_map[f"{package_name}@{version}"] = vulns
                        self.logger.debug(
                            f"Found {len(vulns)} vulnerabilities for {package_name}@{version}"
                        )
                except Exception as e:
                    self.logger.warning(
                        f"Error querying OSV for {package_name}@{version}: {e}"
                    )
                    # Continue with next package on error
        
        self.logger.info(
            f"OSV scan completed. Found {len(vulnerabilities_map)} packages with vulnerabilities"
        )
        
        return {
            "vulnerabilities": vulnerabilities_map,
            "packages": packages
        }
    
    async def _query_osv(
        self,
        session: aiohttp.ClientSession,
        package_name: str,
        version: str
    ) -> List[Dict[str, Any]]:
        """Query OSV API for a specific package version."""
        payload = {
            "package": {
                "name": package_name,
                "ecosystem": "PyPI"
            },
            "version": version
        }
        
        try:
            async with session.post(self.api_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    vulns = data.get("vulns", [])
                    return vulns
                else:
                    self.logger.debug(
                        f"OSV returned status {response.status} for {package_name}@{version}"
                    )
                    return []
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout querying OSV for {package_name}@{version}")
            return []
        except Exception as e:
            self.logger.warning(f"Error querying OSV: {e}")
            return []
    
    def _parse_requirements(
        self, 
        content: str
    ) -> List[tuple[str, str]]:
        """Parse requirements.txt format into (name, version) tuples."""
        packages: List[tuple[str, str]] = []
        
        for line in content.split("\n"):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            
            # Handle various version specifiers
            # Format: package==version or package>=version,<version or just package
            for sep in ["==", ">=", "<=", ">", "<", "~=", "!="]:
                if sep in line:
                    parts = line.split(sep)
                    name = parts[0].strip()
                    # Extract version (first part after separator, removing other specifiers)
                    version_part = parts[1].split(",")[0].strip()
                    packages.append((name, version_part))
                    break
            else:
                # No version specifier found
                packages.append((line, "*"))
        
        return packages


# Add asyncio import at module level for timeout handling
import asyncio
