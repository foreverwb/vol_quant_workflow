"""
Input schemas - Data structure definitions for pipeline inputs.
Defines the 22 core input fields and validation rules.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


# === 22 Core Input Fields ===
REQUIRED_FIELDS = {
    "meta": ["symbol", "datetime"],
    "market": ["spot"],
    "regime": [
        "vol_trigger",
        "net_gex_sign",
        "gamma_wall_call",
        "gamma_wall_put",
        "gamma_wall_proximity_pct",
    ],
    "volatility": [
        "iv_m1_atm",
        "hv10",
        "hv20",
        "hv60",
    ],
    "structure": [
        "term_slope",
        "term_curvature",
        "skew_asymmetry",
        "vex_net_5_60",
        "vanna_atm_abs",
    ],
    "liquidity": [
        "spread_atm",
        "iv_ask_premium_pct",
        "liquidity_flag",
    ],
}

OPTIONAL_FIELDS = {
    "volatility": ["iv_event_atm", "iv_m2_atm"],
}


@dataclass
class MetaFields:
    """Meta information fields."""
    symbol: str
    datetime: str  # ISO format: YYYY-MM-DDTHH:MM:SS
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MarketFields:
    """Market data fields."""
    spot: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RegimeFields:
    """Regime and structure fields."""
    vol_trigger: float
    net_gex_sign: int  # -1, 0, or 1
    gamma_wall_call: float
    gamma_wall_put: float
    gamma_wall_proximity_pct: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VolatilityFields:
    """Volatility metrics fields."""
    iv_m1_atm: float
    hv10: float
    hv20: float
    hv60: float
    iv_event_atm: Optional[float] = None
    iv_m2_atm: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class StructureFields:
    """Term structure and Greeks fields."""
    term_slope: float
    term_curvature: float
    skew_asymmetry: float
    vex_net_5_60: float
    vanna_atm_abs: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LiquidityFields:
    """Liquidity metrics fields."""
    spread_atm: float
    iv_ask_premium_pct: float
    liquidity_flag: str  # "good", "fair", "poor"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InputData:
    """Complete input data container."""
    meta: MetaFields
    market: MarketFields
    regime: RegimeFields
    volatility: VolatilityFields
    structure: StructureFields
    liquidity: LiquidityFields
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "market": self.market.to_dict(),
            "regime": self.regime.to_dict(),
            "volatility": self.volatility.to_dict(),
            "structure": self.structure.to_dict(),
            "liquidity": self.liquidity.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputData":
        """Create InputData from dictionary."""
        return cls(
            meta=MetaFields(**data["meta"]),
            market=MarketFields(**data["market"]),
            regime=RegimeFields(**data["regime"]),
            volatility=VolatilityFields(**data["volatility"]),
            structure=StructureFields(**data["structure"]),
            liquidity=LiquidityFields(**data["liquidity"]),
        )


def validate_input(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate input data against schema.
    
    Args:
        data: Input data dictionary
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check required sections
    for section in REQUIRED_FIELDS:
        if section not in data:
            errors.append(f"Missing required section: {section}")
            continue
        
        # Check required fields in section
        for field_name in REQUIRED_FIELDS[section]:
            if field_name not in data[section]:
                errors.append(f"Missing required field: {section}.{field_name}")
            elif data[section][field_name] is None:
                # Allow None only for optional fields
                if section in OPTIONAL_FIELDS and field_name in OPTIONAL_FIELDS[section]:
                    continue
                errors.append(f"Field cannot be None: {section}.{field_name}")
    
    # Validate field types and values
    if "market" in data and "spot" in data["market"]:
        if data["market"]["spot"] <= 0:
            errors.append("market.spot must be positive")
    
    if "regime" in data:
        regime = data["regime"]
        if "net_gex_sign" in regime:
            if regime["net_gex_sign"] not in [-1, 0, 1]:
                errors.append("regime.net_gex_sign must be -1, 0, or 1")
    
    if "liquidity" in data:
        liq = data["liquidity"]
        if "liquidity_flag" in liq:
            if liq["liquidity_flag"] not in ["good", "fair", "poor"]:
                errors.append("liquidity.liquidity_flag must be 'good', 'fair', or 'poor'")
    
    return len(errors) == 0, errors


def get_empty_template(symbol: str = "SYMBOL", datetime: str = "") -> Dict[str, Any]:
    """
    Get empty input template with all fields.
    
    Args:
        symbol: Default symbol
        datetime: Default datetime
        
    Returns:
        Template dictionary with None values
    """
    return {
        "meta": {
            "symbol": symbol,
            "datetime": datetime,
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
