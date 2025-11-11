"""
Clock Adapter - Implements ClockPort for time operations.
"""

from __future__ import annotations
from datetime import datetime, timezone

from src.domain.ports import ClockPort


class SystemClockAdapter(ClockPort):
    """System clock implementation."""
    
    def now(self) -> datetime:
        """Get current datetime."""
        return datetime.now(timezone.utc)