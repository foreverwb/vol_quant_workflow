"""
评分计算模块
综合各信号计算 Long/Short Vol 得分
"""
from typing import Dict, Tuple, Optional
from dataclasses import asdict

from core.types import (
    MarketData,
    Features,
    SignalScore,
    Scores,
)
from core.constants import WEIGHTS_LONG_VOL, WEIGHTS_SHORT_VOL

from analysis.features import (
    vrp_to_signal_score,
    gex_to_signal_score,
    term_to_signal_score,
    calculate_carry,
    skew_to_signal_score,
    liquidity_to_signal_score,
)


class SignalCalculator:
    """信号计算器"""
    
    def __init__(self, features: Features, data: MarketData):
        self.features = features
        self.data = data
        self.signals: Dict[str, SignalScore] = {}
        
    def calculate_all_signals(self) -> Dict[str, SignalScore]:
        """计算所有信号"""
        f = self.features
        
        # VRP 信号
        long_vrp, short_vrp = vrp_to_signal_score(
            f.vrp_selected, f.vrp_regime
        )
        self._add_signal("vrp", long_vrp, short_vrp, "VRP信号")
        
        # GEX 信号
        long_gex, short_gex = gex_to_signal_score(
            f.net_gex_regime, f.gex_level, f.is_pin_risk
        )
        self._add_signal("gex", long_gex, short_gex, "GEX环境信号")
        
        # VEX 信号
        long_vex, short_vex = self._calculate_vex_signal()
        self._add_signal("vex", long_vex, short_vex, "VEX信号")
        
        # Carry 信号
        long_carry, short_carry = calculate_carry(f.term_slope)
        self._add_signal("carry", long_carry, short_carry, "Carry信号")
        
        # Skew 信号
        long_skew, short_skew = skew_to_signal_score(
            f.skew_regime, f.skew_asym
        )
        self._add_signal("skew", long_skew, short_skew, "Skew信号")
        
        # RV Momentum 信号
        long_rv, short_rv = self._calculate_rv_signal()
        self._add_signal("rv", long_rv, short_rv, "RV动量信号")
        
        # Liquidity 信号 (作为修正因子)
        liq_long, liq_short = liquidity_to_signal_score(
            f.liquidity_score or 50
        )
        self._add_signal("liq", liq_long - 1, liq_short - 1, "流动性修正")
        
        # VoV 信号
        long_vov, short_vov = self._calculate_vov_signal()
        self._add_signal("vov", long_vov, short_vov, "VoV信号")
        
        # Term structure 信号
        long_ts, short_ts = term_to_signal_score(
            f.term_regime, f.term_slope
        )
        self._add_signal("vix_ts", long_ts, short_ts, "期限结构信号")
        
        return self.signals
    
    def _add_signal(
        self,
        name: str,
        long_score: float,
        short_score: float,
        notes: str = ""
    ):
        """添加信号"""
        weight_long = WEIGHTS_LONG_VOL.get(name, 0)
        weight_short = WEIGHTS_SHORT_VOL.get(name, 0)
        
        self.signals[name] = SignalScore(
            name=name,
            raw_score=long_score if long_score > short_score else -short_score,
            weight_long=weight_long,
            weight_short=weight_short,
            contribution_long=long_score * weight_long,
            contribution_short=short_score * weight_short,
            notes=notes
        )
    
    def _calculate_vex_signal(self) -> Tuple[float, float]:
        """计算 VEX 信号"""
        vex_net = self.data.vex_net
        if vex_net is None:
            return 0.0, 0.0
        
        # 负 VEX → 期权卖方主导 → short vol 有利
        # 正 VEX → 期权买方主导 → long vol 有利
        if vex_net < -0.2:
            strength = min(abs(vex_net), 1.0)
            return -strength * 0.3, strength * 0.5
        elif vex_net > 0.2:
            strength = min(abs(vex_net), 1.0)
            return strength * 0.5, -strength * 0.3
        else:
            return 0.0, 0.0
    
    def _calculate_rv_signal(self) -> Tuple[float, float]:
        """计算 RV 动量信号"""
        rv_momo = self.features.rv_momo
        if rv_momo is None:
            return 0.0, 0.0
        
        # RV 上升 → 波动率上升趋势 → long vol
        # RV 下降 → 波动率下降趋势 → short vol
        if rv_momo > 10:
            strength = min(rv_momo / 30, 1.0)
            return strength * 0.5, -strength * 0.2
        elif rv_momo < -10:
            strength = min(abs(rv_momo) / 30, 1.0)
            return -strength * 0.2, strength * 0.4
        else:
            return 0.0, 0.0
    
    def _calculate_vov_signal(self) -> Tuple[float, float]:
        """计算 VoV 信号"""
        vov_level = self.features.vov_level
        if vov_level is None:
            return 0.0, 0.0
        
        # 高 VoV → 波动率不稳定 → long vol 倾向
        # 低 VoV → 波动率稳定 → short vol 倾向
        if vov_level >= 2:
            return 0.4, -0.2
        elif vov_level == 1:
            return 0.1, 0.0
        else:
            return -0.1, 0.2


def calculate_scores(
    features: Features,
    data: MarketData,
    is_single_stock: bool = True
) -> Scores:
    """
    计算综合评分
    
    Args:
        features: 特征对象
        data: 市场数据
        is_single_stock: 是否为个股 (非指数)
        
    Returns:
        Scores 对象
    """
    calculator = SignalCalculator(features, data)
    signals = calculator.calculate_all_signals()
    
    # 计算加权总分
    long_vol_score = sum(s.contribution_long for s in signals.values())
    short_vol_score = sum(s.contribution_short for s in signals.values())
    
    # 确定主导方向
    if long_vol_score > short_vol_score + 0.3:
        dominant = "long"
    elif short_vol_score > long_vol_score + 0.3:
        dominant = "short"
    else:
        dominant = "neutral"
    
    score_diff = abs(long_vol_score - short_vol_score)
    
    # 置信度
    confidence_pct = min(score_diff / 3 * 100, 100)
    
    return Scores(
        long_vol_score=round(long_vol_score, 4),
        short_vol_score=round(short_vol_score, 4),
        dominant_direction=dominant,
        score_diff=round(score_diff, 4),
        confidence_pct=round(confidence_pct, 2),
        signal_breakdown=signals
    )
