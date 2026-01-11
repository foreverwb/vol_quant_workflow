"""
Deterministic vision prompts for parsing gexbot chart outputs.
All prompts must output strict JSON only.
"""

PROMPT_SURFACE = """You are extracting values from a surface chart image.
Return ONLY strict JSON, no extra text.
If any value is missing or uncertain, use null.

Required JSON fields:
{
  "metric": "spread|ivmid|ivask",
  "spot": number|null,
  "atm_strike": number|null,
  "value_atm": number|null,
  "dte_target_used": number|null,
  "confidence_score": number|null,
  "notes": string|null
}

Rules:
- "value_atm" must be the value at the strike nearest to spot on the surface grid.
- "dte_target_used" must reflect the DTE shown/used in the chart title or legend.
- Do not infer values not present; prefer null.
"""

PROMPT_VEXN = """You are extracting values from a VEXN chart image.
Return ONLY strict JSON, no extra text.
If any value is missing or uncertain, use null.

Required JSON fields:
{
  "vex_net_5_60": number|null,
  "dominant_strikes": [number]|null,
  "dte_target_used": number|null,
  "confidence_score": number|null,
  "notes": string|null
}

Rules:
- "vex_net_5_60" is the net signed VEX exposure aggregated for the 5-60 DTE window.
- "dte_target_used" must reflect the DTE shown/used in the chart title or legend.
- Do not infer values not present; prefer null.
"""

PROMPT_VANNA = """You are extracting values from a VANNA chart image.
Return ONLY strict JSON, no extra text.
If any value is missing or uncertain, use null.

Required JSON fields:
{
  "vanna_atm_abs": number|null,
  "dte_target_used": number|null,
  "confidence_score": number|null,
  "notes": string|null
}

Rules:
- "vanna_atm_abs" is the absolute magnitude of ATM vanna exposure.
- "dte_target_used" must reflect the DTE shown/used in the chart title or legend.
- Do not infer values not present; prefer null.
"""

PROMPT_SKEW = """You are extracting values from a SKEW chart image.
Return ONLY strict JSON, no extra text.
If any value is missing or uncertain, use null.

Required JSON fields:
{
  "skew_asymmetry": number|null,
  "method": "delta25|moneyness|unknown",
  "dte_target_used": number|null,
  "confidence_score": number|null,
  "notes": string|null
}

Rules:
- If delta25 skew is available, use it and set method="delta25".
- Otherwise compute using symmetric moneyness (e.g., +/-10% or similar) and set method="moneyness".
- "dte_target_used" must reflect the DTE shown/used in the chart title or legend.
- Do not infer values not present; prefer null.
"""

PROMPT_BY_COMMAND = {
    "surface": PROMPT_SURFACE,
    "vexn": PROMPT_VEXN,
    "vanna": PROMPT_VANNA,
    "skew": PROMPT_SKEW,
}

EXPECTED_FIELDS = {
    "surface": ["metric", "spot", "atm_strike", "value_atm", "dte_target_used", "confidence_score", "notes"],
    "vexn": ["vex_net_5_60", "dominant_strikes", "dte_target_used", "confidence_score", "notes"],
    "vanna": ["vanna_atm_abs", "dte_target_used", "confidence_score", "notes"],
    "skew": ["skew_asymmetry", "method", "dte_target_used", "confidence_score", "notes"],
}
