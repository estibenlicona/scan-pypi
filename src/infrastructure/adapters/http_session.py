"""Shared aiohttp session factory.

The corporate TLS-intercepting proxy presents certificates signed by a CA that
is not in the trust store, so certificate verification is disabled — same stance
as ``pypi_info.py`` (``SSL_VERIFY = False``).
"""
from __future__ import annotations
import aiohttp

# Disable TLS certificate verification (corporate intercepting proxy).
SSL_VERIFY = False


def make_client_session(
    timeout: aiohttp.ClientTimeout | None = None,
) -> aiohttp.ClientSession:
    """Return a ClientSession honoring the SSL_VERIFY flag.

    ``ssl=False`` skips certificate validation but still uses TLS. The connector
    is owned and closed by the session on ``async with`` exit.
    """
    return aiohttp.ClientSession(
        timeout=timeout,
        connector=aiohttp.TCPConnector(ssl=SSL_VERIFY),
    )
