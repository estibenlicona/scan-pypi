"""
Centralized configuration for the application.
Reads from environment variables with defaults and validation.
"""

from __future__ import annotations
import os
from typing import Optional, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass(frozen=True)
class CacheSettings:
    """Cache configuration."""
    enabled: bool = True
    directory: str = ".cache"
    ttl_hours: int = 24
    
    @classmethod
    def from_env(cls) -> CacheSettings:
        """Create CacheSettings from environment variables."""
        return cls(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            directory=os.getenv("CACHE_DIRECTORY", ".cache"),
            ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24"))
        )


@dataclass(frozen=True)
class PolicySettings:
    """Business policy configuration."""
    maintainability_years_threshold: int = 2
    blocked_licenses: List[str] = field(default_factory=list)
    max_vulnerability_severity: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> PolicySettings:
        """Create PolicySettings from environment variables."""
        # Parse blocked licenses from comma-separated string
        blocked_licenses_str = os.getenv("BLOCKED_LICENSES", "")
        blocked_licenses = [
            license.strip() for license in blocked_licenses_str.split(",")
            if license.strip()
        ]
        
        return cls(
            maintainability_years_threshold=int(os.getenv("MAINTAINED_YEARS", "2")),
            blocked_licenses=blocked_licenses,
            max_vulnerability_severity=os.getenv("MAX_VULNERABILITY_SEVERITY")
        )


@dataclass(frozen=True)
class APISettings:
    """External API configuration."""
    pypi_base_url: str = "https://pypi.org/pypi"
    github_base_url: str = "https://api.github.com"
    github_token: Optional[str] = None  # GitHub Personal Access Token for higher rate limits
    request_timeout: int = 10
    max_retries: int = 3
    
    @classmethod
    def from_env(cls) -> APISettings:
        """Create APISettings from environment variables."""
        return cls(
            github_token=os.getenv("GITHUB_TOKEN"),  # Load from env if available
            pypi_base_url=os.getenv("PYPI_BASE_URL", "https://pypi.org/pypi"),
            github_base_url=os.getenv("GITHUB_BASE_URL", "https://api.github.com"),
            request_timeout=int(os.getenv("API_REQUEST_TIMEOUT", "10")),
            max_retries=int(os.getenv("API_MAX_RETRIES", "3"))
        )


@dataclass(frozen=True)
class ReportSettings:
    """Report generation configuration."""
    output_path: str = "consolidated_report.json"
    format_type: str = "json"
    include_summary: bool = True
    
    @classmethod
    def from_env(cls) -> ReportSettings:
        """Create ReportSettings from environment variables."""
        return cls(
            output_path=os.getenv("REPORT_OUTPUT_PATH", "consolidated_report.json"),
            format_type=os.getenv("REPORT_FORMAT", "json"),
            include_summary=os.getenv("REPORT_INCLUDE_SUMMARY", "true").lower() == "true"
        )


@dataclass(frozen=True)
class LoggingSettings:
    """Logging configuration."""
    level: str = "INFO"
    format_type: str = "text"  # "text" or "json"
    
    @classmethod
    def from_env(cls) -> LoggingSettings:
        """Create LoggingSettings from environment variables."""
        return cls(
            level=os.getenv("LOG_LEVEL", "INFO").upper(),
            format_type=os.getenv("LOG_FORMAT", "text").lower()
        )


@dataclass(frozen=True)
class Settings:
    """Complete application settings."""
    cache: CacheSettings
    policy: PolicySettings
    api: APISettings
    report: ReportSettings
    logging: LoggingSettings
    dependency_resolver_type: str = "uv"  # "uv" or "pipgrip"
    
    @classmethod
    def from_env(cls) -> Settings:
        """Create complete Settings from environment variables."""
        return cls(
            cache=CacheSettings.from_env(),
            policy=PolicySettings.from_env(),
            api=APISettings.from_env(),
            report=ReportSettings.from_env(),
            logging=LoggingSettings.from_env(),
            dependency_resolver_type=os.getenv("DEPENDENCY_RESOLVER", "uv").lower()
        )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    global _settings
    load_dotenv(override=True)
    _settings = Settings.from_env()
    return _settings