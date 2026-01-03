"""
GEX (Gamma Exposure) 特征计算模块
"""
from typing import Optional, Tuple
from core.types import GEXRegime
from core.constants import GEX_CONFIG


def calculate_gex_regime(
    spot: float,
    vol_trigger: Optional[float]
) -> GEXRegime:
    """
    判断 GEX 环境
    
    Args:
        spot: 现价
        vol_trigger: VOL TRIGGER 价格
        
    Returns:
        GEXRegime
    """
    if vol_trigger is None:
        return GEXRegime.NEUTRAL
    
    pct_diff = (spot - vol_trigger) / vol_trigger
    neutral_pct = GEX_CONFIG["vol_trigger_neutral_pct"]
    
    if pct_diff > neutral_pct:
        return GEXRegime.POSITIVE
    elif pct_diff < -neutral_pct:
        return GEXRegime.NEGATIVE
    else:
        return GEXRegime.NEUTRAL


def calculate_gamma_wall_proximity(
    spot: float,
    gamma_wall: Optional[float],
    gamma_wall_2: Optional[float] = None
) -> Optional[float]:
    """
    计算距 Gamma Wall 的接近度
    
    Returns:
        距离百分比，越小越接近
    """
    if gamma_wall is None:
        return None
    
    prox1 = abs(spot - gamma_wall) / spot
    
    if gamma_wall_2 is not None:
        prox2 = abs(spot - gamma_wall_2) / spot
        return min(prox1, prox2)
    
    return prox1


def is_pin_risk(
    spot: float,
    gamma_wall: Optional[float],
    gamma_wall_prox: Optional[float] = None
) -> bool:
    """
    判断是否存在 Pin 风险
    """
    if gamma_wall_prox is not None:
        return gamma_wall_prox < GEX_CONFIG["gamma_wall_pin_pct"]
    
    if gamma_wall is None:
        return False
    
    prox = abs(spot - gamma_wall) / spot
    return prox < GEX_CONFIG["gamma_wall_pin_pct"]


def calculate_gex_level(
    regime: GEXRegime,
    vex_net: Optional[float] = None,
    total_net_gex: Optional[float] = None
) -> int:
    """
    计算 GEX 水平 (-2 到 +2)
    
    -2: 强负 GEX
    -1: 弱负 GEX
     0: 中性
    +1: 弱正 GEX
    +2: 强正 GEX
    """
    base_level = {
        GEXRegime.POSITIVE: 1,
        GEXRegime.NEGATIVE: -1,
        GEXRegime.NEUTRAL: 0,
    }.get(regime, 0)
    
    # 根据 VEX 调整
    if vex_net is not None:
        if vex_net < -0.3:
            base_level -= 1
        elif vex_net > 0.3:
            base_level += 1
    
    # 限制范围
    return max(-2, min(2, base_level))


def gex_to_signal_score(
    regime: GEXRegime,
    gex_level: int,
    is_pin: bool
) -> Tuple[float, float]:
    """
    将 GEX 转换为信号分数
    
    Positive GEX → 压制波动 → short vol 信号
    Negative GEX → 放大波动 → long vol 信号
    
    Returns:
        (long_score, short_score)
    """
    # Pin risk 削弱信号
    pin_factor = 0.5 if is_pin else 1.0
    
    if regime == GEXRegime.POSITIVE:
        # 正 GEX 支持 short vol
        strength = abs(gex_level) / 2 * pin_factor
        return -strength * 0.7, strength
    
    elif regime == GEXRegime.NEGATIVE:
        # 负 GEX 支持 long vol
        strength = abs(gex_level) / 2 * pin_factor
        return strength, -strength * 0.7
    
    else:
        return 0.0, 0.0
