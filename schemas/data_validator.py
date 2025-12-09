"""
DataValidator 节点 Schema (#3001)
数据校验结果的 JSON Schema 定义

v2.0 更新：
- 新增嵌套结构 (gamma_regime, key_levels, iv_hv, structure)
- 新增字段: net_dex_sign, max_pain, pcr_ratio, major_oi_strikes 等
- 更新枚举值: status, next_step
- 新增 data_quality 和 charts_parsed
"""
from .base import SchemaDefinition, register_schema


DATA_VALIDATOR_SCHEMA = register_schema(SchemaDefinition(
    name="data_validator",
    description="gexbot 图表解析与数据校验结果",
    version="2.0",
    
    schema={
        "type": "object",
        "required": ["symbol", "timestamp", "spot", "status", "core_fields", "missing_fields", "data_quality", "next_step"],
        "properties": {
            "symbol": {
                "type": "string",
                "description": "标的代码"
            },
            "timestamp": {
                "type": "string",
                "description": "数据时间戳(ET)"
            },
            "spot": {
                "type": "number",
                "description": "现价"
            },
            "status": {
                "type": "string",
                "enum": ["data_ready", "missing_critical", "missing_high", "missing_optional"],
                "description": "数据状态"
            },
            "core_fields": {
                "type": "object",
                "description": "核心字段数据（嵌套结构）",
                "properties": {
                    "gamma_regime": {
                        "type": "object",
                        "properties": {
                            "vol_trigger": {
                                "type": "number",
                                "description": "VOL TRIGGER / GEX Flip 价格"
                            },
                            "spot_vs_trigger": {
                                "type": "string",
                                "enum": ["above", "below", "near"],
                                "description": "现价相对VOL TRIGGER位置"
                            },
                            "net_gex_sign": {
                                "type": "string",
                                "enum": ["positive", "negative", "neutral"],
                                "description": "NET-GEX 符号"
                            },
                            "net_dex_sign": {
                                "type": "string",
                                "enum": ["positive", "negative", "neutral", "bullish", "bearish"],
                                "description": "NET-DEX 方向"
                            },
                            "total_net_gex": {
                                "type": "number",
                                "description": "Total NET GEX 数值"
                            }
                        }
                    },
                    "key_levels": {
                        "type": "object",
                        "properties": {
                            "gamma_wall": {
                                "type": "number",
                                "description": "主 Gamma Wall 位置"
                            },
                            "call_wall": {
                                "type": "number",
                                "description": "Call Wall 位置"
                            },
                            "put_wall": {
                                "type": "number",
                                "description": "Put Wall 位置"
                            },
                            "gamma_wall_prox": {
                                "type": "number",
                                "description": "Gamma Wall 接近度 (%)"
                            },
                            "max_pain": {
                                "type": "number",
                                "description": "Max Pain 价格"
                            },
                            "major_oi_strikes": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "主要 OI 聚集行权价列表"
                            }
                        }
                    },
                    "iv_hv": {
                        "type": "object",
                        "properties": {
                            "iv_atm": {
                                "type": "number",
                                "description": "当前 ATM IV (%)"
                            },
                            "iv_front": {
                                "type": "number",
                                "description": "近月 IV (%)"
                            },
                            "iv_back": {
                                "type": "number",
                                "description": "远月 IV (%)"
                            },
                            "hv10": {
                                "type": "number",
                                "description": "10日历史波动率 (%)"
                            },
                            "hv20": {
                                "type": "number",
                                "description": "20日历史波动率 (%)"
                            },
                            "hv60": {
                                "type": "number",
                                "description": "60日历史波动率 (%)"
                            }
                        }
                    },
                    "structure": {
                        "type": "object",
                        "properties": {
                            "vex_net": {
                                "type": "number",
                                "description": "VEX 净值"
                            },
                            "vanna_atm": {
                                "type": "number",
                                "description": "Vanna ATM 值"
                            },
                            "term_slope": {
                                "type": "number",
                                "description": "期限结构斜率"
                            },
                            "term_structure_type": {
                                "type": "string",
                                "enum": ["contango", "backwardation", "flat"],
                                "description": "期限结构类型"
                            },
                            "put_skew_25": {
                                "type": "number",
                                "description": "25Δ Put Skew"
                            },
                            "call_skew_25": {
                                "type": "number",
                                "description": "25Δ Call Skew"
                            },
                            "skew_asym": {
                                "type": "number",
                                "description": "Skew 不对称性 (Put - Call)"
                            },
                            "spread_atm": {
                                "type": "number",
                                "description": "ATM Bid-Ask Spread (%)"
                            },
                            "pcr_ratio": {
                                "type": "number",
                                "description": "Put/Call Ratio"
                            },
                            "smile_curvature": {
                                "type": "number",
                                "description": "微笑曲率"
                            }
                        }
                    }
                }
            },
            "missing_fields": {
                "type": "array",
                "description": "缺失字段列表",
                "items": {
                    "type": "object",
                    "required": ["field", "priority"],
                    "properties": {
                        "field": {
                            "type": "string",
                            "description": "缺失字段名"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["critical", "high", "medium"],
                            "description": "优先级"
                        },
                        "command": {
                            "type": "string",
                            "description": "补齐命令"
                        },
                        "alternative": {
                            "type": "string",
                            "description": "替代数据源"
                        }
                    }
                }
            },
            "charts_parsed": {
                "type": "array",
                "description": "已解析的图表列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "识别到的命令"
                        },
                        "fields_extracted": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "提取的字段列表"
                        }
                    }
                }
            },
            "data_quality": {
                "type": "object",
                "required": ["completeness", "critical_ok"],
                "description": "数据质量评估",
                "properties": {
                    "completeness": {
                        "type": "number",
                        "description": "完整度 (0.0-1.0)"
                    },
                    "critical_ok": {
                        "type": "boolean",
                        "description": "Critical 字段是否完整"
                    },
                    "high_ok": {
                        "type": "boolean",
                        "description": "High 字段是否完整"
                    }
                }
            },
            "next_step": {
                "type": "string",
                "enum": ["proceed", "request_critical", "request_high", "abort"],
                "description": "下一步操作"
            }
        }
    }
))


def get_data_validator_schema():
    """获取 DataValidator schema 字典"""
    return DATA_VALIDATOR_SCHEMA.schema