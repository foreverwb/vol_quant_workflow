"""
Schemas module - Data structure definitions.
Provides type-safe data structures for pipeline I/O.
"""

from .input import (
    REQUIRED_FIELDS,
    OPTIONAL_FIELDS,
    MetaFields,
    MarketFields,
    RegimeFields,
    VolatilityFields,
    StructureFields,
    LiquidityFields,
    InputData,
    validate_input,
    get_empty_template as get_input_template,
)

from .output import (
    SignalScores,
    CompositeScores,
    ProbabilityEstimate,
    DecisionResult,
    StrategyCandidate,
    TradeOutput,
    AnalysisOutput,
    UpdateOutput,
    get_output_template,
)

__all__ = [
    # Input schemas
    "REQUIRED_FIELDS",
    "OPTIONAL_FIELDS",
    "MetaFields",
    "MarketFields",
    "RegimeFields",
    "VolatilityFields",
    "StructureFields",
    "LiquidityFields",
    "InputData",
    "validate_input",
    "get_input_template",
    # Output schemas
    "SignalScores",
    "CompositeScores",
    "ProbabilityEstimate",
    "DecisionResult",
    "StrategyCandidate",
    "TradeOutput",
    "AnalysisOutput",
    "UpdateOutput",
    "get_output_template",
]
