"""
Retry Policy Utilities - Implements retry strategies with exponential backoff.

Provides resilient HTTP request handling with configurable retry logic.
"""

from __future__ import annotations
import asyncio
import random
from typing import TypeVar, Callable, Awaitable, Optional, Type
from src.domain.ports import LoggerPort

T = TypeVar('T')


class RetryPolicy:
    """Implements retry logic with exponential backoff and jitter."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        logger: Optional[LoggerPort] = None
    ):
        """
        Initialize retry policy.
        
        Args:
            max_retries: Maximum number of retry attempts (excluding initial attempt)
            base_delay_seconds: Base delay in seconds for exponential backoff
            max_delay_seconds: Maximum delay between retries
            logger: Optional logger for debug output
        """
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.logger = logger
    
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """
        Execute async function with retry policy.
        
        Retries up to max_retries times with exponential backoff + random jitter.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of successful function execution
            
        Raises:
            Last exception if all retries are exhausted
        """
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 0 and self.logger:
                    self.logger.debug(f"Retry successful on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Don't retry on the last attempt
                if attempt >= self.max_retries:
                    if self.logger:
                        self.logger.warning(
                            f"All {self.max_retries + 1} retry attempts exhausted",
                            error=str(e)
                        )
                    raise
                
                # Calculate delay with exponential backoff + random jitter
                delay = self._calculate_delay(attempt)
                
                if self.logger:
                    self.logger.debug(
                        f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s",
                        error=str(e)
                    )
                
                await asyncio.sleep(delay)
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected state in retry policy")
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and random jitter.
        
        Formula: min(base_delay * 2^attempt + random(0, 1), max_delay)
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: 2^attempt
        exponential_delay = self.base_delay_seconds * (2 ** attempt)
        
        # Add random jitter (0 to 1 second)
        jitter = random.uniform(0, 1.0)
        
        # Total delay with jitter
        total_delay = exponential_delay + jitter
        
        # Cap at max_delay
        return min(total_delay, self.max_delay_seconds)


# Default retry policy: 3 retries with 1-30 second delays
DEFAULT_RETRY_POLICY = RetryPolicy(
    max_retries=3,
    base_delay_seconds=1.0,
    max_delay_seconds=30.0
)
