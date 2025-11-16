"""
集中管理所有JSON schemas
"""
from typing import Dict, Any

SCHEMAS = {
    "data_validation": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "timestamp": {"type": "string"},
            "status": {
                "type": "string",
                "enum": ["data_ready", "missing_data"]
            },
            "core_fields": {
                "type": "object",
                "properties": {
                    "vol_trigger": {"type": "number"},
                    "spot": {"type": "number"},
                    "net_gex_sign": {
                        "type": "string",
                        "enum": ["positive", "negative", "neutral"]
                    },
                    "gamma_wall_prox": {"type": "number"},
                    "iv_event_w_atm": {"type": "number"},
                    "hv10": {"type": "number"},
                    "hv20": {"type": "number"},
                    "hv60": {"type": "number"},
                    "gamma_wall": {"type": "number"},
                    "call_wall": {"type": "number"},
                    "put_wall": {"type": "number"},
                    "spot_vs_trigger": {
                        "type": "string",
                        "enum": ["above", "below", "near"]
                    },
                    "iv_m1_atm": {"type": "number"},
                    "iv_m2_atm": {"type": "number"},
                    "vex_net": {"type": "number"},
                    "vanna_atm": {"type": "number"},
                    "term_slope": {"type": "number"},
                    "put_skew_25": {"type": "number"},
                    "call_skew_25": {"type": "number"},
                    "spread_atm": {"type": "number"},
                    "ask_premium_atm": {"type": "number"}
                },
                "required": [
                    "vol_trigger", "spot", "net_gex_sign", "gamma_wall_prox",
                    "iv_event_w_atm", "hv10"
                ]
            },
            "missing_fields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"]
                        },
                        "command": {"type": "string"},
                        "alternative": {"type": "string"}
                    }
                }
            },
            "next_step": {
                "type": "string",
                "enum": ["proceed_to_analysis", "request_missing_data"]
            }
        },
        "required": [
            "symbol", "timestamp", "status", "core_fields",
            "missing_fields", "next_step"
        ]
    },
    
    "probability_calibration": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "probability_calibration": {
                "type": "object",
                "properties": {
                    "p_long": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "p_short": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"]
                    },
                    "method": {
                        "type": "string",
                        "enum": ["冷启动先验", "历史回测", "Platt_scaling"]
                    },
                    "rationale": {"type": "string"}
                },
                "required": ["p_long", "p_short", "method"]
            },
            "decision_gate": {
                "type": "object",
                "properties": {
                    "long_vol_pass": {"type": "boolean"},
                    "short_vol_pass": {"type": "boolean"},
                    "final_direction": {
                        "type": "string",
                        "enum": ["做多波动率", "做空波动率", "观望"]
                    },
                    "gate_check": {
                        "type": "object",
                        "properties": {
                            "long_score_check": {"type": "string"},
                            "short_score_check": {"type": "string"},
                            "prob_check": {"type": "string"},
                            "conflict_check": {"type": "string"}
                        }
                    }
                },
                "required": [
                    "long_vol_pass", "short_vol_pass",
                    "final_direction"
                ]
            }
        },
        "required": [
            "symbol", "probability_calibration", "decision_gate"
        ]
    },
    
    "strategy_mapping": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "direction": {
                "type": "string",
                "enum": ["做多波动率", "做空波动率", "观望"]
            },
            "strategies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tier": {
                            "type": "string",
                            "enum": ["进取版", "均衡版", "保守版"]
                        },
                        "structure": {"type": "string"},
                        "dte": {"type": "string"},
                        "legs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "action": {"type": "string"},
                                    "strike": {"type": "string"},
                                    "delta": {"type": "string"},
                                    "rationale": {"type": "string"}
                                }
                            }
                        },
                        "entry": {
                            "type": "object",
                            "properties": {
                                "trigger": {"type": "string"},
                                "timing": {"type": "string"},
                                "condition": {"type": "string"}
                            }
                        },
                        "exit": {
                            "type": "object",
                            "properties": {
                                "profit_target": {"type": "string"},
                                "stop_loss": {"type": "string"},
                                "time_decay": {"type": "string"},
                                "regime_change": {"type": "string"}
                            }
                        },
                        "edge_estimate": {
                            "type": "object",
                            "properties": {
                                "win_rate": {"type": "string"},
                                "rr_ratio": {"type": "string"},
                                "ev": {"type": "string"},
                                "ev_numeric": {"type": "number"},
                                "meets_threshold": {"type": "boolean"},
                                "note": {"type": "string"}
                            },
                            "required": [
                                "win_rate", "rr_ratio", "ev", "meets_threshold"
                            ]
                        }
                    },
                    "required": [
                        "tier", "structure", "dte", "legs", "entry",
                        "exit", "edge_estimate"
                    ]
                }
            }
        },
        "required": ["symbol", "direction", "strategies"]
    }
}

def get_schema(schema_name: str) -> Dict[str, Any]:
    """获取指定schema"""
    return SCHEMAS.get(schema_name, {})
