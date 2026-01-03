"""
流动性计算模块
"""
from typing import Optional, Tuple
from core.constants import LIQUIDITY_CONFIG


def calculate_liquidity_score(
    spread_atm: Optional[float],
    volume_ratio: Optional[float] = None
) -> float:
    """
    计算流动性评分 (0-100)
    
    Args:
        spread_atm: ATM Bid-Ask Spread (%)
        volume_ratio: 成交量相对平均的比率 (可选)
    """
    score = 50.0  # 基准分
    
    if spread_atm is not None:
        if spread_atm <= LIQUIDITY_CONFIG["spread_excellent"]:
            spread_score = 100
        elif spread_atm <= LIQUIDITY_CONFIG["spread_good"]:
            spread_score = 70
        elif spread_atm <= LIQUIDITY_CONFIG["spread_poor"]:
            spread_score = 40
        else:
            spread_score = 20
        
        score = spread_score * LIQUIDITY_CONFIG["spread_weight"]
    
    if volume_ratio is not None:
        if volume_ratio >= 1.5:
            volume_score = 100
        elif volume_ratio >= 1.0:
            volume_score = 70
        elif volume_ratio >= 0.5:
            volume_score = 50
        else:
            volume_score = 30
        
        score += volume_score * LIQUIDITY_CONFIG["volume_weight"]
    else:
        # 没有成交量数据时，用 spread 填充
        score = score / LIQUIDITY_CONFIG["spread_weight"] if spread_atm else 50
    
    return min(100, max(0, score))


def liquidity_to_signal_score(
    liquidity_score: float
) -> Tuple[float, float]:
    """
    将流动性转换为信号分数
    
    高流动性: 两个方向都可执行
    低流动性: 削弱所有信号
    
    Returns:
        (long_modifier, short_modifier) 作为乘数使用
    """
    if liquidity_score >= 80:
        # 优秀流动性，不削弱
        return 1.0, 1.0
    elif liquidity_score >= 60:
        # 良好流动性，轻微削弱
        return 0.9, 0.9
    elif liquidity_score >= 40:
        # 一般流动性，中等削弱
        return 0.7, 0.7
    else:
        # 差流动性，大幅削弱
        return 0.5, 0.5


def calculate_execution_quality(
    spread_atm: Optional[float],
    ask_premium_pct: Optional[float] = None
) -> str:
    """
    评估执行质量
    
    Returns:
        "excellent" / "good" / "fair" / "poor"
    """
    if spread_atm is None:
        return "fair"
    
    if spread_atm <= 0.02:
        quality = "excellent"
    elif spread_atm <= 0.05:
        quality = "good"
    elif spread_atm <= 0.10:
        quality = "fair"
    else:
        quality = "poor"
    
    # Ask premium 调整
    if ask_premium_pct is not None and ask_premium_pct > 5:
        # 卖方溢价高，执行质量下降
        quality_order = ["excellent", "good", "fair", "poor"]
        idx = quality_order.index(quality)
        if idx < 3:
            quality = quality_order[idx + 1]
    
    return quality
