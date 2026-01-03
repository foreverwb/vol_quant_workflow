"""
期限结构计算模块
"""
from typing import Optional, Tuple
from core.types import TermStructure
from core.constants import TERM_STRUCTURE_CONFIG


def calculate_term_slope(
    iv_front: Optional[float],
    iv_back: Optional[float]
) -> Optional[float]:
    """
    计算期限结构斜率
    
    正值: 近月 IV > 远月 IV (backwardation)
    负值: 近月 IV < 远月 IV (contango)
    """
    if iv_front is None or iv_back is None:
        return None
    
    return iv_front - iv_back


def determine_term_structure(
    term_slope: Optional[float]
) -> TermStructure:
    """
    判断期限结构类型
    """
    if term_slope is None:
        return TermStructure.FLAT
    
    if term_slope > TERM_STRUCTURE_CONFIG["backwardation_threshold"]:
        return TermStructure.BACKWARDATION
    elif term_slope < TERM_STRUCTURE_CONFIG["contango_threshold"]:
        return TermStructure.CONTANGO
    else:
        return TermStructure.FLAT


def term_to_signal_score(
    term_structure: TermStructure,
    term_slope: Optional[float]
) -> Tuple[float, float]:
    """
    将期限结构转换为信号分数
    
    Backwardation: 近月 IV 高 → 可卖近买远 → short vol 倾向
    Contango: 远月 IV 高 → 正常结构 → neutral/long vol
    
    Returns:
        (long_score, short_score)
    """
    if term_slope is None:
        return 0.0, 0.0
    
    if term_structure == TermStructure.BACKWARDATION:
        # Backwardation 支持 short vol (卖近买远)
        strength = min(abs(term_slope) / 10, 1.0)
        return -strength * 0.3, strength * 0.5
    
    elif term_structure == TermStructure.CONTANGO:
        # Contango 微弱支持 long vol
        strength = min(abs(term_slope) / 10, 1.0)
        return strength * 0.2, -strength * 0.1
    
    else:
        return 0.0, 0.0


def calculate_carry(
    term_slope: Optional[float],
    spread_atm: Optional[float] = None
) -> Tuple[float, float]:
    """
    计算 Carry 信号
    
    Carry = 时间价值衰减成本/收益
    正 Carry: short vol 有利 (收取 theta)
    负 Carry: long vol 有利
    
    Returns:
        (long_score, short_score)
    """
    if term_slope is None:
        return 0.0, 0.0
    
    # Term slope > 0 意味着 short near / long far 有正 carry
    if term_slope > 2:
        strength = min(term_slope / 10, 1.0)
        return -strength * 0.3, strength * 0.6
    elif term_slope < -2:
        strength = min(abs(term_slope) / 10, 1.0)
        return strength * 0.3, -strength * 0.2
    else:
        return 0.0, 0.1  # 微弱 short bias
