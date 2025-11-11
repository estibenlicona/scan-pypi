"""
Logger Adapter - Implements LoggerPort using Python logging.
"""

from __future__ import annotations
import logging
import json
from typing import Any

from src.domain.ports import LoggerPort
from src.infrastructure.config.settings import LoggingSettings


class LoggerAdapter(LoggerPort):
    """Standard Python logging adapter."""
    
    def __init__(self, settings: LoggingSettings, name: str = "pypi_scanner") -> None:
        self.settings = settings
        self.logger = logging.getLogger(name)
        self._configure_logger()
    
    def _configure_logger(self) -> None:
        """Configure the logger with appropriate format and level."""
        self.logger.setLevel(getattr(logging, self.settings.level))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create console handler
        handler = logging.StreamHandler()
        
        if self.settings.format_type == "json":
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, kwargs)
    
    def _log(self, level: int, message: str, context: dict[str, Any]) -> None:
        """Log message with context."""
        if self.settings.format_type == "json":
            # For JSON format, pass context as extra
            self.logger.log(level, message, extra={"context": context})
        else:
            # For text format, format context into message
            if context:
                context_str = " | ".join(f"{k}={v}" for k, v in context.items())
                message = f"{message} | {context_str}"
            self.logger.log(level, message)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        
        # Add context if available
        if hasattr(record, 'context') and record.context:
            log_data.update(record.context)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)