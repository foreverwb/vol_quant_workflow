"""
Tests for shared single-symbol runner helper.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ..core import runner as runner_module


class _DummyParams:
    def to_dict(self):
        return {"strikes": 9, "dte_gex": 12}


class TestRunSymbolOnce(unittest.TestCase):
    def test_run_symbol_once_builds_and_writes_via_handlers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input" / "AAPL_i_2026-01-05.json"
            output_path = Path(tmpdir) / "output" / "AAPL_o_2026-01-05.json"

            def fake_input_handler(path, symbol, date, bridge):
                payload = {
                    "meta": {"symbol": symbol, "datetime": f"{date}T09:30:00"},
                    "bridge_seen": bridge is not None,
                }
                path.write_text(json.dumps(payload))
                return {"action": "created"}

            def fake_output_handler(path, symbol, date, commands, bridge_payload, params_payload):
                payload = {
                    "symbol": symbol,
                    "date": date,
                    "commands": commands,
                    "bridge": bridge_payload,
                    "params": params_payload,
                }
                path.write_text(json.dumps(payload))
                return {"action": "created"}

            ctx = runner_module.CmdContext(
                symbol="aapl",
                date="2026-01-05",
                context="schema_core",
                input_handler=fake_input_handler,
                output_handler=fake_output_handler,
            )
            bridge = {"market_state": {"as_of": "2026-01-05T10:00:00"}}

            with patch.object(
                runner_module,
                "resolve_gexbot_params",
                return_value=(_DummyParams(), "minimum", {"bridge_used": True}),
            ):
                with patch.object(runner_module, "GexbotCommandGenerator") as mock_generator:
                    mock_generator.return_value.get_commands_for_context.return_value = ["!trigger AAPL 12"]
                    mock_generator.return_value.format_for_output.return_value = "!trigger AAPL 12"

                    result = runner_module.run_symbol_once(
                        ctx=ctx,
                        bridge_payload=bridge,
                        input_path=input_path,
                        output_path=output_path,
                    )

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["symbol"], "AAPL")
            self.assertTrue(input_path.exists())
            self.assertTrue(output_path.exists())
            self.assertEqual(result["input_status"]["action"], "created")
            self.assertEqual(result["output_status"]["action"], "created")

            mock_generator.return_value.get_commands_for_context.assert_called_once_with("schema_core")

            output_payload = json.loads(output_path.read_text())
            self.assertEqual(output_payload["symbol"], "AAPL")
            self.assertEqual(output_payload["date"], "2026-01-05")
            self.assertEqual(output_payload["commands"], ["!trigger AAPL 12"])
