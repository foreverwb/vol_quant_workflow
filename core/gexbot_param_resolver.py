"""
Resolve GexbotParams from bridge snapshot and local rules.
"""

from dataclasses import replace
from typing import Any, Dict, Optional, Tuple

from .gexbot_params import GexbotParams
from .constants import (
    DEFAULT_STRIKES,
    DEFAULT_DTE_GEX,
    DEFAULT_DTE_VEX,
    DEFAULT_DTE_VEX_5_60,
    DEFAULT_DTE_TERM,
    DEFAULT_DTE_SKEW,
    DEFAULT_DTE_TRIGGER,
    DEFAULT_DTE_VANNA_ATM,
    DEFAULT_DTE_VANNA_ATM_5_60,
    DEFAULT_DTE_VANNA_NTM,
    DEFAULT_DTE_EXTRINSIC_NTM,
    DEFAULT_DTE_THETA_ATM,
    DEFAULT_DTE_GAMMA_SURFACE,
    DEFAULT_DTE_VEGA_SURFACE,
    DEFAULT_DTE_LIQUIDITY,
    EXPIRATION_FILTER_ALL,
)

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


def _default_rules() -> Dict[str, Any]:
    return {
        "clamps": {
            "strikes": {"min": 7, "max": 31},
            "dte_short": {"min": 7, "max": 120},
            "dte_mid": {"min": 14, "max": 180},
            "dte_long": {"min": 30, "max": 365},
            "dte_term": {"min": 60, "max": 730},
        },
        "defaults": {
            "strikes": DEFAULT_STRIKES,
            "dte_gex": DEFAULT_DTE_GEX,
            "dte_vex": DEFAULT_DTE_VEX,
            "dte_vex_5_60": DEFAULT_DTE_VEX_5_60,
            "dte_term": DEFAULT_DTE_TERM,
            "dte_skew": DEFAULT_DTE_SKEW,
            "dte_trigger": DEFAULT_DTE_TRIGGER,
            "dte_vanna_atm": DEFAULT_DTE_VANNA_ATM,
            "dte_vanna_atm_5_60": DEFAULT_DTE_VANNA_ATM_5_60,
            "dte_vanna_ntm": DEFAULT_DTE_VANNA_NTM,
            "dte_extrinsic_ntm": DEFAULT_DTE_EXTRINSIC_NTM,
            "dte_theta_atm": DEFAULT_DTE_THETA_ATM,
            "dte_gamma_surface": DEFAULT_DTE_GAMMA_SURFACE,
            "dte_vega_surface": DEFAULT_DTE_VEGA_SURFACE,
            "dte_liquidity": DEFAULT_DTE_LIQUIDITY,
            "expiration_filter": EXPIRATION_FILTER_ALL,
        },
        "liquidity_strikes": {
            "excellent": 21,
            "good": 17,
            "fair": 13,
            "poor": 9,
        },
        "oi_unavailable_max_strikes": 11,
        "confidence_gate": {
            "min_confidence": 0.35,
            "low_confidence_context": "minimum",
        },
        "horizon_multipliers": {
            "adjustment_weight": 1.0,
            "bias_weight": 1.0,
            "weights": {"gex": 1.0, "skew": 0.8, "vex": 1.0, "term": 1.0},
            "state_overrides": {
                "short_low": {"gex_scale": 0.85, "skew_scale": 0.90, "trigger_scale": 0.85},
            },
        },
        "earnings_window": {
            "enabled": True,
            "event_context": "event",
            "tighten": {
                "dte_extrinsic_ntm": 30,
                "dte_theta_atm": 14,
                "dte_gex_scale": 0.85,
            },
        },
    }


def load_yaml_rules(path: str = "config/bridge_rules_gexbot.yaml") -> Tuple[Dict[str, Any], str]:
    if yaml is None:
        return _default_rules(), "defaults"
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        return (data if isinstance(data, dict) else _default_rules()), "yaml"
    except Exception:
        return _default_rules(), "defaults"


def _safe_float(val: Any, default: float) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _clamp_int(val: Any, lo: int, hi: int, default: int) -> int:
    try:
        v = int(val)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def resolve(
    bridge: Optional[Dict[str, Any]],
    symbol: str,
) -> Tuple[GexbotParams, str, Dict[str, Any]]:
    rules, rules_source = load_yaml_rules()
    defaults = rules.get("defaults", {})

    params = GexbotParams(
        strikes=int(defaults.get("strikes", DEFAULT_STRIKES)),
        dte_gex=int(defaults.get("dte_gex", DEFAULT_DTE_GEX)),
        dte_vex=int(defaults.get("dte_vex", DEFAULT_DTE_VEX)),
        dte_vex_5_60=int(defaults.get("dte_vex_5_60", DEFAULT_DTE_VEX_5_60)),
        dte_term=int(defaults.get("dte_term", DEFAULT_DTE_TERM)),
        dte_skew=int(defaults.get("dte_skew", DEFAULT_DTE_SKEW)),
        dte_trigger=int(defaults.get("dte_trigger", DEFAULT_DTE_TRIGGER)),
        dte_vanna_atm=int(defaults.get("dte_vanna_atm", DEFAULT_DTE_VANNA_ATM)),
        dte_vanna_atm_5_60=int(defaults.get("dte_vanna_atm_5_60", DEFAULT_DTE_VANNA_ATM_5_60)),
        dte_vanna_ntm=int(defaults.get("dte_vanna_ntm", DEFAULT_DTE_VANNA_NTM)),
        dte_extrinsic_ntm=int(defaults.get("dte_extrinsic_ntm", DEFAULT_DTE_EXTRINSIC_NTM)),
        dte_theta_atm=int(defaults.get("dte_theta_atm", DEFAULT_DTE_THETA_ATM)),
        dte_gamma_surface=int(defaults.get("dte_gamma_surface", DEFAULT_DTE_GAMMA_SURFACE)),
        dte_vega_surface=int(defaults.get("dte_vega_surface", DEFAULT_DTE_VEGA_SURFACE)),
        dte_liquidity=int(defaults.get("dte_liquidity", DEFAULT_DTE_LIQUIDITY)),
        expiration_filter=str(defaults.get("expiration_filter", EXPIRATION_FILTER_ALL)),
    )

    explain: Dict[str, Any] = {
        "symbol": symbol,
        "bridge_used": bridge is not None,
        "context_reason": "defaults_only",
        "rules_loaded": rules_source,
    }
    context = "standard"

    if not bridge:
        return params, context, explain

    exec_state = bridge.get("execution_state", {}) or {}
    liquidity = exec_state.get("liquidity")
    oi_available = exec_state.get("oi_data_available", True)
    confidence = _safe_float(exec_state.get("confidence"), 1.0)

    strikes = params.strikes
    liq_map = rules.get("liquidity_strikes", {})
    if isinstance(liq_map, dict) and isinstance(liquidity, str):
        strikes = liq_map.get(liquidity, strikes)

    if oi_available is False:
        strikes = min(strikes, int(rules.get("oi_unavailable_max_strikes", strikes)))

    gate = rules.get("confidence_gate", {})
    if confidence < float(gate.get("min_confidence", 0.0)):
        context = gate.get("low_confidence_context", context)
        explain["context_reason"] = "low_confidence"
    else:
        explain["context_reason"] = "bridge"

    term = bridge.get("term_structure", {}) or {}
    label_code = term.get("label_code") or term.get("label")
    adjustment = _safe_float(term.get("adjustment"), 0.0)
    horizon_bias = term.get("horizon_bias", {}) or {}
    bias_short = _safe_float(horizon_bias.get("short"), 0.0)
    bias_mid = _safe_float(horizon_bias.get("mid"), 0.0)
    bias_long = _safe_float(horizon_bias.get("long"), 0.0)

    multipliers = rules.get("horizon_multipliers", {})
    weights = multipliers.get("weights", {})
    adj_weight = _safe_float(multipliers.get("adjustment_weight"), 1.0)
    bias_weight = _safe_float(multipliers.get("bias_weight"), 1.0)
    scale_short = 1.0 + adj_weight * adjustment + bias_weight * bias_short
    scale_mid = 1.0 + adj_weight * adjustment + bias_weight * bias_mid
    scale_long = 1.0 + adj_weight * adjustment + bias_weight * bias_long
    gex_scale = scale_mid * _safe_float(weights.get("gex"), 1.0)
    skew_scale = scale_short * _safe_float(weights.get("skew"), 1.0)
    vex_scale = scale_long * _safe_float(weights.get("vex"), 1.0)
    term_scale = scale_long * _safe_float(weights.get("term"), 1.0)
    trigger_scale = gex_scale

    flags = term.get("state_flags", {}) or {}
    overrides = multipliers.get("state_overrides", {})
    for flag, override in overrides.items():
        if flags.get(flag) is True and isinstance(override, dict):
            gex_scale *= _safe_float(override.get("gex_scale"), 1.0)
            skew_scale *= _safe_float(override.get("skew_scale"), 1.0)
            vex_scale *= _safe_float(override.get("vex_scale"), 1.0)
            term_scale *= _safe_float(override.get("term_scale"), 1.0)
            trigger_scale *= _safe_float(override.get("trigger_scale"), 1.0)

    params = replace(
        params,
        strikes=int(strikes),
        dte_skew=int(params.dte_skew * skew_scale),
        dte_theta_atm=int(params.dte_theta_atm * skew_scale),
        dte_extrinsic_ntm=int(params.dte_extrinsic_ntm * skew_scale),
        dte_gex=int(params.dte_gex * gex_scale),
        dte_trigger=int(params.dte_trigger * trigger_scale),
        dte_vanna_ntm=int(params.dte_vanna_ntm * gex_scale),
        dte_vex=int(params.dte_vex * vex_scale),
        dte_vex_5_60=int(params.dte_vex_5_60 * scale_short),
        dte_term=int(params.dte_term * term_scale),
        dte_gamma_surface=int(params.dte_gamma_surface * term_scale),
        dte_vega_surface=int(params.dte_vega_surface * term_scale),
        dte_vanna_atm=int(params.dte_vex * vex_scale),
        dte_vanna_atm_5_60=int(params.dte_vanna_atm_5_60 * scale_short),
        dte_liquidity=int(params.dte_liquidity * gex_scale),
    )

    event_state = bridge.get("event_state", {}) or {}
    earnings_enabled = rules.get("earnings_window", {}).get("enabled", False)
    if earnings_enabled and event_state.get("is_earnings_window") is True:
        context = rules.get("earnings_window", {}).get("event_context", context)
        tighten = rules.get("earnings_window", {}).get("tighten", {}) or {}
        gex_tighten = _safe_float(tighten.get("dte_gex_scale"), 1.0)
        params = replace(
            params,
            dte_extrinsic_ntm=int(tighten.get("dte_extrinsic_ntm", params.dte_extrinsic_ntm)),
            dte_theta_atm=int(tighten.get("dte_theta_atm", params.dte_theta_atm)),
            dte_gex=int(params.dte_gex * gex_tighten),
        )
        explain["context_reason"] = "earnings_window"

    clamps = rules.get("clamps", {})
    strikes_clamp = clamps.get("strikes", {})
    dte_min = int(clamps.get("dte_short", {}).get("min", 7))
    dte_max = int(clamps.get("dte_long", {}).get("max", 365))
    params = replace(
        params,
        strikes=_clamp_int(params.strikes, strikes_clamp.get("min", 7), strikes_clamp.get("max", 31), params.strikes),
        dte_skew=_clamp_int(params.dte_skew, dte_min, dte_max, params.dte_skew),
        dte_theta_atm=_clamp_int(params.dte_theta_atm, dte_min, dte_max, params.dte_theta_atm),
        dte_extrinsic_ntm=_clamp_int(params.dte_extrinsic_ntm, dte_min, dte_max, params.dte_extrinsic_ntm),
        dte_gex=_clamp_int(params.dte_gex, dte_min, dte_max, params.dte_gex),
        dte_trigger=_clamp_int(params.dte_trigger, dte_min, dte_max, params.dte_trigger),
        dte_vanna_ntm=_clamp_int(params.dte_vanna_ntm, dte_min, dte_max, params.dte_vanna_ntm),
        dte_vex=_clamp_int(params.dte_vex, dte_min, dte_max, params.dte_vex),
        dte_vex_5_60=_clamp_int(params.dte_vex_5_60, dte_min, dte_max, params.dte_vex_5_60),
        dte_gamma_surface=_clamp_int(params.dte_gamma_surface, dte_min, dte_max, params.dte_gamma_surface),
        dte_vega_surface=_clamp_int(params.dte_vega_surface, dte_min, dte_max, params.dte_vega_surface),
        dte_term=_clamp_int(params.dte_term, dte_min, dte_max, params.dte_term),
        dte_vanna_atm=_clamp_int(params.dte_vanna_atm, dte_min, dte_max, params.dte_vanna_atm),
        dte_vanna_atm_5_60=_clamp_int(params.dte_vanna_atm_5_60, dte_min, dte_max, params.dte_vanna_atm_5_60),
        dte_liquidity=_clamp_int(params.dte_liquidity, dte_min, dte_max, params.dte_liquidity),
    )

    explain.update(
        {
            "liquidity": liquidity,
            "oi_available": oi_available,
            "confidence": confidence,
            "term_structure": term,
            "label_code_used": label_code,
            "adjustment_used": adjustment,
            "bias_source": {"short": bias_short, "mid": bias_mid, "long": bias_long},
            "horizon_bias": {"short": bias_short, "mid": bias_mid, "long": bias_long},
            "scales": {
                "gex": gex_scale,
                "skew": skew_scale,
                "vex": vex_scale,
                "term": term_scale,
                "trigger": trigger_scale,
            },
        }
    )

    return params, context, explain
