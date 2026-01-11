"""
Bridge market_state enrichment for input templates.
"""

from typing import Any, Dict, Optional


def apply_bridge_market_state(
    data: Dict[str, Any],
    bridge: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Fill schema-allowed fields from bridge.market_state without overwriting user data.
    Only writes into existing schema fields.
    """
    if not bridge or not isinstance(bridge, dict):
        return data

    market_state = bridge.get("market_state") or {}
    if not isinstance(market_state, dict):
        return data

    as_of = market_state.get("as_of") or bridge.get("as_of")
    if as_of and data.get("meta", {}).get("datetime") in (None, ""):
        data["meta"]["datetime"] = as_of

    hv20 = market_state.get("hv20")
    if hv20 is not None:
        volatility = data.get("volatility", {})
        if volatility.get("hv20") is None:
            volatility["hv20"] = hv20
            data["volatility"] = volatility

    iv30 = market_state.get("iv30")
    if iv30 is not None:
        volatility = data.get("volatility", {})
        if volatility.get("iv_m1_atm") is None:
            volatility["iv_m1_atm"] = iv30
            data["volatility"] = volatility

    return data
