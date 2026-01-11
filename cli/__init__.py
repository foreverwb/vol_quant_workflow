"""
CLI module - Command-line interface for volatility strategy.
Three commands: cmd, updated, task

Note: Lazy imports to avoid RuntimeWarning when running as module.
"""

__all__ = [
    "CmdHandler",
    "UpdateHandler", 
    "TaskHandler",
    "GexbotCommandGenerator",
]


def __getattr__(name):
    """Lazy import to avoid circular import warnings."""
    if name == "CmdHandler":
        from .cmd import CmdHandler
        return CmdHandler
    elif name == "UpdateHandler":
        from .update import UpdateHandler
        return UpdateHandler
    elif name == "TaskHandler":
        from .task import TaskHandler
        return TaskHandler
    elif name == "GexbotCommandGenerator":
        from .gexbot import GexbotCommandGenerator
        return GexbotCommandGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
