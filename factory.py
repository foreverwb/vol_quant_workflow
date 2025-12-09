"""
Factory - 工作流工厂函数
提供便捷的工作流创建方法
"""

from typing import Optional, Dict, Any, Union
from pathlib import Path
import json
import yaml

from .config import WorkflowConfig, ModelConfig
from .workflow import VolatilityWorkflow


def create_workflow(
    model_name: str = "gpt-4",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    base_url: Optional[str] = None,  # 别名
    max_retries: int = 3,
    timeout: int = 60,
    debug: bool = False,
    vision_model_name: Optional[str] = None,
    temperature: float = 0.7,
    **kwargs,
) -> VolatilityWorkflow:
    """
    创建工作流实例
    
    Args:
        model_name: 模型名称
        api_key: API 密钥（可选，从环境变量读取）
        api_base: API 基础 URL（可选）
        base_url: API 基础 URL 别名
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
        debug: 是否开启调试模式
        vision_model_name: 视觉模型名称
        temperature: 温度参数
        **kwargs: 其他配置参数
    
    Returns:
        VolatilityWorkflow 实例
    """
    # 处理 api_base 别名
    actual_api_base = api_base or base_url or ""
    
    # 创建模型配置
    model_config = ModelConfig(
        name=model_name,
        api_key=api_key or "",
        api_base=actual_api_base,
        timeout=timeout,
        retry_count=max_retries,
        temperature=temperature,
    )
    
    # 创建视觉模型配置（如果指定）
    vision_model_config = None
    if vision_model_name:
        vision_model_config = ModelConfig(
            name=vision_model_name,
            api_key=api_key or "",
            api_base=actual_api_base,
            timeout=timeout,
            retry_count=max_retries,
            temperature=temperature,
            vision_enabled=True,
        )
    
    # 创建工作流配置
    config = WorkflowConfig(
        model_config=model_config,
        vision_model_config=vision_model_config,
        max_retries=max_retries,
        debug=debug,
        **{k: v for k, v in kwargs.items() if hasattr(WorkflowConfig, k)},
    )
    
    return VolatilityWorkflow(config)


def create_workflow_from_config(
    config_path: Union[str, Path],
    overrides: Optional[Dict[str, Any]] = None,
) -> VolatilityWorkflow:
    """
    从配置文件创建工作流
    
    Args:
        config_path: 配置文件路径（支持 JSON/YAML）
        overrides: 覆盖配置项
    
    Returns:
        VolatilityWorkflow 实例
    """
    config_path = Path(config_path)
    
    # 读取配置文件
    if config_path.suffix in (".yaml", ".yml"):
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
    elif config_path.suffix == ".json":
        with open(config_path) as f:
            config_dict = json.load(f)
    else:
        raise ValueError(f"Unsupported config format: {config_path.suffix}")
    
    # 应用覆盖
    if overrides:
        config_dict = _deep_merge(config_dict, overrides)
    
    # 构建配置对象
    config = _build_config_from_dict(config_dict)
    
    return VolatilityWorkflow(config)


def create_workflow_from_env() -> VolatilityWorkflow:
    """
    从环境变量创建工作流
    
    环境变量:
        - VOL_WORKFLOW_MODEL: 模型名称
        - VOL_WORKFLOW_API_KEY: API 密钥
        - VOL_WORKFLOW_BASE_URL: API 基础 URL
        - VOL_WORKFLOW_DEBUG: 是否调试模式
    """
    import os
    
    return create_workflow(
        model_name=os.getenv("VOL_WORKFLOW_MODEL", "gpt-4"),
        api_key=os.getenv("VOL_WORKFLOW_API_KEY"),
        api_base=os.getenv("VOL_WORKFLOW_BASE_URL"),
        debug=os.getenv("VOL_WORKFLOW_DEBUG", "").lower() == "true",
    )


# ==================== 辅助函数 ====================

def _deep_merge(base: Dict, override: Dict) -> Dict:
    """深度合并两个字典"""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def _build_config_from_dict(config_dict: Dict[str, Any]) -> WorkflowConfig:
    """从字典构建配置对象"""
    # 提取模型配置
    model_dict = config_dict.pop("model", {})
    model_config = ModelConfig(
        name=model_dict.get("name", "gpt-4"),
        api_key=model_dict.get("api_key", ""),
        api_base=model_dict.get("base_url", "") or model_dict.get("api_base", ""),
        timeout=model_dict.get("timeout", 60),
        retry_count=model_dict.get("retry_count", 3),
    )
    
    # 构建工作流配置
    return WorkflowConfig(
        model_config=model_config,
        max_retries=config_dict.get("max_retries", 3),
        debug=config_dict.get("debug", False),
        blacklist=config_dict.get("blacklist", []),
        max_position_size=config_dict.get("max_position_size", 100),
        min_edge_threshold=config_dict.get("min_edge_threshold", 0.05),
    )