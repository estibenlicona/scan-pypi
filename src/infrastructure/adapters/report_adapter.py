"""
Report Sink Adapter - Implements ReportSinkPort for saving reports to disk.
"""

from __future__ import annotations
import json
import os
from typing import Optional, Any
from dataclasses import is_dataclass, asdict

from src.domain.entities import AnalysisResult, Package
from src.domain.ports import ReportSinkPort, LoggerPort
from src.infrastructure.config.settings import ReportSettings
from src.application.dtos import ReportDTO


class FileReportSinkAdapter(ReportSinkPort):
    """File system report sink implementation."""
    
    def __init__(self, settings: ReportSettings, logger: LoggerPort) -> None:
        self.settings = settings
        self.logger = logger
    
    async def save_report(self, result, format_type: str = "json") -> str:
        """Save analysis result or report DTO to file system.

        Accepts either a domain AnalysisResult or an application ReportDTO/dataclass.
        This makes the adapter tolerant to both eventualities in the call chain.
        """
        output_path = self.settings.output_path
        
        try:
            # Support both domain AnalysisResult and dataclass ReportDTO
            if isinstance(result, ReportDTO):
                # Convert ReportDTO to plain dict
                report_data = asdict(result)
            elif isinstance(result, AnalysisResult):
                # Use existing converter for domain AnalysisResult
                report_data = self._convert_to_dict(result)
            else:
                # Fallback for other dataclasses
                report_data = self._convert_to_dict(result)
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                if format_type.lower() == "json":
                    json.dump(report_data, f, indent=2, ensure_ascii=False)
                else:
                    f.write(str(report_data))
            
            self.logger.info(f"Report saved to {output_path}")
            return os.path.abspath(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
            raise

    async def load_report(self, location: str) -> Optional[AnalysisResult]:
        """Load analysis result from file system."""
        try:
            with open(location, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # This would require implementing conversion back to domain entities
            # For now, just log that it would be loaded
            self.logger.info(f"Report loaded from {location}")
            return None  # TODO: Implement proper deserialization
            
        except Exception as e:
            self.logger.warning(f"Failed to load report from {location}: {e}")
            return None

    def _convert_to_dict(self, result: AnalysisResult) -> dict[str, Any]:
        """Convert AnalysisResult to dictionary for serialization."""
        # Convert vulnerabilities
        vulnerabilities = []
        for vuln in result.vulnerabilities:
            vuln_dict = {
                "id": vuln.id,
                "title": vuln.title,
                "description": vuln.description,
                "severity": vuln.severity.value,
                "packageName": vuln.package_name,
                "version": vuln.version,
                "type": "vulnerability"
            }
            if vuln.license:
                vuln_dict["license"] = vuln.license.name
            vulnerabilities.append(vuln_dict)
        
        # Convert packages
        all_packages = result.get_all_packages()
        packages = [self._package_to_dict(pkg) for pkg in all_packages]
        
        # Convert maintained packages
        filtered_packages = [self._package_to_dict(pkg) for pkg in result.maintained_packages]
        
        return {
            "timestamp": result.timestamp.isoformat(),
            "vulnerabilities": vulnerabilities,
            "packages": packages,
            "filtered_packages": filtered_packages
        }
    
    def _package_to_dict(self, package: Package) -> dict[str, Any]:
        """Convert Package to dictionary."""
        return {
            "package": package.identifier.name,
            "version": package.identifier.version,
            "license": package.license.name if package.license else None,
            "upload_time": package.upload_time.isoformat() if package.upload_time else None,
            "summary": package.summary,
            "home_page": package.home_page,
            "author": package.author,
            "author_email": package.author_email,
            "maintainer": package.maintainer,
            "maintainer_email": package.maintainer_email,
            "keywords": package.keywords,
            "classifiers": package.classifiers,
            "requires_dist": package.requires_dist,
            "project_urls": package.project_urls,
            "dependencies": [str(dep) for dep in package.dependencies],
            "license_rejected": package.license.is_rejected if package.license else False
        }