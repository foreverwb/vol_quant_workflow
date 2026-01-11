"""
cmd handler - Initialization command.

Usage: vol cmd -s SYMBOL -d YYYY-MM-DD

Functions:
1. Generate gexbot commands for data collection
2. Create/validate runtime input file
3. Create output file skeleton
"""

import json
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .gexbot import GexbotCommandGenerator
from ..integrations.bridge_client import BridgeClient
from ..core.gexbot_param_resolver import resolve as resolve_gexbot_params
from ..core.schema import InputSchema, OutputSchema
from ..core.config import Config, get_config
from ..core.input_enrichment import apply_bridge_market_state


class CmdHandler:
    """
    Handles the `cmd` CLI command for initialization.
    
    This is the entry point that:
    1. Generates gexbot commands for the user to run
    2. Creates the input file template
    3. Creates the output file skeleton
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize handler."""
        self.config = config or get_config()
        self.bridge_client = BridgeClient()
    
    def execute(
        self,
        symbol: str,
        date: Optional[str],
        context: Optional[str] = None,
        runtime_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the cmd command.
        
        Args:
            symbol: Trading symbol (e.g., "SPY", "AAPL")
            date: Date in YYYY-MM-DD format
            context: Command context ("standard", "event", "intraday", etc.)
            runtime_dir: Override runtime directory path
            
        Returns:
            Dictionary with execution results
        """
        symbol = symbol.upper()
        runtime_dir = runtime_dir or self.config.runtime_dir
        
        # Validate date format if provided
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid date format: {date}. Use YYYY-MM-DD.",
                }
        effective_date = date or datetime.now().strftime("%Y-%m-%d")
        
        # Generate gexbot commands
        bridge = self.bridge_client.get_bridge(symbol, date=date)
        params, resolved_context, explain = resolve_gexbot_params(bridge, symbol)
        chosen_context = context or resolved_context

        gexbot = GexbotCommandGenerator(symbol, params=params)
        commands = gexbot.get_commands_for_context(chosen_context)
        
        # Create runtime directories
        inputs_dir = Path(runtime_dir) / "inputs"
        outputs_dir = Path(runtime_dir) / "outputs" / symbol / effective_date
        inputs_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate file paths
        input_path = inputs_dir / f"{symbol}_i_{effective_date}.json"
        output_path = outputs_dir / f"{symbol}_o_{effective_date}.json"
        
        # Create or validate input file
        input_result = self._handle_input_file(input_path, symbol, effective_date, bridge)
        
        # Create output file skeleton
        bridge_payload = {
            "used": bridge is not None,
            "explain": explain,
            "term_structure": bridge.get("term_structure") if bridge else None,
            "market_state": bridge.get("market_state") if bridge else None,
            "as_of": (bridge.get("market_state") or {}).get("as_of") if bridge else None,
            "version": bridge.get("version") if bridge else None,
        }
        output_result = self._handle_output_file(
            output_path,
            symbol,
            effective_date,
            commands,
            bridge_payload,
            params.to_dict(),
        )
        
        return {
            "success": True,
            "symbol": symbol,
            "date": effective_date,
            "gexbot_commands": commands,
            "gexbot_output": gexbot.format_for_output(commands),
            "input_file": str(input_path),
            "output_file": str(output_path),
            "input_status": input_result,
            "output_status": output_result,
            "bridge": bridge_payload,
            "command_config": params.to_dict(),
        }
    
    def _handle_input_file(
        self,
        path: Path,
        symbol: str,
        date: str,
        bridge: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create or validate input file."""
        bridge_state = bridge.get("market_state") if isinstance(bridge, dict) else {}
        bridge_as_of = bridge_state.get("as_of") if isinstance(bridge_state, dict) else None
        now = bridge_as_of or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        if path.exists():
            # Validate existing file
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                data = apply_bridge_market_state(data, bridge)
                with open(path, 'w') as f:
                    json.dump(data, f, indent=2)
                is_valid, errors = InputSchema.validate(data)
                
                return {
                    "action": "validated",
                    "valid": is_valid,
                    "errors": errors if not is_valid else [],
                }
            except json.JSONDecodeError as e:
                return {
                    "action": "validation_failed",
                    "valid": False,
                    "errors": [f"JSON parse error: {str(e)}"],
                }
        else:
            # Create new template
            template = InputSchema.get_empty_template(symbol, now)
            template = apply_bridge_market_state(template, bridge)
            
            with open(path, 'w') as f:
                json.dump(template, f, indent=2)
            
            return {
                "action": "created",
                "valid": False,  # Template has null values
                "message": "Input template created. Please fill in the 22 core fields.",
            }
    
    def _handle_output_file(
        self,
        path: Path,
        symbol: str,
        date: str,
        commands: list,
        bridge_payload: Dict[str, Any],
        params_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create or update output file skeleton."""
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        if path.exists():
            # Load existing and update
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                data["last_update"] = now
                data["gexbot_commands"] = commands
                data["bridge"] = bridge_payload
                data["command_config"] = params_payload
                
                with open(path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                return {
                    "action": "updated",
                    "updates_count": len(data.get("updates", [])),
                }
            except Exception as e:
                return {
                    "action": "update_failed",
                    "error": str(e),
                }
        else:
            # Create new skeleton
            skeleton = OutputSchema.get_empty_template(symbol, date)
            skeleton["last_update"] = now
            skeleton["gexbot_commands"] = commands
            skeleton["bridge"] = bridge_payload
            skeleton["command_config"] = params_payload
            
            with open(path, 'w') as f:
                json.dump(skeleton, f, indent=2)
            
            return {
                "action": "created",
            }
    
    def format_output(self, result: Dict[str, Any]) -> str:
        """Format result for console output."""
        if not result["success"]:
            return f"ERROR: {result.get('error', 'Unknown error')}"
        
        lines = [
            f"═══════════════════════════════════════════════════════════════",
            f"  VOL QUANT WORKFLOW - Initialization Complete",
            f"═══════════════════════════════════════════════════════════════",
            f"",
            f"  Symbol: {result['symbol']}",
            f"  Date:   {result['date']}",
            f"",
            f"───────────────────────────────────────────────────────────────",
            f"  GEXBOT COMMANDS (copy and run):",
            f"───────────────────────────────────────────────────────────────",
            f"",
        ]
        
        for cmd in result["gexbot_commands"]:
            lines.append(f"  {cmd}")
        
        lines.extend([
            f"",
            f"───────────────────────────────────────────────────────────────",
            f"  FILES:",
            f"───────────────────────────────────────────────────────────────",
            f"",
            f"  Input:  {result['input_file']}",
            f"  Output: {result['output_file']}",
            f"",
            f"  Input status:  {result['input_status'].get('action', 'unknown')}",
            f"  Output status: {result['output_status'].get('action', 'unknown')}",
            f"",
            f"═══════════════════════════════════════════════════════════════",
            f"",
            f"  NEXT STEPS:",
            f"  1. Run the gexbot commands above",
            f"  2. Fill in the input file with the 22 core fields",
            f"  3. Run: vol update -i {result['symbol']}_i_{result['date']} -c {result['symbol']}_o_{result['date']}",
            f"  4. Run: vol task -i {result['symbol']}_i_{result['date']} -c {result['symbol']}_o_{result['date']}",
            f"",
        ])
        
        return "\n".join(lines)


def main():
    """CLI entry point for cmd command."""
    parser = argparse.ArgumentParser(
        description="Initialize volatility strategy for a symbol/date",
        usage="cmd SYMBOL [-d DATE] [-c CONTEXT]"
    )
    parser.add_argument(
        "symbol",
        help="Trading symbol (e.g., SPY, AAPL)"
    )
    parser.add_argument(
        "-d", "--date",
        default=None,
        help="Date in YYYY-MM-DD format (default: today)"
    )
    parser.add_argument(
        "-c", "--context",
        default=None,
        choices=["standard", "minimum", "event", "intraday", "post_event", "long_term", "schema_core"],
        help="Command context for gexbot suite"
    )
    parser.add_argument(
        "--runtime-dir",
        default="runtime",
        help="Runtime directory path"
    )
    
    args = parser.parse_args()
    
    context_provided = any(arg in ("-c", "--context") for arg in sys.argv[1:])
    if not context_provided:
        args.context = None

    handler = CmdHandler()
    result = handler.execute(
        symbol=args.symbol,
        date=args.date,
        context=args.context,
        runtime_dir=args.runtime_dir,
    )
    
    print(handler.format_output(result))


if __name__ == "__main__":
    main()
