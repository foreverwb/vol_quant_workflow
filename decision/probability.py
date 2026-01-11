"""
Probability calibration - Maps scores to calibrated probabilities.
This module is allowed to use LLM for uncertainty quantification.
"""

from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass

from ..llm import get_llm_client
from ..prompts import format_probability_prompt, get_probability_system_prompt


@dataclass
class ProbabilityEstimate:
    """Calibrated probability estimate with confidence interval."""
    point_estimate: float
    lower_bound: float
    upper_bound: float
    calibration_method: str
    confidence: float


class ProbabilityCalibrator:
    """
    Calibrates raw scores to probabilities.
    
    Methods:
    1. Cold start: Use prior ranges from strategy spec
    2. Platt scaling: Logistic regression on historical data
    3. Isotonic regression: Non-parametric calibration
    
    LLM may be used for:
    - Uncertainty mapping
    - Context-aware adjustments
    - Regime-specific calibration
    """
    
    # Cold start probability priors from strategy spec
    COLD_START_PRIORS = {
        "long": {
            1.0: (0.55, 0.60),  # L >= 1.0
            1.5: (0.60, 0.65),  # L >= 1.5
            2.0: (0.65, 0.70),  # L >= 2.0
        },
        "short": {
            1.0: (0.55, 0.60),  # S >= 1.0
            1.5: (0.60, 0.65),  # S >= 1.5
            2.0: (0.65, 0.70),  # S >= 2.0
        },
    }
    
    def __init__(
        self,
        method: str = "cold_start",
        historical_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize calibrator.
        
        Args:
            method: Calibration method ("cold_start", "platt", "isotonic")
            historical_data: Historical outcomes for fitted calibration
        """
        self.method = method
        self.historical_data = historical_data
        self._platt_params = None
        self._isotonic_map = None
        self._llm_client = None
        
        if method == "platt" and historical_data:
            self._fit_platt()
        elif method == "isotonic" and historical_data:
            self._fit_isotonic()
    
    def calibrate(
        self,
        long_vol_score: float,
        short_vol_score: float,
        context: Optional[Dict[str, Any]] = None,
        signal_breakdown: Optional[Dict[str, float]] = None,
    ) -> Dict[str, ProbabilityEstimate]:
        """
        Calibrate scores to probabilities.
        
        Args:
            long_vol_score: L score from signal aggregation
            short_vol_score: S score from signal aggregation
            context: Optional context for regime-aware calibration
            
        Returns:
            Dictionary with p_long and p_short estimates
        """
        if self.method == "llm":
            p_long, p_short = self._llm_calibrate(long_vol_score, short_vol_score, context, signal_breakdown)
            if p_long is None or p_short is None:
                p_long = self._cold_start_calibrate(long_vol_score, "long")
                p_short = self._cold_start_calibrate(short_vol_score, "short")
        elif self.method == "cold_start":
            p_long = self._cold_start_calibrate(long_vol_score, "long")
            p_short = self._cold_start_calibrate(short_vol_score, "short")
        elif self.method == "platt":
            p_long = self._platt_calibrate(long_vol_score, "long")
            p_short = self._platt_calibrate(short_vol_score, "short")
        elif self.method == "isotonic":
            p_long = self._isotonic_calibrate(long_vol_score, "long")
            p_short = self._isotonic_calibrate(short_vol_score, "short")
        else:
            raise ValueError(f"Unknown calibration method: {self.method}")
        
        # Apply context adjustments if available
        if context:
            p_long = self._apply_context_adjustment(p_long, context, "long")
            p_short = self._apply_context_adjustment(p_short, context, "short")
        
        return {
            "p_long": p_long,
            "p_short": p_short,
        }

    def _llm_calibrate(
        self,
        long_vol_score: float,
        short_vol_score: float,
        context: Optional[Dict[str, Any]],
        signal_breakdown: Optional[Dict[str, float]],
    ) -> Tuple[Optional[ProbabilityEstimate], Optional[ProbabilityEstimate]]:
        if self._llm_client is None:
            self._llm_client = get_llm_client()

        prompt = format_probability_prompt(
            long_vol_score=long_vol_score,
            short_vol_score=short_vol_score,
            context=context or {},
            signal_breakdown=signal_breakdown or {},
        )

        try:
            response = self._llm_client.chat(
                prompt=prompt,
                system_prompt=get_probability_system_prompt(),
                node_type="probability",
                response_format="json",
            )
            data = response.parse_json() or {}
        except Exception:
            return None, None

        p_long = data.get("p_long")
        p_short = data.get("p_short")
        confidence = data.get("confidence")

        if not isinstance(p_long, (int, float)) or not isinstance(p_short, (int, float)):
            return None, None

        def _mk_estimate(point: float) -> ProbabilityEstimate:
            point = max(0.40, min(0.75, float(point)))
            low = max(0.40, point - 0.05)
            high = min(0.75, point + 0.05)
            conf = float(confidence) if isinstance(confidence, (int, float)) else 0.6
            return ProbabilityEstimate(
                point_estimate=point,
                lower_bound=low,
                upper_bound=high,
                calibration_method="llm",
                confidence=max(0.0, min(1.0, conf)),
            )

        return _mk_estimate(p_long), _mk_estimate(p_short)
    
    def _cold_start_calibrate(
        self,
        score: float,
        direction: str,
    ) -> ProbabilityEstimate:
        """
        Use cold start priors for probability estimation.
        
        Interpolates between prior ranges based on score level.
        """
        priors = self.COLD_START_PRIORS[direction]
        
        if score < 1.0:
            # Below threshold - extrapolate down
            base_low, base_high = priors[1.0]
            scale = score / 1.0 if score > 0 else 0
            point = 0.50 + (base_low - 0.50) * scale
            low = 0.45 + (base_low - 0.50) * scale
            high = 0.50 + (base_high - 0.50) * scale
        elif score < 1.5:
            # Interpolate between 1.0 and 1.5
            low1, high1 = priors[1.0]
            low2, high2 = priors[1.5]
            t = (score - 1.0) / 0.5
            point = (1 - t) * (low1 + high1) / 2 + t * (low2 + high2) / 2
            low = (1 - t) * low1 + t * low2
            high = (1 - t) * high1 + t * high2
        elif score < 2.0:
            # Interpolate between 1.5 and 2.0
            low1, high1 = priors[1.5]
            low2, high2 = priors[2.0]
            t = (score - 1.5) / 0.5
            point = (1 - t) * (low1 + high1) / 2 + t * (low2 + high2) / 2
            low = (1 - t) * low1 + t * low2
            high = (1 - t) * high1 + t * high2
        else:
            # Above 2.0 - use 2.0 priors with slight extrapolation
            base_low, base_high = priors[2.0]
            extra = min(0.05, (score - 2.0) * 0.02)  # Cap at +5%
            point = (base_low + base_high) / 2 + extra
            low = base_low + extra
            high = min(0.85, base_high + extra)  # Cap at 85%
        
        # Confidence based on score magnitude
        confidence = min(0.9, 0.5 + score * 0.15)
        
        return ProbabilityEstimate(
            point_estimate=point,
            lower_bound=low,
            upper_bound=high,
            calibration_method="cold_start",
            confidence=confidence,
        )
    
    def _platt_calibrate(
        self,
        score: float,
        direction: str,
    ) -> ProbabilityEstimate:
        """
        Use Platt scaling (logistic regression) for calibration.
        Requires fitted parameters from historical data.
        """
        import math
        
        if self._platt_params is None:
            # Fall back to cold start if not fitted
            return self._cold_start_calibrate(score, direction)
        
        params = self._platt_params.get(direction, {"a": 1.0, "b": 0.0})
        a, b = params["a"], params["b"]
        
        # Sigmoid: P = 1 / (1 + exp(a*score + b))
        logit = a * score + b
        point = 1.0 / (1.0 + math.exp(-logit))
        
        # Confidence interval from parameter uncertainty
        # (simplified - in production, use bootstrap or asymptotic CI)
        std_err = 0.05  # Placeholder
        low = max(0.01, point - 1.96 * std_err)
        high = min(0.99, point + 1.96 * std_err)
        
        return ProbabilityEstimate(
            point_estimate=point,
            lower_bound=low,
            upper_bound=high,
            calibration_method="platt",
            confidence=0.8,
        )
    
    def _isotonic_calibrate(
        self,
        score: float,
        direction: str,
    ) -> ProbabilityEstimate:
        """
        Use isotonic regression for non-parametric calibration.
        Requires fitted mapping from historical data.
        """
        if self._isotonic_map is None:
            return self._cold_start_calibrate(score, direction)
        
        iso_map = self._isotonic_map.get(direction, [])
        if not iso_map:
            return self._cold_start_calibrate(score, direction)
        
        # Linear interpolation in isotonic map
        # iso_map is list of (score, prob) tuples
        for i, (s, p) in enumerate(iso_map):
            if score <= s:
                if i == 0:
                    point = p
                else:
                    s_prev, p_prev = iso_map[i - 1]
                    t = (score - s_prev) / (s - s_prev) if s != s_prev else 0
                    point = p_prev + t * (p - p_prev)
                break
        else:
            point = iso_map[-1][1]  # Use last value if beyond range
        
        # Simple CI
        low = max(0.01, point - 0.05)
        high = min(0.99, point + 0.05)
        
        return ProbabilityEstimate(
            point_estimate=point,
            lower_bound=low,
            upper_bound=high,
            calibration_method="isotonic",
            confidence=0.85,
        )
    
    def _apply_context_adjustment(
        self,
        estimate: ProbabilityEstimate,
        context: Dict[str, Any],
        direction: str,
    ) -> ProbabilityEstimate:
        """
        Apply context-aware adjustments to probability.
        
        This is where LLM could be invoked for nuanced adjustments
        based on market conditions, event proximity, etc.
        """
        adjustment = 0.0
        
        # Event proximity adjustment
        if context.get("is_event_week"):
            if direction == "long":
                adjustment += 0.02  # Events favor long vol slightly
            else:
                adjustment -= 0.01
        
        # Regime strength adjustment
        regime_state = context.get("regime_state")
        trigger_dist = context.get("trigger_distance_pct", 0.01)
        
        if regime_state == "negative_gamma" and direction == "long":
            adjustment += min(0.03, trigger_dist * 2)  # Stronger signal further below
        elif regime_state == "positive_gamma" and direction == "short":
            adjustment += min(0.03, trigger_dist * 2)
        
        # Liquidity penalty
        if context.get("liquidity_flag") == "poor":
            adjustment -= 0.03  # Reduce confidence in poor liquidity
        
        # Apply adjustment
        new_point = max(0.01, min(0.99, estimate.point_estimate + adjustment))
        new_low = max(0.01, estimate.lower_bound + adjustment)
        new_high = min(0.99, estimate.upper_bound + adjustment)
        
        return ProbabilityEstimate(
            point_estimate=new_point,
            lower_bound=new_low,
            upper_bound=new_high,
            calibration_method=estimate.calibration_method,
            confidence=estimate.confidence * 0.95 if adjustment != 0 else estimate.confidence,
        )
    
    def _fit_platt(self) -> None:
        """Fit Platt scaling parameters from historical data."""
        # In production, this would use scipy.optimize or sklearn
        # Placeholder implementation
        if not self.historical_data:
            return
        
        # Extract scores and outcomes
        long_data = self.historical_data.get("long", [])
        short_data = self.historical_data.get("short", [])
        
        # Simplified fitting (would use logistic regression in production)
        self._platt_params = {
            "long": {"a": 0.5, "b": -0.25},  # Placeholder
            "short": {"a": 0.5, "b": -0.25},
        }
    
    def _fit_isotonic(self) -> None:
        """Fit isotonic regression mapping from historical data."""
        # In production, this would use sklearn.isotonic.IsotonicRegression
        # Placeholder implementation
        if not self.historical_data:
            return
        
        # Simplified mapping
        self._isotonic_map = {
            "long": [
                (0.0, 0.45),
                (0.5, 0.50),
                (1.0, 0.57),
                (1.5, 0.62),
                (2.0, 0.68),
                (2.5, 0.72),
            ],
            "short": [
                (0.0, 0.45),
                (0.5, 0.50),
                (1.0, 0.57),
                (1.5, 0.62),
                (2.0, 0.68),
                (2.5, 0.72),
            ],
        }
