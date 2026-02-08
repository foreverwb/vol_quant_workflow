"""
Compatibility checks for existing single-symbol cmd behavior.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ..cli.cmd import CmdHandler
from ..cli.task import resolve_file_path as resolve_task_path
from ..cli.update import resolve_file_path as resolve_update_path


class TestCmdSingleCompat(unittest.TestCase):
    def test_cmd_runtime_paths_remain_unchanged(self):
        handler = CmdHandler()
        bridge = {"market_state": {"as_of": "2026-01-05T09:45:00", "hv20": 0.21}}

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = str(Path(tmpdir) / "runtime")
            with patch.object(handler.bridge_client, "get_bridge", return_value=bridge):
                result = handler.execute(
                    symbol="aapl",
                    date="2026-01-05",
                    context=None,
                    runtime_dir=runtime_dir,
                )

            self.assertTrue(result["success"])
            self.assertEqual(result["symbol"], "AAPL")
            self.assertEqual(
                result["input_file"],
                str(Path(runtime_dir) / "inputs" / "2026-01-05" / "AAPL_i_2026-01-05.json"),
            )
            self.assertEqual(
                result["output_file"],
                str(Path(runtime_dir) / "outputs" / "AAPL" / "2026-01-05" / "AAPL_o_2026-01-05.json"),
            )

            output_payload = json.loads(Path(result["output_file"]).read_text())
            self.assertEqual(output_payload["symbol"], "AAPL")
            self.assertEqual(output_payload["date"], "2026-01-05")
            self.assertIn("gexbot_commands", output_payload)

    def test_update_and_task_resolve_input_date_dir_with_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = str(Path(tmpdir) / "runtime")
            name = "AAPL_i_2026-01-05"
            expected_dated = str(Path(runtime_dir) / "inputs" / "2026-01-05" / f"{name}.json")
            expected_legacy = str(Path(runtime_dir) / "inputs" / f"{name}.json")

            # No files: default to new dated location
            self.assertEqual(resolve_update_path(name, "input", runtime_dir), expected_dated)
            self.assertEqual(resolve_task_path(name, "input", runtime_dir), expected_dated)

            # Legacy exists only: resolve to legacy for backward compatibility
            Path(expected_legacy).parent.mkdir(parents=True, exist_ok=True)
            Path(expected_legacy).write_text("{}")
            self.assertEqual(resolve_update_path(name, "input", runtime_dir), expected_legacy)
            self.assertEqual(resolve_task_path(name, "input", runtime_dir), expected_legacy)

            # Dated file exists: prefer new dated path
            Path(expected_dated).parent.mkdir(parents=True, exist_ok=True)
            Path(expected_dated).write_text("{}")
            self.assertEqual(resolve_update_path(name, "input", runtime_dir), expected_dated)
            self.assertEqual(resolve_task_path(name, "input", runtime_dir), expected_dated)
