"""
核心类型定义模块
包含所有数据类、枚举、类型别名
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime


# =============================================================================
# 枚举定义
# =============================================================================

class EventType(Enum):
    """事件类型"""
    NONE = "none"
    EARNINGS = "earnings"
    FOMC = "fomc"
    CPI = "cpi"
    NFP = "nfp"
    OPEX = "opex"
    MACRO = "macro"


class Decision(Enum):
    """交易决策"""
    LONG_VOL = "long_vol"
    SHORT_VOL = "short_vol"
    HOLD = "hold"


class Confidence(Enum):
    """置信度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GEXRegime(Enum):
    """GEX 环境"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class TermStructure(Enum):
    """期限结构"""
    CONTANGO = "contango"
    BACKWARDATION = "backwardation"
    FLAT = "flat"


class VRPRegime(Enum):
    """VRP 状态"""
    LONG_BIAS = "long_bias"
    SHORT_BIAS = "short_bias"
    FAIR = "fair"


class SkewRegime(Enum):
    """Skew 状态"""
    PUT_HEAVY = "put_heavy"
    CALL_HEAVY = "call_heavy"
    BALANCED = "balanced"


class StrategyType(Enum):
    """策略类型"""
    LONG_STRADDLE = "long_straddle"
    LONG_STRANGLE = "long_strangle"
    SHORT_STRADDLE = "short_straddle"
    SHORT_STRANGLE = "short_strangle"
    IRON_CONDOR = "iron_condor"
    IRON_BUTTERFLY = "iron_butterfly"
    CREDIT_PUT_SPREAD = "credit_put_spread"
    CREDIT_CALL_SPREAD = "credit_call_spread"
    DEBIT_PUT_SPREAD = "debit_put_spread"
    DEBIT_CALL_SPREAD = "debit_call_spread"
    CALENDAR_SPREAD = "calendar_spread"
    DIAGONAL_SPREAD = "diagonal_spread"
    BUTTERFLY = "butterfly"


class RiskProfile(Enum):
    """风险等级"""
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"


class ValidationStatus(Enum):
    """校验状态"""
    VALID = "valid"
    MISSING = "missing"
    INVALID = "invalid"
    ESTIMATED = "estimated"
    PROXY = "proxy"


class FieldPriority(Enum):
    """字段优先级"""
    CRITICAL = "critical"
    HIGH = "high"
    OPTIONAL = "optional"


class DataStatus(Enum):
    """数据状态"""
    DATA_READY = "data_ready"
    MISSING_CRITICAL = "missing_critical"
    MISSING_HIGH = "missing_high"
    MISSING_OPTIONAL = "missing_optional"


# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class MarketData:
    """市场数据"""
    symbol: str
    spot: float
    timestamp: Optional[str] = None
    
    # Gamma Regime
    vol_trigger: Optional[float] = None
    net_gex_sign: Optional[GEXRegime] = None
    total_net_gex: Optional[float] = None
    
    # Key Levels
    gamma_wall: Optional[float] = None
    gamma_wall_2: Optional[float] = None
    call_wall: Optional[float] = None
    put_wall: Optional[float] = None
    max_pain: Optional[float] = None
    
    # IV/HV
    iv_atm: Optional[float] = None
    iv_front: Optional[float] = None
    iv_back: Optional[float] = None
    iv_event_w: Optional[float] = None
    hv10: Optional[float] = None
    hv20: Optional[float] = None
    hv60: Optional[float] = None
    
    # Structure
    vex_net: Optional[float] = None
    vanna_atm: Optional[float] = None
    term_slope: Optional[float] = None
    put_skew_25: Optional[float] = None
    call_skew_25: Optional[float] = None
    spread_atm: Optional[float] = None
    pcr_ratio: Optional[float] = None
    
    # Enhanced
    vvix: Optional[float] = None
    vix9d: Optional[float] = None
    vix: Optional[float] = None


@dataclass
class FieldValidation:
    """字段校验结果"""
    field_name: str
    value: Any
    status: ValidationStatus
    source: str = "user_input"
    notes: Optional[str] = None
    confidence: float = 1.0


@dataclass
class Features:
    """计算特征"""
    # VRP
    vrp_hv20: Optional[float] = None
    vrp_hv10: Optional[float] = None
    vrp_selected: Optional[float] = None
    vrp_regime: Optional[VRPRegime] = None
    
    # Term Structure
    term_slope: Optional[float] = None
    term_regime: Optional[TermStructure] = None
    
    # GEX
    gex_level: Optional[int] = None
    gamma_wall_prox: Optional[float] = None
    is_pin_risk: bool = False
    net_gex_regime: Optional[GEXRegime] = None
    
    # Skew
    skew_asym: Optional[float] = None
    skew_regime: Optional[SkewRegime] = None
    
    # Momentum
    rv_momo: Optional[float] = None
    
    # Liquidity
    liquidity_score: Optional[float] = None
    
    # VoV
    vov_level: Optional[float] = None


@dataclass
class SignalScore:
    """单个信号得分"""
    name: str
    raw_score: float
    weight_long: float
    weight_short: float
    contribution_long: float
    contribution_short: float
    notes: Optional[str] = None


@dataclass
class Scores:
    """综合评分"""
    long_vol_score: float
    short_vol_score: float
    dominant_direction: str
    score_diff: float
    confidence_pct: float
    signal_breakdown: Dict[str, SignalScore] = field(default_factory=dict)


@dataclass
class Probability:
    """概率分布"""
    p_long: float
    p_short: float
    p_hold: float


@dataclass
class DecisionResult:
    """决策结果"""
    decision: Decision
    probability: Probability
    confidence: Confidence
    rationale: str
    key_factors: List[str]
    risk_notes: List[str]
    suggested_strategy: Optional[str] = None


@dataclass
class OptionLeg:
    """期权腿"""
    action: str  # buy/sell
    option_type: str  # call/put
    strike: float
    delta: Optional[float] = None
    quantity: int = 1
    premium: Optional[float] = None


@dataclass
class Strategy:
    """交易策略"""
    name: str
    type: StrategyType
    risk_profile: RiskProfile
    rationale: str
    legs: List[OptionLeg] = field(default_factory=list)
    dte_min: int = 0
    dte_max: int = 45
    dte_optimal: int = 30
    entry_conditions: List[str] = field(default_factory=list)
    exit_conditions: List[str] = field(default_factory=list)
    max_loss: Optional[float] = None
    target_profit: Optional[float] = None
    reward_risk: Optional[float] = None


@dataclass
class EdgeMetrics:
    """Edge 指标"""
    win_rate: float
    avg_win: float
    avg_loss: float
    expected_value: float
    reward_risk: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    is_profitable: bool = False
    confidence_interval: Optional[tuple] = None


@dataclass 
class AnalysisResult:
    """完整分析结果"""
    symbol: str
    timestamp: str
    market_data: MarketData
    features: Features
    scores: Scores
    decision: DecisionResult
    strategy: Strategy
    edge: EdgeMetrics
    data_quality: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 类型别名
# =============================================================================

FieldMap = Dict[str, FieldValidation]
SignalMap = Dict[str, SignalScore]
ConfigDict = Dict[str, Any]
