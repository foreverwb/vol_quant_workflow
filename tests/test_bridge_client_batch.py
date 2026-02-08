"""
Tests for BridgeClient batch endpoint wrapper.
"""

import unittest
from unittest.mock import patch

from ..integrations.bridge_client import BridgeClient


class TestBridgeClientBatch(unittest.TestCase):
    def test_get_bridge_batch_posts_and_normalizes(self):
        client = BridgeClient(base_url="http://127.0.0.1:9999")
        api_response = {
            "success": True,
            "results": [
                {"symbol": "AAPL", "bridge": {"market_state": {"hv20": 0.2}}},
                {"symbol": "MSFT", "bridge": {"market_state": {"hv20": 0.18}}},
                {"symbol": "BAD1", "bridge": None},
                {"symbol": None, "bridge": {"market_state": {}}},
                "invalid",
            ],
        }

        with patch.object(client, "_post", return_value=api_response) as mock_post:
            rows = client.get_bridge_batch(date="2026-01-05", limit=20)

        mock_post.assert_called_once_with(
            "/api/bridge/batch",
            body={"date": "2026-01-05", "source": "vol", "limit": 20},
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["symbol"], "AAPL")
        self.assertEqual(rows[1]["symbol"], "MSFT")

    def test_get_bridge_batch_includes_symbol_filter_when_provided(self):
        client = BridgeClient(base_url="http://127.0.0.1:9999")
        with patch.object(client, "_post", return_value={"success": True, "results": []}) as mock_post:
            client.get_bridge_batch(date="2026-01-05", limit=5, symbol="aapl")

        mock_post.assert_called_once_with(
            "/api/bridge/batch",
            body={"date": "2026-01-05", "source": "vol", "limit": 5, "symbol": "AAPL"},
        )
