"""
节点基类

所有 LLM 节点和 Code 节点的基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Type

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


# ============================================================
# 节点注册表
# ============================================================

class NodeFactory:
    """
    节点工厂 - 管理节点注册和创建
    """
    _instance: Optional['NodeFactory'] = None
    _registry: Dict[str, Type['LLMNodeBase']]
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = {}
        return cls._instance
    
    def register(self, name: str, node_class: Type['LLMNodeBase']) -> None:
        """注册节点类"""
        self._registry[name] = node_class
    
    def get(self, name: str) -> Optional[Type['LLMNodeBase']]:
        """获取节点类"""
        return self._registry.get(name)
    
    def create(self, name: str, client: Any, config: Any) -> Optional['LLMNodeBase']:
        """创建节点实例"""
        node_class = self.get(name)
        if node_class:
            return node_class(client, config)
        return None
    
    def list_nodes(self) -> List[str]:
        """列出所有已注册的节点"""
        return list(self._registry.keys())


# 全局工厂实例
_factory = NodeFactory()


def register_node(name: str):
    """
    节点注册装饰器
    
    Usage:
        @register_node("router")
        class RouterNode(LLMNodeBase):
            ...
    """
    def decorator(cls: Type['LLMNodeBase']) -> Type['LLMNodeBase']:
        _factory.register(name, cls)
        return cls
    return decorator


def get_node_factory() -> NodeFactory:
    """获取节点工厂实例"""
    return _factory


# ============================================================
# LLM 节点基类
# ============================================================

class LLMNodeBase(ABC):
    """
    LLM 节点基类
    
    所有需要调用 LLM 的节点都应继承此类
    """
    
    # 子类应设置节点名称
    NODE_NAME: str = "base_llm_node"
    
    def __init__(self, client: Any, config: Any):
        """
        初始化 LLM 节点
        
        Args:
            client: LLM 客户端实例
            config: 工作流配置
        """
        self.client = client
        self.config = config
        self.logger = NodeLogger(self.NODE_NAME)
    
    @abstractmethod
    async def execute(self, **kwargs) -> NodeResult:
        """执行节点逻辑 - 子类必须实现"""
        pass
    
    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """从配置中获取值"""
        if hasattr(self.config, key):
            return getattr(self.config, key)
        return default
    
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
            model = getattr(self.client, 'model_name', 'unknown')
        self.logger.info(f"Calling LLM: {model}")
    
    def _log_llm_response(self, response: Any, model: str = ""):
        """记录 LLM 响应"""
        if not model:
            model = getattr(self.client, 'model_name', 'unknown')
        self.logger.log_llm_response(response, model)


# 向后兼容别名
BaseNode = LLMNodeBase


# ============================================================
# 代码节点基类
# ============================================================

class CodeNodeBase(ABC):
    """
    代码节点基类
    
    用于纯计算类节点，不涉及 LLM 调用
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


# 向后兼容别名
BaseCodeNode = CodeNodeBase