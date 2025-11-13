"""
OSV.dev API Adapter - Implements VulnerabilityScannerPort using OSV.dev API.

Queries the OSV.dev API (api.osv.dev) for vulnerabilities in Python packages.
Uses batch queries for optimal performance.
"""

from __future__ import annotations
import json
import asyncio
from typing import Dict, Any, List, Optional
import aiohttp

from src.domain.ports import VulnerabilityscannerPort, LoggerPort
from src.domain.entities import Vulnerability, SeverityLevel


class OSVAdapter(VulnerabilityscannerPort):
    """Adapter for OSV.dev vulnerability scanning using batch queries."""
    
    def __init__(self, logger: LoggerPort) -> None:
        """Initialize OSV adapter."""
        self.logger = logger
        self.query_url = "https://api.osv.dev/v1/query"
        self.batch_url = "https://api.osv.dev/v1/querybatch"
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.batch_size = 100  # OSV can handle multiple queries, keep it reasonable
    
    async def scan_vulnerabilities(
        self, 
        requirements_content: str
    ) -> Dict[str, Any]:
        """
        Scan vulnerabilities using OSV.dev batch API.
        
        Parses requirements.txt and queries OSV using batch endpoint for efficiency.
        
        Args:
            requirements_content: Content of requirements.txt file
            
        Returns:
            Dictionary with vulnerabilities and dependency information
        """
        self.logger.info("Starting OSV vulnerability scan")
        
        # Parse requirements
        packages = self._parse_requirements(requirements_content)
        
        if not packages:
            self.logger.warning("No packages found in requirements")
            return {"vulnerabilities": {}}
        
        self.logger.info(f"Querying OSV for {len(packages)} packages using batch API")
        
        vulnerabilities_map: Dict[str, List[Dict[str, Any]]] = {}
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            # Process packages in batches
            for i in range(0, len(packages), self.batch_size):
                batch = packages[i:i + self.batch_size]
                try:
                    batch_results = await self._query_batch(session, batch)
                    vulnerabilities_map.update(batch_results)
                except Exception as e:
                    self.logger.warning(f"Error in batch query: {e}")
                    # Fallback to individual queries for this batch
                    for package_name, version in batch:
                        try:
                            vulns = await self._query_single(session, package_name, version)
                            if vulns:
                                vulnerabilities_map[f"{package_name}@{version}"] = vulns
                        except Exception as e2:
                            self.logger.debug(f"Error querying {package_name}: {e2}")
        
        self.logger.info(
            f"OSV scan completed. Found {len(vulnerabilities_map)} packages with vulnerabilities"
        )
        
        return {
            "vulnerabilities": vulnerabilities_map,
            "packages": packages
        }
    
    async def _query_batch(
        self,
        session: aiohttp.ClientSession,
        packages: List[tuple[str, str]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query multiple packages using OSV batch endpoint.
        
        Handles pagination for large result sets.
        """
        vulnerabilities_map: Dict[str, List[Dict[str, Any]]] = {}
        
        # Build initial batch payload
        queries = [
            {
                "package": {
                    "name": package_name,
                    "ecosystem": "PyPI"
                },
                "version": version
            }
            for package_name, version in packages
        ]
        
        # Process batch with pagination handling
        next_page_tokens: Dict[int, str] = {}
        
        while True:
            # Update queries with page tokens if present
            for idx, token in next_page_tokens.items():
                queries[idx]["page_token"] = token
            
            payload = {"queries": queries}
            
            try:
                async with session.post(self.batch_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Process results
                        for idx, result in enumerate(data.get("queries", [])):
                            package_name = packages[idx][0]
                            version = packages[idx][1]
                            key = f"{package_name}@{version}"
                            
                            vulns = result.get("vulns", [])
                            if key in vulnerabilities_map:
                                vulnerabilities_map[key].extend(vulns)
                            else:
                                vulnerabilities_map[key] = vulns
                            
                            # Check for pagination
                            if result.get("page_token"):
                                next_page_tokens[idx] = result["page_token"]
                            elif idx in next_page_tokens:
                                del next_page_tokens[idx]
                            
                            if vulns:
                                self.logger.debug(
                                    f"Found {len(vulns)} vulnerabilities for {key}"
                                )
                        
                        # If no more pagination tokens, we're done
                        if not next_page_tokens:
                            break
                        
                        # Prepare for next batch of paginated results
                        # Keep only paginated queries
                        queries = [
                            {
                                "package": {
                                    "name": packages[idx][0],
                                    "ecosystem": "PyPI"
                                },
                                "version": packages[idx][1]
                            }
                            for idx in next_page_tokens.keys()
                        ]
                    else:
                        self.logger.warning(
                            f"OSV batch endpoint returned status {response.status}"
                        )
                        return vulnerabilities_map
            except asyncio.TimeoutError:
                self.logger.warning("Timeout querying OSV batch endpoint")
                return vulnerabilities_map
            except Exception as e:
                self.logger.warning(f"Error querying OSV batch endpoint: {e}")
                return vulnerabilities_map
        
        return vulnerabilities_map
    
    async def _query_single(
        self,
        session: aiohttp.ClientSession,
        package_name: str,
        version: str
    ) -> List[Dict[str, Any]]:
        """Fallback: Query single package using individual query endpoint."""
        payload = {
            "package": {
                "name": package_name,
                "ecosystem": "PyPI"
            },
            "version": version
        }
        
        try:
            async with session.post(self.query_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("vulns", [])
                else:
                    self.logger.debug(
                        f"OSV returned status {response.status} for {package_name}@{version}"
                    )
                    return []
        except asyncio.TimeoutError:
            self.logger.debug(f"Timeout querying OSV for {package_name}@{version}")
            return []
        except Exception as e:
            self.logger.debug(f"Error querying OSV: {e}")
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
