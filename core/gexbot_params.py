"""
Gexbot command parameter model.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class GexbotParams:
    strikes: int
    dte_gex: int
    dte_vex: int
    dte_vex_5_60: int
    dte_term: int
    dte_skew: int
    dte_trigger: int
    dte_vanna_atm: int
    dte_vanna_atm_5_60: int
    dte_vanna_ntm: int
    dte_extrinsic_ntm: int
    dte_theta_atm: int
    dte_gamma_surface: int
    dte_vega_surface: int
    dte_liquidity: int
    expiration_filter: str = "*"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize parameters to a dict for rendering/logging."""
        return asdict(self)
