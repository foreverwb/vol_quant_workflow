"""
Schemas 模块
集中管理所有 LLM 节点的 JSON Schema 定义

使用方法:
    from schemas import get_schema, list_schemas, validate_against_schema
    
    # 获取 schema 字典
    schema = get_schema("data_validator")
    
    # 验证数据
    is_valid, errors = validate_against_schema(data, "data_validator")
    
    # 列出所有可用 schemas
    available = list_schemas()  # ['data_validator', 'probability_calibrator', ...]

添加新 Schema:
    1. 在 schemas/ 目录创建新文件 (如 my_node.py)
    2. 使用 register_schema() 注册:
       
       from .base import SchemaDefinition, register_schema
       
       MY_SCHEMA = register_schema(SchemaDefinition(
           name="my_node",
           schema={...}
       ))
    
    3. 在此 __init__.py 中导入该模块
"""

# 基础类和工具
from .base import (
    SchemaDefinition,
    SchemaRegistry,
    register_schema,
    get_schema,
    get_schema_definition,
    validate_against_schema,
    registry,
    # 类型辅助
    TYPE_STRING,
    TYPE_NUMBER,
    TYPE_INTEGER,
    TYPE_BOOLEAN,
    TYPE_ARRAY,
    TYPE_OBJECT,
    nullable,
    enum_type,
    number_range,
)

# 导入各个 schema 模块（触发注册）
from . import data_validator
from . import probability_calibrator
from . import strategy_mapper

# 便捷访问各个 schema 定义
from .data_validator import DATA_VALIDATOR_SCHEMA
from .probability_calibrator import PROBABILITY_CALIBRATOR_SCHEMA
from .strategy_mapper import STRATEGY_MAPPER_SCHEMA


def list_schemas() -> list:
    """列出所有已注册的 schema 名称"""
    return registry.list_names()


def get_all_schemas() -> dict:
    """获取所有已注册的 schemas"""
    return registry.list_all()


__all__ = [
    # 基础类
    "SchemaDefinition",
    "SchemaRegistry",
    "register_schema",
    "get_schema",
    "get_schema_definition",
    "validate_against_schema",
    "list_schemas",
    "get_all_schemas",
    # 类型辅助
    "TYPE_STRING",
    "TYPE_NUMBER",
    "TYPE_INTEGER", 
    "TYPE_BOOLEAN",
    "TYPE_ARRAY",
    "TYPE_OBJECT",
    "nullable",
    "enum_type",
    "number_range",
    # Schema 定义
    "DATA_VALIDATOR_SCHEMA",
    "PROBABILITY_CALIBRATOR_SCHEMA",
    "STRATEGY_MAPPER_SCHEMA",
]
