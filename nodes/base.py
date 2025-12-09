"""
节点基类

所有 LLM 节点和 Code 节点的基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

try:
    from ..core.logger import NodeLogger, error_collector
except ImportError:
    from core.logger import NodeLogger, error_collector


@dataclass
class NodeResult:
    """节点执行结果"""
    success: bool = False
    text: str = ""
    structured_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 新增: 执行信息
    duration: float = 0.0
    model_used: str = ""
    token_usage: Optional[Dict[str, int]] = None


@dataclass
class CodeNodeResult:
    """代码节点执行结果"""
    success: bool = False
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    # 新增: 执行信息
    duration: float = 0.0


class BaseNode(ABC):
    """
    LLM 节点基类
    """
    
    # 子类应设置节点名称
    NODE_NAME: str = "base_node"
    
    def __init__(self, llm_client, config):
        self.llm_client = llm_client
        self.config = config
        self.logger = NodeLogger(self.NODE_NAME)
    
    @abstractmethod
    async def execute(self, **kwargs) -> NodeResult:
        """执行节点逻辑"""
        pass
    
    def _log_start(self, input_summary: str = ""):
        """记录开始"""
        self.logger.start(input_summary)
    
    def _log_end(self, result: NodeResult):
        """记录结束"""
        if result.success:
            self.logger.end(success=True)
            
            # 记录结构化输出
            if result.structured_output:
                self.logger.log_structured_output(
                    result.structured_output,
                    schema_name=self.NODE_NAME
                )
            elif result.text:
                self.logger.log_output(result.text[:500], "响应")
        else:
            self.logger.end(success=False, message=result.error or "Unknown error")
    
    def _log_llm_call(self, prompt: str, model: str = ""):
        """记录 LLM 调用"""
        self.logger.debug(f"Prompt length: {len(prompt)} chars")
        if not model:
            model = getattr(self.llm_client, 'model_name', 'unknown')
        self.logger.info(f"Calling LLM: {model}")
    
    def _log_llm_response(self, response: Any, model: str = ""):
        """记录 LLM 响应"""
        if not model:
            model = getattr(self.llm_client, 'model_name', 'unknown')
        self.logger.log_llm_response(response, model)


class BaseCodeNode(ABC):
    """
    代码节点基类
    """
    
    NODE_NAME: str = "base_code_node"
    
    def __init__(self):
        self.logger = NodeLogger(self.NODE_NAME)
    
    @abstractmethod
    def execute(self, **kwargs) -> CodeNodeResult:
        """执行计算逻辑"""
        pass
    
    def _log_start(self, input_summary: str = ""):
        """记录开始"""
        self.logger.start(input_summary)
    
    def _log_end(self, result: CodeNodeResult):
        """记录结束"""
        if result.success:
            self.logger.end(success=True)
            self.logger.log_code_result(result.result)
        else:
            self.logger.end(success=False, message=result.error or "Unknown error")
    
    def _log_calculation(self, name: str, value: Any):
        """记录中间计算结果"""
        self.logger.info(f"{name}: {value}")