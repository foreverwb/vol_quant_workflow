"""
核心模块
包含类型定义、常量、异常
"""
from .types import (
    # 枚举
    EventType,
    Decision,
    Confidence,
    GEXRegime,
    TermStructure,
    VRPRegime,
    SkewRegime,
    StrategyType,
    RiskProfile,
    ValidationStatus,
    FieldPriority,
    DataStatus,
    
    # 数据类
    MarketData,
    FieldValidation,
    Features,
    SignalScore,
    Scores,
    Probability,
    DecisionResult,
    OptionLeg,
    Strategy,
    EdgeMetrics,
    AnalysisResult,
    
    # 类型别名
    FieldMap,
    SignalMap,
    ConfigDict,
)

from .constants import (
    WEIGHTS_LONG_VOL,
    WEIGHTS_SHORT_VOL,
    DECISION_THRESHOLDS,
    PROB_THRESHOLDS,
    EDGE_THRESHOLDS,
    GEX_CONFIG,
    VRP_CONFIG,
    TERM_STRUCTURE_CONFIG,
    RV_CONFIG,
    RIM_CONFIG,
    MONTE_CARLO_CONFIG,
    STRATEGY_CONFIG,
    LOG_CONFIG,
    FIELD_RANGES,
    REQUIRED_FIELDS,
    GEXBOT_COMMANDS,
    SCORE_TO_PROB_MAP,
    LIQUIDITY_CONFIG,
    FILE_PATTERNS,
)

from .exceptions import (
    VolAnalyzerError,
    DataValidationError,
    MissingCriticalFieldError,
    InvalidFieldValueError,
    ConfigurationError,
    LLMError,
    LLMConnectionError,
    LLMResponseError,
    StrategyError,
    InsufficientDataError,
    SimulationError,
    PipelineError,
)

__all__ = [
    # 枚举
    "EventType",
    "Decision",
    "Confidence",
    "GEXRegime",
    "TermStructure",
    "VRPRegime",
    "SkewRegime",
    "StrategyType",
    "RiskProfile",
    "ValidationStatus",
    "FieldPriority",
    "DataStatus",
    
    # 数据类
    "MarketData",
    "FieldValidation",
    "Features",
    "SignalScore",
    "Scores",
    "Probability",
    "DecisionResult",
    "OptionLeg",
    "Strategy",
    "EdgeMetrics",
    "AnalysisResult",
    
    # 常量
    "WEIGHTS_LONG_VOL",
    "WEIGHTS_SHORT_VOL",
    "DECISION_THRESHOLDS",
    "EDGE_THRESHOLDS",
    "GEX_CONFIG",
    
    # 异常
    "VolAnalyzerError",
    "DataValidationError",
    "MissingCriticalFieldError",
]
