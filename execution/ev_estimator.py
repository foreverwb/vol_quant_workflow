"""
EV (Expected Value) estimator - Estimates strategy profitability.
Computes win rate, reward:risk, and expected value after costs.
"""

from typing import Dict, Any, Optional, Tuple
import math


class EVEstimator:
    """
    Estimates expected value for strategy candidates.
    
    Methods:
    1. Quick approximation (analytical)
    2. Monte Carlo simulation
    3. Grid integration over IV surface
    
    EV = P(win) * E[win] - P(loss) * E[loss] - costs
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize estimator."""
        self.config = config or {}
        self.cost_per_contract = self.config.get("cost_per_contract", 1.0)
        self.slippage_pct = self.config.get("slippage_pct", 0.01)
    
    def estimate(
        self,
        strategy_params: Dict[str, Any],
        strikes: Dict[str, float],
        market_context: Dict[str, Any],
        probability: float,
    ) -> Dict[str, Any]:
        """
        Estimate EV for a strategy.
        
        Args:
            strategy_params: Strategy configuration
            strikes: Calculated strikes
            market_context: Market data (spot, IV, etc.)
            probability: Calibrated win probability
            
        Returns:
            Dictionary with EV metrics
        """
        strategy_name = strategy_params["name"]
        direction = strategy_params["direction"]
        target_rr = strategy_params.get("target_rr", (1.5, 2.0))
        
        # Route to appropriate estimator
        if "straddle" in strategy_name or "strangle" in strategy_name:
            return self._estimate_long_vol_outright(
                strikes, market_context, probability, direction, target_rr
            )
        elif "condor" in strategy_name:
            return self._estimate_iron_condor(
                strikes, market_context, probability, target_rr
            )
        elif "spread" in strategy_name:
            return self._estimate_vertical_spread(
                strikes, market_context, probability, direction, target_rr
            )
        elif "calendar" in strategy_name:
            return self._estimate_calendar(
                strikes, market_context, probability, target_rr
            )
        else:
            return self._estimate_generic(
                strikes, market_context, probability, target_rr
            )
    
    def _estimate_long_vol_outright(
        self,
        strikes: Dict[str, float],
        context: Dict[str, Any],
        probability: float,
        direction: str,
        target_rr: Tuple[float, float],
    ) -> Dict[str, Any]:
        """
        Estimate EV for long straddle/strangle.
        
        Quick approximation:
        EV ≈ (RV - IV) * vega/gamma - carry - costs
        
        Or probability-based:
        EV = P(move > breakeven) * E[profit | move] - P(decay) * premium
        """
        spot = context.get("spot", 100)
        iv_atm = context.get("iv_atm", 0.25)
        hv = context.get("hv20", 0.20)
        dte = context.get("dte", 30)
        
        # Estimate straddle/strangle cost
        # Approximate premium: straddle ≈ 0.8 * S * IV * sqrt(T)
        t = dte / 365.0
        sqrt_t = math.sqrt(t)
        
        if "straddle" in str(strikes):
            premium_pct = 0.8 * iv_atm * sqrt_t
        else:  # strangle
            premium_pct = 0.5 * iv_atm * sqrt_t  # OTM options cheaper
        
        premium = spot * premium_pct
        
        # Breakeven move required
        breakeven_move_pct = premium / spot
        
        # Expected move based on IV
        expected_move_iv = iv_atm * sqrt_t
        
        # Win scenario: RV > IV, move exceeds breakeven
        # Using probability from calibration
        win_rate = probability
        
        # Expected profit if win: (actual_move - breakeven) * leverage
        # Assume average winning move is 1.5x breakeven
        avg_win_multiplier = 1.5
        expected_profit = premium * (avg_win_multiplier - 1) * (hv / iv_atm)
        
        # Loss scenario: decay to near zero
        expected_loss = premium * 0.8  # Assume 80% loss on average
        
        # Costs
        spread_cost = context.get("spread_atm", 0.02) * premium
        slippage = self.slippage_pct * premium
        total_costs = spread_cost + slippage + self.cost_per_contract * 2
        
        # EV calculation
        gross_ev = win_rate * expected_profit - (1 - win_rate) * expected_loss
        net_ev = gross_ev - total_costs
        
        # Reward:Risk ratio
        rr_ratio = expected_profit / expected_loss if expected_loss > 0 else 0
        
        return {
            "premium": premium,
            "breakeven_move_pct": breakeven_move_pct,
            "expected_move_iv": expected_move_iv,
            "win_rate": win_rate,
            "expected_profit": expected_profit,
            "expected_loss": expected_loss,
            "total_costs": total_costs,
            "gross_ev": gross_ev,
            "net_ev": net_ev,
            "rr_ratio": rr_ratio,
            "target_rr_met": rr_ratio >= target_rr[0],
            "ev_positive": net_ev > 0,
        }
    
    def _estimate_iron_condor(
        self,
        strikes: Dict[str, float],
        context: Dict[str, Any],
        probability: float,
        target_rr: Tuple[float, float],
    ) -> Dict[str, Any]:
        """
        Estimate EV for iron condor.
        
        EV = credit - P(breach) * max_loss - costs
        """
        spot = context.get("spot", 100)
        iv_atm = context.get("iv_atm", 0.25)
        dte = context.get("dte", 30)
        
        # Extract strikes
        strike_values = sorted(strikes.values())
        if len(strike_values) >= 4:
            put_buy, put_sell, call_sell, call_buy = strike_values
        else:
            # Estimate strikes
            put_buy = spot * 0.90
            put_sell = spot * 0.95
            call_sell = spot * 1.05
            call_buy = spot * 1.10
        
        # Wing widths
        put_width = put_sell - put_buy
        call_width = call_buy - call_sell
        max_width = max(put_width, call_width)
        
        # Estimate credit received (simplified)
        t = dte / 365.0
        credit_pct = 0.15 * iv_atm * math.sqrt(t)  # Rough approximation
        credit = spot * credit_pct
        
        # Max loss = width - credit
        max_loss = max_width - credit
        
        # Win rate from probability (short vol wins when RV < IV)
        win_rate = probability
        
        # Expected outcomes
        # Win: keep most of credit (target 50-70%)
        expected_win = credit * 0.6
        
        # Loss: average loss is less than max (early exit)
        expected_loss = max_loss * 0.7
        
        # Costs
        spread_cost = context.get("spread_atm", 0.02) * credit * 2
        slippage = self.slippage_pct * credit
        total_costs = spread_cost + slippage + self.cost_per_contract * 4
        
        # EV
        gross_ev = win_rate * expected_win - (1 - win_rate) * expected_loss
        net_ev = gross_ev - total_costs
        
        # RR ratio (for credit spreads: credit/max_loss)
        rr_ratio = credit / max_loss if max_loss > 0 else 0
        
        return {
            "credit": credit,
            "max_loss": max_loss,
            "wing_width": max_width,
            "win_rate": win_rate,
            "expected_win": expected_win,
            "expected_loss": expected_loss,
            "total_costs": total_costs,
            "gross_ev": gross_ev,
            "net_ev": net_ev,
            "rr_ratio": rr_ratio,
            "target_rr_met": rr_ratio >= target_rr[0],
            "ev_positive": net_ev > 0,
        }
    
    def _estimate_vertical_spread(
        self,
        strikes: Dict[str, float],
        context: Dict[str, Any],
        probability: float,
        direction: str,
        target_rr: Tuple[float, float],
    ) -> Dict[str, Any]:
        """
        Estimate EV for vertical spreads (debit or credit).
        """
        spot = context.get("spot", 100)
        iv_atm = context.get("iv_atm", 0.25)
        dte = context.get("dte", 30)
        
        strike_values = sorted(strikes.values())
        if len(strike_values) >= 2:
            low_strike, high_strike = strike_values[0], strike_values[-1]
        else:
            low_strike = spot * 0.95
            high_strike = spot * 1.05
        
        spread_width = high_strike - low_strike
        
        # Debit spread cost approximation
        t = dte / 365.0
        if direction == "long_vol":
            # Debit spread
            debit = spread_width * 0.4  # Rough: 40% of width
            max_profit = spread_width - debit
            max_loss = debit
        else:
            # Credit spread
            credit = spread_width * 0.3
            max_profit = credit
            max_loss = spread_width - credit
        
        win_rate = probability
        
        # Expected outcomes
        expected_win = max_profit * 0.7
        expected_loss = max_loss * 0.8
        
        # Costs
        total_costs = context.get("spread_atm", 0.02) * spot * 0.01 + self.cost_per_contract * 2
        
        gross_ev = win_rate * expected_win - (1 - win_rate) * expected_loss
        net_ev = gross_ev - total_costs
        
        rr_ratio = max_profit / max_loss if max_loss > 0 else 0
        
        return {
            "spread_width": spread_width,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "win_rate": win_rate,
            "expected_win": expected_win,
            "expected_loss": expected_loss,
            "total_costs": total_costs,
            "gross_ev": gross_ev,
            "net_ev": net_ev,
            "rr_ratio": rr_ratio,
            "target_rr_met": rr_ratio >= target_rr[0],
            "ev_positive": net_ev > 0,
        }
    
    def _estimate_calendar(
        self,
        strikes: Dict[str, float],
        context: Dict[str, Any],
        probability: float,
        target_rr: Tuple[float, float],
    ) -> Dict[str, Any]:
        """Estimate EV for calendar spread."""
        spot = context.get("spot", 100)
        iv_m1 = context.get("iv_m1_atm", 0.25)
        iv_m2 = context.get("iv_m2_atm", 0.22)
        
        # Calendar benefits from term structure
        term_slope = (iv_m2 - iv_m1) / iv_m1 if iv_m1 > 0 else 0
        
        # Debit = far - near premium (simplified)
        debit = spot * 0.02  # Rough estimate
        max_profit = debit * 1.5  # If term normalizes
        max_loss = debit
        
        win_rate = probability
        
        expected_win = max_profit * 0.6
        expected_loss = max_loss * 0.7
        
        total_costs = self.cost_per_contract * 2
        
        gross_ev = win_rate * expected_win - (1 - win_rate) * expected_loss
        net_ev = gross_ev - total_costs
        
        rr_ratio = max_profit / max_loss if max_loss > 0 else 0
        
        return {
            "debit": debit,
            "term_slope": term_slope,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "win_rate": win_rate,
            "total_costs": total_costs,
            "gross_ev": gross_ev,
            "net_ev": net_ev,
            "rr_ratio": rr_ratio,
            "target_rr_met": rr_ratio >= target_rr[0],
            "ev_positive": net_ev > 0,
        }
    
    def _estimate_generic(
        self,
        strikes: Dict[str, float],
        context: Dict[str, Any],
        probability: float,
        target_rr: Tuple[float, float],
    ) -> Dict[str, Any]:
        """Generic EV estimation fallback."""
        spot = context.get("spot", 100)
        
        # Simple probability-based estimate
        assumed_profit = spot * 0.05
        assumed_loss = spot * 0.03
        
        win_rate = probability
        
        gross_ev = win_rate * assumed_profit - (1 - win_rate) * assumed_loss
        total_costs = self.cost_per_contract * 2
        net_ev = gross_ev - total_costs
        
        rr_ratio = assumed_profit / assumed_loss if assumed_loss > 0 else 0
        
        return {
            "assumed_profit": assumed_profit,
            "assumed_loss": assumed_loss,
            "win_rate": win_rate,
            "total_costs": total_costs,
            "gross_ev": gross_ev,
            "net_ev": net_ev,
            "rr_ratio": rr_ratio,
            "target_rr_met": rr_ratio >= target_rr[0],
            "ev_positive": net_ev > 0,
        }
