"""
Gexbot command generator using template rendering.
"""

from dataclasses import fields
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..core.gexbot_params import GexbotParams
from ..core.gexbot_param_resolver import load_yaml_rules
from ..core.constants import (
    EXPIRATION_FILTER_ALL,
    EXPIRATION_FILTER_WEEKLY,
    EXPIRATION_FILTER_MONTHLY,
)

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


DEFAULT_TEMPLATES: Dict[str, List[str]] = {
    "standard": [
        "!gexn {symbol} {strikes} {dte_gex}",
        "!gexr {symbol} {strikes} {dte_gex}",
        "!vexn {symbol} {strikes} {dte_vex} {exp_all}",
        "!vanna {symbol} atm {dte_vanna_atm} {exp_all}",
        "!vanna {symbol} ntm {dte_vanna_ntm}",
        "!trigger {symbol} {dte_trigger}",
        "!term {symbol} {dte_term} {exp_w}",
        "!term {symbol} {dte_term} {exp_m}",
        "!skew {symbol} ivmid atm {dte_skew}",
        "!skew {symbol} ivmid ntm {dte_skew}",
        "!skew {symbol} ivmid put {dte_skew} {exp_w}",
        "!surface {symbol} ivmid {dte_gex}",
        "!surface {symbol} ivmid ntm {dte_gex}",
        "!surface {symbol} ivask ntm {dte_gex}",
        "!surface {symbol} spread atm {dte_gex}",
        "!surface {symbol} extrinsic ntm {dte_extrinsic_ntm} {exp_w}",
        "!surface {symbol} gex ntm {dte_gex}",
        "!surface {symbol} vex ntm {dte_vex}",
    ],
    "minimum": [
        "!trigger {symbol} {dte_trigger}",
        "!gexr {symbol} {strikes} {dte_gex}",
        "!vexn {symbol} {strikes} {dte_vex} {exp_all}",
        "!surface {symbol} ivmid {dte_gex}",
        "!surface {symbol} ivask ntm {dte_gex}",
        "!surface {symbol} spread atm {dte_gex}",
        "!skew {symbol} ivmid atm {dte_skew}",
    ],
    "event": [
        "!trigger {symbol} {dte_trigger}",
        "!gexn {symbol} {strikes} {dte_gex}",
        "!gexr {symbol} {strikes} {dte_gex}",
        "!vexn {symbol} {strikes} {dte_vex} {exp_all}",
        "!surface {symbol} ivmid {dte_gex}",
        "!surface {symbol} extrinsic ntm {dte_extrinsic_ntm} {exp_w}",
        "!surface {symbol} theta atm {dte_theta_atm} {exp_w}",
    ],
    "intraday": [
        "!trigger {symbol} {dte_trigger}",
        "!gexr {symbol} {strikes} {dte_gex}",
        "!surface {symbol} gamma atm {dte_gamma_surface} {exp_w}",
        "!surface {symbol} spread atm {dte_gex}",
        "!surface {symbol} ivask ntm {dte_gex}",
        "!skew {symbol} ivmid atm {dte_skew}",
    ],
    "post_event": [
        "!trigger {symbol} {dte_trigger}",
        "!surface {symbol} ivmid {dte_gex}",
        "!surface {symbol} extrinsic ntm {dte_extrinsic_ntm} {exp_w}",
        "!vexn {symbol} {strikes} {dte_vex} {exp_all}",
        "!surface {symbol} theta atm {dte_theta_atm} {exp_w}",
        "!vanna {symbol} atm {dte_vanna_atm} {exp_all}",
    ],
    "long_term": [
        "!term {symbol} {dte_term} {exp_w}",
        "!term {symbol} {dte_term} {exp_m}",
        "!surface {symbol} vega atm {dte_vega_surface}",
        "!surface {symbol} rho atm {dte_vex}",
        "!vexn {symbol} {strikes} {dte_vex} {exp_all}",
    ],
    "diagnostic": [
        "!surface {symbol} gamma atm {dte_gamma_surface} {exp_w}",
        "!surface {symbol} vega atm {dte_vega_surface}",
        "!surface {symbol} theta atm {dte_theta_atm} {exp_w}",
        "!surface {symbol} rho atm {dte_vex}",
    ],
    "schema_core": [
        "!vexn {symbol} {strikes} {dte_vex_5_60} {exp_all}",
        "!vanna {symbol} atm {dte_vanna_atm_5_60} {exp_all}",
        "!skew {symbol} ivmid atm {dte_skew}",
        "!skew {symbol} ivmid ntm {dte_skew}",
        "!surface {symbol} spread ntm {dte_liquidity}",
        "!surface {symbol} ivmid ntm {dte_liquidity}",
        "!surface {symbol} ivask ntm {dte_liquidity}",
    ],
}


def _load_templates(path: Optional[str] = None) -> Dict[str, List[str]]:
    templates_path = Path(path or "config/gexbot_templates.yaml")
    if yaml is None or not templates_path.exists():
        return DEFAULT_TEMPLATES

    try:
        with open(templates_path, "r") as f:
            data = yaml.safe_load(f) or {}
        contexts = data.get("contexts") if isinstance(data, dict) else {}
        if isinstance(contexts, dict):
            return {k: v for k, v in contexts.items() if isinstance(v, list)}
    except Exception:
        return DEFAULT_TEMPLATES

    return DEFAULT_TEMPLATES


class GexbotCommandGenerator:
    """Render gexbot commands from templates and parameters."""

    def __init__(
        self,
        symbol: str,
        params: Optional[Any] = None,
        templates_path: Optional[str] = None,
    ):
        self.symbol = symbol.upper()
        self.templates = _load_templates(templates_path)
        self.params = self._coerce_params(params)

    def _coerce_params(self, params: Optional[Any]) -> GexbotParams:
        if isinstance(params, GexbotParams):
            return params
        params_dict = params or {}
        if params is None:
            rules, _ = load_yaml_rules()
            params_dict = rules.get("defaults", {})
        if isinstance(params_dict, dict):
            allowed = {f.name for f in fields(GexbotParams)}
            filtered = {k: v for k, v in params_dict.items() if k in allowed}
            return GexbotParams(**filtered)
        raise ValueError("params must be a GexbotParams or dict")

    def _payload(self) -> Dict[str, Any]:
        data = self.params.to_dict()
        data.update(
            {
                "symbol": self.symbol,
                "exp_all": EXPIRATION_FILTER_ALL,
                "exp_w": EXPIRATION_FILTER_WEEKLY,
                "exp_m": EXPIRATION_FILTER_MONTHLY,
            }
        )
        return data

    def generate_commands(self, context: str = "standard") -> List[str]:
        tmpl_list = self.templates.get(context) or self.templates.get("standard", [])
        data = self._payload()
        commands = []
        for tmpl in tmpl_list:
            try:
                commands.append(tmpl.format(**data))
            except KeyError:
                continue
        return commands

    def format_for_output(self, commands: List[str]) -> str:
        """Format commands for copy-paste output (one per line)."""
        return "\n".join(commands)

    def get_commands_for_context(
        self,
        context: str = "standard",
        include_diagnostic: bool = False,
    ) -> List[str]:
        """
        Get appropriate command suite based on context.

        Args:
            context: "standard" | "minimum" | "event" | "intraday" | "post_event" | "long_term"
            include_diagnostic: Whether to append diagnostic commands
        """
        commands = self.generate_commands(context)
        if include_diagnostic:
            commands.extend(self.generate_commands("diagnostic"))
        return commands
