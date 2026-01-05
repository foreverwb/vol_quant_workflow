"""
LLM module - Language model integration.
Provides unified interface for multi-model LLM calls.
"""

from .client import (
    LLMClient,
    LLMResponse,
    get_llm_client,
)

__all__ = [
    "LLMClient",
    "LLMResponse",
    "get_llm_client",
]
