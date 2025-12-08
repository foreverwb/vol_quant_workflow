"""
代码节点基类和通用工具
"""
import math
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class CodeNodeResult:
    """代码节点执行结果"""
    success: bool
    result: Dict[str, Any]
    error: Optional[str] = None


def z_score(x: float, mean: float = 0, std: float = 1) -> float:
    """计算 z-score"""
    if std == 0:
        return 0
    return (x - mean) / std


def safe_divide(a: float, b: float, default: float = 0) -> float:
    """安全除法"""
    if b == 0:
        return default
    return a / b


def clamp(value: float, min_val: float, max_val: float) -> float:
    """限制值在范围内"""
    return max(min_val, min(max_val, value))


# 检查 scipy 是否可用
try:
    import numpy as np
    from scipy.stats import norm
    from scipy.optimize import brentq
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def bs_delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    """
    Black-Scholes Delta 计算
    
    Args:
        S: 现价
        K: 行权价
        T: 到期时间（年）
        r: 无风险利率
        sigma: 波动率
        option_type: 'call' 或 'put'
    """
    if T <= 0:
        return 1.0 if (option_type == 'call' and S > K) else 0.0
    
    if not HAS_SCIPY:
        # 简化近似
        if option_type == 'call':
            return 0.5 + 0.4 * (S - K) / (sigma * S * math.sqrt(T))
        else:
            return -0.5 + 0.4 * (S - K) / (sigma * S * math.sqrt(T))
    
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    
    if option_type == 'call':
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1


def find_strike_by_delta(S: float, target_delta: float, T: float, r: float, 
                         sigma: float, option_type: str) -> float:
    """
    反推满足目标 Delta 的行权价
    
    Args:
        S: 现价
        target_delta: 目标 Delta
        T: 到期时间（年）
        r: 无风险利率
        sigma: 波动率
        option_type: 'call' 或 'put'
    """
    if not HAS_SCIPY:
        # 简化线性近似
        if option_type == 'call':
            return round(S * (1 + (0.5 - target_delta) * 0.3), 2)
        else:
            return round(S * (1 - (0.5 - abs(target_delta)) * 0.3), 2)
    
    def objective(K):
        return bs_delta(S, K, T, r, sigma, option_type) - target_delta
    
    try:
        strike = brentq(objective, S * 0.5, S * 1.5)
        return round(strike, 2)
    except:
        if option_type == 'call':
            return round(S * (1 + (0.5 - target_delta) * 0.3), 2)
        else:
            return round(S * (1 - (0.5 - abs(target_delta)) * 0.3), 2)
