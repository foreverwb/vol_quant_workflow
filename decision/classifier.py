"""
Decision classifier - Three-class classification logic.
Implements decision gates from strategy specification.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..core.constants import (
    Decision,
    LONG_VOL_SCORE_MIN, LONG_VOL_PROB_MIN, LONG_VOL_OPPOSING_MAX,
    SHORT_VOL_SCORE_MIN, SHORT_VOL_PROB_MIN, SHORT_VOL_OPPOSING_MAX,
    LONG_VOL_SCORE_PREFERRED, LONG_VOL_PROB_PREFERRED,
    SHORT_VOL_SCORE_PREFERRED, SHORT_VOL_PROB_PREFERRED,
    CONSERVATIVE_PROB_MIN,
)
from .probability import ProbabilityEstimate


@dataclass
class DecisionResult:
    """Result of decision classification."""
    decision: Decision
    confidence: float
    is_preferred: bool  # Meets preferred (stronger) thresholds
    primary_reasons: List[str]
    gate_details: Dict[str, Any]


class DecisionClassifier:
    """
    Implements three-class decision logic.
    
    Decision rules from strategy spec:
    
    LONG_VOL:
      - L >= 1.00 AND S <= 0.30 AND p_long >= 0.55
      - Preferred: L >= 1.50 AND p_long >= 0.60
    
    SHORT_VOL:
      - S >= 1.00 AND L <= 0.30 AND p_short >= 0.55
      - Preferred: S >= 1.50 AND p_short >= 0.60
    
    STAND_ASIDE:
      - All other cases
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration overrides."""
        self.config = config or {}
        
        # Allow config overrides
        self.long_score_min = self.config.get("long_score_min", LONG_VOL_SCORE_MIN)
        self.long_prob_min = self.config.get("long_prob_min", LONG_VOL_PROB_MIN)
        self.long_opposing_max = self.config.get("long_opposing_max", LONG_VOL_OPPOSING_MAX)
        
        self.short_score_min = self.config.get("short_score_min", SHORT_VOL_SCORE_MIN)
        self.short_prob_min = self.config.get("short_prob_min", SHORT_VOL_PROB_MIN)
        self.short_opposing_max = self.config.get("short_opposing_max", SHORT_VOL_OPPOSING_MAX)
    
    def classify(
        self,
        long_vol_score: float,
        short_vol_score: float,
        p_long: ProbabilityEstimate,
        p_short: ProbabilityEstimate,
        context: Optional[Dict[str, Any]] = None,
    ) -> DecisionResult:
        """
        Classify into LONG_VOL, SHORT_VOL, or STAND_ASIDE.
        
        Args:
            long_vol_score: L score
            short_vol_score: S score
            p_long: Calibrated P(RV > IV | L)
            p_short: Calibrated P(RV < IV | S)
            context: Optional context for additional gates
            
        Returns:
            DecisionResult with decision and details
        """
        # Check long vol gates
        long_gates = self._check_long_vol_gates(
            long_vol_score, short_vol_score, p_long
        )
        
        # Check short vol gates
        short_gates = self._check_short_vol_gates(
            long_vol_score, short_vol_score, p_short
        )
        
        # Apply additional context gates if available
        if context:
            long_gates = self._apply_context_gates(long_gates, context, "long")
            short_gates = self._apply_context_gates(short_gates, context, "short")
        
        # Decision logic
        if long_gates["passes_all"] and not short_gates["passes_all"]:
            decision = Decision.LONG_VOL
            is_preferred = long_gates["is_preferred"]
            confidence = self._compute_confidence(long_gates, p_long)
            reasons = self._build_long_reasons(long_vol_score, p_long, long_gates)
            gate_details = long_gates
            
        elif short_gates["passes_all"] and not long_gates["passes_all"]:
            decision = Decision.SHORT_VOL
            is_preferred = short_gates["is_preferred"]
            confidence = self._compute_confidence(short_gates, p_short)
            reasons = self._build_short_reasons(short_vol_score, p_short, short_gates)
            gate_details = short_gates
            
        elif long_gates["passes_all"] and short_gates["passes_all"]:
            # Both pass - choose stronger signal
            if long_vol_score > short_vol_score:
                decision = Decision.LONG_VOL
                is_preferred = long_gates["is_preferred"]
                confidence = self._compute_confidence(long_gates, p_long) * 0.8  # Reduce confidence
                reasons = ["Both signals active, L score stronger"]
                gate_details = long_gates
            else:
                decision = Decision.SHORT_VOL
                is_preferred = short_gates["is_preferred"]
                confidence = self._compute_confidence(short_gates, p_short) * 0.8
                reasons = ["Both signals active, S score stronger"]
                gate_details = short_gates
        else:
            decision = Decision.STAND_ASIDE
            is_preferred = False
            confidence = 0.5
            reasons = self._build_stand_aside_reasons(long_gates, short_gates)
            gate_details = {"long": long_gates, "short": short_gates}
        
        return DecisionResult(
            decision=decision,
            confidence=confidence,
            is_preferred=is_preferred,
            primary_reasons=reasons,
            gate_details=gate_details,
        )
    
    def _check_long_vol_gates(
        self,
        long_score: float,
        short_score: float,
        p_long: ProbabilityEstimate,
    ) -> Dict[str, Any]:
        """Check all gates for long vol decision."""
        score_gate = long_score >= self.long_score_min
        opposing_gate = short_score <= self.long_opposing_max
        prob_gate = p_long.point_estimate >= self.long_prob_min
        
        passes_all = score_gate and opposing_gate and prob_gate
        
        # Check preferred (stronger) thresholds
        score_preferred = long_score >= LONG_VOL_SCORE_PREFERRED
        prob_preferred = p_long.point_estimate >= LONG_VOL_PROB_PREFERRED
        is_preferred = passes_all and score_preferred and prob_preferred
        
        return {
            "score_gate": score_gate,
            "opposing_gate": opposing_gate,
            "prob_gate": prob_gate,
            "passes_all": passes_all,
            "is_preferred": is_preferred,
            "score": long_score,
            "opposing_score": short_score,
            "probability": p_long.point_estimate,
            "thresholds": {
                "score_min": self.long_score_min,
                "opposing_max": self.long_opposing_max,
                "prob_min": self.long_prob_min,
            },
        }
    
    def _check_short_vol_gates(
        self,
        long_score: float,
        short_score: float,
        p_short: ProbabilityEstimate,
    ) -> Dict[str, Any]:
        """Check all gates for short vol decision."""
        score_gate = short_score >= self.short_score_min
        opposing_gate = long_score <= self.short_opposing_max
        prob_gate = p_short.point_estimate >= self.short_prob_min
        
        passes_all = score_gate and opposing_gate and prob_gate
        
        # Check preferred thresholds
        score_preferred = short_score >= SHORT_VOL_SCORE_PREFERRED
        prob_preferred = p_short.point_estimate >= SHORT_VOL_PROB_PREFERRED
        is_preferred = passes_all and score_preferred and prob_preferred
        
        return {
            "score_gate": score_gate,
            "opposing_gate": opposing_gate,
            "prob_gate": prob_gate,
            "passes_all": passes_all,
            "is_preferred": is_preferred,
            "score": short_score,
            "opposing_score": long_score,
            "probability": p_short.point_estimate,
            "thresholds": {
                "score_min": self.short_score_min,
                "opposing_max": self.short_opposing_max,
                "prob_min": self.short_prob_min,
            },
        }
    
    def _apply_context_gates(
        self,
        gates: Dict[str, Any],
        context: Dict[str, Any],
        direction: str,
    ) -> Dict[str, Any]:
        """Apply additional context-based gates."""
        # Liquidity gate
        if context.get("liquidity_flag") == "poor":
            gates["liquidity_gate"] = False
            gates["passes_all"] = False
        else:
            gates["liquidity_gate"] = True
        
        # Conservative mode: require higher probability
        if context.get("conservative_mode"):
            if gates["probability"] < CONSERVATIVE_PROB_MIN:
                gates["conservative_gate"] = False
                gates["passes_all"] = False
            else:
                gates["conservative_gate"] = True
        
        return gates
    
    def _compute_confidence(
        self,
        gates: Dict[str, Any],
        prob: ProbabilityEstimate,
    ) -> float:
        """Compute decision confidence."""
        # Base confidence from probability
        base = prob.confidence * prob.point_estimate
        
        # Boost for preferred status
        if gates["is_preferred"]:
            base *= 1.1
        
        # Penalty for close to thresholds
        margin = gates["score"] - gates["thresholds"]["score_min"]
        if margin < 0.5:
            base *= 0.9
        
        return min(1.0, base)
    
    def _build_long_reasons(
        self,
        score: float,
        prob: ProbabilityEstimate,
        gates: Dict[str, Any],
    ) -> List[str]:
        """Build explanation for long vol decision."""
        reasons = [
            f"L score {score:.2f} >= {gates['thresholds']['score_min']}",
            f"S score {gates['opposing_score']:.2f} <= {gates['thresholds']['opposing_max']}",
            f"P(RV > IV) = {prob.point_estimate:.1%}",
        ]
        
        if gates["is_preferred"]:
            reasons.append("Meets preferred thresholds")
        
        return reasons
    
    def _build_short_reasons(
        self,
        score: float,
        prob: ProbabilityEstimate,
        gates: Dict[str, Any],
    ) -> List[str]:
        """Build explanation for short vol decision."""
        reasons = [
            f"S score {score:.2f} >= {gates['thresholds']['score_min']}",
            f"L score {gates['opposing_score']:.2f} <= {gates['thresholds']['opposing_max']}",
            f"P(RV < IV) = {prob.point_estimate:.1%}",
        ]
        
        if gates["is_preferred"]:
            reasons.append("Meets preferred thresholds")
        
        return reasons
    
    def _build_stand_aside_reasons(
        self,
        long_gates: Dict[str, Any],
        short_gates: Dict[str, Any],
    ) -> List[str]:
        """Build explanation for stand aside decision."""
        reasons = []
        
        # Long gates failures
        if not long_gates["score_gate"]:
            reasons.append(f"L score {long_gates['score']:.2f} < {long_gates['thresholds']['score_min']}")
        if not long_gates["opposing_gate"]:
            reasons.append(f"S score too high: {long_gates['opposing_score']:.2f}")
        if not long_gates["prob_gate"]:
            reasons.append(f"P(long) {long_gates['probability']:.1%} below threshold")
        
        # Short gates failures
        if not short_gates["score_gate"]:
            reasons.append(f"S score {short_gates['score']:.2f} < {short_gates['thresholds']['score_min']}")
        if not short_gates["opposing_gate"]:
            reasons.append(f"L score too high: {short_gates['opposing_score']:.2f}")
        if not short_gates["prob_gate"]:
            reasons.append(f"P(short) {short_gates['probability']:.1%} below threshold")
        
        if not reasons:
            reasons.append("No clear directional signal")
        
        return reasons
