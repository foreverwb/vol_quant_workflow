"""
Type definitions for the volatility strategy system.
Defines the 22 core input fields and output structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# =============================================================================
# INPUT DATA STRUCTURES (22 CORE FIELDS)
# =============================================================================

@dataclass
class MetaFields:
    """Meta information fields."""
    symbol: str
    datetime: str  # ISO format ET timestamp


@dataclass
class MarketFields:
    """Market price fields."""
    spot: float


@dataclass
class RegimeFields:
    """Regime detection fields (VOL TRIGGER based)."""
    vol_trigger: float
    net_gex_sign: int  # +1, -1, or 0
    gamma_wall_call: float
    gamma_wall_put: float
    gamma_wall_proximity_pct: float


@dataclass
class VolatilityFields:
    """Volatility measurement fields."""
    iv_event_atm: Optional[float]  # Event week ATM IV
    iv_m1_atm: float               # Front month ATM IV
    iv_m2_atm: Optional[float]     # Back month ATM IV
    hv10: float                    # 10-day Yang-Zhang HV
    hv20: float                    # 20-day Yang-Zhang HV  
    hv60: float                    # 60-day Yang-Zhang HV


@dataclass
class StructureFields:
    """Term structure and skew fields."""
    term_slope: float          # IV term structure slope
    term_curvature: float      # IV term structure curvature
    skew_asymmetry: float      # Put-call skew asymmetry
    vex_net_5_60: float        # Net vanna exposure 5-60 DTE
    vanna_atm_abs: float       # Absolute ATM vanna


@dataclass
class LiquidityFields:
    """Liquidity and execution quality fields."""
    spread_atm: float          # ATM bid-ask spread
    iv_ask_premium_pct: float  # IV ask premium percentage
    liquidity_flag: str        # "good" / "fair" / "poor"


@dataclass
class InputData:
    """
    Complete input data structure containing all 22 core fields.
    This is the only valid input contract for Step3.
    """
    meta: MetaFields
    market: MarketFields
    regime: RegimeFields
    volatility: VolatilityFields
    structure: StructureFields
    liquidity: LiquidityFields
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "meta": {
                "symbol": self.meta.symbol,
                "datetime": self.meta.datetime,
            },
            "market": {
                "spot": self.market.spot,
            },
            "regime": {
                "vol_trigger": self.regime.vol_trigger,
                "net_gex_sign": self.regime.net_gex_sign,
                "gamma_wall_call": self.regime.gamma_wall_call,
                "gamma_wall_put": self.regime.gamma_wall_put,
                "gamma_wall_proximity_pct": self.regime.gamma_wall_proximity_pct,
            },
            "volatility": {
                "iv_event_atm": self.volatility.iv_event_atm,
                "iv_m1_atm": self.volatility.iv_m1_atm,
                "iv_m2_atm": self.volatility.iv_m2_atm,
                "hv10": self.volatility.hv10,
                "hv20": self.volatility.hv20,
                "hv60": self.volatility.hv60,
            },
            "structure": {
                "term_slope": self.structure.term_slope,
                "term_curvature": self.structure.term_curvature,
                "skew_asymmetry": self.structure.skew_asymmetry,
                "vex_net_5_60": self.structure.vex_net_5_60,
                "vanna_atm_abs": self.structure.vanna_atm_abs,
            },
            "liquidity": {
                "spread_atm": self.liquidity.spread_atm,
                "iv_ask_premium_pct": self.liquidity.iv_ask_premium_pct,
                "liquidity_flag": self.liquidity.liquidity_flag,
            },
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputData":
        """Create InputData from dictionary."""
        return cls(
            meta=MetaFields(
                symbol=data["meta"]["symbol"],
                datetime=data["meta"]["datetime"],
            ),
            market=MarketFields(
                spot=data["market"]["spot"],
            ),
            regime=RegimeFields(
                vol_trigger=data["regime"]["vol_trigger"],
                net_gex_sign=data["regime"]["net_gex_sign"],
                gamma_wall_call=data["regime"]["gamma_wall_call"],
                gamma_wall_put=data["regime"]["gamma_wall_put"],
                gamma_wall_proximity_pct=data["regime"]["gamma_wall_proximity_pct"],
            ),
            volatility=VolatilityFields(
                iv_event_atm=data["volatility"].get("iv_event_atm"),
                iv_m1_atm=data["volatility"]["iv_m1_atm"],
                iv_m2_atm=data["volatility"].get("iv_m2_atm"),
                hv10=data["volatility"]["hv10"],
                hv20=data["volatility"]["hv20"],
                hv60=data["volatility"]["hv60"],
            ),
            structure=StructureFields(
                term_slope=data["structure"]["term_slope"],
                term_curvature=data["structure"]["term_curvature"],
                skew_asymmetry=data["structure"]["skew_asymmetry"],
                vex_net_5_60=data["structure"]["vex_net_5_60"],
                vanna_atm_abs=data["structure"]["vanna_atm_abs"],
            ),
            liquidity=LiquidityFields(
                spread_atm=data["liquidity"]["spread_atm"],
                iv_ask_premium_pct=data["liquidity"]["iv_ask_premium_pct"],
                liquidity_flag=data["liquidity"]["liquidity_flag"],
            ),
        )


# =============================================================================
# OUTPUT DATA STRUCTURES
# =============================================================================

@dataclass
class SignalScores:
    """Individual signal scores (all normalized to 'long vol positive')."""
    s_vrp: float = 0.0
    s_gex: float = 0.0
    s_vex: float = 0.0
    s_carry: float = 0.0
    s_skew: float = 0.0
    s_vanna: float = 0.0
    s_rv: float = 0.0
    s_liq: float = 0.0
    # Enhanced signals (optional)
    s_vov: Optional[float] = None
    s_vix_ts: Optional[float] = None
    s_rim: Optional[float] = None
    s_compress: Optional[float] = None
    s_eir_long: Optional[float] = None
    s_eir_short: Optional[float] = None
    s_corr_idx: Optional[float] = None
    s_flow_putcrowd: Optional[float] = None


@dataclass
class CompositeScores:
    """Aggregated long/short volatility scores."""
    long_vol_score: float
    short_vol_score: float


@dataclass
class ProbabilityEstimates:
    """Calibrated probability estimates."""
    p_long: float           # P(RV > IV | L score)
    p_short: float          # P(RV < IV | S score)
    p_long_range: tuple     # (low, high) confidence interval
    p_short_range: tuple    # (low, high) confidence interval
    calibration_method: str # "cold_start" | "platt" | "isotonic"


@dataclass
class StrategyCandidate:
    """A candidate strategy with Edge/EV estimates."""
    name: str                    # e.g., "long_straddle", "iron_condor"
    tier: str                    # "aggressive" | "balanced" | "conservative"
    direction: str               # "long_vol" | "short_vol"
    dte_range: tuple             # (min_dte, max_dte)
    delta_targets: Dict[str, float]  # {"buy": 0.35, "sell": 0.15}
    strike_anchors: Dict[str, str]   # {"buy": "atm", "sell": "gamma_wall"}
    expected_rr: float           # Expected reward:risk ratio
    win_rate: float              # Estimated win rate
    ev: float                    # Expected value (after costs)
    entry_triggers: List[str]    # Conditions for entry
    exit_triggers: List[str]     # Conditions for exit
    cost_adjustment: float       # Spread/slippage penalty
    is_executable: bool          # Passes all gates?


@dataclass 
class DecisionOutput:
    """Final decision output structure."""
    decision: str              # "LONG_VOL" | "SHORT_VOL" | "STAND_ASIDE"
    confidence: float          # 0-1 confidence level
    primary_reasons: List[str] # Key factors driving decision
    scores: CompositeScores
    signal_breakdown: SignalScores
    probabilities: ProbabilityEstimates
    candidates: List[StrategyCandidate]
    selected_strategy: Optional[StrategyCandidate]
    timestamp: str
    warnings: List[str]
    missing_fields: List[str]


@dataclass
class UpdateOutput:
    """Lightweight update output (no strategy/probability)."""
    timestamp: str
    regime_state: str          # "positive_gamma" | "negative_gamma" | "neutral"
    regime_changed: bool       # True if regime flipped since last update
    vol_trigger: float
    spot: float
    gamma_wall_proximity_pct: float
    key_metrics: Dict[str, float]  # VRP, term slope, etc.
    alerts: List[str]          # Any threshold crossings


@dataclass
class OutputData:
    """
    Complete output cache structure.
    Contains all pipeline outputs and intermediate states.
    """
    symbol: str
    date: str
    last_update: str
    updates: List[UpdateOutput]
    full_analysis: Optional[DecisionOutput]
    gexbot_commands: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "date": self.date,
            "last_update": self.last_update,
            "updates": [
                {
                    "timestamp": u.timestamp,
                    "regime_state": u.regime_state,
                    "regime_changed": u.regime_changed,
                    "vol_trigger": u.vol_trigger,
                    "spot": u.spot,
                    "gamma_wall_proximity_pct": u.gamma_wall_proximity_pct,
                    "key_metrics": u.key_metrics,
                    "alerts": u.alerts,
                }
                for u in self.updates
            ],
            "full_analysis": self._decision_to_dict(self.full_analysis) if self.full_analysis else None,
            "gexbot_commands": self.gexbot_commands,
        }
    
    def _decision_to_dict(self, d: DecisionOutput) -> Dict[str, Any]:
        """Convert DecisionOutput to dict."""
        return {
            "decision": d.decision,
            "confidence": d.confidence,
            "primary_reasons": d.primary_reasons,
            "scores": {
                "long_vol_score": d.scores.long_vol_score,
                "short_vol_score": d.scores.short_vol_score,
            },
            "signal_breakdown": {
                "s_vrp": d.signal_breakdown.s_vrp,
                "s_gex": d.signal_breakdown.s_gex,
                "s_vex": d.signal_breakdown.s_vex,
                "s_carry": d.signal_breakdown.s_carry,
                "s_skew": d.signal_breakdown.s_skew,
                "s_vanna": d.signal_breakdown.s_vanna,
                "s_rv": d.signal_breakdown.s_rv,
                "s_liq": d.signal_breakdown.s_liq,
                "s_vov": d.signal_breakdown.s_vov,
                "s_vix_ts": d.signal_breakdown.s_vix_ts,
                "s_rim": d.signal_breakdown.s_rim,
                "s_compress": d.signal_breakdown.s_compress,
                "s_eir_long": d.signal_breakdown.s_eir_long,
                "s_eir_short": d.signal_breakdown.s_eir_short,
                "s_corr_idx": d.signal_breakdown.s_corr_idx,
                "s_flow_putcrowd": d.signal_breakdown.s_flow_putcrowd,
            },
            "probabilities": {
                "p_long": d.probabilities.p_long,
                "p_short": d.probabilities.p_short,
                "p_long_range": d.probabilities.p_long_range,
                "p_short_range": d.probabilities.p_short_range,
                "calibration_method": d.probabilities.calibration_method,
            },
            "candidates": [
                {
                    "name": c.name,
                    "tier": c.tier,
                    "direction": c.direction,
                    "dte_range": c.dte_range,
                    "delta_targets": c.delta_targets,
                    "strike_anchors": c.strike_anchors,
                    "expected_rr": c.expected_rr,
                    "win_rate": c.win_rate,
                    "ev": c.ev,
                    "entry_triggers": c.entry_triggers,
                    "exit_triggers": c.exit_triggers,
                    "cost_adjustment": c.cost_adjustment,
                    "is_executable": c.is_executable,
                }
                for c in d.candidates
            ],
            "selected_strategy": {
                "name": d.selected_strategy.name,
                "tier": d.selected_strategy.tier,
                "direction": d.selected_strategy.direction,
                "dte_range": d.selected_strategy.dte_range,
                "delta_targets": d.selected_strategy.delta_targets,
                "strike_anchors": d.selected_strategy.strike_anchors,
                "expected_rr": d.selected_strategy.expected_rr,
                "win_rate": d.selected_strategy.win_rate,
                "ev": d.selected_strategy.ev,
                "entry_triggers": d.selected_strategy.entry_triggers,
                "exit_triggers": d.selected_strategy.exit_triggers,
                "cost_adjustment": d.selected_strategy.cost_adjustment,
                "is_executable": d.selected_strategy.is_executable,
            } if d.selected_strategy else None,
            "timestamp": d.timestamp,
            "warnings": d.warnings,
            "missing_fields": d.missing_fields,
        }
