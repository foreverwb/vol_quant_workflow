"""
LLM 节点基类
提供通用的节点执行框架
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import json


@dataclass
class NodeResult:
    """节点执行结果"""
    success: bool
    text: str = ""
    structured_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMNodeBase(ABC):
    """
    LLM 节点基类
    
    所有 LLM 节点继承此类并实现 execute 方法
    """
    
    def __init__(self, llm_client, workflow_config=None):
        """
        初始化节点
        
        Args:
            llm_client: LLM 客户端实例
            workflow_config: 工作流配置
        """
        self.client = llm_client
        self.config = workflow_config
        self._name = self.__class__.__name__
    
    @property
    def name(self) -> str:
        """节点名称"""
        return self._name
    
    @abstractmethod
    async def execute(self, **kwargs) -> NodeResult:
        """
        执行节点逻辑
        
        Args:
            **kwargs: 节点特定参数
            
        Returns:
            NodeResult 实例
        """
        pass
    
    def execute_sync(self, **kwargs) -> NodeResult:
        """同步执行节点"""
        import asyncio
        return asyncio.run(self.execute(**kwargs))
    
    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析 JSON 响应
        
        Args:
            text: LLM 响应文本
            
        Returns:
            解析后的字典，失败返回 None
        """
        try:
            # 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        import re
        json_patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'\{[\s\S]*\}'
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    json_str = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if self.config is None:
            return default
        return getattr(self.config, key, default)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class CodeNodeBase(ABC):
    """
    代码节点基类
    
    所有纯计算节点继承此类
    """
    
    def __init__(self, workflow_config=None):
        self.config = workflow_config
        self._name = self.__class__.__name__
    
    @property
    def name(self) -> str:
        return self._name
    
    @abstractmethod
    def execute(self, **kwargs) -> NodeResult:
        """执行计算逻辑"""
        pass
    
    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if self.config is None:
            return default
        return getattr(self.config, key, default)


class NodeFactory:
    """
    节点工厂
    用于动态创建节点实例
    """
    _registry: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, node_class: type) -> None:
        """注册节点类"""
        cls._registry[name] = node_class
    
    @classmethod
    def create(cls, name: str, *args, **kwargs) -> LLMNodeBase:
        """创建节点实例"""
        if name not in cls._registry:
            raise ValueError(f"Unknown node type: {name}. Available: {list(cls._registry.keys())}")
        return cls._registry[name](*args, **kwargs)
    
    @classmethod
    def list_available(cls) -> List[str]:
        """列出所有可用节点"""
        return list(cls._registry.keys())


def register_node(name: str):
    """
    节点注册装饰器
    
    Example:
        @register_node("router")
        class RouterNode(LLMNodeBase):
            ...
    """
    def decorator(cls):
        NodeFactory.register(name, cls)
        return cls
    return decorator
