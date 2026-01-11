"""
Prompts module - Centralized prompt management.
All LLM prompts and templates are maintained here for easy updates.
"""

from .probability import (
    PROBABILITY_SYSTEM_PROMPT,
    PROBABILITY_USER_TEMPLATE,
    COLD_START_TEMPLATE,
    format_probability_prompt,
    get_probability_system_prompt,
    get_cold_start_reference,
)

from .strategy import (
    STRATEGY_SYSTEM_PROMPT,
    STRATEGY_USER_TEMPLATE,
    STRATEGY_TEMPLATES,
    format_strategy_prompt,
    get_strategy_system_prompt,
    get_strategy_templates,
    get_strategy_template,
)
from .report import (
    REPORT_SYSTEM_PROMPT,
    REPORT_USER_TEMPLATE,
    format_report_prompt,
    get_report_system_prompt,
)

__all__ = [
    # Probability prompts
    "PROBABILITY_SYSTEM_PROMPT",
    "PROBABILITY_USER_TEMPLATE",
    "COLD_START_TEMPLATE",
    "format_probability_prompt",
    "get_probability_system_prompt",
    "get_cold_start_reference",
    # Strategy prompts
    "STRATEGY_SYSTEM_PROMPT",
    "STRATEGY_USER_TEMPLATE",
    "STRATEGY_TEMPLATES",
    "format_strategy_prompt",
    "get_strategy_system_prompt",
    "get_strategy_templates",
    "get_strategy_template",
    # Report prompts
    "REPORT_SYSTEM_PROMPT",
    "REPORT_USER_TEMPLATE",
    "format_report_prompt",
    "get_report_system_prompt",
]
