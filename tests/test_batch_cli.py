"""
Tests for batch CLI behavior.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ..cli.batch import BatchHandler


class TestBatchCli(unittest.TestCase):
    def test_batch_writes_input_and_output_files_by_date(self):
        rows = [
            {
                "symbol": "AAPL",
                "bridge": {
                    "market_state": {"as_of": "2026-01-05T10:00:00", "hv20": 0.22},
                },
            },
            {
                "symbol": "MSFT",
                "bridge": {
                    "market_state": {"as_of": "2026-01-05T10:05:00", "hv20": 0.18},
                },
            },
        ]
        handler = BatchHandler()

        with patch.object(handler.bridge_client, "get_bridge_batch", return_value=rows) as mock_batch:
            with tempfile.TemporaryDirectory() as tmpdir:
                old_cwd = os.getcwd()
                os.chdir(tmpdir)
                try:
                    result = handler.execute(date="2026-01-05", limit=2)
                finally:
                    os.chdir(old_cwd)

                self.assertEqual(result["source"], "vol")
                self.assertEqual(result["requested"], 2)
                self.assertEqual(result["processed"], 2)
                self.assertEqual(result["failures"], [])
                self.assertIsNone(result["symbol"])
                mock_batch.assert_called_once_with(
                    date="2026-01-05",
                    limit=2,
                    symbol=None,
                )

                input_aapl = Path(tmpdir) / "runtime" / "inputs" / "2026-01-05" / "AAPL_i_2026-01-05.json"
                input_msft = Path(tmpdir) / "runtime" / "inputs" / "2026-01-05" / "MSFT_i_2026-01-05.json"
                output_aapl = Path(tmpdir) / "runtime" / "outputs" / "AAPL" / "2026-01-05" / "AAPL_o_2026-01-05.json"
                output_msft = Path(tmpdir) / "runtime" / "outputs" / "MSFT" / "2026-01-05" / "MSFT_o_2026-01-05.json"

                self.assertTrue(input_aapl.exists())
                self.assertTrue(input_msft.exists())
                self.assertTrue(output_aapl.exists())
                self.assertTrue(output_msft.exists())

                output_payload = json.loads(output_aapl.read_text())
                self.assertEqual(output_payload["symbol"], "AAPL")
                self.assertEqual(output_payload["date"], "2026-01-05")
                self.assertIn("gexbot_commands", output_payload)

    def test_batch_forwards_symbol_filter(self):
        rows = [
            {
                "symbol": "AAPL",
                "bridge": {
                    "market_state": {"as_of": "2026-01-05T10:00:00", "hv20": 0.22},
                },
            },
        ]
        handler = BatchHandler()

        with patch.object(handler.bridge_client, "get_bridge_batch", return_value=rows) as mock_batch:
            with tempfile.TemporaryDirectory() as tmpdir:
                old_cwd = os.getcwd()
                os.chdir(tmpdir)
                try:
                    result = handler.execute(
                        date="2026-01-05",
                        limit=2,
                        symbol="aapl",
                    )
                finally:
                    os.chdir(old_cwd)

        self.assertEqual(result["source"], "vol")
        self.assertEqual(result["symbol"], "AAPL")
        mock_batch.assert_called_once_with(
            date="2026-01-05",
            limit=2,
            symbol="AAPL",
        )
