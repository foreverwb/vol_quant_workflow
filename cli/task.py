"""
task handler - Full analysis pipeline.

Usage: vol task -i INPUT_FILE -c OUTPUT_FILE

Full pipeline:
1. Features → 2. Signals → 3. Probability (LLM) → 
4. Strategy Mapping (LLM) → 5. Strikes → 6. EV → 7. Persist
"""

import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..core.schema import InputSchema, OutputSchema
from ..core.config import Config, get_config
from ..core.constants import Decision
from ..features import FeatureCalculator
from ..signals import SignalScorer
from ..decision import ProbabilityCalibrator, DecisionClassifier, StrategyMapper
from ..execution import StrikeCalculator, EVEstimator, ExecutionGate


class TaskHandler:
    """
    Handles the `task` CLI command for full analysis.
    
    Pipeline:
    1. Load and validate input (22 core fields)
    2. Compute features from input
    3. Compute signal scores
    4. Calibrate probabilities (LLM allowed)
    5. Make three-class decision
    6. Map to strategy templates (LLM allowed)
    7. Calculate strikes
    8. Estimate EV
    9. Apply execution gates
    10. Persist results
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize handler with all pipeline components."""
        self.config = config or get_config()
        
        # Pipeline components
        self.feature_calculator = FeatureCalculator()
        self.signal_scorer = SignalScorer(self.config)
        self.probability_calibrator = ProbabilityCalibrator(method="cold_start")
        self.decision_classifier = DecisionClassifier()
        self.strategy_mapper = StrategyMapper()
        self.strike_calculator = StrikeCalculator()
        self.ev_estimator = EVEstimator()
        self.execution_gate = ExecutionGate()
    
    def execute(
        self,
        input_file: str,
        output_file: str,
        replay_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute the full analysis pipeline.
        
        Args:
            input_file: Path to input JSON file
            output_file: Path to output JSON file
            replay_mode: If True, use for backtest replay
            
        Returns:
            Dictionary with full analysis results
        """
        # Step 1: Load and validate input
        input_result = self._load_input(input_file)
        if not input_result["success"]:
            return input_result
        
        input_data = input_result["data"]
        symbol = input_data["meta"]["symbol"]
        
        # Determine if single stock or index
        is_single_stock = symbol not in ["SPY", "SPX", "QQQ", "NDX", "IWM", "DIA"]
        is_index = symbol in ["SPX", "NDX", "RUT", "DJX"]
        
        # Step 2: Compute features
        features = self.feature_calculator.calculate(input_data)
        
        # Step 3: Compute signal scores
        signals = self.signal_scorer.compute_signals(features)
        composite = self.signal_scorer.compute_composite_scores(
            signals, 
            is_single_stock=is_single_stock,
            is_index=is_index,
        )
        
        # Step 4: Calibrate probabilities (LLM allowed here)
        context = self._build_calibration_context(input_data, features)
        probabilities = self.probability_calibrator.calibrate(
            long_vol_score=composite.long_vol_score,
            short_vol_score=composite.short_vol_score,
            context=context,
        )
        
        # Step 5: Make decision
        decision_result = self.decision_classifier.classify(
            long_vol_score=composite.long_vol_score,
            short_vol_score=composite.short_vol_score,
            p_long=probabilities["p_long"],
            p_short=probabilities["p_short"],
            context=context,
        )
        
        # Step 6: Map to strategies (LLM allowed here)
        strategy_candidates = []
        selected_strategy = None
        
        if decision_result.decision != Decision.STAND_ASIDE:
            candidates = self.strategy_mapper.get_candidates(
                decision=decision_result.decision,
                context=context,
            )
            
            # Step 7 & 8: For each candidate, calculate strikes and EV
            for candidate in candidates:
                params = self.strategy_mapper.customize_parameters(candidate, context)
                
                # Calculate strikes
                market_context = self._build_market_context(input_data, features)
                strikes_result = self.strike_calculator.calculate_strikes(
                    strategy_params=params,
                    market_context=market_context,
                )
                
                # Estimate EV
                probability = (
                    probabilities["p_long"].point_estimate 
                    if decision_result.decision == Decision.LONG_VOL 
                    else probabilities["p_short"].point_estimate
                )
                
                ev_result = self.ev_estimator.estimate(
                    strategy_params=params,
                    strikes=strikes_result["strikes"],
                    market_context=market_context,
                    probability=probability,
                )
                
                # Step 9: Check execution gates
                gate_result = self.execution_gate.check(
                    ev_estimate=ev_result,
                    probability=probability,
                    liquidity=features["liquidity"],
                    strategy_tier=params["tier"],
                    context=context,
                )
                
                strategy_candidates.append({
                    "name": candidate.name,
                    "tier": candidate.tier.value,
                    "direction": candidate.direction,
                    "dte_range": candidate.dte_range,
                    "delta_targets": params["delta_targets"],
                    "strike_anchors": params["strike_anchors"],
                    "strikes": strikes_result["strikes"],
                    "ev": ev_result,
                    "gate_result": {
                        "passes": gate_result.passes,
                        "failed_gates": gate_result.failed_gates,
                        "warnings": gate_result.warnings,
                    },
                    "is_executable": gate_result.passes and ev_result["ev_positive"],
                })
            
            # Select best executable strategy
            executable = [c for c in strategy_candidates if c["is_executable"]]
            if executable:
                # Sort by EV
                executable.sort(key=lambda x: x["ev"]["net_ev"], reverse=True)
                selected_strategy = executable[0]
        
        # Build full analysis output
        analysis = {
            "decision": decision_result.decision.value,
            "confidence": decision_result.confidence,
            "is_preferred": decision_result.is_preferred,
            "primary_reasons": decision_result.primary_reasons,
            "scores": {
                "long_vol_score": composite.long_vol_score,
                "short_vol_score": composite.short_vol_score,
            },
            "signal_breakdown": {
                "s_vrp": signals.s_vrp,
                "s_gex": signals.s_gex,
                "s_vex": signals.s_vex,
                "s_carry": signals.s_carry,
                "s_skew": signals.s_skew,
                "s_vanna": signals.s_vanna,
                "s_rv": signals.s_rv,
                "s_liq": signals.s_liq,
            },
            "probabilities": {
                "p_long": probabilities["p_long"].point_estimate,
                "p_long_range": (probabilities["p_long"].lower_bound, probabilities["p_long"].upper_bound),
                "p_short": probabilities["p_short"].point_estimate,
                "p_short_range": (probabilities["p_short"].lower_bound, probabilities["p_short"].upper_bound),
                "calibration_method": probabilities["p_long"].calibration_method,
            },
            "candidates": strategy_candidates,
            "selected_strategy": selected_strategy,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "warnings": self._collect_warnings(features, decision_result, strategy_candidates),
            "missing_fields": input_result.get("missing_fields", []),
        }
        
        # Step 10: Persist to output file
        self._save_analysis(output_file, analysis, input_data)
        
        return {
            "success": True,
            "analysis": analysis,
            "output_file": output_file,
        }
    
    def _load_input(self, path: str) -> Dict[str, Any]:
        """Load and validate input file."""
        if not os.path.exists(path):
            return {
                "success": False,
                "error": f"Input file not found: {path}",
            }
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON parse error: {str(e)}",
            }
        
        is_valid, errors = InputSchema.validate(data)
        if not is_valid:
            return {
                "success": False,
                "error": f"Invalid input: {'; '.join(errors)}",
                "missing_fields": errors,
            }
        
        return {
            "success": True,
            "data": data,
            "missing_fields": [],
        }
    
    def _build_calibration_context(
        self,
        input_data: Dict[str, Any],
        features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build context for probability calibration."""
        regime = features["regime"]
        
        return {
            "regime_state": regime["regime_state"],
            "trigger_distance_pct": regime["trigger_distance_pct"],
            "is_event_week": input_data["volatility"].get("iv_event_atm") is not None,
            "liquidity_flag": input_data["liquidity"]["liquidity_flag"],
            "term_regime": features["term_structure"]["term_regime"],
            "skew_regime": features["skew"]["skew_regime"],
            "is_pin_risk": regime["is_pin_risk"],
        }
    
    def _build_market_context(
        self,
        input_data: Dict[str, Any],
        features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build market context for strike calculation."""
        return {
            "spot": input_data["market"]["spot"],
            "vol_trigger": input_data["regime"]["vol_trigger"],
            "gamma_wall_call": input_data["regime"]["gamma_wall_call"],
            "gamma_wall_put": input_data["regime"]["gamma_wall_put"],
            "iv_atm": input_data["volatility"]["iv_m1_atm"],
            "iv_m1_atm": input_data["volatility"]["iv_m1_atm"],
            "iv_m2_atm": input_data["volatility"].get("iv_m2_atm"),
            "hv20": input_data["volatility"]["hv20"],
            "spread_atm": input_data["liquidity"]["spread_atm"],
            "dte": 30,  # Default, should be from context
        }
    
    def _collect_warnings(
        self,
        features: Dict[str, Any],
        decision: Any,
        candidates: List[Dict],
    ) -> List[str]:
        """Collect all warnings from pipeline."""
        warnings = []
        
        # Feature warnings
        if features["liquidity"]["liquidity_flag"] == "poor":
            warnings.append("Poor liquidity may impact execution")
        
        # Gate warnings from candidates
        for c in candidates:
            for w in c["gate_result"]["warnings"]:
                if w not in warnings:
                    warnings.append(w)
        
        # No executable strategy warning
        if decision.decision != Decision.STAND_ASIDE:
            executable = [c for c in candidates if c["is_executable"]]
            if not executable:
                warnings.append("No strategy passes execution gates - output is NO TRADE")
        
        return warnings
    
    def _save_analysis(
        self,
        path: str,
        analysis: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> None:
        """Save analysis to output file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing or create new
        if os.path.exists(path):
            with open(path, 'r') as f:
                output_data = json.load(f)
        else:
            output_data = {
                "symbol": input_data["meta"]["symbol"],
                "date": input_data["meta"]["datetime"].split("T")[0],
                "last_update": "",
                "updates": [],
                "full_analysis": None,
                "gexbot_commands": [],
            }
        
        output_data["full_analysis"] = analysis
        output_data["last_update"] = analysis["timestamp"]
        
        with open(path, 'w') as f:
            json.dump(output_data, f, indent=2)
    
    def format_output(self, result: Dict[str, Any]) -> str:
        """Format result for console output."""
        if not result["success"]:
            return f"ERROR: {result.get('error', 'Unknown error')}"
        
        analysis = result["analysis"]
        
        lines = [
            f"═══════════════════════════════════════════════════════════════",
            f"  VOL QUANT WORKFLOW - Full Analysis",
            f"  {analysis['timestamp']}",
            f"═══════════════════════════════════════════════════════════════",
            f"",
            f"  DECISION: {analysis['decision']}",
            f"  Confidence: {analysis['confidence']:.1%}",
            f"  Preferred: {'Yes' if analysis['is_preferred'] else 'No'}",
            f"",
        ]
        
        # Reasons
        lines.append(f"  PRIMARY REASONS:")
        for reason in analysis["primary_reasons"]:
            lines.append(f"    • {reason}")
        lines.append("")
        
        # Scores
        lines.extend([
            f"───────────────────────────────────────────────────────────────",
            f"  SCORES",
            f"───────────────────────────────────────────────────────────────",
            f"",
            f"  Long Vol Score:  {analysis['scores']['long_vol_score']:+.2f}",
            f"  Short Vol Score: {analysis['scores']['short_vol_score']:+.2f}",
            f"",
            f"  Signal Breakdown:",
        ])
        
        for signal, value in analysis["signal_breakdown"].items():
            lines.append(f"    {signal}: {value:+.3f}")
        lines.append("")
        
        # Probabilities
        lines.extend([
            f"───────────────────────────────────────────────────────────────",
            f"  PROBABILITIES",
            f"───────────────────────────────────────────────────────────────",
            f"",
            f"  P(long):  {analysis['probabilities']['p_long']:.1%} [{analysis['probabilities']['p_long_range'][0]:.1%}-{analysis['probabilities']['p_long_range'][1]:.1%}]",
            f"  P(short): {analysis['probabilities']['p_short']:.1%} [{analysis['probabilities']['p_short_range'][0]:.1%}-{analysis['probabilities']['p_short_range'][1]:.1%}]",
            f"  Method:   {analysis['probabilities']['calibration_method']}",
            f"",
        ])
        
        # Strategy
        if analysis["selected_strategy"]:
            strat = analysis["selected_strategy"]
            lines.extend([
                f"───────────────────────────────────────────────────────────────",
                f"  SELECTED STRATEGY",
                f"───────────────────────────────────────────────────────────────",
                f"",
                f"  Name: {strat['name']}",
                f"  Tier: {strat['tier']}",
                f"  DTE:  {strat['dte_range']}",
                f"",
                f"  Strikes:",
            ])
            for leg, strike in strat["strikes"].items():
                lines.append(f"    {leg}: {strike:.1f}")
            
            lines.extend([
                f"",
                f"  EV Metrics:",
                f"    Win Rate: {strat['ev']['win_rate']:.1%}",
                f"    Net EV:   ${strat['ev']['net_ev']:.2f}",
                f"    RR Ratio: {strat['ev']['rr_ratio']:.2f}:1",
                f"",
            ])
        else:
            lines.extend([
                f"───────────────────────────────────────────────────────────────",
                f"  SELECTED STRATEGY: NO TRADE",
                f"───────────────────────────────────────────────────────────────",
                f"",
            ])
        
        # Warnings
        if analysis["warnings"]:
            lines.extend([
                f"───────────────────────────────────────────────────────────────",
                f"  WARNINGS",
                f"───────────────────────────────────────────────────────────────",
            ])
            for w in analysis["warnings"]:
                lines.append(f"  ⚠ {w}")
            lines.append("")
        
        lines.extend([
            f"═══════════════════════════════════════════════════════════════",
            f"  Output saved to: {result['output_file']}",
            f"═══════════════════════════════════════════════════════════════",
        ])
        
        return "\n".join(lines)


def resolve_file_path(name: str, file_type: str, runtime_dir: str = "runtime") -> str:
    """
    Resolve simplified file name to full path.
    
    Examples:
        AAPL_i_2025-01-05 -> runtime/inputs/AAPL_i_2025-01-05.json
        AAPL_o_2025-01-05 -> runtime/outputs/AAPL_o_2025-01-05.json
        /full/path/file.json -> /full/path/file.json (unchanged)
    """
    # If already a full path (contains / or \), use as-is
    if '/' in name or '\\' in name:
        return name
    
    # Add .json extension if missing
    if not name.endswith('.json'):
        name = f"{name}.json"
    
    # Add appropriate directory prefix
    if file_type == "input":
        return str(Path(runtime_dir) / "inputs" / name)
    else:  # output
        return str(Path(runtime_dir) / "outputs" / name)


def main():
    """CLI entry point for task command."""
    parser = argparse.ArgumentParser(
        description="Full analysis pipeline - features to strategy",
        usage="task -i INPUT -c OUTPUT [--replay]"
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        dest="input_file",
        help="Input file (e.g., AAPL_i_2025-01-05 or full path)"
    )
    parser.add_argument(
        "-c", "--cache",
        required=True,
        dest="output_file",
        help="Output file (e.g., AAPL_o_2025-01-05 or full path)"
    )
    parser.add_argument(
        "--runtime-dir",
        default="runtime",
        help="Runtime directory path"
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Enable replay/backtest mode"
    )
    
    args = parser.parse_args()
    
    # Resolve file paths
    input_path = resolve_file_path(args.input_file, "input", args.runtime_dir)
    output_path = resolve_file_path(args.output_file, "output", args.runtime_dir)
    
    handler = TaskHandler()
    result = handler.execute(
        input_file=input_path,
        output_file=output_path,
        replay_mode=args.replay,
    )
    
    print(handler.format_output(result))


if __name__ == "__main__":
    main()
