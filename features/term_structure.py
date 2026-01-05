"""
Term structure metrics computation.
Analyzes IV across expiration dates.
"""

from typing import Dict, Any


def compute_term_metrics(
    term_slope: float,
    term_curvature: float,
) -> Dict[str, Any]:
    """
    Compute term structure metrics.
    
    Term slope: (IV_far - IV_near) / IV_near
    - Positive: Contango (normal), short vol favorable
    - Negative: Backwardation, long vol favorable
    
    Term curvature: Second derivative of term structure
    - Positive: Convex (U-shape)
    - Negative: Concave
    
    Args:
        term_slope: Pre-computed term structure slope
        term_curvature: Pre-computed term structure curvature
        
    Returns:
        Dictionary with term structure analysis
    """
    # Term structure regime classification
    if term_slope > 0.02:  # >2% contango
        term_regime = "contango"
        term_signal = "short_vol_favorable"
    elif term_slope < -0.02:  # >2% backwardation
        term_regime = "backwardation"
        term_signal = "long_vol_favorable"
    else:
        term_regime = "flat"
        term_signal = "neutral"
    
    # Curvature interpretation
    if term_curvature > 0.01:
        curvature_regime = "convex"
    elif term_curvature < -0.01:
        curvature_regime = "concave"
    else:
        curvature_regime = "linear"
    
    # Calendar spread opportunity detection
    # Strong contango + convex = calendar spread opportunity
    calendar_opportunity = (
        term_slope > 0.03 and 
        term_curvature > 0.005
    )
    
    # Event-driven spike detection (backwardation near term)
    event_spike = term_slope < -0.05  # Significant backwardation
    
    return {
        "term_slope": term_slope,
        "term_curvature": term_curvature,
        "term_regime": term_regime,
        "term_signal": term_signal,
        "curvature_regime": curvature_regime,
        "calendar_opportunity": calendar_opportunity,
        "event_spike": event_spike,
    }


def compute_term_slope_from_ivs(
    iv_near: float,
    iv_far: float,
    dte_near: int = 30,
    dte_far: int = 60,
) -> float:
    """
    Compute term slope from two IV points.
    
    Args:
        iv_near: Near-term IV
        iv_far: Far-term IV
        dte_near: Days to near expiration
        dte_far: Days to far expiration
        
    Returns:
        Term slope (annualized)
    """
    if iv_near <= 0 or dte_far <= dte_near:
        return 0.0
    
    # Simple slope
    raw_slope = (iv_far - iv_near) / iv_near
    
    # Annualize based on DTE difference
    dte_diff = dte_far - dte_near
    annualized_slope = raw_slope * (365 / dte_diff) if dte_diff > 0 else raw_slope
    
    return annualized_slope
