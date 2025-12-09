"""
StrategyMapper 节点 Schema (#7001)
策略映射结果的 JSON Schema 定义

v2.0 更新：
- direction 枚举值改为英文
- tier 枚举值改为英文
- legs 结构重构 (新增 strike_method, strike_value)
- entry 改为 entry_conditions 数组
- exit 改为 exit_rules 对象
- 新增 rejected_strategies, context_applied, risk_notes
"""
from .base import SchemaDefinition, register_schema


STRATEGY_MAPPER_SCHEMA = register_schema(SchemaDefinition(
    name="strategy_mapper",
    description="策略映射与 Edge 估算结果",
    version="2.0",
    
    schema={
        "type": "object",
        "required": ["direction", "strategies"],
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["LONG_VOL", "SHORT_VOL"],
                "description": "交易方向"
            },
            "strategies": {
                "type": "array",
                "description": "策略列表（1-3个）",
                "items": {
                    "type": "object",
                    "required": ["tier", "name", "structure", "legs", "entry_conditions", "exit_rules", "edge_estimate"],
                    "properties": {
                        "tier": {
                            "type": "string",
                            "enum": ["aggressive", "balanced", "conservative"],
                            "description": "策略档位"
                        },
                        "name": {
                            "type": "string",
                            "description": "策略名称"
                        },
                        "structure": {
                            "type": "string",
                            "description": "策略结构描述"
                        },
                        "legs": {
                            "type": "array",
                            "description": "策略腿",
                            "items": {
                                "type": "object",
                                "required": ["action", "type"],
                                "properties": {
                                    "action": {
                                        "type": "string",
                                        "enum": ["buy", "sell"],
                                        "description": "买卖方向"
                                    },
                                    "type": {
                                        "type": "string",
                                        "enum": ["call", "put"],
                                        "description": "期权类型"
                                    },
                                    "delta": {
                                        "type": "number",
                                        "description": "Delta 值 (如 0.30)"
                                    },
                                    "strike_method": {
                                        "type": "string",
                                        "enum": ["ATM", "Delta", "Wall", "OTM"],
                                        "description": "行权价计算方法"
                                    },
                                    "strike_value": {
                                        "type": "string",
                                        "description": "行权价值或计算方式"
                                    },
                                    "dte": {
                                        "type": "integer",
                                        "description": "到期天数"
                                    }
                                }
                            }
                        },
                        "entry_conditions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "入场条件列表"
                        },
                        "exit_rules": {
                            "type": "object",
                            "description": "退出规则",
                            "properties": {
                                "profit_target": {
                                    "type": "string",
                                    "description": "止盈目标"
                                },
                                "stop_loss": {
                                    "type": "string",
                                    "description": "止损条件"
                                },
                                "time_exit": {
                                    "type": "string",
                                    "description": "时间退出规则"
                                },
                                "regime_change": {
                                    "type": "string",
                                    "description": "Regime 变化退出"
                                }
                            }
                        },
                        "edge_estimate": {
                            "type": "object",
                            "required": ["win_rate", "rr_ratio", "meets_threshold"],
                            "description": "Edge 估算",
                            "properties": {
                                "win_rate": {
                                    "type": "number",
                                    "description": "胜率 (0-1)"
                                },
                                "rr_ratio": {
                                    "type": "string",
                                    "description": "盈亏比 (如 '2:1')"
                                },
                                "expected_value": {
                                    "type": "string",
                                    "enum": ["positive", "negative", "neutral"],
                                    "description": "期望值方向"
                                },
                                "meets_threshold": {
                                    "type": "boolean",
                                    "description": "是否满足 Edge 门槛"
                                }
                            }
                        },
                        "risk_notes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "风险提示"
                        }
                    }
                }
            },
            "rejected_strategies": {
                "type": "array",
                "description": "被拒绝的策略列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "策略名称"
                        },
                        "reason": {
                            "type": "string",
                            "description": "拒绝原因"
                        }
                    }
                }
            },
            "context_applied": {
                "type": "object",
                "description": "应用的上下文",
                "properties": {
                    "dte_range": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "DTE 范围 [min, max]"
                    },
                    "delta_bias": {
                        "type": "string",
                        "enum": ["neutral", "bullish", "bearish"],
                        "description": "Delta 偏好"
                    },
                    "blacklist_checked": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "已检查的黑名单策略"
                    }
                }
            }
        }
    }
))


def get_strategy_mapper_schema():
    """获取 StrategyMapper schema 字典"""
    return STRATEGY_MAPPER_SCHEMA.schema