"""
Variance Risk Premium (VRP) computation.
VRP = IV - HV (positive indicates premium for selling vol)
"""

from typing import Dict, Any, Optional


def compute_vrp(
    iv_event_atm: Optional[float],
    iv_m1_atm: float,
    iv_m2_atm: Optional[float],
    hv10: float,
    hv20: float,
    hv60: float,
    is_event_week: bool = False,
) -> Dict[str, Any]:
    """
    Compute Variance Risk Premium metrics.
    
    HV window matching per strategy spec:
    - Event week / 5-20 DTE → HV10
    - Near month → HV20
    - Next near month → HV60
    
    Args:
        iv_event_atm: Event week ATM IV (optional)
        iv_m1_atm: Front month ATM IV
        iv_m2_atm: Back month ATM IV (optional)
        hv10: 10-day historical volatility
        hv20: 20-day historical volatility
        hv60: 60-day historical volatility
        is_event_week: Whether current period is event week
        
    Returns:
        Dictionary with VRP metrics
    """
    # VRP calculations
    vrp_event_week = None
    if iv_event_atm is not None:
        vrp_event_week = iv_event_atm - hv10
    
    vrp_30d = iv_m1_atm - hv20
    
    vrp_60d = None
    if iv_m2_atm is not None:
        vrp_60d = iv_m2_atm - hv60
    
    # Select appropriate VRP based on context
    if is_event_week and vrp_event_week is not None:
        vrp_selected = vrp_event_week
        vrp_context = "event_week"
    else:
        vrp_selected = vrp_30d
        vrp_context = "regular_30d"
    
    # Normalized VRP (as percentage of HV)
    vrp_normalized = vrp_30d / hv20 if hv20 > 0 else 0.0
    
    # VRP regime classification
    if vrp_selected > 0.05:  # IV significantly above HV (>5 vol points)
        vrp_regime = "high_premium"
    elif vrp_selected < -0.05:  # HV significantly above IV
        vrp_regime = "discount"
    else:
        vrp_regime = "fair"
    
    return {
        "vrp_event_week": vrp_event_week,
        "vrp_30d": vrp_30d,
        "vrp_60d": vrp_60d,
        "vrp_selected": vrp_selected,
        "vrp_context": vrp_context,
        "vrp_normalized": vrp_normalized,
        "vrp_regime": vrp_regime,
    }


def compute_carry(
    iv_m1_atm: float,
    iv_m2_atm: Optional[float],
    days_to_m1: int = 30,
    days_to_m2: int = 60,
) -> Dict[str, float]:
    """
    Compute carry (theta decay) metrics.
    
    Carry is the expected decay if IV stays constant.
    Positive carry favors short vol (collect premium).
    
    Args:
        iv_m1_atm: Front month ATM IV
        iv_m2_atm: Back month ATM IV
        days_to_m1: Days to front month expiry
        days_to_m2: Days to back month expiry
        
    Returns:
        Dictionary with carry metrics
    """
    import math
    
    # Daily carry from front month (approximation)
    # Theta decay is roughly proportional to IV / sqrt(DTE)
    daily_carry_m1 = iv_m1_atm / (2 * math.sqrt(days_to_m1)) if days_to_m1 > 0 else 0
    
    # Calendar spread carry (if back month available)
    calendar_carry = None
    if iv_m2_atm is not None and days_to_m2 > days_to_m1:
        # Roll yield approximation
        calendar_carry = (iv_m2_atm - iv_m1_atm) / (days_to_m2 - days_to_m1)
    
    return {
        "daily_carry_m1": daily_carry_m1,
        "calendar_carry": calendar_carry,
    }
