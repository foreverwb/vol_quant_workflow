#!/usr/bin/env python3
"""
Volatility Strategy CLI - Main entry point.

Usage:
    vol cmd -s SYMBOL -d YYYY-MM-DD
    vol updated -i INPUT -c OUTPUT  
    vol task -i INPUT -c OUTPUT
"""

import sys
import argparse


def main():
    """Main CLI entry point with subcommands."""
    parser = argparse.ArgumentParser(
        prog="vol",
        description="Volatility Strategy Framework CLI",
        epilog="Use 'vol <command> --help' for command-specific help",
    )
    
    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="available commands",
    )
    
    # cmd subcommand
    cmd_parser = subparsers.add_parser(
        "cmd",
        help="Initialize session, generate gexbot commands",
    )
    cmd_parser.add_argument(
        "-s", "--symbol",
        required=True,
        help="Trading symbol (e.g., SPY, AAPL)",
    )
    cmd_parser.add_argument(
        "-d", "--date",
        required=True,
        help="Date in YYYY-MM-DD format",
    )
    cmd_parser.add_argument(
        "-c", "--context",
        default="standard",
        choices=["standard", "minimum", "event", "intraday", "post_event", "long_term"],
        help="Command context for gexbot suite",
    )
    cmd_parser.add_argument(
        "--runtime-dir",
        default="runtime",
        help="Runtime directory path",
    )
    
    # updated subcommand
    update_parser = subparsers.add_parser(
        "updated",
        help="Lightweight monitoring - regime/volatility only",
    )
    update_parser.add_argument(
        "-i", "--input",
        required=True,
        dest="input_file",
        help="Path to input JSON file",
    )
    update_parser.add_argument(
        "-c", "--cache",
        required=True,
        dest="output_file",
        help="Path to output/cache JSON file",
    )
    
    # task subcommand
    task_parser = subparsers.add_parser(
        "task",
        help="Full analysis pipeline",
    )
    task_parser.add_argument(
        "-i", "--input",
        required=True,
        dest="input_file",
        help="Path to input JSON file",
    )
    task_parser.add_argument(
        "-c", "--cache",
        required=True,
        dest="output_file",
        help="Path to output/cache JSON file",
    )
    task_parser.add_argument(
        "--replay",
        action="store_true",
        help="Enable replay/backtest mode",
    )
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "cmd":
        from .cli.cmd import CmdHandler
        handler = CmdHandler()
        result = handler.execute(
            symbol=args.symbol,
            date=args.date,
            context=args.context,
            runtime_dir=args.runtime_dir,
        )
        print(handler.format_output(result))
        
    elif args.command == "updated":
        from .cli.update import UpdateHandler
        handler = UpdateHandler()
        result = handler.execute(
            input_file=args.input_file,
            output_file=args.output_file,
        )
        print(handler.format_output(result))
        
    elif args.command == "task":
        from .cli.task import TaskHandler
        handler = TaskHandler()
        result = handler.execute(
            input_file=args.input_file,
            output_file=args.output_file,
            replay_mode=args.replay,
        )
        print(handler.format_output(result))
    
    sys.exit(0 if result.get("success", False) else 1)


if __name__ == "__main__":
    main()
