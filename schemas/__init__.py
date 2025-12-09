"""
Schema 模块
提供 JSON Schema 定义、注册和验证功能

支持 OpenAI Strict Mode 自动转换
"""
from .base import (
    SchemaDefinition,
    SchemaRegistry,
    registry,
    register_schema,
    make_strict_schema,
    get_schema,
    get_schema_definition,
    validate_against_schema,
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

# 导入各节点 schema (触发注册)
from .data_validator import DATA_VALIDATOR_SCHEMA, get_data_validator_schema
from .probability_calibrator import PROBABILITY_CALIBRATOR_SCHEMA, get_probability_calibrator_schema
from .strategy_mapper import STRATEGY_MAPPER_SCHEMA, get_strategy_mapper_schema


__all__ = [
    # 基础类
    'SchemaDefinition',
    'SchemaRegistry',
    'registry',
    'register_schema',
    
    # 核心函数
    'make_strict_schema',
    'get_schema',
    'get_schema_definition',
    'validate_against_schema',
    
    # 类型辅助
    'TYPE_STRING',
    'TYPE_NUMBER',
    'TYPE_INTEGER',
    'TYPE_BOOLEAN',
    'TYPE_ARRAY',
    'TYPE_OBJECT',
    'nullable',
    'enum_type',
    'number_range',
    
    # 节点 Schema
    'DATA_VALIDATOR_SCHEMA',
    'PROBABILITY_CALIBRATOR_SCHEMA',
    'STRATEGY_MAPPER_SCHEMA',
    
    # 便捷获取函数
    'get_router_schema',
    'get_command_generator_schema',
    'get_data_validator_schema',
    'get_probability_calibrator_schema',
    'get_strategy_mapper_schema',
]