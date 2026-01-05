"""
Output schemas - Data structure definitions for pipeline outputs.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


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
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class CompositeScores:
    """Composite signal scores."""
    long_vol_score: float = 0.0
    short_vol_score: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class ProbabilityEstimate:
    """Probability estimate with confidence interval."""
    point_estimate: float
    lower_bound: float
    upper_bound: float
    calibration_method: str = "cold_start"
    confidence: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionResult:
    """Decision classification result."""
    decision: str  # LONG_VOL, SHORT_VOL, STAND_ASIDE
    confidence: float
    is_preferred: bool
    primary_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyCandidate:
    """Strategy candidate."""
    name: str
    tier: str  # aggressive, balanced, conservative
    direction: str  # long_vol, short_vol
    dte_range: Tuple[int, int] = (14, 45)
    delta_targets: Dict[str, float] = field(default_factory=dict)
    target_rr: Tuple[float, float] = (1.5, 2.0)
    strikes: Dict[str, float] = field(default_factory=dict)
    ev_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tier": self.tier,
            "direction": self.direction,
            "dte_range": list(self.dte_range),
            "delta_targets": self.delta_targets,
            "target_rr": list(self.target_rr),
            "strikes": self.strikes,
            "ev_metrics": self.ev_metrics,
        }


@dataclass
class TradeOutput:
    """Final trade output."""
    action: str  # TRADE, NO_TRADE
    strategy: Optional[Dict[str, Any]] = None
    strikes: Optional[Dict[str, float]] = None
    metrics: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    gate_details: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "action": self.action,
            "warnings": self.warnings,
        }
        if self.action == "TRADE":
            result["strategy"] = self.strategy
            result["strikes"] = self.strikes
            result["metrics"] = self.metrics
            result["gate_details"] = self.gate_details
        else:
            result["reason"] = self.reason
            result["gate_details"] = self.gate_details
        return result


@dataclass
class AnalysisOutput:
    """Complete analysis output."""
    meta: Dict[str, Any]
    decision: DecisionResult
    scores: CompositeScores
    signal_breakdown: SignalScores
    probabilities: Dict[str, ProbabilityEstimate]
    regime: Dict[str, Any]
    candidates: List[StrategyCandidate]
    trade: Optional[TradeOutput]
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": self.meta,
            "decision": self.decision.to_dict(),
            "scores": self.scores.to_dict(),
            "signal_breakdown": self.signal_breakdown.to_dict(),
            "probabilities": {
                k: v.to_dict() for k, v in self.probabilities.items()
            },
            "regime": self.regime,
            "candidates": [c.to_dict() for c in self.candidates],
            "trade": self.trade.to_dict() if self.trade else None,
            "warnings": self.warnings,
        }


@dataclass
class UpdateOutput:
    """Lightweight update output."""
    timestamp: str
    regime_state: str
    regime_changed: bool
    spot: float
    vol_trigger: float
    key_metrics: Dict[str, Any]
    alerts: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_output_template(symbol: str, date: str) -> Dict[str, Any]:
    """
    Get empty output template.
    
    Args:
        symbol: Trading symbol
        date: Date string
        
    Returns:
        Template dictionary
    """
    return {
        "symbol": symbol,
        "date": date,
        "last_update": "",
        "updates": [],
        "full_analysis": None,
        "gexbot_commands": [],
    }
