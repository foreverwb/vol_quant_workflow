"""
Features module - Feature calculation from raw input data.
Computes VRP, term structure metrics, skew, and derived features.
"""

from .calculator import FeatureCalculator
from .vrp import compute_vrp
from .term_structure import compute_term_metrics
from .skew import compute_skew_metrics
from .regime import compute_regime_state

__all__ = [
    "FeatureCalculator",
    "compute_vrp",
    "compute_term_metrics", 
    "compute_skew_metrics",
    "compute_regime_state",
]
