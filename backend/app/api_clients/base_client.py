"""
Base async HTTP client used by all upstream Gadgets360 API clients.

Provides shared request handling, timeout configuration, auth headers,
and graceful degradation: if the upstream API is unreachable or returns
an error, the client raises UpstreamAPIError so the orchestrator layer
can decide how to handle it, rather than silently failing.
"""

from typing import Any, Dict, Optional

import httpx

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UpstreamAPIError(Exception):
    """Raised when an upstream Gadgets360 API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BaseAPIClient:
    """Shared HTTP request logic for all upstream API clients."""

    def __init__(self, base_url: str, timeout: Optional[float] = None):
        # Do NOT unconditionally strip the trailing slash here. Some
        # upstream endpoints (e.g. the NDTV reviews feed's
        # ".../client_key/<key>/" path) require that trailing slash as a
        # meaningful part of the path — stripping it silently changes
        # the URL being requested and can break routing on the server
        # side. Callers that don't need a trailing slash simply won't
        # have one in their configured base_url.
        self.base_url = base_url
        self.timeout = timeout or settings.UPSTREAM_REQUEST_TIMEOUT

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if settings.UPSTREAM_API_KEY:
            headers["Authorization"] = f"Bearer {settings.UPSTREAM_API_KEY}"
        return headers

    def _build_url(self, path: str) -> str:
        """
        Join base_url + path without disturbing a meaningful trailing
        slash on base_url when there's no extra path to append (e.g.
        base_url already points directly at a script/endpoint).
        """
        if path.lstrip("/"):
            return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        return self.base_url

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Perform an async GET request against the upstream API."""
        url = self._build_url(path)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=self._headers())
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("Upstream HTTP error for %s: %s", url, exc)
            raise UpstreamAPIError(
                f"Upstream API returned an error for {url}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("Upstream request failed for %s: %s", url, exc)
            raise UpstreamAPIError(f"Failed to reach upstream API at {url}") from exc

    async def post(self, path: str, json_body: Optional[Dict[str, Any]] = None) -> Any:
        """Perform an async POST request against the upstream API."""
        url = self._build_url(path)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=json_body, headers=self._headers())
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("Upstream HTTP error for %s: %s", url, exc)
            raise UpstreamAPIError(
                f"Upstream API returned an error for {url}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("Upstream request failed for %s: %s", url, exc)
            raise UpstreamAPIError(f"Failed to reach upstream API at {url}") from exc
