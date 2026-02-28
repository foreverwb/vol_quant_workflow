"""
Bridge client for fetching bridge snapshot parameters.
"""

import json
import logging
import urllib.parse
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, List

from ..config.settings import get_settings


class BridgeClientError(RuntimeError):
    """Bridge client protocol/request error."""


class BridgeClient:
    """HTTP client wrapper for BridgeSnapshot retrieval."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 6.0):
        settings = get_settings()
        self.base_url = (base_url or settings.provider_api_base).rstrip("/")
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

    @staticmethod
    def _normalize_symbols(
        symbols: Optional[List[str]] = None,
        symbol: Optional[str] = None,
    ) -> Optional[List[str]]:
        out: List[str] = []
        if isinstance(symbols, list):
            for item in symbols:
                if isinstance(item, str) and item.strip():
                    normalized = item.strip().upper()
                    if normalized not in out:
                        out.append(normalized)
        if isinstance(symbol, str) and symbol.strip():
            normalized = symbol.strip().upper()
            if normalized not in out:
                out.append(normalized)
        return out or None

    def get_bridge_batch(
        self,
        date: Optional[str],
        symbols: Optional[List[str]] = None,
        limit: Optional[int] = None,
        symbol: Optional[str] = None,
    ) -> list:
        """Fetch batch bridge payloads; return normalized list or empty list on failure."""
        body: Dict[str, Any] = {
            "source": "vol",
        }
        if date:
            body["date"] = date
        normalized_symbols = self._normalize_symbols(symbols=symbols, symbol=symbol)
        if normalized_symbols:
            body["symbols"] = normalized_symbols
        if limit is not None:
            body["limit"] = limit

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

    def get_bridge_single_via_batch(self, symbol: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch one symbol via batch endpoint and return row['bridge'] only.

        Raises BridgeClientError when no valid bridge row exists.
        """
        symbol_u = symbol.upper()
        effective_date = date or "latest"

        rows = self.get_bridge_batch(
            date=date,
            symbols=[symbol_u],
            limit=1,
        )
        if not rows:
            raise BridgeClientError(
                f"No bridge batch result for symbol {symbol_u} on {effective_date}."
            )

        row = rows[0]
        bridge = row.get("bridge") if isinstance(row, dict) else None
        if not isinstance(bridge, dict):
            raise BridgeClientError(
                f"Bridge batch row missing 'bridge' object for symbol {symbol_u} on {effective_date}."
            )
        return bridge

    def get_bridge(self, symbol: str, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Backward-compatible single-symbol helper.
        Internally routed to batch endpoint.
        """
        try:
            return self.get_bridge_single_via_batch(symbol=symbol, date=date)
        except BridgeClientError as exc:
            self._logger.debug("Bridge single fetch failed for %s: %s", symbol, exc)
            return None
