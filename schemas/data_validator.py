"""
DataValidator 节点 Schema (#3001)
数据校验结果的 JSON Schema 定义
"""
from .base import SchemaDefinition, register_schema


DATA_VALIDATOR_SCHEMA = register_schema(SchemaDefinition(
    name="data_validator",
    description="gexbot 图表解析与数据校验结果",
    version="1.0",
    
    schema={
        "type": "object",
        "required": ["symbol", "timestamp", "status", "core_fields", "missing_fields", "next_step"],
        "properties": {
            "symbol": {
                "type": "string",
                "description": "标的代码"
            },
            "timestamp": {
                "type": "string",
                "description": "数据时间戳(ET)"
            },
            "status": {
                "type": "string",
                "enum": ["data_ready", "missing_data"],
                "description": "数据状态"
            },
            "core_fields": {
                "type": "object",
                "required": ["vol_trigger", "spot", "net_gex_sign", "gamma_wall_prox", "iv_event_w_atm", "hv10"],
                "properties": {
                    # VOL TRIGGER 相关
                    "vol_trigger": {
                        "type": "number",
                        "description": "VOL TRIGGER数值"
                    },
                    "spot": {
                        "type": "number",
                        "description": "现价"
                    },
                    "spot_vs_trigger": {
                        "type": "string",
                        "enum": ["above", "below", "near"],
                        "description": "现价相对VOL TRIGGER位置"
                    },
                    "net_gex_sign": {
                        "type": "string",
                        "enum": ["positive", "negative", "neutral"],
                        "description": "NET-GEX符号"
                    },
                    
                    # Gamma Walls
                    "gamma_wall": {
                        "type": "number",
                        "description": "Gamma Wall位置"
                    },
                    "call_wall": {
                        "type": "number",
                        "description": "Call Wall位置"
                    },
                    "put_wall": {
                        "type": "number",
                        "description": "Put Wall位置"
                    },
                    "gamma_wall_prox": {
                        "type": "number",
                        "description": "Gamma Wall接近度 (min(|Spot - GammaWall_i|/Spot))"
                    },
                    
                    # IV/HV 数据
                    "iv_event_w_atm": {
                        "type": "number",
                        "description": "事件周ATM IV"
                    },
                    "iv_m1_atm": {
                        "type": "number",
                        "description": "近月ATM IV"
                    },
                    "iv_m2_atm": {
                        "type": "number",
                        "description": "次近月ATM IV"
                    },
                    "hv10": {
                        "type": "number",
                        "description": "历史波动率10日"
                    },
                    "hv20": {
                        "type": "number",
                        "description": "历史波动率20日"
                    },
                    "hv60": {
                        "type": "number",
                        "description": "历史波动率60日"
                    },
                    
                    # 结构性指标
                    "vex_net": {
                        "type": "number",
                        "description": "VEX净值（5-60 DTE）"
                    },
                    "vanna_atm": {
                        "type": "number",
                        "description": "Vanna ATM"
                    },
                    "term_slope": {
                        "type": "number",
                        "description": "期限结构斜率"
                    },
                    "put_skew_25": {
                        "type": "number",
                        "description": "Put Skew 25Δ"
                    },
                    "call_skew_25": {
                        "type": "number",
                        "description": "Call Skew 25Δ"
                    },
                    "spread_atm": {
                        "type": "number",
                        "description": "ATM Spread"
                    },
                    "ask_premium_atm": {
                        "type": "number",
                        "description": "ATM Ask Premium %"
                    }
                }
            },
            "missing_fields": {
                "type": "array",
                "description": "缺失字段列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "string",
                            "description": "缺失字段名"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                            "description": "优先级"
                        },
                        "command": {
                            "type": "string",
                            "description": "补齐命令"
                        },
                        "alternative": {
                            "type": "string",
                            "description": "替代方法"
                        }
                    }
                }
            },
            "next_step": {
                "type": "string",
                "enum": ["proceed_to_analysis", "request_missing_data"],
                "description": "下一步操作"
            }
        }
    }
))


# 便捷获取 schema 字典
def get_data_validator_schema():
    """获取 DataValidator schema 字典"""
    return DATA_VALIDATOR_SCHEMA.schema
