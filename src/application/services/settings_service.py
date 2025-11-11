"""
Application services - Orchestration and coordination between domain and infrastructure.
"""

from __future__ import annotations
from src.domain.entities import Policy
from src.infrastructure.config import Settings, get_settings


class SettingsService:
    """Service for loading and managing application settings."""
    
    def load_settings(self) -> Settings:
        """Load settings from environment and configuration."""
        return get_settings()
    
    def create_policy(self, settings: Settings) -> Policy:
        """Create a Policy domain entity from settings."""
        return Policy(
            name="Default Policy",
            description="Policy derived from environment settings",
            maintainability_years_threshold=settings.policy.maintainability_years_threshold,
            blocked_licenses=settings.policy.blocked_licenses
        )