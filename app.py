"""
Command-line interface for volatility analysis system.
"""

import asyncio
import argparse
import sys
import logging
from typing import Optional, Dict, Any

from llm.llm_client import init_llm_client
from workflow import VolatilityWorkflow
from batch_processor import process_single_symbol_folder
from config.env_config import default_config
from utils.logger import setup_logger

logger = logging.getLogger(__name__)


async def analyze_folder(
    folder_path: str,
    symbol: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze symbol folder."""
    
    logger.info(f"Processing folder: {folder_path}")
    
    api_base = api_base or default_config.LLM_API_BASE
    api_key = api_key or default_config.LLM_API_KEY
    
    result = await process_single_symbol_folder(
        folder_path=folder_path,
        api_base=api_base,
        api_key=api_key,
        symbol=symbol,
        output_dir=output_dir,
        env_config=default_config
    )
    
    return result


async def generate_commands(
    query: str,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """Generate gexbot command list."""
    
    logger.info("Generating commands...")
    
    api_base = api_base or default_config.LLM_API_BASE
    api_key = api_key or default_config.LLM_API_KEY
    
    init_llm_client(api_base, api_key)
    workflow = VolatilityWorkflow(default_config)
    
    try:
        result = await workflow.process_input(query=query)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.final_report or "")
            logger.info(f"Commands saved to: {output_file}")
        
        return {
            "status": "success",
            "report": result.final_report
        }
    
    except Exception as e:
        logger.error(f"Command generation failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description="Volatility Trading Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py analyze -d /data/SPY -o /output
  python main.py analyze -d /data/charts -s SPY -o /output
  python main.py commands -q "SPY earnings 5-20 DTE" -o commands.md
        """
    )
    
    parser.add_argument(
        "--api-base",
        help="LLM API base URL (default from .env)"
    )
    
    parser.add_argument(
        "--api-key",
        help="LLM API key (default from .env)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze symbol folder"
    )
    analyze_parser.add_argument(
        "-d", "--directory",
        required=True,
        help="Chart folder path"
    )
    analyze_parser.add_argument(
        "-s", "--symbol",
        help="Symbol code (auto-detect if not provided)"
    )
    analyze_parser.add_argument(
        "-o", "--output",
        help="Output directory"
    )
    
    commands_parser = subparsers.add_parser(
        "commands",
        help="Generate gexbot commands"
    )
    commands_parser.add_argument(
        "-q", "--query",
        required=True,
        help="Query (e.g., 'SPY earnings 5-20 DTE')"
    )
    commands_parser.add_argument(
        "-o", "--output",
        help="Output file path"
    )
    
    args = parser.parse_args()
    
    setup_logger(verbose=args.verbose)
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "analyze":
            result = asyncio.run(analyze_folder(
                folder_path=args.directory,
                symbol=args.symbol,
                api_base=args.api_base,
                api_key=args.api_key,
                output_dir=args.output
            ))
            
            if result["status"] == "success":
                print(f"\n✅ Analysis completed!")
                print(f"Symbol: {result['result'].symbol}")
                if result['result'].decision:
                    print(f"Direction: {result['result'].decision.final_direction.value}")
            else:
                print(f"\n❌ Analysis failed: {result['error']}")
                sys.exit(1)
        
        elif args.command == "commands":
            result = asyncio.run(generate_commands(
                query=args.query,
                api_base=args.api_base,
                api_key=args.api_key,
                output_file=args.output
            ))
            
            if result["status"] == "success":
                print(f"\n✅ Commands generated!")
            else:
                print(f"\n❌ Failed: {result['error']}")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
