"""
Prompts 模块
集中管理所有 LLM 节点的 prompt 模板

使用方法:
    from prompts import get_prompt, list_prompts
    
    # 获取单个 prompt
    router_prompt = get_prompt("router")
    
    # 格式化 prompt
    formatted = router_prompt.format_user(user_input="NVDA 财报 5-20DTE")
    
    # 列出所有可用 prompts
    available = list_prompts()  # ['router', 'command_generator', ...]

添加新 Prompt:
    1. 在 prompts/ 目录创建新文件 (如 my_node.py)
    2. 使用 register_prompt() 注册:
       
       from .base import PromptTemplate, register_prompt
       
       MY_PROMPT = register_prompt(PromptTemplate(
           name="my_node",
           system="...",
           user="..."
       ))
    
    3. 在此 __init__.py 中导入该模块
"""

# 基础类和工具
from .base import (
    PromptTemplate,
    PromptRegistry,
    register_prompt,
    get_prompt,
    registry,
)

# 导入各个 prompt 模块（触发注册）
from . import router
from . import command_generator
from . import data_validator
from . import probability_calibrator
from . import strategy_mapper
from . import final_report

# 便捷访问各个 prompt 常量
from .router import ROUTER_PROMPT
from .command_generator import COMMAND_GENERATOR_PROMPT
from .data_validator import DATA_VALIDATOR_PROMPT
from .probability_calibrator import PROBABILITY_CALIBRATOR_PROMPT
from .strategy_mapper import STRATEGY_MAPPER_PROMPT
from .final_report import FINAL_REPORT_PROMPT


def list_prompts() -> list:
    """列出所有已注册的 prompt 名称"""
    return registry.list_names()


def get_all_prompts() -> dict:
    """获取所有已注册的 prompts"""
    return registry.list_all()


__all__ = [
    # 基础类
    "PromptTemplate",
    "PromptRegistry",
    "register_prompt",
    "get_prompt",
    "list_prompts",
    "get_all_prompts",
    # Prompt 常量
    "ROUTER_PROMPT",
    "COMMAND_GENERATOR_PROMPT",
    "DATA_VALIDATOR_PROMPT",
    "PROBABILITY_CALIBRATOR_PROMPT",
    "STRATEGY_MAPPER_PROMPT",
    "FINAL_REPORT_PROMPT",
]
