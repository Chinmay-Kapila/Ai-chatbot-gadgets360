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
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout or settings.UPSTREAM_REQUEST_TIMEOUT

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if settings.UPSTREAM_API_KEY:
            headers["Authorization"] = f"Bearer {settings.UPSTREAM_API_KEY}"
        return headers

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Perform an async GET request against the upstream API."""
        url = f"{self.base_url}/{path.lstrip('/')}"

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
        url = f"{self.base_url}/{path.lstrip('/')}"

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
