"""
Snyk CLI Adapter - Implements VulnerabilityscannerPort using Snyk CLI.
"""

from __future__ import annotations
import subprocess
import json
import tempfile
import os
from typing import Dict, Any, Tuple, List

from src.domain.ports import VulnerabilityscannerPort, LoggerPort
from src.infrastructure.config.settings import SnykSettings


class SnykCLIAdapter(VulnerabilityscannerPort):
    """Adapter for Snyk CLI vulnerability scanning."""
    
    def __init__(self, settings: SnykSettings, logger: LoggerPort) -> None:
        self.settings = settings
        self.logger = logger
    
    async def scan_vulnerabilities(
        self, 
        requirements_content: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Scan vulnerabilities using Snyk CLI.
        
        Organization is handled internally from configuration.
        This encapsulates Snyk-specific details from the domain layer.
        """
        self.logger.info(
            f"Starting Snyk vulnerability scan for organization: {self.settings.org}"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write requirements to file
            requirements_path = os.path.join(temp_dir, "requirements.txt")
            with open(requirements_path, 'w', encoding='utf-8') as f:
                f.write(requirements_content)
            
            self.logger.debug(f"Created requirements file: {requirements_path}")
            
            # Build Snyk command
            cmd = [
                self.settings.path,
                'test',
                '--json',
                f'--org={self.settings.org}',
                '--print-deps',
                f'--file={requirements_path}'
            ]
            
            try:
                self.logger.debug(f"Executing Snyk command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.settings.timeout,
                    cwd=temp_dir
                )
                
                self.logger.debug(f"Snyk exit code: {result.returncode}")
                
                # Parse JSON output
                if result.stdout:
                    try:
                        json_output = json.loads(result.stdout)
                        
                        # Snyk returns dependencies and vulnerabilities in the same output
                        dependencies = self._extract_dependencies(json_output)
                        vulnerabilities = self._extract_vulnerabilities(json_output)
                        
                        self.logger.info(
                            f"Snyk scan completed",
                            dependencies_count=len(dependencies.get("dependencies", [])),
                            vulnerabilities_count=len(vulnerabilities.get("vulnerabilities", []))
                        )
                        
                        return dependencies, vulnerabilities
                        
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse Snyk JSON output: {e}")
                        raise RuntimeError(f"Invalid JSON from Snyk: {e}")
                else:
                    self.logger.warning("Snyk produced no output")
                    return {"dependencies": []}, {"vulnerabilities": []}
                
            except subprocess.TimeoutExpired:
                error_msg = f"Snyk scan timed out after {self.settings.timeout} seconds"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            except subprocess.CalledProcessError as e:
                error_msg = f"Snyk scan failed with exit code {e.returncode}: {e.stderr}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            except Exception as e:
                error_msg = f"Unexpected error during Snyk scan: {e}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
    
    def _extract_dependencies(self, json_output: Dict[str, Any]) -> Dict[str, Any]:
        """Extract dependency information from Snyk output."""
        # Snyk's JSON structure varies, but typically includes dependency graph
        dependencies = []
        
        # Look for dependency graph in various possible locations
        if "dependencyGraph" in json_output:
            dep_graph = json_output["dependencyGraph"]
            dependencies = self._parse_dependency_graph(dep_graph)
        elif "dependencies" in json_output:
            dependencies = json_output["dependencies"]
        
        return {"dependencies": dependencies}
    
    def _extract_vulnerabilities(self, json_output: Dict[str, Any]) -> Dict[str, Any]:
        """Extract vulnerability information from Snyk output."""
        vulnerabilities = []
        
        if "vulnerabilities" in json_output:
            vulnerabilities = json_output["vulnerabilities"]
        
        return {"vulnerabilities": vulnerabilities}
    
    def _parse_dependency_graph(self, dep_graph: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Snyk's dependency graph format."""
        dependencies: List[Dict[str, Any]] = []
        
        # This is a simplified parser - Snyk's actual format is complex
        # The original code would need to be adapted here
        if "nodes" in dep_graph:
            for _, node_data in dep_graph["nodes"].items():
                if node_data.get("info"):
                    info = node_data["info"]
                    dependency: Dict[str, Any] = {
                        "name": info.get("name", ""),
                        "version": info.get("version", ""),
                        "dependencies": []
                    }
                    dependencies.append(dependency)
        
        return dependencies