"""
VA API 客户端 - 从 volatility_analysis 服务获取市场参数

使用方法：
    from utils.va_client import VAClient, fetch_market_params
    
    client = VAClient()
    params = client.get_params('NVDA', vix=18.5)
    # => {'vix': 18.5, 'ivr': 63, 'iv30': 47.2, 'hv20': 40, 'earning_date': '2025-11-19'}
"""

import requests
from typing import Dict, Optional, List, Any
from datetime import datetime
import json
import os


class VAClient:
    """
    Volatility Analysis API 客户端
    
    用于从 va 项目获取 swing 分析所需的市场参数
    """
    
    DEFAULT_BASE_URL = "http://localhost:8668"
    
    def __init__(self, base_url: str = None, timeout: int = 10):
        """
        初始化客户端
        
        Args:
            base_url: API 基础 URL，默认 http://localhost:8668
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发起 HTTP 请求
        """
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            raise VAClientError(
                f"无法连接到 VA 服务 ({self.base_url})。"
                f"请确保 volatility_analysis 服务正在运行。"
            )
        except requests.exceptions.Timeout:
            raise VAClientError(f"请求超时 ({self.timeout}秒)")
        except requests.exceptions.HTTPError as e:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', str(e))
            except:
                error_msg = str(e)
            raise VAClientError(f"API 请求失败: {error_msg}")
        except Exception as e:
            raise VAClientError(f"请求异常: {str(e)}")
    
    def get_params(self, symbol: str, vix: float = None, date: str = None) -> Dict[str, Any]:
        """
        获取单个 symbol 的市场参数
        
        Args:
            symbol: 股票代码
            vix: VIX 指数（可选）
            date: 目标日期，格式 YYYY-MM-DD（可选）
            
        Returns:
            市场参数字典
        """
        params = {}
        if vix is not None:
            params['vix'] = vix
        if date is not None:
            params['date'] = date
        
        data = self._make_request(
            'GET', 
            f'/api/swing/params/{symbol.upper()}',
            params=params
        )
        
        if not data.get('success'):
            raise VAClientError(data.get('error', 'Unknown error'))
        
        return data['params']
    
    def get_params_batch(
        self, 
        symbols: List[str], 
        vix: float = None,
        date: str = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量获取多个 symbol 的市场参数
        """
        payload = {'symbols': symbols}
        if vix is not None:
            payload['vix'] = vix
        if date is not None:
            payload['date'] = date
        
        data = self._make_request(
            'POST',
            '/api/swing/params/batch',
            json=payload
        )
        
        if not data.get('success'):
            raise VAClientError(data.get('error', 'Unknown error'))
        
        return data.get('results', {})
    
    def list_symbols(self) -> List[str]:
        """获取所有可用的 symbol 列表"""
        data = self._make_request('GET', '/api/swing/symbols')
        return data.get('symbols', [])
    
    def list_symbol_dates(self, symbol: str) -> List[str]:
        """获取指定 symbol 的所有可用日期"""
        data = self._make_request('GET', f'/api/swing/dates/{symbol.upper()}')
        return data.get('dates', [])
    
    def is_available(self) -> bool:
        """检查 VA 服务是否可用"""
        try:
            self._make_request('GET', '/api/swing/symbols')
            return True
        except VAClientError:
            return False


class VAClientError(Exception):
    """VA API 客户端异常"""
    pass


# ============================================================
# 便捷函数
# ============================================================

_default_client: VAClient = None


def get_default_client() -> VAClient:
    """获取默认客户端实例（单例）"""
    global _default_client
    if _default_client is None:
        _default_client = VAClient()
    return _default_client


def fetch_market_params(symbol: str, vix: float = None, date: str = None) -> Dict[str, Any]:
    """
    便捷函数：获取市场参数
    
    Args:
        symbol: 股票代码
        vix: VIX 指数
        date: 目标日期 (YYYY-MM-DD)
        
    Returns:
        市场参数字典
    """
    return get_default_client().get_params(symbol, vix, date)


def is_va_service_running() -> bool:
    """检查 VA 服务是否在运行"""
    return get_default_client().is_available()
