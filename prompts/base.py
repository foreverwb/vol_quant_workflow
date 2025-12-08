"""
Prompt 模板基类
提供模板变量替换和格式化功能
"""
from dataclasses import dataclass, field
from string import Template
from typing import Dict, Any, Optional


@dataclass
class PromptTemplate:
    """
    Prompt 模板类
    
    Attributes:
        name: 模板名称标识
        description: 模板描述
        system: 系统提示词模板
        user: 用户提示词模板
        variables: 模板中使用的变量说明
    
    Example:
        >>> template = PromptTemplate(
        ...     name="greeting",
        ...     system="你是一个助手",
        ...     user="你好, ${name}!"
        ... )
        >>> template.format_user(name="世界")
        '你好, 世界!'
    """
    name: str
    system: str
    user: str
    description: str = ""
    variables: Dict[str, str] = field(default_factory=dict)
    
    def format_system(self, **kwargs) -> str:
        """
        格式化系统提示词
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            格式化后的系统提示词
        """
        return Template(self.system).safe_substitute(**kwargs)
    
    def format_user(self, **kwargs) -> str:
        """
        格式化用户提示词
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            格式化后的用户提示词
        """
        return Template(self.user).safe_substitute(**kwargs)
    
    def format(self, **kwargs) -> Dict[str, str]:
        """
        同时格式化系统和用户提示词
        
        Returns:
            包含 system 和 user 的字典
        """
        return {
            "system": self.format_system(**kwargs),
            "user": self.format_user(**kwargs)
        }
    
    def get_variable_names(self) -> list:
        """获取模板中的变量名列表"""
        import re
        pattern = r'\$\{(\w+)\}|\$(\w+)'
        system_vars = re.findall(pattern, self.system)
        user_vars = re.findall(pattern, self.user)
        # 合并并去重
        all_vars = set()
        for match in system_vars + user_vars:
            var = match[0] or match[1]
            if var:
                all_vars.add(var)
        return sorted(list(all_vars))


class PromptRegistry:
    """
    Prompt 注册表
    集中管理所有 prompt 模板，支持动态注册和查询
    """
    _instance: Optional['PromptRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._prompts = {}
        return cls._instance
    
    def register(self, prompt: PromptTemplate) -> None:
        """注册 prompt 模板"""
        self._prompts[prompt.name] = prompt
    
    def get(self, name: str) -> Optional[PromptTemplate]:
        """获取 prompt 模板"""
        return self._prompts.get(name)
    
    def list_names(self) -> list:
        """列出所有已注册的 prompt 名称"""
        return list(self._prompts.keys())
    
    def list_all(self) -> Dict[str, PromptTemplate]:
        """获取所有已注册的 prompts"""
        return self._prompts.copy()


# 全局注册表实例
registry = PromptRegistry()


def register_prompt(prompt: PromptTemplate) -> PromptTemplate:
    """
    注册 prompt 的装饰器/函数
    
    Example:
        ROUTER_PROMPT = register_prompt(PromptTemplate(
            name="router",
            system="...",
            user="..."
        ))
    """
    registry.register(prompt)
    return prompt


def get_prompt(name: str) -> PromptTemplate:
    """
    获取已注册的 prompt
    
    Args:
        name: prompt 名称
        
    Returns:
        PromptTemplate 实例
        
    Raises:
        KeyError: 如果 prompt 不存在
    """
    prompt = registry.get(name)
    if prompt is None:
        available = registry.list_names()
        raise KeyError(f"Prompt '{name}' not found. Available: {available}")
    return prompt
