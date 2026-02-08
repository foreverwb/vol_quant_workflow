"""
Batch cmd handler - Initialize multiple symbols from bridge batch endpoint.
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..config.settings import Settings, get_settings
from ..core.config import Config, get_config
from ..core.runner import CmdContext, run_symbol_once
from ..integrations.bridge_client import BridgeClient
from .cmd import CmdHandler


class BatchHandler:
    """Handles batch initialization from /api/bridge/batch."""

    def __init__(
        self,
        config: Optional[Config] = None,
        settings: Optional[Settings] = None,
        bridge_client: Optional[BridgeClient] = None,
        cmd_handler: Optional[CmdHandler] = None,
    ):
        self.config = config or get_config()
        self.settings = settings or get_settings()
        self.bridge_client = bridge_client or BridgeClient(base_url=self.settings.va_api_base)
        self.cmd_handler = cmd_handler or CmdHandler(config=self.config)

    def execute(
        self,
        date: str,
        limit: Optional[int] = None,
        symbol: Optional[str] = None,
        runtime_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute batch initialization for one date."""
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid date format: {date}. Use YYYY-MM-DD.",
            }

        chosen_source = "vol"
        chosen_limit = limit if limit is not None else self.settings.va_batch_limit
        chosen_runtime_dir = runtime_dir or self.config.runtime_dir
        requested_symbol = symbol.upper() if isinstance(symbol, str) and symbol else None

        batch_rows = self.bridge_client.get_bridge_batch(
            date=date,
            limit=chosen_limit,
            symbol=requested_symbol,
        )

        results = []
        failures = []
        for row in batch_rows:
            row_symbol = (row.get("symbol") or "").upper()
            bridge_payload = row.get("bridge")
            if not row_symbol:
                failures.append({"symbol": "UNKNOWN", "error": "Missing symbol in batch row"})
                continue
            if not isinstance(bridge_payload, dict):
                failures.append({"symbol": row_symbol, "error": "Missing bridge payload"})
                continue

            input_path = Path(chosen_runtime_dir) / "inputs" / date / f"{row_symbol}_i_{date}.json"
            output_path = Path(chosen_runtime_dir) / "outputs" / row_symbol / date / f"{row_symbol}_o_{date}.json"
            ctx = CmdContext(
                symbol=row_symbol,
                date=date,
                source=chosen_source,
                bridge_base_url=self.bridge_client.base_url,
                input_handler=self.cmd_handler._handle_input_file,
                output_handler=self.cmd_handler._handle_output_file,
            )
            try:
                run_result = run_symbol_once(
                    ctx=ctx,
                    bridge_payload=bridge_payload,
                    input_path=input_path,
                    output_path=output_path,
                )
                results.append(
                    {
                        "symbol": row_symbol,
                        "status": run_result.get("status", "ok"),
                        "input_file": run_result.get("input_file"),
                        "output_file": run_result.get("output_file"),
                    }
                )
            except Exception as exc:
                failures.append({"symbol": row_symbol, "error": str(exc)})

        return {
            "success": len(failures) == 0,
            "date": date,
            "source": chosen_source,
            "limit": chosen_limit,
            "symbol": requested_symbol,
            "runtime_dir": chosen_runtime_dir,
            "requested": len(batch_rows),
            "processed": len(results),
            "results": results,
            "failures": failures,
        }

    def format_output(self, result: Dict[str, Any]) -> str:
        """Format batch result for console output."""
        if "error" in result:
            return f"ERROR: {result['error']}"

        lines = [
            "Batch initialization summary",
            f"Date: {result.get('date')}",
            f"Source: {result.get('source')}",
            f"Symbol filter: {result.get('symbol') or 'ALL'}",
            f"Runtime dir: {result.get('runtime_dir')}",
            f"Requested symbols: {result.get('requested', 0)}",
            f"Processed symbols: {result.get('processed', 0)}",
        ]

        failures = result.get("failures") or []
        if failures:
            lines.append("Failures:")
            for item in failures:
                lines.append(f"  - {item.get('symbol', 'UNKNOWN')}: {item.get('error', 'unknown error')}")

        return "\n".join(lines)


def main():
    """CLI entry point for batch command."""
    settings = get_settings()

    parser = argparse.ArgumentParser(
        description="Batch initialize symbols for a date via bridge batch endpoint",
        usage="batch -d DATE [--limit N] [--symbol SYMBOL] [--runtime-dir DIR]",
    )
    parser.add_argument(
        "-d",
        "--date",
        required=True,
        help="Date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=settings.va_batch_limit,
        help="Optional max number of symbols from bridge batch",
    )
    parser.add_argument(
        "--symbol",
        default=None,
        help="Optional symbol filter (e.g., AAPL)",
    )
    parser.add_argument(
        "--runtime-dir",
        default="runtime",
        help="Runtime directory path",
    )
    args = parser.parse_args()

    handler = BatchHandler(settings=settings)
    result = handler.execute(
        date=args.date,
        limit=args.limit,
        symbol=args.symbol,
        runtime_dir=args.runtime_dir,
    )
    print(handler.format_output(result))


if __name__ == "__main__":
    main()
