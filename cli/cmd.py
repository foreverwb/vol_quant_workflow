"""
cmd handler - Initialization command.

Usage: vol cmd -s SYMBOL -d YYYY-MM-DD

Functions:
1. Generate gexbot commands for data collection
2. Create/validate runtime input file
3. Create output file skeleton
"""

import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .gexbot import GexbotCommandGenerator
from ..core.schema import InputSchema, OutputSchema
from ..core.config import Config, get_config


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
    
    def execute(
        self,
        symbol: str,
        date: str,
        context: str = "standard",
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
        
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid date format: {date}. Use YYYY-MM-DD.",
            }
        
        # Generate gexbot commands
        gexbot = GexbotCommandGenerator(symbol)
        commands = gexbot.get_commands_for_context(context)
        
        # Create runtime directories
        inputs_dir = Path(runtime_dir) / "inputs"
        outputs_dir = Path(runtime_dir) / "outputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate file paths
        input_path = inputs_dir / f"{symbol}_i_{date}.json"
        output_path = outputs_dir / f"{symbol}_o_{date}.json"
        
        # Create or validate input file
        input_result = self._handle_input_file(input_path, symbol, date)
        
        # Create output file skeleton
        output_result = self._handle_output_file(output_path, symbol, date, commands)
        
        return {
            "success": True,
            "symbol": symbol,
            "date": date,
            "gexbot_commands": commands,
            "gexbot_output": gexbot.format_for_output(commands),
            "input_file": str(input_path),
            "output_file": str(output_path),
            "input_status": input_result,
            "output_status": output_result,
        }
    
    def _handle_input_file(
        self,
        path: Path,
        symbol: str,
        date: str,
    ) -> Dict[str, Any]:
        """Create or validate input file."""
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        if path.exists():
            # Validate existing file
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
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
            f"  3. Run: vol update -i {result['input_file']} -c {result['output_file']}",
            f"  4. Run: vol task -i {result['input_file']} -c {result['output_file']}",
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
        default="standard",
        choices=["standard", "minimum", "event", "intraday", "post_event", "long_term"],
        help="Command context for gexbot suite"
    )
    parser.add_argument(
        "--runtime-dir",
        default="runtime",
        help="Runtime directory path"
    )
    
    args = parser.parse_args()
    
    # Default date to today if not specified
    if args.date is None:
        args.date = datetime.now().strftime("%Y-%m-%d")
    
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
