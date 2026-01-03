"""
VRP (波动率风险溢价) 计算模块
"""
from typing import Optional, Tuple
from core.types import VRPRegime
from core.constants import VRP_CONFIG


def calculate_vrp(
    iv_atm: Optional[float],
    hv20: Optional[float],
    hv10: Optional[float] = None,
    is_event: bool = False
) -> Tuple[Optional[float], Optional[float], Optional[float], VRPRegime]:
    """
    计算波动率风险溢价
    
    Args:
        iv_atm: ATM 隐含波动率
        hv20: 20日历史波动率
        hv10: 10日历史波动率 (可选)
        is_event: 是否为事件期
        
    Returns:
        (vrp_hv20, vrp_hv10, vrp_selected, vrp_regime)
    """
    vrp_hv20 = None
    vrp_hv10 = None
    
    if iv_atm and hv20:
        vrp_hv20 = iv_atm - hv20
    
    if iv_atm and hv10:
        vrp_hv10 = iv_atm - hv10
    
    # 选择使用的 VRP
    if is_event and vrp_hv10 is not None:
        vrp_selected = vrp_hv10
    elif vrp_hv20 is not None:
        vrp_selected = vrp_hv20
    else:
        vrp_selected = None
    
    # 判断 regime
    if vrp_selected is None:
        regime = VRPRegime.FAIR
    elif vrp_selected < VRP_CONFIG["long_bias_threshold"]:
        regime = VRPRegime.LONG_BIAS
    elif vrp_selected > VRP_CONFIG["short_bias_threshold"]:
        regime = VRPRegime.SHORT_BIAS
    else:
        regime = VRPRegime.FAIR
    
    return vrp_hv20, vrp_hv10, vrp_selected, regime


def vrp_to_signal_score(
    vrp: Optional[float],
    regime: VRPRegime
) -> Tuple[float, float]:
    """
    将 VRP 转换为信号分数
    
    Returns:
        (long_score, short_score) 范围 [-1, 1]
    """
    if vrp is None:
        return 0.0, 0.0
    
    # VRP 越负，越支持 long vol
    # VRP 越正，越支持 short vol
    
    if regime == VRPRegime.LONG_BIAS:
        # VRP < -3%: 强 long vol 信号
        strength = min(abs(vrp) / 10, 1.0)
        return strength, -strength * 0.7
    
    elif regime == VRPRegime.SHORT_BIAS:
        # VRP > 3%: 强 short vol 信号
        strength = min(abs(vrp) / 10, 1.0)
        return -strength * 0.7, strength
    
    else:
        # 中性，微弱信号
        if vrp < 0:
            return 0.2, -0.1
        else:
            return -0.1, 0.2
