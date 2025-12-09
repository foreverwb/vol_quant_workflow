"""
Schema 基类和工具函数
提供 JSON Schema 定义、注册和验证功能

支持 OpenAI Strict Mode 自动转换:
- 自动添加 additionalProperties: false
- 自动将所有属性加入 required
- 自动处理可选字段 (nullable)
"""
from typing import Dict, Any, Optional, Tuple, List, Set
from dataclasses import dataclass, field
import copy


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


# ============================================================
# Strict Mode 转换核心函数
# ============================================================

def make_strict_schema(schema: Dict[str, Any], optional_fields: Optional[Set[str]] = None) -> Dict[str, Any]:
    """
    将普通 JSON Schema 转换为 OpenAI Strict Mode 兼容格式
    
    转换规则:
    1. 所有 object 类型添加 "additionalProperties": false
    2. 所有 object 的 properties 中的字段都加入 required
    3. optional_fields 中的字段类型转换为 nullable (["type", "null"])
    4. 递归处理所有嵌套的 object 和 array
    5. 移除 strict mode 不支持的字段 (如 minimum, maximum, default)
    
    Args:
        schema: 原始 JSON Schema
        optional_fields: 可选字段集合 (这些字段会被标记为 nullable)
                        如果为 None，则从原 schema 推断
    
    Returns:
        转换后的 Strict Mode 兼容 Schema
        
    Example:
        >>> schema = {
        ...     "type": "object",
        ...     "required": ["name"],
        ...     "properties": {
        ...         "name": {"type": "string"},
        ...         "age": {"type": "number"}
        ...     }
        ... }
        >>> strict = make_strict_schema(schema)
        >>> # age 不在 required 中，会被转换为 nullable
        >>> strict["properties"]["age"]["type"]
        ['number', 'null']
    """
    return _transform_schema(copy.deepcopy(schema), optional_fields, path="root")


def _transform_schema(
    schema: Dict[str, Any], 
    optional_fields: Optional[Set[str]] = None,
    path: str = "root"
) -> Dict[str, Any]:
    """
    递归转换 schema 节点
    
    Args:
        schema: 当前节点
        optional_fields: 全局可选字段集合
        path: 当前路径 (用于调试)
    """
    schema_type = schema.get("type")
    
    if schema_type == "object":
        return _transform_object(schema, optional_fields, path)
    elif schema_type == "array":
        return _transform_array(schema, optional_fields, path)
    else:
        # 基础类型，移除不支持的字段
        return _clean_basic_type(schema)


def _transform_object(
    schema: Dict[str, Any],
    optional_fields: Optional[Set[str]] = None,
    path: str = "root"
) -> Dict[str, Any]:
    """
    转换 object 类型的 schema
    """
    properties = schema.get("properties", {})
    original_required = set(schema.get("required", []))
    
    # 1. 添加 additionalProperties: false
    schema["additionalProperties"] = False
    
    # 2. 计算哪些字段是可选的
    all_props = set(properties.keys())
    
    if optional_fields is not None:
        # 使用显式指定的可选字段
        nullable_fields = optional_fields & all_props
    else:
        # 推断: 不在 required 中的字段为可选
        nullable_fields = all_props - original_required
    
    # 3. 将所有属性加入 required
    schema["required"] = list(all_props)
    
    # 4. 递归处理每个属性
    new_properties = {}
    for prop_name, prop_schema in properties.items():
        new_path = f"{path}.{prop_name}"
        
        # 递归转换
        transformed = _transform_schema(prop_schema, None, new_path)
        
        # 如果是可选字段，转换为 nullable
        if prop_name in nullable_fields:
            transformed = _make_nullable(transformed)
        
        new_properties[prop_name] = transformed
    
    schema["properties"] = new_properties
    
    return schema


def _transform_array(
    schema: Dict[str, Any],
    optional_fields: Optional[Set[str]] = None,
    path: str = "root"
) -> Dict[str, Any]:
    """
    转换 array 类型的 schema
    """
    items = schema.get("items")
    if items and isinstance(items, dict):
        schema["items"] = _transform_schema(items, optional_fields, f"{path}[]")
    
    return schema


def _make_nullable(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 schema 转换为 nullable 类型
    
    策略:
    - 简单类型 {"type": "string"} -> {"type": ["string", "null"]}
    - 枚举类型 {"type": "string", "enum": [...]} -> {"type": ["string", "null"], "enum": [..., null]}
    - 复杂类型 使用原样返回 (object/array 一般不需要 nullable)
    """
    schema_type = schema.get("type")
    
    # 已经是 nullable
    if isinstance(schema_type, list) and "null" in schema_type:
        return schema
    
    # 简单类型
    if isinstance(schema_type, str) and schema_type not in ("object", "array"):
        schema["type"] = [schema_type, "null"]
        
        # 如果有 enum，需要添加 null 到枚举值
        if "enum" in schema:
            enum_values = schema["enum"]
            if None not in enum_values:
                schema["enum"] = enum_values + [None]
    
    return schema


def _clean_basic_type(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    清理基础类型中 strict mode 不支持的字段
    
    不支持的字段:
    - minimum, maximum (数值范围)
    - minLength, maxLength (字符串长度)
    - pattern (正则)
    - default (默认值)
    - format (格式)
    """
    unsupported_keys = {
        "minimum", "maximum", 
        "minLength", "maxLength",
        "pattern", "default", "format",
        "exclusiveMinimum", "exclusiveMaximum"
    }
    
    for key in unsupported_keys:
        schema.pop(key, None)
    
    return schema


# ============================================================
# 公共 API
# ============================================================

def get_schema(name: str, strict: bool = True) -> Dict[str, Any]:
    """
    获取已注册的 schema 字典
    
    Args:
        name: schema 名称
        strict: 是否转换为 strict mode (默认 True)
        
    Returns:
        JSON Schema 字典
        
    Raises:
        KeyError: 如果 schema 不存在
    """
    schema_def = registry.get(name)
    if schema_def is None:
        available = registry.list_names()
        raise KeyError(f"Schema '{name}' not found. Available: {available}")
    
    schema = schema_def.schema
    
    if strict:
        return make_strict_schema(schema)
    
    return copy.deepcopy(schema)


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
        schema = get_schema(schema_name, strict=False)  # 验证用原始 schema
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
        schema = get_schema(schema_name, strict=False)
    except KeyError as e:
        return False, [str(e)]
    
    errors = []
    required = schema.get("required", [])
    
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    return len(errors) == 0, errors


# ============================================================
# 常用 schema 类型定义（便于复用）
# ============================================================

TYPE_STRING = {"type": "string"}
TYPE_NUMBER = {"type": "number"}
TYPE_INTEGER = {"type": "integer"}
TYPE_BOOLEAN = {"type": "boolean"}
TYPE_ARRAY = {"type": "array"}
TYPE_OBJECT = {"type": "object"}


def nullable(type_def: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建可空类型
    
    Args:
        type_def: 原始类型定义，如 {"type": "string"}
        
    Returns:
        可空类型定义
        
    Example:
        nullable({"type": "string"}) -> {"type": ["string", "null"]}
    """
    return _make_nullable(copy.deepcopy(type_def))


def enum_type(values: List[str], description: str = "") -> Dict[str, Any]:
    """创建枚举类型"""
    result = {"type": "string", "enum": values}
    if description:
        result["description"] = description
    return result


def number_range(min_val: float = None, max_val: float = None, description: str = "") -> Dict[str, Any]:
    """
    创建带范围的数字类型
    
    注意: minimum/maximum 在 strict mode 下会被移除，
    但在原始 schema 验证时仍然有效
    """
    result = {"type": "number"}
    if min_val is not None:
        result["minimum"] = min_val
    if max_val is not None:
        result["maximum"] = max_val
    if description:
        result["description"] = description
    return result