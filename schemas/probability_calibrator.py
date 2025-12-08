"""
ProbabilityCalibrator 节点 Schema (#6001)
概率校准结果的 JSON Schema 定义
"""
from .base import SchemaDefinition, register_schema


PROBABILITY_CALIBRATOR_SCHEMA = register_schema(SchemaDefinition(
    name="probability_calibrator",
    description="概率校准与决策门控结果",
    version="1.0",
    
    schema={
        "type": "object",
        "required": ["symbol", "probability_calibration", "decision_gate"],
        "properties": {
            "symbol": {
                "type": "string",
                "description": "标的代码"
            },
            "probability_calibration": {
                "type": "object",
                "required": ["p_long", "p_short", "method"],
                "properties": {
                    "p_long": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "做多波动率概率"
                    },
                    "p_short": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "做空波动率概率"
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "概率置信度"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["冷启动先验", "历史回测", "Platt_scaling"],
                        "description": "概率标定方法"
                    },
                    "rationale": {
                        "type": "string",
                        "description": "概率判断理由"
                    }
                }
            },
            "decision_gate": {
                "type": "object",
                "required": ["long_vol_pass", "short_vol_pass", "final_direction"],
                "properties": {
                    "long_vol_pass": {
                        "type": "boolean",
                        "description": "做多波动率是否通过门槛"
                    },
                    "short_vol_pass": {
                        "type": "boolean",
                        "description": "做空波动率是否通过门槛"
                    },
                    "final_direction": {
                        "type": "string",
                        "enum": ["做多波动率", "做空波动率", "观望"],
                        "description": "最终方向判定"
                    },
                    "gate_check": {
                        "type": "object",
                        "description": "门槛检查详情",
                        "properties": {
                            "long_score_check": {
                                "type": "string",
                                "description": "做多评分检查结果"
                            },
                            "short_score_check": {
                                "type": "string",
                                "description": "做空评分检查结果"
                            },
                            "prob_check": {
                                "type": "string",
                                "description": "概率检查结果"
                            },
                            "conflict_check": {
                                "type": "string",
                                "description": "冲突检查结果"
                            }
                        }
                    }
                }
            }
        }
    }
))


# 便捷获取 schema 字典
def get_probability_calibrator_schema():
    """获取 ProbabilityCalibrator schema 字典"""
    return PROBABILITY_CALIBRATOR_SCHEMA.schema
