"""
数据模型定义
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

class Direction(str, Enum):
    """交易方向"""
    LONG_VOL = "做多波动率"
    SHORT_VOL = "做空波动率"
    NEUTRAL = "观望"

class OptionType(str, Enum):
    """期权类型"""
    CALL = "call"
    PUT = "put"

class OptionAction(str, Enum):
    """期权操作"""
    BUY = "buy"
    SELL = "sell"

class StrategyTier(str, Enum):
    """策略等级"""
    AGGRESSIVE = "进取版"
    BALANCED = "均衡版"
    CONSERVATIVE = "保守版"

@dataclass
class CoreFields:
    """核心字段数据"""
    symbol: str
    timestamp: str
    
    # VOL TRIGGER相关
    vol_trigger: float
    spot: float
    net_gex_sign: str  # positive/negative/neutral
    spot_vs_trigger: str  # above/below/near
    
    # Gamma Walls
    gamma_wall: Optional[float] = None
    call_wall: Optional[float] = None
    put_wall: Optional[float] = None
    gamma_wall_prox: float = 0.0
    
    # IV/HV数据
    iv_event_w_atm: Optional[float] = None
    iv_m1_atm: Optional[float] = None
    iv_m2_atm: Optional[float] = None
    hv10: Optional[float] = None
    hv20: Optional[float] = None
    hv60: Optional[float] = None
    
    # 结构性指标
    vex_net: Optional[float] = None
    vanna_atm: Optional[float] = None
    term_slope: Optional[float] = None
    put_skew_25: Optional[float] = None
    call_skew_25: Optional[float] = None
    spread_atm: Optional[float] = None
    ask_premium_atm: Optional[float] = None

@dataclass
class MissingField:
    """缺失字段信息"""
    field: str
    priority: str  # critical/high/medium/low
    command: str
    alternative: Optional[str] = None

@dataclass
class ValidationResult:
    """数据校验结果"""
    symbol: str
    timestamp: str
    status: str  # data_ready/missing_data
    core_fields: CoreFields
    missing_fields: List[MissingField]
    next_step: str  # proceed_to_analysis/request_missing_data

@dataclass
class Features:
    """计算特征"""
    vrp_ew: float
    vrp_30: float
    term_slope: float
    term_curv: float
    skew_asym: float
    rv_momo: float
    gex_level: int  # 1/-1/0
    pin_risk: int  # -1/0
    vex_net: float
    vanna_atm: float
    spread_atm: float
    ask_premium_atm: float
    gamma_wall_prox: float
    vrp_sel: float

@dataclass
class Signals:
    """信号评分"""
    s_vrp: float
    s_carry: float
    s_skew: float
    s_gex: float
    s_vex: float
    s_vanna: float
    s_rv: float
    s_liq: float
    s_vov: float = 0
    s_vix_ts: float = 0
    s_rim: float = 0
    s_compress: float = 0
    s_eir_long: float = 0
    s_eir_short: float = 0
    s_corr_idx: float = 0
    s_flow_putcrowd: float = 0

@dataclass
class Scores:
    """评分结果"""
    long_vol_score: float
    short_vol_score: float
    score_breakdown: Dict[str, Dict[str, float]]

@dataclass
class ProbabilityCalibration:
    """概率校准结果"""
    p_long: float
    p_short: float
    confidence: str  # high/medium/low
    method: str
    rationale: str

@dataclass
class DecisionGate:
    """决策门控"""
    long_vol_pass: bool
    short_vol_pass: bool
    final_direction: Direction
    gate_check: Dict[str, str]

@dataclass
class OptionLeg:
    """期权腿"""
    type: OptionType
    action: OptionAction
    strike: str  # 描述性表示
    strike_calculated: Optional[float] = None
    delta: Optional[float] = None
    rationale: str = ""
    calculation_method: Optional[str] = None

@dataclass
class EdgeEstimate:
    """Edge估算"""
    win_rate: str
    rr_ratio: str
    ev: str
    ev_numeric: float
    meets_threshold: bool
    note: Optional[str] = None

@dataclass
class StrategyEntry:
    """策略入场条件"""
    trigger: str
    timing: str
    condition: str

@dataclass
class StrategyExit:
    """策略退出条件"""
    profit_target: str
    stop_loss: str
    time_decay: str
    regime_change: str

@dataclass
class Strategy:
    """策略方案"""
    tier: StrategyTier
    structure: str  # Long Straddle、Iron Condor等
    dte: str
    legs: List[OptionLeg]
    entry: StrategyEntry
    exit: StrategyExit
    edge_estimate: EdgeEstimate
    description: str = ""

@dataclass
class StrategyMapping:
    """策略映射结果"""
    symbol: str
    direction: Direction
    strategies: List[Strategy]

@dataclass
class AnalysisResult:
    """完整分析结果"""
    symbol: str
    timestamp: str
    
    validation: Optional[ValidationResult] = None
    features: Optional[Features] = None
    signals: Optional[Signals] = None
    scores: Optional[Scores] = None
    probability: Optional[ProbabilityCalibration] = None
    decision: Optional[DecisionGate] = None
    strategies: Optional[StrategyMapping] = None
    
    final_report: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'validation': self.validation.__dict__ if self.validation else None,
            'features': self.features.__dict__ if self.features else None,
            'signals': self.signals.__dict__ if self.signals else None,
            'scores': self.scores.__dict__ if self.scores else None,
            'probability': self.probability.__dict__ if self.probability else None,
            'decision': self.decision.__dict__ if self.decision else None,
            'strategies': self.strategies.__dict__ if self.strategies else None,
            'final_report': self.final_report
        }
