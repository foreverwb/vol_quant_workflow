"""
Core Module - 核心组件
"""

from .context import WorkflowContext, WorkflowStatus
from .client_manager import ClientManager
from .fallback import SimpleLogger, SimpleErrorCollector
from .pipeline import PipelineExecutor
from .result_builder import ResultBuilder
from .meso_handler import MesoHandler

__all__ = [
    # 上下文
    "WorkflowContext",
    "WorkflowStatus",
    
    # 客户端
    "ClientManager",
    
    # 降级方案
    "SimpleLogger",
    "SimpleErrorCollector",
    
    # 流水线
    "PipelineExecutor",
    
    # 结果构建
    "ResultBuilder",
    
    # Meso 处理
    "MesoHandler",
]