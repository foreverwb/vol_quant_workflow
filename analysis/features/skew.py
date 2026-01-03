"""
Skew (波动率偏斜) 计算模块
"""
from typing import Optional, Tuple
from core.types import SkewRegime


def calculate_skew_asymmetry(
    put_skew_25: Optional[float],
    call_skew_25: Optional[float]
) -> Optional[float]:
    """
    计算 Skew 不对称性
    
    正值: Put skew 更陡 (下行保护需求高)
    负值: Call skew 更陡 (上行期望高)
    """
    if put_skew_25 is None or call_skew_25 is None:
        return None
    
    # Put skew 通常为正，Call skew 通常为负
    return put_skew_25 - abs(call_skew_25)


def determine_skew_regime(
    skew_asym: Optional[float]
) -> SkewRegime:
    """
    判断 Skew 状态
    """
    if skew_asym is None:
        return SkewRegime.BALANCED
    
    if skew_asym > 3:  # Put skew 明显更陡
        return SkewRegime.PUT_HEAVY
    elif skew_asym < -3:  # Call skew 明显更陡
        return SkewRegime.CALL_HEAVY
    else:
        return SkewRegime.BALANCED


def skew_to_signal_score(
    skew_regime: SkewRegime,
    skew_asym: Optional[float]
) -> Tuple[float, float]:
    """
    将 Skew 转换为信号分数
    
    Put Heavy: 市场担忧下行 → 可卖 put skew
    Call Heavy: 市场看涨 → 可卖 call skew
    
    Returns:
        (long_score, short_score)
    """
    if skew_asym is None:
        return 0.0, 0.0
    
    if skew_regime == SkewRegime.PUT_HEAVY:
        # Put skew 陡峭，可以卖 OTM put
        strength = min(abs(skew_asym) / 10, 1.0)
        return -strength * 0.2, strength * 0.4
    
    elif skew_regime == SkewRegime.CALL_HEAVY:
        # Call skew 陡峭，可以卖 OTM call
        strength = min(abs(skew_asym) / 10, 1.0)
        return strength * 0.2, strength * 0.3
    
    else:
        return 0.0, 0.0


def calculate_smile_curvature(
    put_skew_25: Optional[float],
    call_skew_25: Optional[float],
    iv_atm: Optional[float]
) -> Optional[float]:
    """
    计算微笑曲率
    
    曲率 = (25D_Put_IV + 25D_Call_IV - 2 * ATM_IV) / ATM_IV
    高曲率: 市场预期尾部风险大
    """
    if any(v is None for v in [put_skew_25, call_skew_25, iv_atm]):
        return None
    
    if iv_atm == 0:
        return None
    
    # put_skew_25 和 call_skew_25 是相对于 ATM 的差值
    iv_put_25 = iv_atm + put_skew_25
    iv_call_25 = iv_atm + call_skew_25
    
    curvature = (iv_put_25 + iv_call_25 - 2 * iv_atm) / iv_atm
    
    return curvature
