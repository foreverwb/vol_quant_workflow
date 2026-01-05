"""
Centralized configuration management.
All parameters are configurable from a single location.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path

from .constants import (
    # Decision thresholds
    LONG_VOL_SCORE_MIN, LONG_VOL_PROB_MIN, LONG_VOL_OPPOSING_MAX,
    SHORT_VOL_SCORE_MIN, SHORT_VOL_PROB_MIN, SHORT_VOL_OPPOSING_MAX,
    CONSERVATIVE_PROB_MIN,
    # Edge thresholds
    EV_MIN_THRESHOLD, RR_MIN_THRESHOLD, RR_TARGET_AGGRESSIVE,
    LIQUIDITY_SPREAD_PERCENTILE_MAX, LIQUIDITY_IVASK_PERCENTILE_MAX,
    # Regime thresholds
    VOL_TRIGGER_NEUTRAL_PCT, GAMMA_WALL_PIN_PCT,
    # RIM thresholds
    RIM_HIGH_THRESHOLD, RIM_LOW_THRESHOLD,
    # Weights - Long Vol
    WEIGHT_LONG_VRP, WEIGHT_LONG_GEX, WEIGHT_LONG_VEX, WEIGHT_LONG_CARRY,
    WEIGHT_LONG_SKEW, WEIGHT_LONG_VANNA, WEIGHT_LONG_RV, WEIGHT_LONG_LIQ,
    WEIGHT_LONG_VOV, WEIGHT_LONG_VIX_TS, WEIGHT_LONG_RIM, WEIGHT_LONG_COMPRESS,
    WEIGHT_LONG_EIR, SINGLE_STOCK_GEX_BOOST,
    # Weights - Short Vol
    WEIGHT_SHORT_VRP, WEIGHT_SHORT_GEX, WEIGHT_SHORT_VEX, WEIGHT_SHORT_CARRY,
    WEIGHT_SHORT_SKEW, WEIGHT_SHORT_RV, WEIGHT_SHORT_LIQ, WEIGHT_SHORT_VOV,
    WEIGHT_SHORT_VIX_TS, WEIGHT_SHORT_RIM, WEIGHT_SHORT_COMPRESS,
    WEIGHT_SHORT_EIR, WEIGHT_SHORT_CORR_IDX, WEIGHT_SHORT_FLOW_PUTCROWD,
    # DTE ranges
    DTE_LONG_VOL_EVENT_MIN, DTE_LONG_VOL_EVENT_MAX,
    DTE_LONG_VOL_NON_EVENT_MIN, DTE_LONG_VOL_NON_EVENT_MAX,
    DTE_SHORT_VOL_MIN, DTE_SHORT_VOL_MAX,
    # Delta targets
    DELTA_STRADDLE_ATM, DELTA_STRANGLE_WING, DELTA_SHORT_SELL, DELTA_SHORT_PROTECT,
    DELTA_DEBIT_BUY, DELTA_DEBIT_SELL,
    # Session
    US_RTH_START_ET, US_RTH_END_ET, EXCLUDE_0DTE,
)


@dataclass
class DecisionConfig:
    """Decision threshold configuration."""
    long_vol_score_min: float = LONG_VOL_SCORE_MIN
    long_vol_prob_min: float = LONG_VOL_PROB_MIN
    long_vol_opposing_max: float = LONG_VOL_OPPOSING_MAX
    short_vol_score_min: float = SHORT_VOL_SCORE_MIN
    short_vol_prob_min: float = SHORT_VOL_PROB_MIN
    short_vol_opposing_max: float = SHORT_VOL_OPPOSING_MAX
    conservative_prob_min: float = CONSERVATIVE_PROB_MIN


@dataclass
class EdgeConfig:
    """Edge/EV threshold configuration."""
    ev_min: float = EV_MIN_THRESHOLD
    rr_min: float = RR_MIN_THRESHOLD
    rr_target_aggressive: float = RR_TARGET_AGGRESSIVE
    liquidity_spread_max_pctl: int = LIQUIDITY_SPREAD_PERCENTILE_MAX
    liquidity_ivask_max_pctl: int = LIQUIDITY_IVASK_PERCENTILE_MAX


@dataclass
class RegimeConfig:
    """Regime detection configuration."""
    vol_trigger_neutral_pct: float = VOL_TRIGGER_NEUTRAL_PCT
    gamma_wall_pin_pct: float = GAMMA_WALL_PIN_PCT


@dataclass
class RIMConfig:
    """RIM (Realized/Implied Move) configuration."""
    high_threshold: float = RIM_HIGH_THRESHOLD
    low_threshold: float = RIM_LOW_THRESHOLD


@dataclass
class WeightsLongVol:
    """Long vol scoring weights."""
    vrp: float = WEIGHT_LONG_VRP
    gex: float = WEIGHT_LONG_GEX
    vex: float = WEIGHT_LONG_VEX
    carry: float = WEIGHT_LONG_CARRY
    skew: float = WEIGHT_LONG_SKEW
    vanna: float = WEIGHT_LONG_VANNA
    rv: float = WEIGHT_LONG_RV
    liq: float = WEIGHT_LONG_LIQ
    vov: float = WEIGHT_LONG_VOV
    vix_ts: float = WEIGHT_LONG_VIX_TS
    rim: float = WEIGHT_LONG_RIM
    compress: float = WEIGHT_LONG_COMPRESS
    eir: float = WEIGHT_LONG_EIR
    single_stock_boost: float = SINGLE_STOCK_GEX_BOOST


@dataclass
class WeightsShortVol:
    """Short vol scoring weights."""
    vrp: float = WEIGHT_SHORT_VRP
    gex: float = WEIGHT_SHORT_GEX
    vex: float = WEIGHT_SHORT_VEX
    carry: float = WEIGHT_SHORT_CARRY
    skew: float = WEIGHT_SHORT_SKEW
    rv: float = WEIGHT_SHORT_RV
    liq: float = WEIGHT_SHORT_LIQ
    vov: float = WEIGHT_SHORT_VOV
    vix_ts: float = WEIGHT_SHORT_VIX_TS
    rim: float = WEIGHT_SHORT_RIM
    compress: float = WEIGHT_SHORT_COMPRESS
    eir: float = WEIGHT_SHORT_EIR
    corr_idx: float = WEIGHT_SHORT_CORR_IDX
    flow_putcrowd: float = WEIGHT_SHORT_FLOW_PUTCROWD


@dataclass
class DTERanges:
    """DTE range configuration."""
    long_vol_event_min: int = DTE_LONG_VOL_EVENT_MIN
    long_vol_event_max: int = DTE_LONG_VOL_EVENT_MAX
    long_vol_non_event_min: int = DTE_LONG_VOL_NON_EVENT_MIN
    long_vol_non_event_max: int = DTE_LONG_VOL_NON_EVENT_MAX
    short_vol_min: int = DTE_SHORT_VOL_MIN
    short_vol_max: int = DTE_SHORT_VOL_MAX


@dataclass
class DeltaTargets:
    """Delta target configuration."""
    straddle_atm: float = DELTA_STRADDLE_ATM
    strangle_wing: tuple = DELTA_STRANGLE_WING
    short_sell: tuple = DELTA_SHORT_SELL
    short_protect: tuple = DELTA_SHORT_PROTECT
    debit_buy: tuple = DELTA_DEBIT_BUY
    debit_sell: tuple = DELTA_DEBIT_SELL


@dataclass
class SessionConfig:
    """Trading session configuration."""
    rth_start: str = US_RTH_START_ET
    rth_end: str = US_RTH_END_ET
    exclude_0dte: bool = EXCLUDE_0DTE


@dataclass
class Config:
    """
    Master configuration class.
    All strategy parameters centralized here.
    """
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    edge: EdgeConfig = field(default_factory=EdgeConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    rim: RIMConfig = field(default_factory=RIMConfig)
    weights_long: WeightsLongVol = field(default_factory=WeightsLongVol)
    weights_short: WeightsShortVol = field(default_factory=WeightsShortVol)
    dte_ranges: DTERanges = field(default_factory=DTERanges)
    delta_targets: DeltaTargets = field(default_factory=DeltaTargets)
    session: SessionConfig = field(default_factory=SessionConfig)
    
    # Runtime paths
    runtime_dir: str = "runtime"
    inputs_dir: str = "runtime/inputs"
    outputs_dir: str = "runtime/outputs"
    logs_dir: str = "runtime/logs"
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from JSON file or use defaults."""
        config = cls()
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                config._update_from_dict(data)
        
        return config
    
    def _update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update config from dictionary."""
        if "decision" in data:
            for k, v in data["decision"].items():
                if hasattr(self.decision, k):
                    setattr(self.decision, k, v)
        
        if "edge" in data:
            for k, v in data["edge"].items():
                if hasattr(self.edge, k):
                    setattr(self.edge, k, v)
        
        if "regime" in data:
            for k, v in data["regime"].items():
                if hasattr(self.regime, k):
                    setattr(self.regime, k, v)
        
        if "weights_long" in data:
            for k, v in data["weights_long"].items():
                if hasattr(self.weights_long, k):
                    setattr(self.weights_long, k, v)
        
        if "weights_short" in data:
            for k, v in data["weights_short"].items():
                if hasattr(self.weights_short, k):
                    setattr(self.weights_short, k, v)
    
    def save(self, config_path: str) -> None:
        """Save configuration to JSON file."""
        data = {
            "decision": {
                "long_vol_score_min": self.decision.long_vol_score_min,
                "long_vol_prob_min": self.decision.long_vol_prob_min,
                "long_vol_opposing_max": self.decision.long_vol_opposing_max,
                "short_vol_score_min": self.decision.short_vol_score_min,
                "short_vol_prob_min": self.decision.short_vol_prob_min,
                "short_vol_opposing_max": self.decision.short_vol_opposing_max,
                "conservative_prob_min": self.decision.conservative_prob_min,
            },
            "edge": {
                "ev_min": self.edge.ev_min,
                "rr_min": self.edge.rr_min,
                "rr_target_aggressive": self.edge.rr_target_aggressive,
                "liquidity_spread_max_pctl": self.edge.liquidity_spread_max_pctl,
                "liquidity_ivask_max_pctl": self.edge.liquidity_ivask_max_pctl,
            },
            "regime": {
                "vol_trigger_neutral_pct": self.regime.vol_trigger_neutral_pct,
                "gamma_wall_pin_pct": self.regime.gamma_wall_pin_pct,
            },
            "rim": {
                "high_threshold": self.rim.high_threshold,
                "low_threshold": self.rim.low_threshold,
            },
            "weights_long": {
                "vrp": self.weights_long.vrp,
                "gex": self.weights_long.gex,
                "vex": self.weights_long.vex,
                "carry": self.weights_long.carry,
                "skew": self.weights_long.skew,
                "vanna": self.weights_long.vanna,
                "rv": self.weights_long.rv,
                "liq": self.weights_long.liq,
            },
            "weights_short": {
                "vrp": self.weights_short.vrp,
                "gex": self.weights_short.gex,
                "vex": self.weights_short.vex,
                "carry": self.weights_short.carry,
                "skew": self.weights_short.skew,
                "rv": self.weights_short.rv,
                "liq": self.weights_short.liq,
            },
            "session": {
                "rth_start": self.session.rth_start,
                "rth_end": self.session.rth_end,
                "exclude_0dte": self.session.exclude_0dte,
            },
        }
        
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)


# Global default configuration instance
_default_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _default_config
    if _default_config is None:
        _default_config = Config.load()
    return _default_config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _default_config
    _default_config = config
