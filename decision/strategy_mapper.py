"""
Strategy mapper - Maps decisions to executable strategy structures.
LLM may be used for template selection based on context.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..core.constants import (
    Decision, StrategyTier,
    DTE_LONG_VOL_EVENT_MIN, DTE_LONG_VOL_EVENT_MAX,
    DTE_LONG_VOL_NON_EVENT_MIN, DTE_LONG_VOL_NON_EVENT_MAX,
    DTE_SHORT_VOL_MIN, DTE_SHORT_VOL_MAX,
    DELTA_STRADDLE_ATM, DELTA_STRANGLE_WING,
    DELTA_SHORT_SELL, DELTA_SHORT_PROTECT,
    DELTA_DEBIT_BUY, DELTA_DEBIT_SELL,
    RR_TARGET_AGGRESSIVE, RR_TARGET_BALANCED_MIN, RR_TARGET_BALANCED_MAX,
    RR_TARGET_CONSERVATIVE_MIN, RR_TARGET_CONSERVATIVE_MAX,
    RIM_HIGH_THRESHOLD, RIM_LOW_THRESHOLD,
)


@dataclass
class StrategyCandidate:
    """A candidate strategy with parameters."""
    name: str
    tier: StrategyTier
    direction: str  # "long_vol" | "short_vol"
    dte_range: tuple
    delta_targets: Dict[str, Any]
    strike_anchors: Dict[str, str]
    target_rr: tuple  # (min, max) reward:risk
    entry_triggers: List[str]
    exit_triggers: List[str]
    applicable_conditions: List[str]
    contraindications: List[str]


class StrategyMapper:
    """
    Maps decisions to executable strategy templates.
    
    Three tiers from strategy spec:
    1. Aggressive: Target RR >= 2:1
    2. Balanced: Target RR 1.2-1.8:1
    3. Conservative: Target RR 0.8-1.2:1
    
    LLM may be used for:
    - Template selection based on nuanced context
    - Parameter optimization suggestions
    """
    
    # Strategy templates from spec
    TEMPLATES = {
        # === AGGRESSIVE (Long Vol) ===
        "long_straddle": StrategyCandidate(
            name="long_straddle",
            tier=StrategyTier.AGGRESSIVE,
            direction="long_vol",
            dte_range=(DTE_LONG_VOL_EVENT_MIN, DTE_LONG_VOL_EVENT_MAX),
            delta_targets={"buy_call": DELTA_STRADDLE_ATM, "buy_put": DELTA_STRADDLE_ATM},
            strike_anchors={"buy_call": "atm", "buy_put": "atm"},
            target_rr=(RR_TARGET_AGGRESSIVE, 4.0),
            entry_triggers=[
                "RIM >= 0.6",
                "Spot < VOL_TRIGGER OR just broke below",
                "Distance to positive gamma wall > 0.5-1%",
            ],
            exit_triggers=[
                "RV/IV ratio normalizes",
                "RR target achieved",
                "Spot returns above VOL_TRIGGER",
                "Touches reverse gamma wall",
                "Theta decay accelerates unfavorably",
            ],
            applicable_conditions=[
                "Event week (5-20 DTE)",
                "Negative gamma regime",
                "High VEX negativity",
            ],
            contraindications=[
                "Positive gamma regime with pin risk",
                "Poor liquidity",
            ],
        ),
        
        "long_strangle": StrategyCandidate(
            name="long_strangle",
            tier=StrategyTier.AGGRESSIVE,
            direction="long_vol",
            dte_range=(DTE_LONG_VOL_NON_EVENT_MIN, DTE_LONG_VOL_NON_EVENT_MAX),
            delta_targets={"buy_call": DELTA_STRANGLE_WING, "buy_put": DELTA_STRANGLE_WING},
            strike_anchors={"buy_call": "30-35d_call", "buy_put": "30-35d_put"},
            target_rr=(RR_TARGET_AGGRESSIVE, 5.0),
            entry_triggers=[
                "RIM >= 0.6",
                "Spot < VOL_TRIGGER",
                "Steep put skew (structure_preference = put_wing)",
            ],
            exit_triggers=[
                "RV/IV normalizes",
                "RR achieved",
                "Regime flip to positive gamma",
            ],
            applicable_conditions=[
                "Non-event period (30-45 DTE)",
                "Negative gamma regime",
                "Elevated skew asymmetry",
            ],
            contraindications=[
                "Flat term structure",
                "Low VVIX",
            ],
        ),
        
        "bull_call_spread": StrategyCandidate(
            name="bull_call_spread",
            tier=StrategyTier.AGGRESSIVE,
            direction="long_vol",
            dte_range=(14, 35),
            delta_targets={"buy": DELTA_DEBIT_BUY, "sell": (0.15, 0.25)},
            strike_anchors={
                "buy": "25-35d or 0.5-0.8x implied_move_upper",
                "sell": "resistance or next gamma_wall, 1.0-1.8x ATR away",
            },
            target_rr=(RR_TARGET_AGGRESSIVE, 3.0),
            entry_triggers=[
                "Directional bias up",
                "Spot breaking above key level",
            ],
            exit_triggers=[
                "Lock 50-70% of spread width",
                "Failure: fall below wall + RIM < 0.4",
            ],
            applicable_conditions=[
                "Bullish directional view",
                "Moderate IV environment",
            ],
            contraindications=[
                "Strong put skew",
                "Negative momentum",
            ],
        ),
        
        # === BALANCED ===
        "calendar_spread": StrategyCandidate(
            name="calendar_spread",
            tier=StrategyTier.BALANCED,
            direction="long_vol",  # Benefits from vol rise in back month
            dte_range=(7, 60),
            delta_targets={"sell_near": 0.50, "buy_far": 0.50},
            strike_anchors={"sell_near": "atm", "buy_far": "atm_or_slight_otm"},
            target_rr=(RR_TARGET_BALANCED_MIN, RR_TARGET_BALANCED_MAX),
            entry_triggers=[
                "term_slope <= 0 (backwardation)",
                "Event week elevated, expect post-event crush",
            ],
            exit_triggers=[
                "Term structure normalizes",
                "Near month expires",
            ],
            applicable_conditions=[
                "Event-driven term structure dislocation",
                "Backwardation in near term",
            ],
            contraindications=[
                "Strong contango",
                "Directional breakout expected",
            ],
        ),
        
        "debit_vertical_call": StrategyCandidate(
            name="debit_vertical_call",
            tier=StrategyTier.BALANCED,
            direction="long_vol",
            dte_range=(21, 45),
            delta_targets={"buy": DELTA_DEBIT_BUY, "sell": DELTA_DEBIT_SELL},
            strike_anchors={"buy": "35d", "sell": "15-20d or resistance"},
            target_rr=(RR_TARGET_BALANCED_MIN, RR_TARGET_BALANCED_MAX),
            entry_triggers=[
                "Bullish bias",
                "Cost control desired",
            ],
            exit_triggers=[
                "Target achieved",
                "Direction invalidated",
            ],
            applicable_conditions=[
                "Moderate bullish view",
                "Want defined risk",
            ],
            contraindications=[
                "Expecting large move beyond sold strike",
            ],
        ),
        
        # === CONSERVATIVE (Short Vol) ===
        "iron_condor": StrategyCandidate(
            name="iron_condor",
            tier=StrategyTier.CONSERVATIVE,
            direction="short_vol",
            dte_range=(DTE_SHORT_VOL_MIN, DTE_SHORT_VOL_MAX),
            delta_targets={
                "sell_call": DELTA_SHORT_SELL,
                "sell_put": DELTA_SHORT_SELL,
                "buy_call": DELTA_SHORT_PROTECT,
                "buy_put": DELTA_SHORT_PROTECT,
            },
            strike_anchors={
                "sell_call": "10-20d_call",
                "sell_put": "10-20d_put",
                "buy_call": "3-5d_call",
                "buy_put": "3-5d_put",
            },
            target_rr=(RR_TARGET_CONSERVATIVE_MIN, RR_TARGET_CONSERVATIVE_MAX),
            entry_triggers=[
                "Spot >= VOL_TRIGGER",
                "GammaWallProx <= 0.5-1.0%",
                "RIM <= 0.4",
                "VVIX falling",
            ],
            exit_triggers=[
                "Collect 50-70% of credit",
                "Break below VOL_TRIGGER → reduce or hedge",
                "Break gamma wall → exit",
            ],
            applicable_conditions=[
                "Positive gamma regime",
                "Pin risk environment",
                "Post-event (T to T+1)",
                "Low realized volatility",
            ],
            contraindications=[
                "Negative gamma regime",
                "High RIM",
                "Event approaching",
                "Poor liquidity",
            ],
        ),
        
        "short_strangle": StrategyCandidate(
            name="short_strangle",
            tier=StrategyTier.CONSERVATIVE,
            direction="short_vol",
            dte_range=(DTE_SHORT_VOL_MIN, DTE_SHORT_VOL_MAX),
            delta_targets={
                "sell_call": DELTA_SHORT_SELL,
                "sell_put": DELTA_SHORT_SELL,
            },
            strike_anchors={
                "sell_call": "10-20d_call",
                "sell_put": "10-20d_put",
            },
            target_rr=(RR_TARGET_CONSERVATIVE_MIN, RR_TARGET_CONSERVATIVE_MAX),
            entry_triggers=[
                "Spot >= VOL_TRIGGER",
                "Very low RIM",
                "Strong pin expectation",
            ],
            exit_triggers=[
                "Collect 50-70% of credit",
                "Any directional breakout",
            ],
            applicable_conditions=[
                "Strong positive gamma",
                "Very low vol expectation",
                "High premium collection opportunity",
            ],
            contraindications=[
                "Any event risk",
                "Negative gamma",
                "High vanna exposure",
            ],
        ),
        
        "credit_spread": StrategyCandidate(
            name="credit_spread",
            tier=StrategyTier.CONSERVATIVE,
            direction="short_vol",
            dte_range=(14, 45),
            delta_targets={
                "sell": DELTA_SHORT_SELL,
                "buy": DELTA_SHORT_PROTECT,
            },
            strike_anchors={
                "sell": "near positive gamma wall ±0.5-1%",
                "buy": "1.0-1.5x ATR from sold",
            },
            target_rr=(RR_TARGET_CONSERVATIVE_MIN, RR_TARGET_CONSERVATIVE_MAX),
            entry_triggers=[
                "Anchor to gamma wall",
                "High premium near resistance/support",
            ],
            exit_triggers=[
                "Collect target credit",
                "Wall breached",
            ],
            applicable_conditions=[
                "Clear gamma wall anchor",
                "Range-bound expectation",
            ],
            contraindications=[
                "Breakout expected",
                "Weak wall (low OI)",
            ],
        ),
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize mapper."""
        self.config = config or {}
    
    def get_candidates(
        self,
        decision: Decision,
        context: Dict[str, Any],
    ) -> List[StrategyCandidate]:
        """
        Get applicable strategy candidates for a decision.
        
        Args:
            decision: LONG_VOL or SHORT_VOL
            context: Market context for filtering
            
        Returns:
            List of applicable StrategyCandidate objects
        """
        if decision == Decision.STAND_ASIDE:
            return []
        
        direction = "long_vol" if decision == Decision.LONG_VOL else "short_vol"
        candidates = []
        
        for name, template in self.TEMPLATES.items():
            if template.direction != direction:
                continue
            
            # Check applicability
            is_applicable, reasons = self._check_applicability(template, context)
            if is_applicable:
                candidates.append(template)
        
        # Sort by tier (aggressive first for long vol, conservative first for short vol)
        if direction == "long_vol":
            tier_order = {StrategyTier.AGGRESSIVE: 0, StrategyTier.BALANCED: 1, StrategyTier.CONSERVATIVE: 2}
        else:
            tier_order = {StrategyTier.CONSERVATIVE: 0, StrategyTier.BALANCED: 1, StrategyTier.AGGRESSIVE: 2}
        
        candidates.sort(key=lambda x: tier_order.get(x.tier, 99))
        
        return candidates
    
    def _check_applicability(
        self,
        template: StrategyCandidate,
        context: Dict[str, Any],
    ) -> tuple:
        """
        Check if a strategy template is applicable given context.
        
        Returns:
            (is_applicable, list_of_reasons)
        """
        reasons = []
        is_applicable = True
        
        # Check regime alignment
        regime_state = context.get("regime_state", "neutral")
        
        if template.direction == "long_vol":
            if regime_state == "positive_gamma" and template.tier == StrategyTier.AGGRESSIVE:
                # Aggressive long vol not ideal in positive gamma
                is_applicable = False
                reasons.append("Positive gamma regime unfavorable for aggressive long vol")
        else:  # short vol
            if regime_state == "negative_gamma":
                is_applicable = False
                reasons.append("Negative gamma regime unfavorable for short vol")
        
        # Check RIM alignment
        rim = context.get("rim")
        if rim is not None:
            if template.direction == "long_vol" and rim < RIM_LOW_THRESHOLD:
                if template.tier == StrategyTier.AGGRESSIVE:
                    is_applicable = False
                    reasons.append(f"RIM {rim:.2f} too low for aggressive long vol")
            elif template.direction == "short_vol" and rim > RIM_HIGH_THRESHOLD:
                is_applicable = False
                reasons.append(f"RIM {rim:.2f} too high for short vol")
        
        # Check liquidity
        if context.get("liquidity_flag") == "poor":
            if template.tier == StrategyTier.AGGRESSIVE:
                is_applicable = False
                reasons.append("Poor liquidity unsuitable for aggressive strategies")
        
        # Check event proximity
        is_event_week = context.get("is_event_week", False)
        if is_event_week:
            if template.name in ["iron_condor", "short_strangle"]:
                is_applicable = False
                reasons.append("Event week unsuitable for short vol premium strategies")
        
        return is_applicable, reasons
    
    def select_best(
        self,
        candidates: List[StrategyCandidate],
        context: Dict[str, Any],
        preference: Optional[StrategyTier] = None,
    ) -> Optional[StrategyCandidate]:
        """
        Select the best strategy from candidates.
        
        Args:
            candidates: List of applicable candidates
            context: Market context
            preference: Optional tier preference
            
        Returns:
            Best StrategyCandidate or None
        """
        if not candidates:
            return None
        
        # Filter by preference if specified
        if preference:
            preferred = [c for c in candidates if c.tier == preference]
            if preferred:
                candidates = preferred
        
        # Score candidates based on context fit
        scored = []
        for candidate in candidates:
            score = self._score_candidate(candidate, context)
            scored.append((score, candidate))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]
    
    def _score_candidate(
        self,
        candidate: StrategyCandidate,
        context: Dict[str, Any],
    ) -> float:
        """Score a candidate strategy based on context fit."""
        score = 0.0
        
        # Base score by tier alignment with probability
        prob = context.get("probability", 0.5)
        if prob >= 0.70:
            # High prob favors conservative
            if candidate.tier == StrategyTier.CONSERVATIVE:
                score += 2.0
            elif candidate.tier == StrategyTier.BALANCED:
                score += 1.5
        elif prob >= 0.60:
            # Medium prob favors balanced
            if candidate.tier == StrategyTier.BALANCED:
                score += 2.0
            else:
                score += 1.0
        else:
            # Lower prob favors aggressive (higher payoff)
            if candidate.tier == StrategyTier.AGGRESSIVE:
                score += 2.0
        
        # Regime alignment bonus
        regime_state = context.get("regime_state")
        if candidate.direction == "long_vol" and regime_state == "negative_gamma":
            score += 1.0
        elif candidate.direction == "short_vol" and regime_state == "positive_gamma":
            score += 1.0
        
        # Term structure alignment
        term_regime = context.get("term_regime")
        if candidate.name == "calendar_spread" and term_regime == "backwardation":
            score += 1.5
        
        # Skew alignment
        skew_regime = context.get("skew_regime")
        if "put" in candidate.name and skew_regime == "steep_put":
            score += 0.5
        
        return score
    
    def customize_parameters(
        self,
        candidate: StrategyCandidate,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Customize strategy parameters based on context.
        
        Returns dictionary with customized parameters.
        """
        params = {
            "name": candidate.name,
            "tier": candidate.tier.value,
            "direction": candidate.direction,
            "dte_range": candidate.dte_range,
            "delta_targets": dict(candidate.delta_targets),
            "strike_anchors": dict(candidate.strike_anchors),
            "target_rr": candidate.target_rr,
            "entry_triggers": list(candidate.entry_triggers),
            "exit_triggers": list(candidate.exit_triggers),
        }
        
        # Adjust DTE based on event timing
        if context.get("is_event_week"):
            # Use shorter DTE range
            min_dte, max_dte = params["dte_range"]
            params["dte_range"] = (max(5, min_dte), min(20, max_dte))
        
        # Adjust strikes based on gamma walls
        gamma_wall_call = context.get("gamma_wall_call")
        gamma_wall_put = context.get("gamma_wall_put")
        vol_trigger = context.get("vol_trigger")
        spot = context.get("spot")
        
        if gamma_wall_call and spot:
            params["reference_levels"] = {
                "gamma_wall_call": gamma_wall_call,
                "gamma_wall_put": gamma_wall_put,
                "vol_trigger": vol_trigger,
                "spot": spot,
            }
        
        return params
