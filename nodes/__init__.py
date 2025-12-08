"""
Nodes 模块
包含所有 LLM 节点和代码节点

使用方法:
    from nodes import RouterNode, CommandGeneratorNode, ...
    from nodes import NodeFactory
    from nodes.code import code1_feature_calculation, code2_signal_scoring, ...

添加新 LLM 节点:
    1. 在 nodes/ 目录创建新文件 (如 my_node.py)
    2. 继承 LLMNodeBase 并实现 execute 方法
    3. 使用 @register_node 装饰器注册
    4. 在此 __init__.py 中导入该模块

添加新代码节点:
    1. 在 nodes/code/ 目录创建新文件
    2. 实现计算函数，返回 CodeNodeResult
    3. 在 nodes/code/__init__.py 中导出
"""

# 基础类
from .base import (
    NodeResult,
    LLMNodeBase,
    CodeNodeBase,
    NodeFactory,
    register_node,
)

# LLM 节点（导入触发注册）
from .router import RouterNode
from .command_generator import CommandGeneratorNode
from .data_validator import DataValidatorNode
from .probability_calibrator import ProbabilityCalibratorNode
from .strategy_mapper import StrategyMapperNode
from .final_report import FinalReportNode

# 代码节点
from .code import CodeNodeResult
from .code.feature_calc import code1_feature_calculation
from .code.signal_scoring import code2_signal_scoring
from .code.strike_calc import code3_strike_calculation
from .code.edge_estimation import code4_edge_estimation


# 兼容性别名
LLMNodeResult = NodeResult


__all__ = [
    # 基础类
    "NodeResult",
    "LLMNodeResult",
    "LLMNodeBase",
    "CodeNodeBase",
    "NodeFactory",
    "register_node",
    # LLM 节点
    "RouterNode",
    "CommandGeneratorNode",
    "DataValidatorNode",
    "ProbabilityCalibratorNode",
    "StrategyMapperNode",
    "FinalReportNode",
    # 代码节点
    "CodeNodeResult",
    "code1_feature_calculation",
    "code2_signal_scoring",
    "code3_strike_calculation",
    "code4_edge_estimation",
]
