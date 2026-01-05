"""
Feature calculator - Orchestrates feature computation from raw inputs.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from .vrp import compute_vrp
from .term_structure import compute_term_metrics
from .skew import compute_skew_metrics
from .regime import compute_regime_state


@dataclass
class FeatureSet:
    """Complete set of computed features."""
    # VRP features
    vrp_event_week: Optional[float]
    vrp_30d: float
    vrp_selected: float  # Based on context (event vs regular)
    
    # Term structure features
    term_slope: float
    term_curvature: float
    
    # Skew features
    skew_asymmetry: float
    
    # Regime features
    regime_state: str  # "positive_gamma" | "negative_gamma" | "neutral"
    net_gex_sign: int  # +1, -1, 0
    gamma_wall_proximity_pct: float
    is_pin_risk: bool
    
    # RV momentum
    rv_momentum: float  # HV10/HV60 - 1
    
    # Liquidity features
    spread_z: float  # z-score of spread
    ivask_premium_z: float  # z-score of ask premium
    liquidity_penalty: float  # Combined penalty score


class FeatureCalculator:
    """
    Calculates all features from input data.
    Pure deterministic logic - no inference or guessing.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration."""
        self.config = config or {}
    
    def calculate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate all features from input data.
        
        Args:
            input_data: Validated input dictionary with 22 core fields
            
        Returns:
            Dictionary containing all computed features
        """
        # Extract input sections
        market = input_data["market"]
        regime = input_data["regime"]
        volatility = input_data["volatility"]
        structure = input_data["structure"]
        liquidity = input_data["liquidity"]
        
        # Compute VRP
        vrp_features = compute_vrp(
            iv_event_atm=volatility.get("iv_event_atm"),
            iv_m1_atm=volatility["iv_m1_atm"],
            iv_m2_atm=volatility.get("iv_m2_atm"),
            hv10=volatility["hv10"],
            hv20=volatility["hv20"],
            hv60=volatility["hv60"],
            is_event_week=volatility.get("iv_event_atm") is not None,
        )
        
        # Compute term structure metrics
        term_features = compute_term_metrics(
            term_slope=structure["term_slope"],
            term_curvature=structure["term_curvature"],
        )
        
        # Compute skew metrics
        skew_features = compute_skew_metrics(
            skew_asymmetry=structure["skew_asymmetry"],
        )
        
        # Compute regime state
        regime_features = compute_regime_state(
            spot=market["spot"],
            vol_trigger=regime["vol_trigger"],
            net_gex_sign=regime["net_gex_sign"],
            gamma_wall_call=regime["gamma_wall_call"],
            gamma_wall_put=regime["gamma_wall_put"],
            gamma_wall_proximity_pct=regime["gamma_wall_proximity_pct"],
        )
        
        # Compute RV momentum
        rv_momentum = (volatility["hv10"] / volatility["hv60"]) - 1.0 if volatility["hv60"] > 0 else 0.0
        
        # Compute liquidity features
        liquidity_features = self._compute_liquidity_features(
            spread_atm=liquidity["spread_atm"],
            iv_ask_premium_pct=liquidity["iv_ask_premium_pct"],
            liquidity_flag=liquidity["liquidity_flag"],
        )
        
        # Aggregate all features
        return {
            "vrp": vrp_features,
            "term_structure": term_features,
            "skew": skew_features,
            "regime": regime_features,
            "rv_momentum": rv_momentum,
            "liquidity": liquidity_features,
            "vex_net_5_60": structure["vex_net_5_60"],
            "vanna_atm_abs": structure["vanna_atm_abs"],
        }
    
    def _compute_liquidity_features(
        self,
        spread_atm: float,
        iv_ask_premium_pct: float,
        liquidity_flag: str,
    ) -> Dict[str, float]:
        """Compute liquidity-related features."""
        # Simple z-score approximation (in production, use historical distribution)
        # These are placeholder normalizations
        spread_z = spread_atm / 0.05  # Assuming 5% spread is 1 std
        ivask_premium_z = iv_ask_premium_pct / 2.0  # Assuming 2% premium is 1 std
        
        # Liquidity penalty combines spread and ask premium
        liquidity_penalty = max(0, spread_z) + 0.5 * max(0, ivask_premium_z)
        
        # Apply flag-based adjustment
        if liquidity_flag == "poor":
            liquidity_penalty *= 1.5
        elif liquidity_flag == "fair":
            liquidity_penalty *= 1.2
        
        return {
            "spread_z": spread_z,
            "ivask_premium_z": ivask_premium_z,
            "liquidity_penalty": liquidity_penalty,
            "liquidity_flag": liquidity_flag,
        }
    
    def calculate_for_update(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lightweight feature calculation for update mode.
        Only computes regime and key metrics, no full feature set.
        """
        market = input_data["market"]
        regime = input_data["regime"]
        volatility = input_data["volatility"]
        
        # Compute regime state only
        regime_features = compute_regime_state(
            spot=market["spot"],
            vol_trigger=regime["vol_trigger"],
            net_gex_sign=regime["net_gex_sign"],
            gamma_wall_call=regime["gamma_wall_call"],
            gamma_wall_put=regime["gamma_wall_put"],
            gamma_wall_proximity_pct=regime["gamma_wall_proximity_pct"],
        )
        
        # Quick VRP calculation
        vrp_30d = volatility["iv_m1_atm"] - volatility["hv20"]
        
        return {
            "regime": regime_features,
            "vrp_30d": vrp_30d,
            "spot": market["spot"],
            "vol_trigger": regime["vol_trigger"],
            "gamma_wall_proximity_pct": regime["gamma_wall_proximity_pct"],
        }
