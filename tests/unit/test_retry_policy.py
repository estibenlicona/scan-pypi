"""Unit tests for RetryPolicy – exponential backoff, jitter, exhaustion."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.utilities.retry_policy import RetryPolicy


# ── Helpers ──────────────────────────────────────────────────────────


def _make_policy(
    max_retries: int = 3,
    base_delay: float = 0.01,
    max_delay: float = 0.1,
) -> RetryPolicy:
    """Create a fast retry policy for testing (tiny delays)."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    return RetryPolicy(
        max_retries=max_retries,
        base_delay_seconds=base_delay,
        max_delay_seconds=max_delay,
        logger=logger,
    )


# ── Tests ────────────────────────────────────────────────────────────


class TestRetryPolicyExecute:
    """Tests for RetryPolicy.execute()."""

    @pytest.mark.asyncio
    async def test_succeeds_first_attempt(self):
        policy = _make_policy()
        func = AsyncMock(return_value="ok")
        result = await policy.execute(func)
        assert result == "ok"
        assert func.await_count == 1

    @pytest.mark.asyncio
    async def test_succeeds_after_retries(self):
        policy = _make_policy(max_retries=3)
        func = AsyncMock(side_effect=[ValueError, ValueError, "ok"])
        result = await policy.execute(func)
        assert result == "ok"
        assert func.await_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_all_retries_raises(self):
        policy = _make_policy(max_retries=2)
        func = AsyncMock(side_effect=RuntimeError("fail"))
        with pytest.raises(RuntimeError, match="fail"):
            await policy.execute(func)
        # initial + 2 retries = 3 calls
        assert func.await_count == 3

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        policy = _make_policy()

        async def my_func(a, b, key=None):
            return (a, b, key)

        result = await policy.execute(my_func, 1, 2, key="val")
        assert result == (1, 2, "val")

    @pytest.mark.asyncio
    async def test_logs_warning_on_exhaustion(self):
        policy = _make_policy(max_retries=1)
        func = AsyncMock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError):
            await policy.execute(func)
        policy.logger.warning.assert_called()


class TestCalculateDelay:
    """Tests for RetryPolicy._calculate_delay()."""

    def test_exponential_backoff(self):
        policy = _make_policy(base_delay=1.0, max_delay=100.0)
        # attempt 0 → base * 2^0 + jitter = ~1.x
        # attempt 2 → base * 2^2 + jitter = ~4.x
        d0 = policy._calculate_delay(0)
        d2 = policy._calculate_delay(2)
        assert d0 >= 1.0
        assert d2 >= 4.0
        assert d2 > d0

    def test_capped_at_max_delay(self):
        policy = _make_policy(base_delay=1.0, max_delay=5.0)
        # attempt 10 → base * 2^10 = 1024, but capped at 5
        d = policy._calculate_delay(10)
        assert d <= 5.0

    def test_includes_jitter(self):
        """Two calls with same attempt should give different delays (random jitter)."""
        policy = _make_policy(base_delay=1.0, max_delay=100.0)
        delays = {policy._calculate_delay(0) for _ in range(20)}
        # With jitter, we should get multiple unique values
        assert len(delays) > 1
