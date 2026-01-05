"""
Signals module - Converts features into standardized signal scores.
All signals normalized to "long vol positive" convention.
"""

from .scorer import SignalScorer
from .normalizer import zscore, indicator

__all__ = [
    "SignalScorer",
    "zscore",
    "indicator",
]
