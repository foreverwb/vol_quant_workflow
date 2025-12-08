"""
Schema 基类和工具函数
提供 JSON Schema 定义、注册和验证功能
"""
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field


@dataclass
class SchemaDefinition:
    """
    Schema 定义类
    
    Attributes:
        name: Schema 名称标识
        description: Schema 描述
        schema: JSON Schema 字典
        version: Schema 版本
    """
    name: str
    schema: Dict[str, Any]
    description: str = ""
    version: str = "1.0"
    
    def get_required_fields(self) -> List[str]:
        """获取必需字段列表"""
        return self.schema.get("required", [])
    
    def get_properties(self) -> Dict[str, Any]:
        """获取属性定义"""
        return self.schema.get("properties", {})
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.schema.copy()


class SchemaRegistry:
    """
    Schema 注册表
    集中管理所有 JSON Schema
    """
    _instance: Optional['SchemaRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._schemas = {}
        return cls._instance
    
    def register(self, schema_def: SchemaDefinition) -> None:
        """注册 schema"""
        self._schemas[schema_def.name] = schema_def
    
    def get(self, name: str) -> Optional[SchemaDefinition]:
        """获取 schema 定义"""
        return self._schemas.get(name)
    
    def get_schema(self, name: str) -> Dict[str, Any]:
        """获取 schema 字典"""
        schema_def = self.get(name)
        return schema_def.schema if schema_def else {}
    
    def list_names(self) -> List[str]:
        """列出所有已注册的 schema 名称"""
        return list(self._schemas.keys())
    
    def list_all(self) -> Dict[str, SchemaDefinition]:
        """获取所有已注册的 schemas"""
        return self._schemas.copy()


# 全局注册表实例
registry = SchemaRegistry()


def register_schema(schema_def: SchemaDefinition) -> SchemaDefinition:
    """
    注册 schema 的装饰器/函数
    
    Example:
        DATA_VALIDATOR_SCHEMA = register_schema(SchemaDefinition(
            name="data_validator",
            schema={...}
        ))
    """
    registry.register(schema_def)
    return schema_def


def get_schema(name: str) -> Dict[str, Any]:
    """
    获取已注册的 schema 字典
    
    Args:
        name: schema 名称
        
    Returns:
        JSON Schema 字典
        
    Raises:
        KeyError: 如果 schema 不存在
    """
    schema_def = registry.get(name)
    if schema_def is None:
        available = registry.list_names()
        raise KeyError(f"Schema '{name}' not found. Available: {available}")
    return schema_def.schema


def get_schema_definition(name: str) -> SchemaDefinition:
    """获取 schema 定义对象"""
    schema_def = registry.get(name)
    if schema_def is None:
        available = registry.list_names()
        raise KeyError(f"Schema '{name}' not found. Available: {available}")
    return schema_def


def validate_against_schema(data: dict, schema_name: str) -> Tuple[bool, List[str]]:
    """
    验证数据是否符合 schema
    
    Args:
        data: 待验证的数据
        schema_name: schema 名称
        
    Returns:
        (is_valid, errors) 元组
    """
    try:
        import jsonschema
        schema = get_schema(schema_name)
        jsonschema.validate(instance=data, schema=schema)
        return True, []
    except ImportError:
        # jsonschema 未安装时进行简单验证
        return _simple_validate(data, schema_name)
    except Exception as e:
        return False, [str(e)]


def _simple_validate(data: dict, schema_name: str) -> Tuple[bool, List[str]]:
    """简单验证（不依赖 jsonschema）"""
    try:
        schema = get_schema(schema_name)
    except KeyError as e:
        return False, [str(e)]
    
    errors = []
    required = schema.get("required", [])
    
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    return len(errors) == 0, errors


# 常用 schema 类型定义（便于复用）
TYPE_STRING = {"type": "string"}
TYPE_NUMBER = {"type": "number"}
TYPE_INTEGER = {"type": "integer"}
TYPE_BOOLEAN = {"type": "boolean"}
TYPE_ARRAY = {"type": "array"}
TYPE_OBJECT = {"type": "object"}


def nullable(type_def: Dict[str, Any]) -> Dict[str, Any]:
    """创建可空类型"""
    return {"anyOf": [type_def, {"type": "null"}]}


def enum_type(values: List[str], description: str = "") -> Dict[str, Any]:
    """创建枚举类型"""
    result = {"type": "string", "enum": values}
    if description:
        result["description"] = description
    return result


def number_range(min_val: float = None, max_val: float = None, description: str = "") -> Dict[str, Any]:
    """创建带范围的数字类型"""
    result = {"type": "number"}
    if min_val is not None:
        result["minimum"] = min_val
    if max_val is not None:
        result["maximum"] = max_val
    if description:
        result["description"] = description
    return result
