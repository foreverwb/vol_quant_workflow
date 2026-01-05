"""
Strike calculator - Computes optimal strike prices based on strategy and context.
"""

from typing import Dict, Any, List, Optional, Tuple
import math


class StrikeCalculator:
    """
    Calculates strike prices for option strategies.
    
    Methods:
    1. Delta-based: Target specific delta
    2. ATR-based: Distance as multiple of ATR
    3. Wall-based: Anchor to gamma/call/put walls
    4. Implied move: Based on expected move
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize calculator."""
        self.config = config or {}
    
    def calculate_strikes(
        self,
        strategy_params: Dict[str, Any],
        market_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate strikes for a strategy.
        
        Args:
            strategy_params: Strategy parameters including delta targets and anchors
            market_context: Market data including spot, walls, IV, etc.
            
        Returns:
            Dictionary with calculated strikes and rationale
        """
        spot = market_context["spot"]
        delta_targets = strategy_params.get("delta_targets", {})
        strike_anchors = strategy_params.get("strike_anchors", {})
        
        strikes = {}
        rationale = {}
        
        for leg, anchor in strike_anchors.items():
            delta_target = delta_targets.get(leg)
            
            if "atm" in anchor.lower():
                # ATM strike
                strike = self._round_strike(spot, spot)
                method = "atm"
            elif "d_" in anchor or "delta" in anchor.lower():
                # Delta-based
                strike = self._strike_from_delta(
                    spot=spot,
                    delta=delta_target[0] if isinstance(delta_target, tuple) else delta_target,
                    iv=market_context.get("iv_atm", 0.25),
                    dte=market_context.get("dte", 30),
                    is_call="call" in leg,
                )
                method = f"delta_{delta_target}"
            elif "gamma_wall" in anchor.lower():
                # Anchor to gamma wall
                if "call" in leg or "upper" in anchor:
                    wall = market_context.get("gamma_wall_call", spot * 1.05)
                else:
                    wall = market_context.get("gamma_wall_put", spot * 0.95)
                strike = self._round_strike(wall, spot)
                method = "gamma_wall"
            elif "atr" in anchor.lower():
                # ATR-based distance
                atr = market_context.get("atr", spot * 0.02)
                multiplier = self._extract_multiplier(anchor)
                if "call" in leg or "upper" in anchor:
                    strike = self._round_strike(spot + atr * multiplier, spot)
                else:
                    strike = self._round_strike(spot - atr * multiplier, spot)
                method = f"atr_{multiplier}x"
            elif "implied_move" in anchor.lower():
                # Based on implied move
                implied_move_pct = market_context.get("implied_move_pct", 0.03)
                multiplier = self._extract_multiplier(anchor)
                if "call" in leg or "upper" in anchor:
                    strike = self._round_strike(spot * (1 + implied_move_pct * multiplier), spot)
                else:
                    strike = self._round_strike(spot * (1 - implied_move_pct * multiplier), spot)
                method = f"implied_move_{multiplier}x"
            else:
                # Default to delta-based if available
                if delta_target:
                    strike = self._strike_from_delta(
                        spot=spot,
                        delta=delta_target[0] if isinstance(delta_target, tuple) else delta_target,
                        iv=market_context.get("iv_atm", 0.25),
                        dte=market_context.get("dte", 30),
                        is_call="call" in leg,
                    )
                    method = "delta_fallback"
                else:
                    strike = self._round_strike(spot, spot)
                    method = "atm_fallback"
            
            strikes[leg] = strike
            rationale[leg] = {
                "method": method,
                "anchor": anchor,
                "delta_target": delta_target,
            }
        
        return {
            "strikes": strikes,
            "rationale": rationale,
            "spot": spot,
        }
    
    def _strike_from_delta(
        self,
        spot: float,
        delta: float,
        iv: float,
        dte: int,
        is_call: bool,
    ) -> float:
        """
        Calculate strike from target delta using Black-Scholes approximation.
        
        Simplified formula: K = S * exp(-d1 * sigma * sqrt(T))
        where d1 is derived from delta via inverse normal CDF.
        """
        # Time to expiration in years
        t = dte / 365.0
        
        # Approximation of inverse normal CDF for delta
        # For calls: delta ≈ N(d1), so d1 ≈ inv_norm(delta)
        # For puts: delta ≈ -N(-d1), so d1 ≈ -inv_norm(-delta)
        
        if is_call:
            # For calls, delta is positive (0 to 1)
            d1 = self._inv_norm(delta)
        else:
            # For puts, delta is negative (-1 to 0), we use |delta|
            d1 = -self._inv_norm(abs(delta))
        
        # K = S * exp(-d1 * sigma * sqrt(T) + 0.5 * sigma^2 * T)
        # Simplified: K ≈ S * exp(-d1 * sigma * sqrt(T))
        sqrt_t = math.sqrt(t) if t > 0 else 0.01
        strike = spot * math.exp(-d1 * iv * sqrt_t + 0.5 * iv * iv * t)
        
        return self._round_strike(strike, spot)
    
    def _inv_norm(self, p: float) -> float:
        """
        Approximate inverse normal CDF (quantile function).
        Uses Abramowitz and Stegun approximation.
        """
        if p <= 0:
            return -4.0
        if p >= 1:
            return 4.0
        
        # Constants for approximation
        a1 = -3.969683028665376e+01
        a2 = 2.209460984245205e+02
        a3 = -2.759285104469687e+02
        a4 = 1.383577518672690e+02
        a5 = -3.066479806614716e+01
        a6 = 2.506628277459239e+00
        
        b1 = -5.447609879822406e+01
        b2 = 1.615858368580409e+02
        b3 = -1.556989798598866e+02
        b4 = 6.680131188771972e+01
        b5 = -1.328068155288572e+01
        
        c1 = -7.784894002430293e-03
        c2 = -3.223964580411365e-01
        c3 = -2.400758277161838e+00
        c4 = -2.549732539343734e+00
        c5 = 4.374664141464968e+00
        c6 = 2.938163982698783e+00
        
        d1 = 7.784695709041462e-03
        d2 = 3.224671290700398e-01
        d3 = 2.445134137142996e+00
        d4 = 3.754408661907416e+00
        
        p_low = 0.02425
        p_high = 1 - p_low
        
        if p < p_low:
            q = math.sqrt(-2 * math.log(p))
            return (((((c1*q+c2)*q+c3)*q+c4)*q+c5)*q+c6) / ((((d1*q+d2)*q+d3)*q+d4)*q+1)
        elif p <= p_high:
            q = p - 0.5
            r = q * q
            return (((((a1*r+a2)*r+a3)*r+a4)*r+a5)*r+a6)*q / (((((b1*r+b2)*r+b3)*r+b4)*r+b5)*r+1)
        else:
            q = math.sqrt(-2 * math.log(1 - p))
            return -(((((c1*q+c2)*q+c3)*q+c4)*q+c5)*q+c6) / ((((d1*q+d2)*q+d3)*q+d4)*q+1)
    
    def _round_strike(self, strike: float, spot: float) -> float:
        """Round strike to appropriate increment based on price level."""
        if spot < 50:
            increment = 0.5
        elif spot < 200:
            increment = 1.0
        elif spot < 500:
            increment = 2.5
        else:
            increment = 5.0
        
        return round(strike / increment) * increment
    
    def _extract_multiplier(self, anchor: str) -> float:
        """Extract numeric multiplier from anchor string."""
        import re
        matches = re.findall(r'(\d+\.?\d*)', anchor)
        if matches:
            return float(matches[0])
        return 1.0
    
    def calculate_spread_width(
        self,
        strikes: Dict[str, float],
        strategy_name: str,
    ) -> Optional[float]:
        """Calculate spread width for vertical/iron condor structures."""
        if "spread" in strategy_name or "condor" in strategy_name:
            strike_values = list(strikes.values())
            if len(strike_values) >= 2:
                return max(strike_values) - min(strike_values)
        return None
