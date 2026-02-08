"""
Bridge client for fetching bridge snapshot parameters.
"""

import json
import logging
import urllib.parse
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from ..config.settings import get_settings


class BridgeClient:
    """HTTP client wrapper for BridgeSnapshot retrieval."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 6.0):
        settings = get_settings()
        self.base_url = (base_url or settings.va_api_base).rstrip("/")
        self.timeout = timeout
        self._logger = logging.getLogger(__name__)

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        query = urllib.parse.urlencode(params or {})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                payload = resp.read()
                return json.loads(payload)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
            self._logger.debug("Bridge request failed for %s: %s", url, exc)
            return None

    def _post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        payload = json.dumps(body or {}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
            self._logger.debug("Bridge request failed for %s: %s", url, exc)
            return None

    def get_bridge(self, symbol: str, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch bridge snapshot; return bridge dict or None on any failure."""
        params = {"source": "vol"}
        if date:
            params["date"] = date
        data = self._get(f"/api/bridge/params/{symbol.upper()}", params=params)
        if not isinstance(data, dict):
            self._logger.debug("Bridge response missing or invalid for %s", symbol)
            return None

        if data.get("success") is True and isinstance(data.get("bridge"), dict):
            return data["bridge"]

        self._logger.debug("Bridge response unsuccessful for %s", symbol)
        return None

    def get_bridge_batch(
        self,
        date: str,
        limit: Optional[int] = None,
        symbol: Optional[str] = None,
    ) -> list:
        """Fetch batch bridge payloads; return normalized list or empty list on failure."""
        body: Dict[str, Any] = {
            "date": date,
            "source": "vol",
        }
        if limit is not None:
            body["limit"] = limit
        if symbol:
            body["symbol"] = symbol.upper()

        data = self._post("/api/bridge/batch", body=body)
        if not isinstance(data, dict):
            self._logger.debug("Batch bridge response missing or invalid for %s", date)
            return []

        if data.get("success") is not True:
            self._logger.debug("Batch bridge response unsuccessful for %s", date)
            return []

        results = data.get("results")
        if not isinstance(results, list):
            self._logger.debug("Batch bridge response has no results list for %s", date)
            return []

        normalized = []
        for item in results:
            if not isinstance(item, dict):
                continue
            symbol = item.get("symbol")
            bridge = item.get("bridge")
            if isinstance(symbol, str) and isinstance(bridge, dict):
                normalized.append(item)

        return normalized
