"""
批量处理器

支持批量处理文件夹中的多个标的
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..workflow import VolatilityWorkflow


class BatchProcessor:
    """
    批量处理器
    
    扫描文件夹，按标的分组处理图表文件
    """
    
    # 支持的图片扩展名
    VALID_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    
    def __init__(
        self,
        workflow: 'VolatilityWorkflow',
        output_dir: Optional[str] = None
    ):
        """
        初始化批量处理器
        
        Args:
            workflow: 工作流实例
            output_dir: 输出目录，默认为 ./output
        """
        self.workflow = workflow
        self.output_dir = Path(output_dir) if output_dir else Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def scan_folder(self, folder_path: str) -> Dict[str, List[str]]:
        """
        扫描文件夹，按标的分组
        
        支持的文件命名格式:
        - {SYMBOL}_{command}.png
        - {SYMBOL}_{command}_{timestamp}.png
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            按标的分组的文件列表
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        grouped_files: Dict[str, List[str]] = {}
        
        for file in folder.iterdir():
            if file.suffix.lower() not in self.VALID_EXTENSIONS:
                continue
            
            # 从文件名提取标的代码 (格式: SYMBOL_xxx.png)
            name_parts = file.stem.split('_')
            if name_parts:
                symbol = name_parts[0].upper()
                # 验证是有效的股票代码格式
                if 1 <= len(symbol) <= 5 and symbol.isalpha():
                    if symbol not in grouped_files:
                        grouped_files[symbol] = []
                    grouped_files[symbol].append(str(file))
        
        return grouped_files
    
    async def process_folder(
        self,
        folder_path: str,
        min_files_per_symbol: int = 10
    ) -> Dict[str, Any]:
        """
        处理文件夹中的所有标的
        
        Args:
            folder_path: 图表文件夹路径
            min_files_per_symbol: 每个标的最少需要的图表数量
            
        Returns:
            处理结果汇总
        """
        grouped_files = self.scan_folder(folder_path)
        
        results = {
            "total_symbols": len(grouped_files),
            "processed": [],
            "skipped": [],
            "errors": []
        }
        
        for symbol, files in grouped_files.items():
            print(f"\n{'='*50}")
            print(f"Processing {symbol} ({len(files)} files)")
            print('='*50)
            
            # 检查文件数量
            if len(files) < min_files_per_symbol:
                results["skipped"].append({
                    "symbol": symbol,
                    "reason": f"Insufficient files ({len(files)} < {min_files_per_symbol})"
                })
                continue
            
            try:
                # 重置工作流
                self.workflow.reset()
                
                # 运行分析
                result = await self.workflow.run(files=files)
                
                # 保存结果
                if result.get("status") == "completed":
                    self._save_result(symbol, result, results)
                else:
                    results["errors"].append({
                        "symbol": symbol,
                        "status": result.get("status"),
                        "message": result.get("message", "")
                    })
                    
            except Exception as e:
                results["errors"].append({
                    "symbol": symbol,
                    "error": str(e)
                })
        
        # 保存汇总
        self._save_summary(results)
        
        return results
    
    def _save_result(
        self, 
        symbol: str, 
        result: Dict[str, Any],
        results: Dict[str, Any]
    ):
        """保存单个标的的结果"""
        # 保存报告
        report_path = self.output_dir / f"{symbol}_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(result.get("report", ""))
        
        # 保存详细数据
        data_path = self.output_dir / f"{symbol}_data.json"
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(result.get("details", {}), f, ensure_ascii=False, indent=2)
        
        results["processed"].append({
            "symbol": symbol,
            "report_path": str(report_path),
            "data_path": str(data_path),
            "summary": result.get("summary", {})
        })
    
    def _save_summary(self, results: Dict[str, Any]):
        """保存批处理汇总"""
        summary_path = self.output_dir / "batch_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    
    def process_folder_sync(
        self,
        folder_path: str,
        min_files_per_symbol: int = 10
    ) -> Dict[str, Any]:
        """同步处理文件夹"""
        return asyncio.run(self.process_folder(folder_path, min_files_per_symbol))