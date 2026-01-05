"""
JSON Schema definitions for input/output validation.
Enforces the 22 core field contract.
"""

from typing import Dict, Any, List, Tuple
import json


class InputSchema:
    """
    JSON Schema for runtime/inputs/{SYMBOL}_i_{YYYY-MM-DD}.json
    Validates the 22 core fields.
    """
    
    SCHEMA: Dict[str, Any] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "VolatilityStrategyInput",
        "type": "object",
        "required": ["meta", "market", "regime", "volatility", "structure", "liquidity"],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["symbol", "datetime"],
                "properties": {
                    "symbol": {"type": "string", "minLength": 1},
                    "datetime": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"},
                },
            },
            "market": {
                "type": "object",
                "required": ["spot"],
                "properties": {
                    "spot": {"type": "number", "exclusiveMinimum": 0},
                },
            },
            "regime": {
                "type": "object",
                "required": ["vol_trigger", "net_gex_sign", "gamma_wall_call", "gamma_wall_put", "gamma_wall_proximity_pct"],
                "properties": {
                    "vol_trigger": {"type": "number", "exclusiveMinimum": 0},
                    "net_gex_sign": {"type": "integer", "enum": [-1, 0, 1]},
                    "gamma_wall_call": {"type": "number"},
                    "gamma_wall_put": {"type": "number"},
                    "gamma_wall_proximity_pct": {"type": "number", "minimum": 0},
                },
            },
            "volatility": {
                "type": "object",
                "required": ["iv_m1_atm", "hv10", "hv20", "hv60"],
                "properties": {
                    "iv_event_atm": {"type": ["number", "null"], "minimum": 0},
                    "iv_m1_atm": {"type": "number", "minimum": 0},
                    "iv_m2_atm": {"type": ["number", "null"], "minimum": 0},
                    "hv10": {"type": "number", "minimum": 0},
                    "hv20": {"type": "number", "minimum": 0},
                    "hv60": {"type": "number", "minimum": 0},
                },
            },
            "structure": {
                "type": "object",
                "required": ["term_slope", "term_curvature", "skew_asymmetry", "vex_net_5_60", "vanna_atm_abs"],
                "properties": {
                    "term_slope": {"type": "number"},
                    "term_curvature": {"type": "number"},
                    "skew_asymmetry": {"type": "number"},
                    "vex_net_5_60": {"type": "number"},
                    "vanna_atm_abs": {"type": "number", "minimum": 0},
                },
            },
            "liquidity": {
                "type": "object",
                "required": ["spread_atm", "iv_ask_premium_pct", "liquidity_flag"],
                "properties": {
                    "spread_atm": {"type": "number", "minimum": 0},
                    "iv_ask_premium_pct": {"type": "number"},
                    "liquidity_flag": {"type": "string", "enum": ["good", "fair", "poor"]},
                },
            },
        },
        "additionalProperties": False,
    }
    
    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate input data against schema.
        Returns (is_valid, list_of_errors).
        """
        errors = []
        
        # Check required top-level keys
        required_keys = ["meta", "market", "regime", "volatility", "structure", "liquidity"]
        for key in required_keys:
            if key not in data:
                errors.append(f"Missing required field: {key}")
        
        if errors:
            return False, errors
        
        # Validate meta
        if "symbol" not in data["meta"]:
            errors.append("meta.symbol is required")
        if "datetime" not in data["meta"]:
            errors.append("meta.datetime is required")
        
        # Validate market
        if "spot" not in data["market"]:
            errors.append("market.spot is required")
        elif data["market"]["spot"] <= 0:
            errors.append("market.spot must be positive")
        
        # Validate regime
        regime_required = ["vol_trigger", "net_gex_sign", "gamma_wall_call", "gamma_wall_put", "gamma_wall_proximity_pct"]
        for field in regime_required:
            if field not in data["regime"]:
                errors.append(f"regime.{field} is required")
        
        if "net_gex_sign" in data["regime"] and data["regime"]["net_gex_sign"] not in [-1, 0, 1]:
            errors.append("regime.net_gex_sign must be -1, 0, or 1")
        
        # Validate volatility
        vol_required = ["iv_m1_atm", "hv10", "hv20", "hv60"]
        for field in vol_required:
            if field not in data["volatility"]:
                errors.append(f"volatility.{field} is required")
            elif data["volatility"][field] < 0:
                errors.append(f"volatility.{field} must be non-negative")
        
        # Validate structure
        struct_required = ["term_slope", "term_curvature", "skew_asymmetry", "vex_net_5_60", "vanna_atm_abs"]
        for field in struct_required:
            if field not in data["structure"]:
                errors.append(f"structure.{field} is required")
        
        # Validate liquidity
        if "spread_atm" not in data["liquidity"]:
            errors.append("liquidity.spread_atm is required")
        if "iv_ask_premium_pct" not in data["liquidity"]:
            errors.append("liquidity.iv_ask_premium_pct is required")
        if "liquidity_flag" not in data["liquidity"]:
            errors.append("liquidity.liquidity_flag is required")
        elif data["liquidity"].get("liquidity_flag") not in ["good", "fair", "poor"]:
            errors.append("liquidity.liquidity_flag must be 'good', 'fair', or 'poor'")
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_empty_template(cls, symbol: str = "", datetime_str: str = "") -> Dict[str, Any]:
        """Generate an empty input template."""
        return {
            "meta": {
                "symbol": symbol,
                "datetime": datetime_str,
            },
            "market": {
                "spot": None,
            },
            "regime": {
                "vol_trigger": None,
                "net_gex_sign": None,
                "gamma_wall_call": None,
                "gamma_wall_put": None,
                "gamma_wall_proximity_pct": None,
            },
            "volatility": {
                "iv_event_atm": None,
                "iv_m1_atm": None,
                "iv_m2_atm": None,
                "hv10": None,
                "hv20": None,
                "hv60": None,
            },
            "structure": {
                "term_slope": None,
                "term_curvature": None,
                "skew_asymmetry": None,
                "vex_net_5_60": None,
                "vanna_atm_abs": None,
            },
            "liquidity": {
                "spread_atm": None,
                "iv_ask_premium_pct": None,
                "liquidity_flag": None,
            },
        }


class OutputSchema:
    """
    JSON Schema for runtime/outputs/{SYMBOL}_o_{YYYY-MM-DD}.json
    Validates pipeline output structure.
    """
    
    SCHEMA: Dict[str, Any] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "VolatilityStrategyOutput",
        "type": "object",
        "required": ["symbol", "date", "last_update", "updates", "gexbot_commands"],
        "properties": {
            "symbol": {"type": "string"},
            "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "last_update": {"type": "string"},
            "updates": {"type": "array"},
            "full_analysis": {"type": ["object", "null"]},
            "gexbot_commands": {"type": "array", "items": {"type": "string"}},
        },
    }
    
    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate output data against schema."""
        errors = []
        
        required = ["symbol", "date", "last_update", "updates", "gexbot_commands"]
        for key in required:
            if key not in data:
                errors.append(f"Missing required field: {key}")
        
        if "updates" in data and not isinstance(data["updates"], list):
            errors.append("updates must be an array")
        
        if "gexbot_commands" in data and not isinstance(data["gexbot_commands"], list):
            errors.append("gexbot_commands must be an array")
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_empty_template(cls, symbol: str, date: str) -> Dict[str, Any]:
        """Generate an empty output template."""
        return {
            "symbol": symbol,
            "date": date,
            "last_update": "",
            "updates": [],
            "full_analysis": None,
            "gexbot_commands": [],
        }
