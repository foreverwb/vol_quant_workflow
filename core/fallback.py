"""
Fallback - 降级方案
提供简单的日志和错误收集器实现，用于依赖不可用时
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class SimpleLogger:
    """简单日志记录器 - 当外部日志库不可用时使用"""
    
    def __init__(self, name: str = "workflow", level: LogLevel = LogLevel.INFO):
        self.name = name
        self.level = level
        self._logs: List[Dict[str, Any]] = []
    
    def _log(self, level: LogLevel, message: str) -> None:
        """记录日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "message": message,
        }
        self._logs.append(log_entry)
        
        # 打印到控制台
        print(f"[{log_entry['timestamp']}] [{level.value}] {message}")
    
    def debug(self, message: str) -> None:
        if self.level == LogLevel.DEBUG:
            self._log(LogLevel.DEBUG, message)
    
    def info(self, message: str) -> None:
        self._log(LogLevel.INFO, message)
    
    def warning(self, message: str) -> None:
        self._log(LogLevel.WARNING, message)
    
    def error(self, message: str) -> None:
        self._log(LogLevel.ERROR, message)
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """获取所有日志"""
        return self._logs.copy()
    
    def clear(self) -> None:
        """清空日志"""
        self._logs.clear()


class SimpleErrorCollector:
    """简单错误收集器 - 当外部错误追踪库不可用时使用"""
    
    def __init__(self):
        self._errors: List[Dict[str, Any]] = []
    
    def add_error(
        self, 
        error: Exception, 
        step: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """添加错误"""
        self._errors.append({
            "timestamp": datetime.now().isoformat(),
            "type": type(error).__name__,
            "message": str(error),
            "step": step,
            "context": context or {},
        })
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """获取所有错误"""
        return self._errors.copy()
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self._errors) > 0
    
    def clear(self) -> None:
        """清空错误"""
        self._errors.clear()
    
    def get_last_error(self) -> Optional[Dict[str, Any]]:
        """获取最后一个错误"""
        return self._errors[-1] if self._errors else None