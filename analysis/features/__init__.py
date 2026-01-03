"""
特征计算模块
包含 VRP、GEX、期限结构、Skew、流动性等特征计算
"""
from typing import Dict, Any, Optional
from dataclasses import asdict

from .vrp import calculate_vrp, vrp_to_signal_score
from .gex import (
    calculate_gex_regime,
    calculate_gamma_wall_proximity,
    is_pin_risk,
    calculate_gex_level,
    gex_to_signal_score,
)
from .term_structure import (
    calculate_term_slope,
    determine_term_structure,
    term_to_signal_score,
    calculate_carry,
)
from .skew import (
    calculate_skew_asymmetry,
    determine_skew_regime,
    skew_to_signal_score,
    calculate_smile_curvature,
)
from .liquidity import (
    calculate_liquidity_score,
    liquidity_to_signal_score,
    calculate_execution_quality,
)

from core.types import MarketData, Features


def calculate_all_features(
    data: MarketData,
    is_event: bool = False
) -> Features:
    """
    计算所有衍生特征
    
    Args:
        data: 市场数据对象
        is_event: 是否为事件期
        
    Returns:
        Features 对象
    """
    # VRP
    vrp_hv20, vrp_hv10, vrp_selected, vrp_regime = calculate_vrp(
        iv_atm=data.iv_atm or data.iv_front,
        hv20=data.hv20,
        hv10=data.hv10,
        is_event=is_event
    )
    
    # GEX
    gex_regime = calculate_gex_regime(data.spot, data.vol_trigger)
    gamma_wall_prox = calculate_gamma_wall_proximity(
        data.spot, data.gamma_wall, data.gamma_wall_2
    )
    pin_risk = is_pin_risk(data.spot, data.gamma_wall, gamma_wall_prox)
    gex_level = calculate_gex_level(gex_regime, data.vex_net)
    
    # Term Structure
    term_slope = data.term_slope
    if term_slope is None:
        term_slope = calculate_term_slope(data.iv_front, data.iv_back)
    term_regime = determine_term_structure(term_slope)
    
    # Skew
    skew_asym = calculate_skew_asymmetry(data.put_skew_25, data.call_skew_25)
    skew_regime = determine_skew_regime(skew_asym)
    
    # RV Momentum
    rv_momo = None
    if data.hv10 and data.hv60:
        rv_momo = (data.hv10 - data.hv60) / data.hv60 * 100
    
    # Liquidity
    liquidity_score = calculate_liquidity_score(data.spread_atm)
    
    # VoV
    vov_level = None
    if data.vvix:
        if data.vvix > 25:
            vov_level = 2  # High VoV
        elif data.vvix > 20:
            vov_level = 1  # Medium VoV
        else:
            vov_level = 0  # Low VoV
    
    return Features(
        vrp_hv20=vrp_hv20,
        vrp_hv10=vrp_hv10,
        vrp_selected=vrp_selected,
        vrp_regime=vrp_regime,
        term_slope=term_slope,
        term_regime=term_regime,
        gex_level=gex_level,
        gamma_wall_prox=gamma_wall_prox,
        is_pin_risk=pin_risk,
        net_gex_regime=gex_regime,
        skew_asym=skew_asym,
        skew_regime=skew_regime,
        rv_momo=rv_momo,
        liquidity_score=liquidity_score,
        vov_level=vov_level,
    )


__all__ = [
    # 主函数
    "calculate_all_features",
    
    # VRP
    "calculate_vrp",
    "vrp_to_signal_score",
    
    # GEX
    "calculate_gex_regime",
    "calculate_gamma_wall_proximity",
    "is_pin_risk",
    "calculate_gex_level",
    "gex_to_signal_score",
    
    # Term Structure
    "calculate_term_slope",
    "determine_term_structure",
    "term_to_signal_score",
    "calculate_carry",
    
    # Skew
    "calculate_skew_asymmetry",
    "determine_skew_regime",
    "skew_to_signal_score",
    "calculate_smile_curvature",
    
    # Liquidity
    "calculate_liquidity_score",
    "liquidity_to_signal_score",
    "calculate_execution_quality",
]
