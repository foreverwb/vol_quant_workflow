"""
Volatility Strategy Framework

A dual-role framework for converting natural-language options volatility 
strategies into production-grade Python code.

System Constraints:
- US RTH intraday only
- 5-45 DTE (0DTE disallowed)  
- VOL TRIGGER solely determines NET-GEX
- No data inference permitted
- LLM usage restricted to probability calibration and strategy template selection

Commands:
- cmd: Initialize session, generate gexbot commands
- update: Lightweight monitoring (regime/volatility only)
- task: Full pipeline (features → signals → probability → strategy → strikes → EV)
"""

__version__ = "1.0.0"
__author__ = "Volatility Strategy Framework"

from .core import Config, InputSchema, OutputSchema, Decision, StrategyTier, RegimeState
from .cli import CmdHandler, UpdateHandler, TaskHandler

__all__ = [
    "Config",
    "InputSchema",
    "OutputSchema",
    "Decision",
    "StrategyTier",
    "RegimeState",
    "CmdHandler",
    "UpdateHandler",
    "TaskHandler",
]
