"""
Prompt 模板基类
提供模板变量替换、条件渲染和格式化功能
"""
from dataclasses import dataclass, field
from string import Template
from typing import Dict, Any, Optional, List, Callable
import re
import json


@dataclass
class PromptTemplate:
    """
    Prompt 模板类
    
    支持功能：
    - 变量替换: ${variable}
    - 默认值: ${variable:default_value}
    - JSON序列化: 自动将dict/list转为JSON字符串
    - 条件渲染: 空值自动省略对应段落
    
    Attributes:
        name: 模板名称标识
        description: 模板描述
        system: 系统提示词模板
        user: 用户提示词模板
        variables: 模板中使用的变量说明
        defaults: 变量默认值
    
    Example:
        >>> template = PromptTemplate(
        ...     name="greeting",
        ...     system="你是一个助手",
        ...     user="你好, ${name}!",
        ...     defaults={"name": "用户"}
        ... )
        >>> template.format_user()  # 使用默认值
        '你好, 用户!'
        >>> template.format_user(name="世界")  # 覆盖默认值
        '你好, 世界!'
    """
    name: str
    system: str
    user: str
    description: str = ""
    variables: Dict[str, str] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    
    def _serialize_value(self, value: Any) -> str:
        """将值序列化为字符串"""
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return str(value)
    
    def _apply_defaults(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """应用默认值"""
        result = self.defaults.copy()
        result.update(kwargs)
        return result
    
    def _render_template(self, template: str, **kwargs) -> str:
        """
        渲染模板
        
        支持：
        1. 标准变量替换 ${var}
        2. 带默认值的变量 ${var:default}
        3. 自动序列化 dict/list
        4. 清理未替换的空变量
        """
        # 应用默认值
        context = self._apply_defaults(kwargs)
        
        # 序列化复杂类型
        serialized = {k: self._serialize_value(v) for k, v in context.items()}
        
        # 先处理带默认值的变量 ${var:default}
        def replace_with_default(match):
            var_name = match.group(1)
            default_val = match.group(2)
            return serialized.get(var_name) or default_val
        
        result = re.sub(r'\$\{(\w+):([^}]*)\}', replace_with_default, template)
        
        # 再处理标准变量
        result = Template(result).safe_substitute(**serialized)
        
        # 清理残留的空变量标记
        result = re.sub(r'\$\{?\w+\}?', '', result)
        
        # 清理多余空行（超过2个连续空行合并为2个）
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()
    
    def format_system(self, **kwargs) -> str:
        """
        格式化系统提示词
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            格式化后的系统提示词
        """
        return self._render_template(self.system, **kwargs)
    
    def format_user(self, **kwargs) -> str:
        """
        格式化用户提示词
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            格式化后的用户提示词
        """
        return self._render_template(self.user, **kwargs)
    
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
    
    def to_messages(self, **kwargs) -> List[Dict[str, str]]:
        """
        转换为消息列表格式（适配 OpenAI API）
        
        Returns:
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        formatted = self.format(**kwargs)
        messages = []
        if formatted["system"]:
            messages.append({"role": "system", "content": formatted["system"]})
        if formatted["user"]:
            messages.append({"role": "user", "content": formatted["user"]})
        return messages
    
    def get_variable_names(self) -> List[str]:
        """获取模板中的变量名列表"""
        pattern = r'\$\{(\w+)(?::[^}]*)?\}|\$(\w+)'
        system_vars = re.findall(pattern, self.system)
        user_vars = re.findall(pattern, self.user)
        # 合并并去重
        all_vars = set()
        for match in system_vars + user_vars:
            var = match[0] or match[1]
            if var:
                all_vars.add(var)
        return sorted(list(all_vars))
    
    def validate_variables(self, **kwargs) -> List[str]:
        """
        验证是否提供了所有必需变量
        
        Returns:
            缺失的变量名列表（空列表表示验证通过）
        """
        required = set(self.get_variable_names())
        provided = set(kwargs.keys()) | set(self.defaults.keys())
        missing = required - provided
        return sorted(list(missing))
    
    def __repr__(self) -> str:
        return f"PromptTemplate(name='{self.name}', vars={self.get_variable_names()})"


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
    
    def list_names(self) -> List[str]:
        """列出所有已注册的 prompt 名称"""
        return list(self._prompts.keys())
    
    def list_all(self) -> Dict[str, PromptTemplate]:
        """获取所有已注册的 prompts"""
        return self._prompts.copy()
    
    def describe(self) -> str:
        """生成所有 prompt 的描述文档"""
        lines = ["# Registered Prompts\n"]
        for name, prompt in sorted(self._prompts.items()):
            lines.append(f"## {name}")
            lines.append(f"- Description: {prompt.description}")
            lines.append(f"- Variables: {prompt.get_variable_names()}")
            lines.append("")
        return "\n".join(lines)


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


def format_prompt(name: str, **kwargs) -> Dict[str, str]:
    """
    便捷函数：获取并格式化 prompt
    
    Args:
        name: prompt 名称
        **kwargs: 模板变量
        
    Returns:
        {"system": "...", "user": "..."}
    """
    return get_prompt(name).format(**kwargs)