"""
波动率套利策略工作流应用

将 YAML 配置文件转化为可运行的 Python 应用程序。

使用方法:
    # 命令行
    python main.py --input "NVDA 财报 5-20DTE delta-neutral"
    python main.py --files chart1.png chart2.png
    python main.py --folder ./charts --output ./reports
    
    # 编程接口
    from vol_workflow import run_workflow, create_workflow
    
    result = run_workflow(
        files=["chart1.png"],
        api_base="https://api.openai.com/v1",
        api_key="sk-xxx"
    )

模块结构:
    vol_workflow/
    ├── config.py              # 配置管理
    ├── workflow.py            # 工作流引擎
    ├── prompts/               # Prompt 集中管理
    ├── schemas/               # JSON Schema 定义
    ├── nodes/                 # LLM 节点和代码节点
    └── utils/                 # 通用工具
"""

__version__ = "2.0.0"
__author__ = "Vol Quant Team"

# 导出核心类和函数
from .config import ModelConfig, WorkflowConfig, FileUploadConfig
from .workflow import VolatilityWorkflow, BatchProcessor, create_workflow

# 便捷导入
from .prompts import get_prompt, list_prompts
from .schemas import get_schema

# 从 schemas 导入 list_schemas（如果存在）
try:
    from .schemas import list_schemas
except ImportError:
    def list_schemas():
        from .schemas.base import registry
        return registry.list_names()

from .nodes import (
    RouterNode,
    CommandGeneratorNode,
    DataValidatorNode,
    ProbabilityCalibratorNode,
    StrategyMapperNode,
    FinalReportNode,
    code1_feature_calculation,
    code2_signal_scoring,
    code3_strike_calculation,
    code4_edge_estimation,
)


def run_workflow(
    user_input: str = "",
    files: list = None,
    api_base: str = "",
    api_key: str = "",
    model_name: str = "gpt-4o",
    vision_model_name: str = None,
    temperature: float = 0.7,
    output_dir: str = "./outputs"
) -> dict:
    """
    运行工作流的便捷函数
    
    Args:
        user_input: 用户输入文本
        files: 图表文件列表
        api_base: API 基础 URL
        api_key: API 密钥
        model_name: 模型名称
        vision_model_name: 视觉模型名称
        temperature: 温度参数
        output_dir: 输出目录
        
    Returns:
        工作流执行结果
    """
    workflow = create_workflow(
        api_base=api_base,
        api_key=api_key,
        model_name=model_name,
        vision_model_name=vision_model_name,
        temperature=temperature
    )
    
    return workflow.run_sync(user_input=user_input, files=files)


__all__ = [
    # 版本
    "__version__",
    # 配置
    "ModelConfig",
    "WorkflowConfig", 
    "FileUploadConfig",
    # 工作流
    "VolatilityWorkflow",
    "BatchProcessor",
    "create_workflow",
    "run_workflow",
    # Prompt/Schema 工具
    "get_prompt",
    "list_prompts",
    "get_schema",
    "list_schemas",
    # 节点
    "RouterNode",
    "CommandGeneratorNode",
    "DataValidatorNode",
    "ProbabilityCalibratorNode",
    "StrategyMapperNode",
    "FinalReportNode",
    # 代码节点
    "code1_feature_calculation",
    "code2_signal_scoring",
    "code3_strike_calculation",
    "code4_edge_estimation",
]
