"""
Execution gate - Final validation before trade output.
Enforces hard constraints from strategy specification.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from ..core.constants import (
    EV_MIN_THRESHOLD,
    RR_MIN_THRESHOLD,
    RR_TARGET_AGGRESSIVE,
    LIQUIDITY_SPREAD_PERCENTILE_MAX,
    LIQUIDITY_IVASK_PERCENTILE_MAX,
    CONSERVATIVE_PROB_MIN,
)


@dataclass
class GateResult:
    """Result of execution gate check."""
    passes: bool
    failed_gates: List[str]
    warnings: List[str]
    adjustments: Dict[str, Any]


class ExecutionGate:
    """
    Final gate before trade execution.
    
    Hard gates (must pass):
    1. EV > 0
    2. RR >= 1.5:1 (minimum), target 2:1
    3. Liquidity: spread/ivask < 80th percentile
    4. Conservative mode: p >= 0.70
    
    Soft gates (warnings):
    1. Approaching thresholds
    2. Missing data points
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize gate."""
        self.config = config or {}
        
        self.ev_min = self.config.get("ev_min", EV_MIN_THRESHOLD)
        self.rr_min = self.config.get("rr_min", RR_MIN_THRESHOLD)
        self.rr_target = self.config.get("rr_target", RR_TARGET_AGGRESSIVE)
        self.spread_max_pctl = self.config.get("spread_max_pctl", LIQUIDITY_SPREAD_PERCENTILE_MAX)
        self.ivask_max_pctl = self.config.get("ivask_max_pctl", LIQUIDITY_IVASK_PERCENTILE_MAX)
        self.conservative_prob_min = self.config.get("conservative_prob_min", CONSERVATIVE_PROB_MIN)
    
    def check(
        self,
        ev_estimate: Dict[str, Any],
        probability: float,
        liquidity: Dict[str, Any],
        strategy_tier: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> GateResult:
        """
        Check all execution gates.
        
        Args:
            ev_estimate: EV estimation results
            probability: Calibrated win probability
            liquidity: Liquidity metrics
            strategy_tier: "aggressive" | "balanced" | "conservative"
            context: Additional context
            
        Returns:
            GateResult with pass/fail and details
        """
        failed_gates = []
        warnings = []
        adjustments = {}
        
        # Gate 1: EV must be positive
        net_ev = ev_estimate.get("net_ev", 0)
        if net_ev <= self.ev_min:
            failed_gates.append(f"EV_NEGATIVE: net_ev={net_ev:.4f} <= {self.ev_min}")
        elif net_ev < 0.01:
            warnings.append(f"EV_MARGINAL: net_ev={net_ev:.4f} is marginally positive")
        
        # Gate 2: RR ratio minimum
        rr_ratio = ev_estimate.get("rr_ratio", 0)
        if rr_ratio < self.rr_min:
            failed_gates.append(f"RR_INSUFFICIENT: rr={rr_ratio:.2f} < {self.rr_min}")
        elif rr_ratio < self.rr_target:
            warnings.append(f"RR_BELOW_TARGET: rr={rr_ratio:.2f} < target {self.rr_target}")
        
        # Gate 3: Liquidity check
        liquidity_flag = liquidity.get("liquidity_flag", "fair")
        spread_z = liquidity.get("spread_z", 0)
        ivask_z = liquidity.get("ivask_premium_z", 0)
        
        # Convert z-score to approximate percentile
        spread_pctl = self._z_to_percentile(spread_z)
        ivask_pctl = self._z_to_percentile(ivask_z)
        
        if spread_pctl > self.spread_max_pctl:
            failed_gates.append(f"SPREAD_HIGH: {spread_pctl:.0f}th percentile > {self.spread_max_pctl}")
        if ivask_pctl > self.ivask_max_pctl:
            failed_gates.append(f"IVASK_HIGH: {ivask_pctl:.0f}th percentile > {self.ivask_max_pctl}")
        
        if liquidity_flag == "poor":
            if strategy_tier == "aggressive":
                failed_gates.append("LIQUIDITY_POOR: unsuitable for aggressive strategy")
            else:
                warnings.append("LIQUIDITY_POOR: consider reducing size")
                adjustments["size_reduction"] = 0.5
        
        # Gate 4: Conservative mode probability
        if strategy_tier == "conservative":
            if probability < self.conservative_prob_min:
                failed_gates.append(
                    f"PROB_LOW_CONSERVATIVE: p={probability:.2%} < {self.conservative_prob_min:.0%}"
                )
        
        # Gate 5: Strategy-tier consistency
        tier_rr_check = self._check_tier_rr_consistency(strategy_tier, rr_ratio)
        if not tier_rr_check[0]:
            warnings.append(tier_rr_check[1])
        
        # Additional context checks
        if context:
            context_gates, context_warnings = self._check_context_gates(context, strategy_tier)
            failed_gates.extend(context_gates)
            warnings.extend(context_warnings)
        
        passes = len(failed_gates) == 0
        
        return GateResult(
            passes=passes,
            failed_gates=failed_gates,
            warnings=warnings,
            adjustments=adjustments,
        )
    
    def _z_to_percentile(self, z: float) -> float:
        """Convert z-score to approximate percentile."""
        # Rough approximation using normal CDF
        import math
        return 50 * (1 + math.erf(z / math.sqrt(2)))
    
    def _check_tier_rr_consistency(
        self,
        tier: str,
        rr: float,
    ) -> Tuple[bool, str]:
        """Check if RR is consistent with strategy tier."""
        if tier == "aggressive":
            if rr < 2.0:
                return False, f"TIER_RR_MISMATCH: aggressive tier expects RR>=2.0, got {rr:.2f}"
        elif tier == "balanced":
            if rr < 1.2 or rr > 1.8:
                return False, f"TIER_RR_MISMATCH: balanced tier expects RR 1.2-1.8, got {rr:.2f}"
        elif tier == "conservative":
            if rr < 0.8 or rr > 1.2:
                return False, f"TIER_RR_MISMATCH: conservative tier expects RR 0.8-1.2, got {rr:.2f}"
        
        return True, ""
    
    def _check_context_gates(
        self,
        context: Dict[str, Any],
        tier: str,
    ) -> Tuple[List[str], List[str]]:
        """Check additional context-based gates."""
        failed = []
        warnings = []
        
        # 0DTE exclusion
        dte = context.get("dte", 30)
        if dte == 0:
            failed.append("0DTE_EXCLUDED: 0DTE trades not allowed per spec")
        elif dte < 5:
            warnings.append(f"DTE_LOW: {dte} days may have gamma risk")
        
        # Session check (US RTH only)
        session = context.get("session", "rth")
        if session != "rth":
            warnings.append(f"SESSION_NON_RTH: execution outside RTH may have wider spreads")
        
        # Event proximity for short vol
        if context.get("is_event_week") and tier == "conservative":
            failed.append("EVENT_WEEK: short vol conservative strategies avoid event week")
        
        # Regime alignment
        regime = context.get("regime_state")
        direction = context.get("direction")
        if regime == "negative_gamma" and direction == "short_vol":
            failed.append("REGIME_MISMATCH: short vol in negative gamma regime")
        
        return failed, warnings
    
    def suggest_adjustments(
        self,
        gate_result: GateResult,
        strategy_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Suggest adjustments to pass gates.
        
        Returns suggested parameter changes.
        """
        suggestions = {}
        
        for gate in gate_result.failed_gates:
            if "EV_NEGATIVE" in gate:
                suggestions["reduce_position_size"] = True
                suggestions["consider_different_strikes"] = True
            
            if "RR_INSUFFICIENT" in gate:
                suggestions["widen_profit_target"] = True
                suggestions["tighten_stop_loss"] = True
                suggestions["consider_different_structure"] = True
            
            if "SPREAD_HIGH" in gate or "IVASK_HIGH" in gate:
                suggestions["use_limit_orders"] = True
                suggestions["consider_different_expiration"] = True
                suggestions["reduce_size"] = True
            
            if "LIQUIDITY_POOR" in gate:
                suggestions["switch_to_liquid_strikes"] = True
                suggestions["use_atm_only"] = True
            
            if "0DTE_EXCLUDED" in gate:
                suggestions["use_minimum_5dte"] = True
        
        return suggestions
    
    def format_output(
        self,
        gate_result: GateResult,
        strategy_name: str,
    ) -> str:
        """Format gate result for output."""
        lines = []
        
        if gate_result.passes:
            lines.append(f"✓ {strategy_name}: All gates passed")
        else:
            lines.append(f"✗ {strategy_name}: BLOCKED - {len(gate_result.failed_gates)} gate(s) failed")
            for gate in gate_result.failed_gates:
                lines.append(f"  ✗ {gate}")
        
        if gate_result.warnings:
            lines.append("  Warnings:")
            for warning in gate_result.warnings:
                lines.append(f"  ⚠ {warning}")
        
        if gate_result.adjustments:
            lines.append("  Adjustments applied:")
            for adj, val in gate_result.adjustments.items():
                lines.append(f"  → {adj}: {val}")
        
        return "\n".join(lines)
