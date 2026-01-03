"""
数据加载模块
处理文件读取、数据加载
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

from .transformer import flatten_nested_data, to_market_data
from .validator import validate_market_data
from core.types import MarketData
from core.exceptions import DataValidationError


class DataLoader:
    """数据加载器"""
    
    def __init__(self, data_dir: str = "data/input"):
        self.data_dir = Path(data_dir)
        
    def load_json(self, filepath: str) -> Dict[str, Any]:
        """加载 JSON 文件"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_json(self, data: Dict[str, Any], filepath: str) -> None:
        """保存 JSON 文件"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def find_data_file(self, symbol: str) -> Optional[str]:
        """查找标的数据文件"""
        # 优先查找 {symbol}.json
        simple_file = self.data_dir / f"{symbol}.json"
        if simple_file.exists():
            return str(simple_file)
        
        # 查找带日期的文件
        pattern = f"{symbol}_*.json"
        files = sorted(self.data_dir.glob(pattern), reverse=True)
        if files:
            return str(files[0])
        
        return None
    
    def load_market_data(
        self,
        symbol: str,
        filepath: Optional[str] = None
    ) -> tuple[MarketData, Dict[str, Any], Dict[str, Any]]:
        """
        加载并解析市场数据
        
        Args:
            symbol: 标的代码
            filepath: 数据文件路径 (可选)
            
        Returns:
            (MarketData对象, 校验结果, 汇总信息)
        """
        if filepath is None:
            filepath = self.find_data_file(symbol)
        
        if filepath is None:
            raise FileNotFoundError(f"No data file found for {symbol}")
        
        # 加载原始数据
        raw_data = self.load_json(filepath)
        
        # 扁平化
        flat_data = flatten_nested_data(raw_data)
        flat_data["SYMBOL"] = symbol
        
        # 校验
        validations, summary = validate_market_data(flat_data, symbol)
        
        # 从校验结果构建 flat_data
        validated_data = {
            v.field_name: v.value 
            for v in validations.values() 
            if v.value is not None
        }
        validated_data["SYMBOL"] = symbol
        
        # 转换为 MarketData
        market_data = to_market_data(validated_data)
        
        return market_data, validations, summary


def load_and_validate(
    symbol: str,
    data_dir: str = "data/input",
    filepath: Optional[str] = None
) -> tuple[MarketData, Dict[str, Any], Dict[str, Any]]:
    """
    便捷函数：加载并校验数据
    """
    loader = DataLoader(data_dir)
    return loader.load_market_data(symbol, filepath)
