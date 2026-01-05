"""
Regime state computation based on VOL TRIGGER.
This is the SOLE determinant of NET-GEX per strategy specification.
"""

from typing import Dict, Any


# Threshold for neutral regime (within 0.2% of trigger)
NEUTRAL_THRESHOLD_PCT = 0.002

# Threshold for pin risk (within 0.5% of gamma wall)
PIN_THRESHOLD_PCT = 0.005


def compute_regime_state(
    spot: float,
    vol_trigger: float,
    net_gex_sign: int,
    gamma_wall_call: float,
    gamma_wall_put: float,
    gamma_wall_proximity_pct: float,
) -> Dict[str, Any]:
    """
    Compute regime state based on VOL TRIGGER.
    
    Per strategy specification:
    - Spot >= VOL_TRIGGER → NET-GEX > 0 (positive gamma, vol suppression)
    - Spot < VOL_TRIGGER → NET-GEX < 0 (negative gamma, vol amplification)
    - Within 0.2% of trigger → Neutral (flip-prone)
    
    Args:
        spot: Current spot price
        vol_trigger: VOL TRIGGER level
        net_gex_sign: Pre-computed GEX sign (-1, 0, +1)
        gamma_wall_call: Call gamma wall level
        gamma_wall_put: Put gamma wall level
        gamma_wall_proximity_pct: Proximity to nearest wall (%)
        
    Returns:
        Dictionary with regime analysis
    """
    # Calculate distance to VOL TRIGGER
    trigger_distance = spot - vol_trigger
    trigger_distance_pct = abs(trigger_distance) / vol_trigger if vol_trigger > 0 else 0
    
    # Determine regime state
    if trigger_distance_pct <= NEUTRAL_THRESHOLD_PCT:
        regime_state = "neutral"
        regime_description = "Near trigger line, flip-prone"
        vol_bias = "uncertain"
    elif spot >= vol_trigger:
        regime_state = "positive_gamma"
        regime_description = "Above trigger, vol suppression, pin-prone"
        vol_bias = "short_vol"
    else:
        regime_state = "negative_gamma"
        regime_description = "Below trigger, vol amplification, breakout-prone"
        vol_bias = "long_vol"
    
    # Validate against provided net_gex_sign
    expected_sign = 1 if spot >= vol_trigger else -1
    if trigger_distance_pct <= NEUTRAL_THRESHOLD_PCT:
        expected_sign = 0
    
    sign_consistent = (net_gex_sign == expected_sign) or (net_gex_sign == 0 and trigger_distance_pct <= NEUTRAL_THRESHOLD_PCT)
    
    # Determine pin risk
    is_pin_risk = (
        regime_state == "positive_gamma" and
        gamma_wall_proximity_pct <= PIN_THRESHOLD_PCT
    )
    
    # Calculate distances to walls
    call_wall_distance = gamma_wall_call - spot if gamma_wall_call > 0 else None
    put_wall_distance = spot - gamma_wall_put if gamma_wall_put > 0 else None
    
    call_wall_distance_pct = call_wall_distance / spot if call_wall_distance else None
    put_wall_distance_pct = put_wall_distance / spot if put_wall_distance else None
    
    # Determine nearest wall
    nearest_wall = None
    nearest_wall_distance_pct = None
    
    if call_wall_distance_pct is not None and put_wall_distance_pct is not None:
        if abs(call_wall_distance_pct) < abs(put_wall_distance_pct):
            nearest_wall = "call"
            nearest_wall_distance_pct = call_wall_distance_pct
        else:
            nearest_wall = "put"
            nearest_wall_distance_pct = put_wall_distance_pct
    elif call_wall_distance_pct is not None:
        nearest_wall = "call"
        nearest_wall_distance_pct = call_wall_distance_pct
    elif put_wall_distance_pct is not None:
        nearest_wall = "put"
        nearest_wall_distance_pct = put_wall_distance_pct
    
    # Regime flip risk assessment
    flip_risk = "low"
    if trigger_distance_pct <= 0.005:  # Within 0.5%
        flip_risk = "high"
    elif trigger_distance_pct <= 0.01:  # Within 1%
        flip_risk = "moderate"
    
    return {
        "regime_state": regime_state,
        "regime_description": regime_description,
        "vol_bias": vol_bias,
        "net_gex_sign": net_gex_sign,
        "sign_consistent": sign_consistent,
        "trigger_distance": trigger_distance,
        "trigger_distance_pct": trigger_distance_pct,
        "is_pin_risk": is_pin_risk,
        "gamma_wall_proximity_pct": gamma_wall_proximity_pct,
        "nearest_wall": nearest_wall,
        "nearest_wall_distance_pct": nearest_wall_distance_pct,
        "call_wall_distance_pct": call_wall_distance_pct,
        "put_wall_distance_pct": put_wall_distance_pct,
        "flip_risk": flip_risk,
    }


def detect_regime_change(
    current_regime: str,
    previous_regime: str,
) -> Dict[str, Any]:
    """
    Detect regime change between updates.
    
    Args:
        current_regime: Current regime state
        previous_regime: Previous regime state
        
    Returns:
        Dictionary with change detection results
    """
    regime_changed = current_regime != previous_regime
    
    # Classify the transition
    transition = None
    significance = "none"
    
    if regime_changed:
        transition = f"{previous_regime} -> {current_regime}"
        
        # Significant transitions
        if (previous_regime == "positive_gamma" and current_regime == "negative_gamma") or \
           (previous_regime == "negative_gamma" and current_regime == "positive_gamma"):
            significance = "major"  # Full regime flip
        elif current_regime == "neutral" or previous_regime == "neutral":
            significance = "minor"  # Transition through neutral
    
    return {
        "regime_changed": regime_changed,
        "transition": transition,
        "significance": significance,
        "alert": regime_changed and significance == "major",
    }
