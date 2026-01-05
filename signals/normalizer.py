"""
Signal normalization utilities.
Converts raw features to standardized scores.
"""

from typing import Optional
import math


def zscore(
    value: float,
    mean: float = 0.0,
    std: float = 1.0,
    clip: Optional[float] = 3.0,
) -> float:
    """
    Compute z-score of a value.
    
    Args:
        value: Raw value to normalize
        mean: Historical mean (default 0)
        std: Historical standard deviation (default 1)
        clip: Maximum absolute z-score (None to disable)
        
    Returns:
        Z-score, optionally clipped
    """
    if std <= 0:
        return 0.0
    
    z = (value - mean) / std
    
    if clip is not None:
        z = max(-clip, min(clip, z))
    
    return z


def indicator(
    condition: bool,
    value_if_true: float = 1.0,
    value_if_false: float = 0.0,
) -> float:
    """
    Binary indicator function.
    
    Args:
        condition: Boolean condition to evaluate
        value_if_true: Value to return if condition is True
        value_if_false: Value to return if condition is False
        
    Returns:
        Indicator value
    """
    return value_if_true if condition else value_if_false


def percentile_rank(
    value: float,
    historical_values: list,
) -> float:
    """
    Compute percentile rank of value in historical distribution.
    
    Args:
        value: Value to rank
        historical_values: List of historical values
        
    Returns:
        Percentile rank (0-100)
    """
    if not historical_values:
        return 50.0  # Default to median if no history
    
    below = sum(1 for v in historical_values if v < value)
    equal = sum(1 for v in historical_values if v == value)
    
    rank = (below + 0.5 * equal) / len(historical_values) * 100
    return rank


def sigmoid_transform(
    value: float,
    center: float = 0.0,
    scale: float = 1.0,
) -> float:
    """
    Apply sigmoid transformation to bound value between 0 and 1.
    
    Args:
        value: Raw value
        center: Center point of sigmoid
        scale: Scale factor (larger = sharper transition)
        
    Returns:
        Transformed value in (0, 1)
    """
    x = (value - center) * scale
    return 1.0 / (1.0 + math.exp(-x))


def winsorize(
    value: float,
    lower: float,
    upper: float,
) -> float:
    """
    Winsorize value to specified bounds.
    
    Args:
        value: Raw value
        lower: Lower bound
        upper: Upper bound
        
    Returns:
        Winsorized value
    """
    return max(lower, min(upper, value))
