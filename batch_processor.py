"""
Single symbol batch processor for analyzing option volatility.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import asdict
from datetime import datetime
import re

from workflow import VolatilityWorkflow
from config.env_config import EnvConfig
from agents.final_decision import FinalDecisionAgent

logger = logging.getLogger(__name__)

__all__ = [
    'SingleSymbolBatchProcessor',
    'process_single_symbol_folder'
]


class SingleSymbolBatchProcessor:
    """Processor for analyzing multiple chart files of a single stock symbol."""
    
    def __init__(self, env_config: Optional[EnvConfig] = None):
        self.workflow = VolatilityWorkflow(env_config)
        self.env_config = env_config or EnvConfig()
    
    def get_symbol_from_folder(self, folder_path: str) -> str:
        """Extract symbol from folder name."""
        folder_name = os.path.basename(folder_path.rstrip('/'))
        
        match = re.search(r'^([A-Z]{1,5})', folder_name)
        if match:
            return match.group(1)
        
        match = re.search(r'[_-]([A-Z]{1,5})[_-]', folder_name)
        if match:
            return match.group(1)
        
        match = re.search(r'([A-Z]{1,5})', folder_name)
        if match:
            return match.group(1)
        
        raise ValueError(f"Cannot infer symbol from folder: {folder_path}")
    
    def collect_images(self, folder_path: str) -> List[str]:
        """Collect all image files from folder."""
        if not os.path.isdir(folder_path):
            raise ValueError(f"Folder not found: {folder_path}")
        
        img_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}
        images = []
        
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            
            if os.path.isdir(file_path):
                continue
            
            if Path(file).suffix.lower() not in img_extensions:
                continue
            
            images.append(file_path)
        
        if not images:
            raise ValueError(f"No image files found in: {folder_path}")
        
        return sorted(images)
    
    async def process_symbol_folder(
        self,
        folder_path: str,
        symbol: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process all chart files for a single symbol.
        
        Args:
            folder_path: Path to folder containing chart images
            symbol: Symbol code (auto-detected if not provided)
            output_dir: Output directory for results
        
        Returns:
            {
                "symbol": symbol code,
                "status": "success" or "error",
                "result": AnalysisResult or None,
                "error": error message or None
            }
        """
        
        if not os.path.isdir(folder_path):
            raise ValueError(f"Folder not found: {folder_path}")
        
        if not symbol:
            symbol = self.get_symbol_from_folder(folder_path)
        
        symbol = symbol.upper()
        
        logger.info(f"{'='*70}")
        logger.info(f"Processing: {symbol}")
        logger.info(f"Folder: {folder_path}")
        logger.info(f"{'='*70}")
        
        try:
            image_files = self.collect_images(folder_path)
            logger.info(f"Found {len(image_files)} chart files")
            
            logger.info("Starting analysis...")
            result = await self.workflow.process_input(
                query="",
                files=image_files,
                symbol=symbol
            )
            
            if result.validation:
                decision_agent = FinalDecisionAgent()
                result.final_report = await decision_agent.generate_report(result)
            
            if output_dir:
                await self._save_results(result, symbol, output_dir)
            
            logger.info(f"✅ {symbol} completed")
            
            return {
                "symbol": symbol,
                "status": "success",
                "result": result,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"❌ {symbol} failed: {str(e)}", exc_info=True)
            return {
                "symbol": symbol,
                "status": "error",
                "result": None,
                "error": str(e)
            }
    
    async def _save_results(
        self,
        result: Any,
        symbol: str,
        output_dir: str
    ) -> None:
        """Save analysis results to JSON and Markdown files."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_file = os.path.join(output_dir, f"{symbol}_analysis_{timestamp}.json")
        result_dict = {
            "symbol": result.symbol,
            "timestamp": result.timestamp,
            "status": "success",
            "data": {
                "validation": asdict(result.validation) if result.validation else None,
                "features": asdict(result.features) if result.features else None,
                "scores": asdict(result.scores) if result.scores else None,
                "probability": asdict(result.probability) if result.probability else None,
                "decision": asdict(result.decision) if result.decision else None,
            }
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Results saved: {json_file}")
        
        if result.final_report:
            report_file = os.path.join(output_dir, f"{symbol}_report_{timestamp}.md")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(result.final_report)
            logger.info(f"Report saved: {report_file}")


async def process_single_symbol_folder(
    folder_path: str,
    api_base: str,
    api_key: str,
    symbol: Optional[str] = None,
    output_dir: Optional[str] = None,
    env_config: Optional[EnvConfig] = None
) -> Dict[str, Any]:
    """
    Process chart files for a single symbol folder.
    
    Args:
        folder_path: Path to symbol folder
        api_base: LLM API base URL
        api_key: LLM API key
        symbol: Symbol code (optional)
        output_dir: Output directory (optional)
        env_config: Environment config (optional)
    
    Returns:
        Analysis result dictionary
    """
    
    from llm.llm_client import init_llm_client
    
    if not folder_path:
        raise ValueError("folder_path required")
    if not api_base:
        raise ValueError("api_base required")
    if not api_key:
        raise ValueError("api_key required")
    
    init_llm_client(api_base, api_key)
    processor = SingleSymbolBatchProcessor(env_config)
    
    return await processor.process_symbol_folder(
        folder_path,
        symbol=symbol,
        output_dir=output_dir
    )
