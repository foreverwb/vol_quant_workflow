"""
Settings - Environment-based configuration loading.
Loads settings from .env file and environment variables.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


def _load_env_file(env_path: Optional[str] = None) -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    
    # Default paths to search
    search_paths = [
        env_path,
        Path.cwd() / ".env",
        Path.cwd() / "_env",
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent.parent / "_env",
        Path.home() / ".vol_workflow" / ".env",
    ]
    
    for path in search_paths:
        if path and Path(path).exists():
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
            break
    
    return env_vars


def _get_env(key: str, default: Any = None, env_vars: Dict[str, str] = None) -> str:
    """Get environment variable with fallback to loaded env file."""
    if env_vars and key in env_vars:
        return env_vars[key]
    return os.environ.get(key, default)


@dataclass
class LLMSettings:
    """LLM API configuration."""
    api_base: str = "http://localhost:8000"
    api_key: str = "sk-default"
    timeout: int = 360
    max_retries: int = 3
    retry_delay: float = 2.0


@dataclass
class MonteCarloSettings:
    """Monte Carlo simulation settings."""
    simulations: int = 10000
    risk_free_rate: float = 0.05


@dataclass
class ProbabilityThresholds:
    """Probability thresholds for decision making."""
    prob_long_l1_0: float = 0.55  # L >= 1.0
    prob_long_l1_5: float = 0.60  # L >= 1.5
    prob_long_l2_0: float = 0.65  # L >= 2.0
    prob_threshold: float = 0.55  # General threshold


@dataclass
class WeightsLongVol:
    """Weights for long volatility scoring."""
    vrp: float = 0.25
    gex: float = 0.18
    vex: float = 0.18
    carry: float = 0.08
    skew: float = 0.08


@dataclass 
class WeightsShortVol:
    """Weights for short volatility scoring."""
    vrp: float = 0.30
    gex: float = 0.12
    carry: float = 0.18


@dataclass
class DecisionThresholds:
    """Decision score thresholds."""
    long_vol: float = 1.00
    short_vol: float = 1.00
    ev_min: float = 0.0
    rr_min: float = 1.5


@dataclass
class TriggerSettings:
    """VOL TRIGGER related settings."""
    neutral_pct: float = 0.002  # Distance considered neutral


@dataclass
class GammaWallSettings:
    """Gamma wall related settings."""
    proximity_threshold: float = 0.005


@dataclass
class RIMSettings:
    """RIM (Relative Intraday Momentum) settings."""
    active_threshold: float = 0.6
    weak_threshold: float = 0.4


@dataclass
class LogSettings:
    """Logging configuration."""
    level: str = "INFO"
    file: str = "vol_quant.log"
    log_api_calls: bool = True
    log_token_usage: bool = True
    log_latency: bool = True


@dataclass
class Settings:
    """Main settings container."""
    llm: LLMSettings = field(default_factory=LLMSettings)
    monte_carlo: MonteCarloSettings = field(default_factory=MonteCarloSettings)
    probability: ProbabilityThresholds = field(default_factory=ProbabilityThresholds)
    weights_long: WeightsLongVol = field(default_factory=WeightsLongVol)
    weights_short: WeightsShortVol = field(default_factory=WeightsShortVol)
    decision: DecisionThresholds = field(default_factory=DecisionThresholds)
    trigger: TriggerSettings = field(default_factory=TriggerSettings)
    gamma_wall: GammaWallSettings = field(default_factory=GammaWallSettings)
    rim: RIMSettings = field(default_factory=RIMSettings)
    log: LogSettings = field(default_factory=LogSettings)
    
    @classmethod
    def load(cls, env_path: Optional[str] = None) -> "Settings":
        """Load settings from environment."""
        env_vars = _load_env_file(env_path)
        
        def get(key: str, default: Any = None) -> str:
            return _get_env(key, default, env_vars)
        
        return cls(
            llm=LLMSettings(
                api_base=get("LLM_API_BASE", "http://localhost:8000"),
                api_key=get("LLM_API_KEY", "sk-default"),
                timeout=int(get("LLM_TIMEOUT", "360")),
                max_retries=int(get("LLM_MAX_RETRIES", "3")),
                retry_delay=float(get("LLM_RETRY_DELAY", "2.0")),
            ),
            monte_carlo=MonteCarloSettings(
                simulations=int(get("MONTE_CARLO_SIMULATIONS", "10000")),
                risk_free_rate=float(get("RISK_FREE_RATE", "0.05")),
            ),
            probability=ProbabilityThresholds(
                prob_long_l1_0=float(get("PROB_LONG_L1_0", "0.55")),
                prob_long_l1_5=float(get("PROB_LONG_L1_5", "0.60")),
                prob_long_l2_0=float(get("PROB_LONG_L2_0", "0.65")),
                prob_threshold=float(get("PROB_THRESHOLD", "0.55")),
            ),
            weights_long=WeightsLongVol(
                vrp=float(get("WEIGHT_VRP_LONG", "0.25")),
                gex=float(get("WEIGHT_GEX_LONG", "0.18")),
                vex=float(get("WEIGHT_VEX_LONG", "0.18")),
                carry=float(get("WEIGHT_CARRY_LONG", "0.08")),
                skew=float(get("WEIGHT_SKEW_LONG", "0.08")),
            ),
            weights_short=WeightsShortVol(
                vrp=float(get("WEIGHT_VRP_SHORT", "0.30")),
                gex=float(get("WEIGHT_GEX_SHORT", "0.12")),
                carry=float(get("WEIGHT_CARRY_SHORT", "0.18")),
            ),
            decision=DecisionThresholds(
                long_vol=float(get("DECISION_THRESHOLD_LONG", "1.00")),
                short_vol=float(get("DECISION_THRESHOLD_SHORT", "1.00")),
                ev_min=float(get("EDGE_EV_THRESHOLD", "0")),
                rr_min=float(get("EDGE_RR_THRESHOLD", "1.5")),
            ),
            trigger=TriggerSettings(
                neutral_pct=float(get("TRIGGER_NEUTRAL_PCT", "0.002")),
            ),
            gamma_wall=GammaWallSettings(
                proximity_threshold=float(get("GAMMA_WALL_PROX_THRESHOLD", "0.005")),
            ),
            rim=RIMSettings(
                active_threshold=float(get("RIM_ACTIVE_THRESHOLD", "0.6")),
                weak_threshold=float(get("RIM_WEAK_THRESHOLD", "0.4")),
            ),
            log=LogSettings(
                level=get("LOG_LEVEL", "INFO"),
                file=get("LOG_FILE", "vol_quant.log"),
            ),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "llm": {
                "api_base": self.llm.api_base,
                "timeout": self.llm.timeout,
            },
            "monte_carlo": {
                "simulations": self.monte_carlo.simulations,
                "risk_free_rate": self.monte_carlo.risk_free_rate,
            },
            "probability": {
                "prob_long_l1_0": self.probability.prob_long_l1_0,
                "prob_long_l1_5": self.probability.prob_long_l1_5,
                "prob_long_l2_0": self.probability.prob_long_l2_0,
                "prob_threshold": self.probability.prob_threshold,
            },
            "weights_long": {
                "vrp": self.weights_long.vrp,
                "gex": self.weights_long.gex,
                "vex": self.weights_long.vex,
                "carry": self.weights_long.carry,
                "skew": self.weights_long.skew,
            },
            "weights_short": {
                "vrp": self.weights_short.vrp,
                "gex": self.weights_short.gex,
                "carry": self.weights_short.carry,
            },
            "decision": {
                "long_vol": self.decision.long_vol,
                "short_vol": self.decision.short_vol,
                "ev_min": self.decision.ev_min,
                "rr_min": self.decision.rr_min,
            },
            "trigger": {
                "neutral_pct": self.trigger.neutral_pct,
            },
            "gamma_wall": {
                "proximity_threshold": self.gamma_wall.proximity_threshold,
            },
            "rim": {
                "active_threshold": self.rim.active_threshold,
                "weak_threshold": self.rim.weak_threshold,
            },
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings(env_path: Optional[str] = None) -> Settings:
    """Get global settings instance (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings.load(env_path)
    return _settings


def reload_settings(env_path: Optional[str] = None) -> Settings:
    """Force reload settings from environment."""
    global _settings
    _settings = Settings.load(env_path)
    return _settings
