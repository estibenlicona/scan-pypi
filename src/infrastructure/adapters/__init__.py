"""
Infrastructure adapters - External integrations implementing domain ports.
"""

# infrastructure/adapters/__init__.py
from .osv_adapter import OSVAdapter
from .pypi_adapter import PyPIClientAdapter
from .cache_adapter import CacheDiskAdapter
from .dependency_resolver_adapter import PipGripAdapter
from .logger_adapter import LoggerAdapter
from .clock_adapter import SystemClockAdapter
from .report_adapter import FileReportSinkAdapter

__all__ = [
    "OSVAdapter",
    "PyPIClientAdapter",
    "CacheDiskAdapter",
    "PipGripAdapter",
    "LoggerAdapter",
    "SystemClockAdapter",
    "FileReportSinkAdapter",
]
