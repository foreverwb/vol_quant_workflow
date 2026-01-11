"""
Parse vision-model JSON outputs for gexbot charts and map to schema fields.
"""

import json
from typing import Any, Dict, Optional, Tuple

from .vision_prompts import EXPECTED_FIELDS


def parse_vision_json(payload: str) -> Optional[Dict[str, Any]]:
    """Parse a strict JSON string into a dict."""
    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def validate_payload(command_type: str, data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate that the payload contains the expected fields."""
    expected = EXPECTED_FIELDS.get(command_type, [])
    missing = [field for field in expected if field not in data]
    if missing:
        return False, f"missing_fields:{','.join(missing)}"
    return True, "ok"


def compute_iv_ask_premium_pct(ivmid: Optional[float], ivask: Optional[float]) -> Optional[float]:
    """Compute iv_ask_premium_pct from ivmid and ivask."""
    if ivmid is None or ivask is None or ivmid == 0:
        return None
    return (ivask - ivmid) / ivmid * 100.0


def map_surface_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Map surface payload to schema updates and intermediates."""
    metric = data.get("metric")
    value_atm = data.get("value_atm")
    updates: Dict[str, Any] = {"liquidity": {}}
    intermediates: Dict[str, Any] = {}

    if metric == "spread":
        updates["liquidity"]["spread_atm"] = value_atm
    elif metric == "ivmid":
        intermediates["ivmid_atm"] = value_atm
    elif metric == "ivask":
        intermediates["ivask_atm"] = value_atm

    return {"updates": updates, "intermediates": intermediates}


def map_vexn_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Map vexn payload to schema updates."""
    return {"structure": {"vex_net_5_60": data.get("vex_net_5_60")}}


def map_vanna_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Map vanna payload to schema updates."""
    return {"structure": {"vanna_atm_abs": data.get("vanna_atm_abs")}}


def map_skew_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Map skew payload to schema updates."""
    return {"structure": {"skew_asymmetry": data.get("skew_asymmetry")}}
