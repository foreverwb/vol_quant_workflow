"""
Reusable symbol runner for cmd-style initialization flows.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..cli.gexbot import GexbotCommandGenerator
from .gexbot_param_resolver import resolve as resolve_gexbot_params


InputHandler = Callable[[Path, str, str, Optional[Dict[str, Any]]], Dict[str, Any]]
OutputHandler = Callable[[Path, str, str, List[str], Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


@dataclass
class CmdContext:
    """Execution context for one symbol/date initialization."""

    symbol: str
    date: str
    context: Optional[str] = None
    source: str = "vol"
    bridge_base_url: Optional[str] = None
    input_handler: Optional[InputHandler] = None
    output_handler: Optional[OutputHandler] = None


def _build_bridge_payload(
    bridge: Optional[Dict[str, Any]],
    explain: Dict[str, Any],
) -> Dict[str, Any]:
    """Keep bridge payload serialization aligned with existing cmd output."""
    return {
        "used": bridge is not None,
        "explain": explain,
        "term_structure": bridge.get("term_structure") if bridge else None,
        "market_state": bridge.get("market_state") if bridge else None,
        "as_of": (bridge.get("market_state") or {}).get("as_of") if bridge else None,
        "version": bridge.get("version") if bridge else None,
    }


def run_symbol_once(
    ctx: CmdContext,
    bridge_payload: Optional[Dict[str, Any]],
    input_path: Path,
    output_path: Path,
) -> Dict[str, Any]:
    """
    Run single-symbol cmd initialization once and persist input/output JSON files.
    """
    if not callable(ctx.input_handler):
        raise ValueError("CmdContext.input_handler must be provided")
    if not callable(ctx.output_handler):
        raise ValueError("CmdContext.output_handler must be provided")

    symbol = ctx.symbol.upper()

    params, resolved_context, explain = resolve_gexbot_params(bridge_payload, symbol)
    chosen_context = ctx.context or resolved_context

    gexbot = GexbotCommandGenerator(symbol, params=params)
    commands = gexbot.get_commands_for_context(chosen_context)

    input_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    input_result = ctx.input_handler(input_path, symbol, ctx.date, bridge_payload)
    bridge_meta = _build_bridge_payload(bridge_payload, explain)
    output_result = ctx.output_handler(
        output_path,
        symbol,
        ctx.date,
        commands,
        bridge_meta,
        params.to_dict(),
    )

    return {
        "success": True,
        "status": "ok",
        "symbol": symbol,
        "date": ctx.date,
        "gexbot_commands": commands,
        "gexbot_output": gexbot.format_for_output(commands),
        "input_file": str(input_path),
        "output_file": str(output_path),
        "input_status": input_result,
        "output_status": output_result,
        "bridge": bridge_meta,
        "command_config": params.to_dict(),
    }
