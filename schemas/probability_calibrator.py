"""
ProbabilityCalibrator 节点 Schema (#6001)
概率校准结果的 JSON Schema 定义

v2.0 更新：
- 新增 confidence_long/confidence_short 分开置信度
- 新增 adjustments_applied
- decision_gate 结构重构
- 新增 risk_flags
- 枚举值改为英文
"""
from .base import SchemaDefinition, register_schema


PROBABILITY_CALIBRATOR_SCHEMA = register_schema(SchemaDefinition(
    name="probability_calibrator",
    description="概率校准与决策门控结果",
    version="2.0",
    
    schema={
        "type": "object",
        "required": ["probability_calibration", "decision_gate"],
        "properties": {
            "probability_calibration": {
                "type": "object",
                "required": ["p_long", "p_short"],
                "description": "概率校准结果",
                "properties": {
                    "p_long": {
                        "type": "number",
                        "description": "做多波动率概率 (0-1)"
                    },
                    "p_short": {
                        "type": "number",
                        "description": "做空波动率概率 (0-1)"
                    },
                    "confidence_long": {
                        "type": "string",
                        "enum": ["high", "medium-high", "medium", "low", "very-low"],
                        "description": "做多概率置信度"
                    },
                    "confidence_short": {
                        "type": "string",
                        "enum": ["high", "medium-high", "medium", "low", "very-low"],
                        "description": "做空概率置信度"
                    },
                    "adjustments_applied": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "应用的调整因子列表"
                    }
                }
            },
            "decision_gate": {
                "type": "object",
                "required": ["final_direction"],
                "description": "决策门控结果",
                "properties": {
                    "final_direction": {
                        "type": "string",
                        "enum": ["LONG_VOL", "SHORT_VOL", "NEUTRAL"],
                        "description": "最终方向判定"
                    },
                    "primary_score": {
                        "type": "number",
                        "description": "主要评分值 (L 或 S)"
                    },
                    "primary_prob": {
                        "type": "number",
                        "description": "主要概率值"
                    },
                    "decision_path": {
                        "type": "string",
                        "description": "决策路径说明"
                    },
                    "conflicts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "信号冲突说明"
                    },
                    "override_reason": {
                        "type": "string",
                        "description": "特殊覆盖原因（如有）"
                    }
                }
            },
            "risk_flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "风险标记列表 (如 Squeeze, EarningsWeek, CrashRisk)"
            }
        }
    }
))


def get_probability_calibrator_schema():
    """获取 ProbabilityCalibrator schema 字典"""
    return PROBABILITY_CALIBRATOR_SCHEMA.schema