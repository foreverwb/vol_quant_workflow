"""
缓存管理模块
处理分析结果的缓存和读取
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class CacheManager:
    """
    分析结果缓存管理器
    
    目录结构:
        data/output/{symbol}/{date}/{symbol}_o_{date}.json
    
    文件格式:
        {
            "tag": "Meso",
            "market_params": {...},
            "source_target": {
                "step3_features": {...},
                "step4_scores": {...},
                "step5_decision": {...},
                "step6_strategy": {...},
                "step7_edge": {...},
                "step8_report": {...}
            }
        }
    """
    
    def __init__(self, base_dir: str = "data/output"):
        self.base_dir = Path(base_dir)
    
    def get_cache_path(self, symbol: str, date: str) -> Path:
        """
        获取缓存文件路径
        
        Args:
            symbol: 股票代码
            date: 日期 (YYYY-MM-DD)
            
        Returns:
            缓存文件路径
        """
        symbol = symbol.upper()
        # data/output/AAPL/2026-01-03/AAPL_o_2026-01-03.json
        return self.base_dir / symbol / date / f"{symbol}_o_{date}.json"
    
    def get_cache_dir(self, symbol: str, date: str) -> Path:
        """获取缓存目录"""
        symbol = symbol.upper()
        return self.base_dir / symbol / date
    
    def load_cache(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """
        加载缓存文件
        
        Returns:
            缓存数据，不存在则返回 None
        """
        path = self.get_cache_path(symbol, date)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def save_cache(self, symbol: str, date: str, data: Dict[str, Any]) -> Path:
        """
        保存缓存文件
        
        Returns:
            保存的文件路径
        """
        path = self.get_cache_path(symbol, date)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return path
    
    def create_initial_cache(
        self,
        symbol: str,
        date: str,
        market_params: Dict[str, Any],
        tag: str = "Meso"
    ) -> Dict[str, Any]:
        """
        创建初始缓存结构
        
        Args:
            symbol: 股票代码
            date: 日期
            market_params: 市场参数
            tag: 标签 (Meso/Macro/Micro)
            
        Returns:
            初始缓存数据结构
        """
        # 添加更新时间
        if 'updated_at' not in market_params:
            market_params['updated_at'] = datetime.now().isoformat()
        
        cache_data = {
            "symbol": symbol.upper(),
            "date": date,
            "tag": tag,
            "market_params": market_params,
            "source_target": {},
            "created_at": datetime.now().isoformat(),
        }
        
        # 保存
        self.save_cache(symbol, date, cache_data)
        
        return cache_data
    
    def update_step(
        self,
        symbol: str,
        date: str,
        step_name: str,
        step_data: Any
    ) -> Dict[str, Any]:
        """
        更新某个步骤的数据
        
        Args:
            symbol: 股票代码
            date: 日期
            step_name: 步骤名称 (step3_features, step4_scores, etc.)
            step_data: 步骤数据
            
        Returns:
            更新后的缓存数据
        """
        cache = self.load_cache(symbol, date)
        if cache is None:
            raise ValueError(f"Cache not found for {symbol} on {date}")
        
        # 确保 source_target 存在
        if 'source_target' not in cache:
            cache['source_target'] = {}
        
        cache['source_target'][step_name] = step_data
        cache['updated_at'] = datetime.now().isoformat()
        
        self.save_cache(symbol, date, cache)
        return cache
    
    def list_cached_symbols(self) -> list:
        """列出所有已缓存的 symbol"""
        if not self.base_dir.exists():
            return []
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]
    
    def list_cached_dates(self, symbol: str) -> list:
        """列出某个 symbol 的所有缓存日期"""
        symbol_dir = self.base_dir / symbol.upper()
        if not symbol_dir.exists():
            return []
        return sorted([d.name for d in symbol_dir.iterdir() if d.is_dir()], reverse=True)
    
    def get_latest_cache(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取最新的缓存"""
        dates = self.list_cached_dates(symbol)
        if dates:
            return self.load_cache(symbol, dates[0])
        return None
    
    def ensure_cache(
        self,
        symbol: str,
        date: str,
        market_params: Dict[str, Any] = None,
        tag: str = "Meso"
    ) -> Dict[str, Any]:
        """
        确保缓存存在，不存在则创建
        
        Args:
            symbol: 股票代码
            date: 日期
            market_params: 市场参数 (创建时使用)
            tag: 标签
            
        Returns:
            缓存数据
        """
        cache = self.load_cache(symbol, date)
        if cache is None:
            # 创建默认市场参数
            if market_params is None:
                market_params = {
                    'vix': None,
                    'ivr': None,
                    'iv30': None,
                    'hv20': None,
                    'vrp': None,
                    'iv_path': None,
                    'updated_at': datetime.now().isoformat()
                }
            cache = self.create_initial_cache(symbol, date, market_params, tag)
        return cache


# 全局实例
_cache_manager: CacheManager = None


def get_cache_manager(base_dir: str = "data/output") -> CacheManager:
    """获取缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(base_dir)
    return _cache_manager
