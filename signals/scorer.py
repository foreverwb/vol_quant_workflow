"""
Signal scoring - Converts features to normalized signal scores.
All signals follow "long vol positive" convention.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from .normalizer import zscore, indicator
from ..core.config import Config, get_config


@dataclass
class SignalScores:
    """Individual signal scores."""
    s_vrp: float = 0.0
    s_gex: float = 0.0
    s_vex: float = 0.0
    s_carry: float = 0.0
    s_skew: float = 0.0
    s_vanna: float = 0.0
    s_rv: float = 0.0
    s_liq: float = 0.0
    # Enhanced signals (optional)
    s_vov: Optional[float] = None
    s_vix_ts: Optional[float] = None
    s_rim: Optional[float] = None
    s_compress: Optional[float] = None
    s_eir_long: Optional[float] = None
    s_eir_short: Optional[float] = None
    s_corr_idx: Optional[float] = None
    s_flow_putcrowd: Optional[float] = None


@dataclass
class CompositeScores:
    """Aggregated long/short vol scores."""
    long_vol_score: float
    short_vol_score: float


class SignalScorer:
    """
    Computes signal scores from features.
    
    All signals are normalized to "long vol positive" convention:
    - Positive signal favors long volatility
    - Negative signal favors short volatility
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize with configuration."""
        self.config = config or get_config()
        
        # Historical statistics for z-score normalization
        # In production, these would be computed from historical data
        self._stats = {
            "vrp": {"mean": 0.02, "std": 0.05},      # VRP typically 2% +/- 5%
            "term_slope": {"mean": 0.01, "std": 0.02},
            "term_curv": {"mean": 0.0, "std": 0.01},
            "skew": {"mean": 0.02, "std": 0.03},
            "vex": {"mean": 0.0, "std": 1.0},        # Normalized VEX
            "vanna": {"mean": 0.0, "std": 1.0},      # Normalized vanna
            "rv_momo": {"mean": 0.0, "std": 0.3},    # RV momentum
            "spread": {"mean": 0.02, "std": 0.02},   # 2% spread typical
            "ivask": {"mean": 0.01, "std": 0.01},    # 1% ask premium typical
        }
    
    def compute_signals(self, features: Dict[str, Any]) -> SignalScores:
        """
        Compute all signal scores from features.
        
        Args:
            features: Dictionary of computed features
            
        Returns:
            SignalScores dataclass with all scores
        """
        scores = SignalScores()
        
        # S_vrp: -z(VRP) → Long vol positive when VRP is LOW (IV < HV)
        vrp = features["vrp"]["vrp_selected"]
        scores.s_vrp = -zscore(
            vrp, 
            self._stats["vrp"]["mean"], 
            self._stats["vrp"]["std"]
        )
        
        # S_carry: -z(TermSlope) - 0.5*z(TermCurv)
        term = features["term_structure"]
        z_slope = zscore(
            term["term_slope"],
            self._stats["term_slope"]["mean"],
            self._stats["term_slope"]["std"]
        )
        z_curv = zscore(
            term["term_curvature"],
            self._stats["term_curv"]["mean"],
            self._stats["term_curv"]["std"]
        )
        scores.s_carry = -z_slope - 0.5 * z_curv
        
        # S_skew: +z(SkewAsym) → Long vol positive when puts are rich
        skew = features["skew"]
        scores.s_skew = zscore(
            skew["skew_asymmetry"],
            self._stats["skew"]["mean"],
            self._stats["skew"]["std"]
        )
        
        # S_gex: Based on VOL TRIGGER regime
        regime = features["regime"]
        scores.s_gex = self._compute_gex_signal(regime)
        
        # S_vex: +z(-VEX_net) → Long vol positive when VEX is negative
        vex_net = features.get("vex_net_5_60", 0.0)
        scores.s_vex = zscore(
            -vex_net,
            self._stats["vex"]["mean"],
            self._stats["vex"]["std"]
        )
        
        # S_vanna: -z(|Vanna_atm|) → Long vol positive when vanna exposure is LOW
        vanna_abs = features.get("vanna_atm_abs", 0.0)
        scores.s_vanna = -zscore(
            vanna_abs,
            self._stats["vanna"]["mean"],
            self._stats["vanna"]["std"]
        )
        
        # S_rv: +z(RV_Momo) → Long vol positive when recent vol is elevated
        rv_momo = features.get("rv_momentum", 0.0)
        scores.s_rv = zscore(
            rv_momo,
            self._stats["rv_momo"]["mean"],
            self._stats["rv_momo"]["std"]
        )
        
        # S_liq: -[max(0, z(spread)) + 0.5*max(0, z(ivask_prem))]
        liq = features.get("liquidity", {})
        z_spread = liq.get("spread_z", 0.0)
        z_ivask = liq.get("ivask_premium_z", 0.0)
        scores.s_liq = -(max(0, z_spread) + 0.5 * max(0, z_ivask))
        
        return scores
    
    def _compute_gex_signal(self, regime: Dict[str, Any]) -> float:
        """
        Compute GEX signal based on VOL TRIGGER regime.
        
        S_gex_level: Spot < VOL_TRIGGER → +1, Spot >= VOL_TRIGGER → -1
        S_pin: -1 if pin risk (positive gamma + near wall)
        S_gex = S_gex_level + S_pin
        """
        regime_state = regime["regime_state"]
        is_pin_risk = regime.get("is_pin_risk", False)
        trigger_distance_pct = regime.get("trigger_distance_pct", 0.0)
        
        # S_gex_level: Simple +1/-1 based on regime
        if regime_state == "negative_gamma":
            s_gex_level = 1.0
        elif regime_state == "positive_gamma":
            s_gex_level = -1.0
        else:  # neutral
            s_gex_level = 0.0
        
        # Intensity based on distance from trigger
        # Further from trigger = stronger signal
        intensity = min(1.0, trigger_distance_pct / 0.02)  # Max intensity at 2%
        s_gex_level *= intensity
        
        # S_pin: Penalty when in positive gamma AND near wall
        s_pin = 0.0
        if is_pin_risk and regime_state == "positive_gamma":
            s_pin = -1.0
        
        return s_gex_level + s_pin
    
    def compute_composite_scores(
        self,
        signals: SignalScores,
        is_single_stock: bool = False,
        is_index: bool = False,
    ) -> CompositeScores:
        """
        Compute weighted composite scores for long/short vol.
        
        Args:
            signals: Individual signal scores
            is_single_stock: Whether target is single stock (adjusts weights)
            is_index: Whether target is index (enables corr signal)
            
        Returns:
            CompositeScores with long_vol_score and short_vol_score
        """
        w_long = self.config.weights_long
        w_short = self.config.weights_short
        
        # Adjust weights for single stock
        gex_boost = w_long.single_stock_boost if is_single_stock else 0.0
        
        # Long Vol Score L
        long_vol_score = (
            w_long.vrp * signals.s_vrp +
            (w_long.gex + gex_boost) * signals.s_gex +
            (w_long.vex + gex_boost) * signals.s_vex +
            w_long.carry * signals.s_carry +
            (w_long.skew + gex_boost) * signals.s_skew +
            w_long.vanna * signals.s_vanna +
            w_long.rv * signals.s_rv +
            w_long.liq * signals.s_liq
        )
        
        # Add enhanced signals if available
        if signals.s_vov is not None:
            long_vol_score += w_long.vov * signals.s_vov
        if signals.s_vix_ts is not None:
            long_vol_score += w_long.vix_ts * signals.s_vix_ts
        if signals.s_rim is not None:
            long_vol_score += w_long.rim * signals.s_rim
        if signals.s_compress is not None:
            long_vol_score += w_long.compress * signals.s_compress
        if signals.s_eir_long is not None:
            long_vol_score += w_long.eir * signals.s_eir_long
        
        # Short Vol Score S (signals are inverted except liquidity)
        short_vol_score = (
            w_short.vrp * (-signals.s_vrp) +
            w_short.gex * (-signals.s_gex) +
            w_short.vex * (-signals.s_vex) +
            w_short.carry * (-signals.s_carry) +
            w_short.skew * (-signals.s_skew) +
            w_short.rv * (-signals.s_rv) +
            w_short.liq * signals.s_liq  # Liquidity keeps same sign
        )
        
        # Add enhanced signals if available
        if signals.s_vov is not None:
            short_vol_score += w_short.vov * (-signals.s_vov)
        if signals.s_vix_ts is not None:
            short_vol_score += w_short.vix_ts * (-signals.s_vix_ts)
        if signals.s_rim is not None:
            short_vol_score += w_short.rim * (-signals.s_rim)
        if signals.s_compress is not None:
            short_vol_score += w_short.compress * (-signals.s_compress)
        if signals.s_eir_short is not None:
            short_vol_score += w_short.eir * signals.s_eir_short
        if is_index and signals.s_corr_idx is not None:
            short_vol_score += w_short.corr_idx * signals.s_corr_idx
        if signals.s_flow_putcrowd is not None:
            short_vol_score += w_short.flow_putcrowd * signals.s_flow_putcrowd
        
        return CompositeScores(
            long_vol_score=long_vol_score,
            short_vol_score=short_vol_score,
        )
