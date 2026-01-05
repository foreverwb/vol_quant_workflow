"""
Skew metrics computation.
Analyzes put-call IV asymmetry.
"""

from typing import Dict, Any, Optional


def compute_skew_metrics(
    skew_asymmetry: float,
    iv_put_25d: Optional[float] = None,
    iv_call_25d: Optional[float] = None,
    iv_atm: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute skew metrics.
    
    Skew asymmetry: Measures relative richness of puts vs calls
    - Positive: Puts richer than calls (bearish demand)
    - Negative: Calls richer than puts (bullish demand)
    
    Args:
        skew_asymmetry: Pre-computed skew asymmetry
        iv_put_25d: 25-delta put IV (optional)
        iv_call_25d: 25-delta call IV (optional)
        iv_atm: ATM IV (optional)
        
    Returns:
        Dictionary with skew analysis
    """
    # Skew regime classification
    if skew_asymmetry > 0.03:  # >3% put premium
        skew_regime = "steep_put"
        skew_signal = "bearish_demand"
    elif skew_asymmetry < -0.02:  # Call premium
        skew_regime = "call_rich"
        skew_signal = "bullish_demand"
    else:
        skew_regime = "balanced"
        skew_signal = "neutral"
    
    # Compute additional skew metrics if components available
    put_skew_25 = None
    call_skew_25 = None
    
    if iv_put_25d is not None and iv_atm is not None and iv_atm > 0:
        put_skew_25 = (iv_put_25d - iv_atm) / iv_atm
    
    if iv_call_25d is not None and iv_atm is not None and iv_atm > 0:
        call_skew_25 = (iv_call_25d - iv_atm) / iv_atm
    
    # Skew steepness (absolute deviation from ATM)
    skew_steepness = abs(skew_asymmetry)
    
    # Trading signals based on skew
    # Steep put skew + long vol = favor put-heavy structures
    # Flat skew + short vol = straddle/strangle favorable
    if skew_steepness < 0.02:
        structure_preference = "symmetric"  # Straddle/strangle
    elif skew_asymmetry > 0:
        structure_preference = "put_wing"   # Put-heavy structures
    else:
        structure_preference = "call_wing"  # Call-heavy structures
    
    return {
        "skew_asymmetry": skew_asymmetry,
        "skew_regime": skew_regime,
        "skew_signal": skew_signal,
        "put_skew_25": put_skew_25,
        "call_skew_25": call_skew_25,
        "skew_steepness": skew_steepness,
        "structure_preference": structure_preference,
    }


def compute_risk_reversal(
    iv_put_25d: float,
    iv_call_25d: float,
) -> float:
    """
    Compute risk reversal (25d put - 25d call IV).
    
    Positive: Put premium (typical in equities)
    Negative: Call premium (unusual, often before events)
    
    Args:
        iv_put_25d: 25-delta put IV
        iv_call_25d: 25-delta call IV
        
    Returns:
        Risk reversal value
    """
    return iv_put_25d - iv_call_25d


def compute_butterfly(
    iv_put_25d: float,
    iv_call_25d: float,
    iv_atm: float,
) -> float:
    """
    Compute butterfly spread (wings vs body).
    
    Measures convexity of the smile.
    High butterfly = fat tails, wing premium
    
    Args:
        iv_put_25d: 25-delta put IV
        iv_call_25d: 25-delta call IV
        iv_atm: ATM IV
        
    Returns:
        Butterfly spread value
    """
    return 0.5 * (iv_put_25d + iv_call_25d) - iv_atm
