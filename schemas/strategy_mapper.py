"""
StrategyMapper 节点 Schema (#7001)
策略映射结果的 JSON Schema 定义
"""
from .base import SchemaDefinition, register_schema


STRATEGY_MAPPER_SCHEMA = register_schema(SchemaDefinition(
    name="strategy_mapper",
    description="策略映射与 Edge 估算结果",
    version="1.0",
    
    schema={
        "type": "object",
        "required": ["symbol", "direction", "strategies"],
        "properties": {
            "symbol": {
                "type": "string",
                "description": "标的代码"
            },
            "direction": {
                "type": "string",
                "enum": ["做多波动率", "做空波动率", "观望"],
                "description": "交易方向"
            },
            "strategies": {
                "type": "array",
                "description": "策略列表（1-3个）",
                "items": {
                    "type": "object",
                    "required": ["name", "tier", "dte", "legs", "entry", "exit", "edge_estimate"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "策略名称 (如 Long Straddle, Iron Condor)"
                        },
                        "tier": {
                            "type": "string",
                            "enum": ["进取版", "均衡版", "保守版"],
                            "description": "策略档位"
                        },
                        "description": {
                            "type": "string",
                            "description": "策略描述"
                        },
                        "dte": {
                            "type": "string",
                            "description": "到期天数 (如 '14-21天')"
                        },
                        "legs": {
                            "type": "array",
                            "description": "策略腿",
                            "items": {
                                "type": "object",
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
                                    "strike": {
                                        "type": "string",
                                        "description": "行权价描述 (如 'ATM', 'Gamma Wall附近')"
                                    },
                                    "delta": {
                                        "type": "string",
                                        "description": "Delta值 (如 '0.30', '25Δ')"
                                    },
                                    "quantity": {
                                        "type": "integer",
                                        "default": 1,
                                        "description": "数量"
                                    }
                                }
                            }
                        },
                        "entry": {
                            "type": "object",
                            "description": "入场条件",
                            "properties": {
                                "trigger": {
                                    "type": "string",
                                    "description": "触发条件"
                                },
                                "timing": {
                                    "type": "string",
                                    "description": "时机"
                                },
                                "conditions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "其他条件"
                                }
                            }
                        },
                        "exit": {
                            "type": "object",
                            "description": "退出条件",
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
                                    "description": "时间退出"
                                },
                                "regime_change": {
                                    "type": "string",
                                    "description": "Regime变化退出"
                                }
                            }
                        },
                        "edge_estimate": {
                            "type": "object",
                            "required": ["win_rate", "rr_ratio", "ev", "meets_threshold"],
                            "description": "Edge 估算",
                            "properties": {
                                "win_rate": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                    "description": "胜率"
                                },
                                "rr_ratio": {
                                    "type": "string",
                                    "description": "盈亏比 (如 '2:1')"
                                },
                                "ev": {
                                    "type": "number",
                                    "description": "期望收益"
                                },
                                "avg_win": {
                                    "type": "number",
                                    "description": "平均盈利"
                                },
                                "avg_loss": {
                                    "type": "number",
                                    "description": "平均亏损"
                                },
                                "max_drawdown": {
                                    "type": "number",
                                    "description": "最大回撤"
                                },
                                "meets_threshold": {
                                    "type": "boolean",
                                    "description": "是否满足 Edge 门槛"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
))


# 便捷获取 schema 字典
def get_strategy_mapper_schema():
    """获取 StrategyMapper schema 字典"""
    return STRATEGY_MAPPER_SCHEMA.schema
