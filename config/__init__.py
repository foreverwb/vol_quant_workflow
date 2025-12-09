"""
配置模块

提供:
- ModelConfig: 模型配置
- WorkflowConfig: 工作流配置
- FileUploadConfig: 文件上传配置
- NodeModelMapping: 节点模型映射
- ModelsConfig: 模型配置管理（从 YAML）
- NodeConfig: 节点配置
"""

# 从父级 config.py 导入核心配置类
import sys
from pathlib import Path

# 手动导入父级 config.py
_parent_dir = Path(__file__).parent.parent
_config_py = _parent_dir / "config.py"

if _config_py.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_config_module", _config_py)
    _config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_config_module)
    
    # 导出核心类
    ModelConfig = _config_module.ModelConfig
    WorkflowConfig = _config_module.WorkflowConfig
    FileUploadConfig = _config_module.FileUploadConfig
    NodeModelMapping = _config_module.NodeModelMapping
    DEFAULT_MODEL_CONFIG = _config_module.DEFAULT_MODEL_CONFIG
    DEFAULT_WORKFLOW_CONFIG = _config_module.DEFAULT_WORKFLOW_CONFIG
    DEFAULT_FILE_CONFIG = _config_module.DEFAULT_FILE_CONFIG
    DEFAULT_NODE_MODEL_MAPPING = _config_module.DEFAULT_NODE_MODEL_MAPPING

# 从 model_config_loader 导入
try:
    from .model_config_loader import (
        ModelsConfig,
        NodeConfig,
        load_models_config,
        get_node_config,
        DEFAULT_CONFIG_PATH,
    )
except ImportError:
    ModelsConfig = None
    NodeConfig = None
    load_models_config = None
    get_node_config = None
    DEFAULT_CONFIG_PATH = None

__all__ = [
    # 核心配置类
    "ModelConfig",
    "WorkflowConfig",
    "FileUploadConfig",
    "NodeModelMapping",
    "DEFAULT_MODEL_CONFIG",
    "DEFAULT_WORKFLOW_CONFIG",
    "DEFAULT_FILE_CONFIG",
    "DEFAULT_NODE_MODEL_MAPPING",
    # YAML 配置类
    "ModelsConfig",
    "NodeConfig", 
    "load_models_config",
    "get_node_config",
    "DEFAULT_CONFIG_PATH",
]