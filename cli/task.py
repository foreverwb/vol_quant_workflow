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
import re
import html as html_lib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..core.schema import InputSchema, OutputSchema
from ..core.config import Config, get_config
from ..core.constants import Decision
from ..features import FeatureCalculator
from ..signals import SignalScorer
from ..decision import ProbabilityCalibrator, DecisionClassifier, StrategyMapper
from ..llm import get_llm_client
from ..prompts import format_strategy_prompt, get_strategy_system_prompt, format_report_prompt, get_report_system_prompt
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
        self.probability_calibrator = ProbabilityCalibrator(method="llm")
        self.decision_classifier = DecisionClassifier()
        self.strategy_mapper = StrategyMapper()
        self.strike_calculator = StrikeCalculator()
        self.ev_estimator = EVEstimator()
        self.execution_gate = ExecutionGate()
        self.llm_client = get_llm_client()
        self.total_steps = 10
    
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
        self._log_step("Step 1", "Load and validate input")
        input_result = self._load_input(input_file)
        if not input_result["success"]:
            return input_result
        self._log_step_done("Load and validate input", input_result.get("data"))
        
        input_data = input_result["data"]
        symbol = input_data["meta"]["symbol"]
        
        # Determine if single stock or index
        is_single_stock = symbol not in ["SPY", "SPX", "QQQ", "NDX", "IWM", "DIA"]
        is_index = symbol in ["SPX", "NDX", "RUT", "DJX"]
        
        # Step 2: Compute features
        self._log_step("Step 2", "Feature calculation")
        features = self.feature_calculator.calculate(input_data)
        self._log_step_done("Feature calculation", features)
        
        # Step 3: Compute signal scores
        self._log_step("Step 3", "Signal scoring")
        signals = self.signal_scorer.compute_signals(features)
        composite = self.signal_scorer.compute_composite_scores(
            signals, 
            is_single_stock=is_single_stock,
            is_index=is_index,
        )
        self._log_step_done("Signal scoring", signals)
        
        # Step 4: Calibrate probabilities (LLM allowed here)
        self._log_step("Step 4", "Probability calibration (LLM)")
        context = self._build_calibration_context(input_data, features)
        probabilities = self.probability_calibrator.calibrate(
            long_vol_score=composite.long_vol_score,
            short_vol_score=composite.short_vol_score,
            context=context,
            signal_breakdown={
                "s_vrp": signals.s_vrp,
                "s_gex": signals.s_gex,
                "s_vex": signals.s_vex,
                "s_carry": signals.s_carry,
                "s_skew": signals.s_skew,
            },
        )
        self._log_step_done("Probability calibration (LLM)", probabilities)
        
        # Step 5: Make decision
        self._log_step("Step 5", "Decision classification")
        decision_result = self.decision_classifier.classify(
            long_vol_score=composite.long_vol_score,
            short_vol_score=composite.short_vol_score,
            p_long=probabilities["p_long"],
            p_short=probabilities["p_short"],
            context=context,
        )
        self._log_step_done("Decision classification", decision_result)
        
        # Step 6: Map to strategies (LLM allowed here)
        self._log_step("Step 6", "Strategy mapping")
        strategy_candidates = []
        selected_strategy = None
        llm_strategy_selection = None
        strategy_run_mode = "decision_only"
        decisions_to_run = [decision_result.decision]
        
        if decision_result.decision == Decision.STAND_ASIDE:
            strategy_run_mode = "stand_aside_explore"
            decisions_to_run = [Decision.LONG_VOL, Decision.SHORT_VOL]
        
        for run_decision in decisions_to_run:
            candidates = self.strategy_mapper.get_candidates(
                decision=run_decision,
                context=context,
            )
            
            # Step 7 & 8: For each candidate, calculate strikes and EV
            for candidate in candidates:
                self._log_step("Step 7", f"Strike calculation ({candidate.name})")
                params = self.strategy_mapper.customize_parameters(candidate, context)
                
                # Calculate strikes
                market_context = self._build_market_context(input_data, features)
                strikes_result = self.strike_calculator.calculate_strikes(
                    strategy_params=params,
                    market_context=market_context,
                )
                self._log_step_done(f"Strike calculation ({candidate.name})", strikes_result)
                
                # Estimate EV
                self._log_step("Step 8", f"Edge estimation ({candidate.name})")
                probability = (
                    probabilities["p_long"].point_estimate
                    if candidate.direction == "long_vol"
                    else probabilities["p_short"].point_estimate
                )
                
                ev_result = self.ev_estimator.estimate(
                    strategy_params=params,
                    strikes=strikes_result["strikes"],
                    market_context=market_context,
                    probability=probability,
                )
                self._log_step_done(f"Edge estimation ({candidate.name})", ev_result)
                
                # Step 9: Check execution gates
                self._log_step("Step 9", f"Execution gate ({candidate.name})")
                gate_result = self.execution_gate.check(
                    ev_estimate=ev_result,
                    probability=probability,
                    liquidity=features["liquidity"],
                    strategy_tier=params["tier"],
                    context=context,
                )
                self._log_step_done(f"Execution gate ({candidate.name})", gate_result)
                
                strategy_candidates.append({
                    "name": candidate.name,
                    "tier": candidate.tier.value,
                    "direction": candidate.direction,
                    "decision_context": run_decision.value,
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
        
        # Select best executable strategy (only when not stand aside)
        if decision_result.decision != Decision.STAND_ASIDE:
            executable = [c for c in strategy_candidates if c["is_executable"]]
            if executable:
                # Sort by EV
                executable.sort(key=lambda x: x["ev"]["net_ev"], reverse=True)
                selected_strategy = executable[0]
        
        self._log_step_done("Strategy mapping", strategy_candidates)
        
        if strategy_candidates:
            self._log_step("Step 6b", "LLM strategy selection")
            llm_strategy_selection = self._llm_select_strategy(
                decision_result,
                probabilities,
                context,
                strategy_candidates,
            )
            self._log_step_done("LLM strategy selection", llm_strategy_selection)
        
        symbol = input_data["meta"].get("symbol", "UNKNOWN")
        date = input_data["meta"].get("datetime", "").split("T")[0] if input_data["meta"].get("datetime") else ""

        # Build full analysis output
        analysis = {
            "symbol": symbol,
            "date": date,
            "decision": decision_result.decision.value,
            "confidence": decision_result.confidence,
            "is_preferred": decision_result.is_preferred,
            "primary_reasons": decision_result.primary_reasons,
            "strategy_run_mode": strategy_run_mode,
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
            "llm_strategy_selection": llm_strategy_selection,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "warnings": self._collect_warnings(features, decision_result, strategy_candidates),
            "missing_fields": input_result.get("missing_fields", []),
        }
        
        self._log_step("Step 10", "Final report (LLM)")
        analysis["final_report"] = self._llm_generate_report(analysis)
        html_path = Path(output_file).parent / "dashboard.html"
        analysis["final_report_html"] = str(html_path)
        report_text = analysis["final_report"] or "Report unavailable."
        self._write_report_html(html_path, report_text, analysis)
        self._log_step_done("Final report (LLM)", {"report": bool(analysis["final_report"])})
        
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

    def _llm_select_strategy(
        self,
        decision_result: Any,
        probabilities: Dict[str, Any],
        context: Dict[str, Any],
        candidates: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to select a strategy from candidates."""
        try:
            prompt = format_strategy_prompt(
                decision=decision_result.decision.value,
                confidence=decision_result.confidence,
                is_preferred=decision_result.is_preferred,
                probabilities={
                    "p_long": probabilities["p_long"].point_estimate,
                    "p_short": probabilities["p_short"].point_estimate,
                },
                context=context,
                candidates=candidates,
            )
            response = self.llm_client.chat(
                prompt=prompt,
                system_prompt=get_strategy_system_prompt(),
                node_type="strategy",
                response_format="json",
            )
            return response.parse_json()
        except Exception:
            return None

    def _llm_generate_report(self, analysis: Dict[str, Any]) -> Optional[str]:
        """Generate a final markdown report with LLM."""
        try:
            prompt = format_report_prompt(analysis)
            response = self.llm_client.chat(
                prompt=prompt,
                system_prompt=get_report_system_prompt(),
                node_type="report",
            )
            return response.content
        except Exception:
            return None

    def _write_report_html(self, path: Path, markdown_text: str, analysis: Dict[str, Any]) -> None:
        """Write a dashboard-style HTML report for browser viewing."""
        symbol = analysis.get("symbol", "SYMBOL")
        date = analysis.get("date", "")
        title = f"{date}-{symbol}-Report" if date else f"{symbol}-Report"
        favicon = "https://www.google.com/s2/favicons?domain=google.com&sz=128"
        timestamp = analysis.get("timestamp", "")
        decision = analysis.get("decision", "UNKNOWN")
        p_long = analysis.get("probabilities", {}).get("p_long", 0.0)
        p_short = analysis.get("probabilities", {}).get("p_short", 0.0)
        candidates = analysis.get("candidates", [])
        selected_strategy = analysis.get("selected_strategy")

        def _inline_format(text: str) -> str:
            safe = html_lib.escape(text)
            safe = re.sub(r"\\*\\*(.+?)\\*\\*", r"<strong>\\1</strong>", safe)
            safe = re.sub(r"`([^`]+)`", r"<code>\\1</code>", safe)
            return safe

        def _is_table_separator(line: str) -> bool:
            stripped = line.strip().strip("|")
            if not stripped:
                return False
            for cell in stripped.split("|"):
                cell = cell.strip()
                if not cell:
                    continue
                if not all(ch in "-: " for ch in cell):
                    return False
            return True

        def _markdown_to_html(text: str) -> str:
            lines = (text or "").splitlines()
            parts = []
            i = 0
            while i < len(lines):
                raw = lines[i]
                line = raw.strip()
                if not line:
                    parts.append("<div class=\"spacer\"></div>")
                    i += 1
                    continue
                if line.startswith("### "):
                    parts.append(f"<h3>{_inline_format(line[4:])}</h3>")
                    i += 1
                    continue
                if line.startswith("## "):
                    parts.append(f"<h2>{_inline_format(line[3:])}</h2>")
                    i += 1
                    continue
                if line.startswith("# "):
                    parts.append(f"<h1>{_inline_format(line[2:])}</h1>")
                    i += 1
                    continue
                if line.startswith(">"):
                    parts.append(f"<blockquote>{_inline_format(line[1:].strip())}</blockquote>")
                    i += 1
                    continue
                if line.startswith("- ") or line.startswith("* "):
                    items = []
                    while i < len(lines):
                        cur = lines[i].strip()
                        if cur.startswith("- ") or cur.startswith("* "):
                            items.append(f"<li>{_inline_format(cur[2:])}</li>")
                            i += 1
                        else:
                            break
                    parts.append("<ul>" + "".join(items) + "</ul>")
                    continue
                if "|" in line and i + 1 < len(lines) and _is_table_separator(lines[i + 1]):
                    headers = [c.strip() for c in line.strip().strip("|").split("|")]
                    i += 2
                    rows = []
                    while i < len(lines):
                        row_line = lines[i].strip()
                        if "|" not in row_line:
                            break
                        cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
                        rows.append(cells)
                        i += 1
                    header_html = "".join(f"<th>{_inline_format(h)}</th>" for h in headers)
                    row_html = []
                    for row in rows:
                        row_html.append("<tr>" + "".join(f"<td>{_inline_format(c)}</td>" for c in row) + "</tr>")
                    parts.append(
                        "<table class=\"data-table\"><thead><tr>"
                        + header_html
                        + "</tr></thead><tbody>"
                        + "".join(row_html)
                        + "</tbody></table>"
                    )
                    continue
                parts.append(f"<p>{_inline_format(line)}</p>")
                i += 1
            return "\n".join(parts)

        report_html = _markdown_to_html(markdown_text)
        strategy_cards = []
        for candidate in candidates[:3]:
            name = candidate.get("name", "Unknown")
            direction = candidate.get("direction", "neutral")
            tier = candidate.get("tier", "")
            is_selected = selected_strategy and selected_strategy.get("name") == name
            strike_payload = candidate.get("strikes") or {}
            strike_text = json.dumps(strike_payload, ensure_ascii=False) if strike_payload else "暂无执行价"
            delta_class = "delta-neutral"
            if direction == "long_vol":
                delta_class = "delta-long"
            elif direction == "short_vol":
                delta_class = "delta-short"
            badge_label = "Selected" if is_selected else direction.replace("_", " ").title()
            strategy_cards.append(
                "<div class=\"strat-card\">"
                "<div class=\"strat-head\">"
                f"<div class=\"strat-name\">{html_lib.escape(name)}</div>"
                f"<span class=\"delta-badge {delta_class}\">{html_lib.escape(badge_label)}</span>"
                "</div>"
                f"<div style=\"font-size:13px;color:#475569;margin-bottom:8px;\">Tier: {html_lib.escape(str(tier))}</div>"
                f"<div class=\"strat-setup\">{html_lib.escape(strike_text)}</div>"
                "</div>"
            )
        strategy_cards_html = "".join(strategy_cards) if strategy_cards else "<p>暂无策略候选。</p>"
        decision_tag_class = "tag-blue"
        if decision in {"LONG_VOL", "ENTER_LONG", "BUY"}:
            decision_tag_class = "tag-green"
        elif decision in {"SHORT_VOL", "ENTER_SHORT", "SELL"}:
            decision_tag_class = "tag-red"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{html_lib.escape(title)}</title>
  <link rel="icon" href="{favicon}">
  <style>
:root {{ --bg-body: #f8fafc; --bg-card: #ffffff; --text-main: #0f172a; --text-sub: #64748b; --accent: #2563eb; --accent-light: #eff6ff; --border: #e2e8f0; --success: #10b981; --warning: #f59e0b; --danger: #ef4444; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "Microsoft YaHei", sans-serif; background: var(--bg-body); color: var(--text-main); line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }}
 .main-header {{ display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }}
 .symbol-logo {{ width: 48px; height: 48px; border-radius: 50%; background: white; border: 1px solid var(--border); padding: 4px; object-fit: contain; }}
 .header-info h1 {{ margin: 0; font-size: 24px; color: var(--text-main); }}
 .header-info .meta {{ color: var(--text-sub); font-size: 13px; }}
 .tab-nav {{ display: flex; border-bottom: 1px solid var(--border); margin-bottom: 20px; background: var(--bg-card); border-radius: 8px 8px 0 0; overflow: hidden; }}
 .tab-btn {{ padding: 12px 24px; border: none; background: none; cursor: pointer; font-weight: 600; color: var(--text-sub); border-bottom: 3px solid transparent; transition: all 0.2s; }}
 .tab-btn:hover {{ background: var(--accent-light); color: var(--accent); }}
 .tab-btn.active {{ color: var(--accent); border-bottom-color: var(--accent); }}
 .tab-content {{ display: none; animation: fadeIn 0.3s; }}
 .tab-content.active {{ display: block; }}
 @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: translateY(0); }} }}
 .card {{ background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 20px; overflow: hidden; }}
 .card-header {{ padding: 15px 20px; border-bottom: 1px solid var(--border); background: #f8fafc; font-weight: 600; font-size: 14px; text-transform: uppercase; color: var(--text-sub); letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center; }}
 .card-body {{ padding: 20px; }}
 .monitor-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 20px; }}
 .metric-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
 .metric-label {{ color: var(--text-sub); font-size: 13px; }}
 .metric-value {{ font-weight: 700; font-size: 16px; color: var(--text-main); }}
 .progress-container {{ background: #f1f5f9; height: 6px; border-radius: 3px; overflow: hidden; margin-top: 4px; }}
 .progress-bar {{ height: 100%; border-radius: 3px; transition: width 0.5s ease; }}
 .tag {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }}
 .tag-green {{ background: #dcfce7; color: #166534; }}
 .tag-red {{ background: #fee2e2; color: #991b1b; }}
 .tag-blue {{ background: #dbeafe; color: #1e40af; }}
 .tag-orange {{ background: #ffedd5; color: #9a3412; }}
 .delta-badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; background: #e3f2fd; color: #1565c0; margin-left: 10px; }}
 .delta-long {{ background: #e8f5e9; color: #2e7d32; }}
 .delta-short {{ background: #ffebee; color: #c62828; }}
 .delta-neutral {{ background: #f3e5f5; color: #7b1fa2; }}
 .strategy-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-top: 15px; }}
 .strat-card {{ border: 1px solid var(--border); border-radius: 8px; padding: 15px; background: #fff; transition: transform 0.2s; }}
 .strat-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
 .strat-head {{ display: flex; justify-content: space-between; margin-bottom: 10px; align-items: center; }}
 .strat-name {{ font-weight: 700; color: var(--text-main); }}
 .strat-setup {{ font-size: 13px; background: #f1f5f9; padding: 10px; border-radius: 6px; margin-top: 10px; font-family: "Menlo", "Monaco", monospace; color: #334155; line-height: 1.5; border-left: 3px solid #cbd5e1; white-space: pre-wrap; }}
 .markdown-body h2 {{ border-bottom: 2px solid var(--accent); padding-bottom: 8px; font-size: 1.4em; margin-top: 1.5em; }}
 .markdown-body h3 {{ color: var(--accent); font-size: 1.1em; margin-top: 1.2em; }}
 .markdown-body p {{ margin: 0 0 12px 0; color: var(--text-main); }}
 .markdown-body blockquote {{ border-left: 4px solid var(--accent); background: var(--accent-light); padding: 10px 15px; margin: 15px 0; border-radius: 0 4px 4px 0; color: #1e3a8a; font-style: italic; }}
 .markdown-body ul {{ padding-left: 20px; margin: 0 0 12px 0; }}
 .markdown-body li {{ margin: 6px 0; }}
 .markdown-body .spacer {{ height: 10px; }}
 .data-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
 .data-table th {{ background: #f8fafc; border-bottom: 2px solid #e2e8f0; padding: 12px; text-align: left; font-weight: 600; color: var(--text-sub); }}
 .data-table td {{ border-bottom: 1px solid #e2e8f0; padding: 12px; color: var(--text-main); }}
 .data-table tr:hover {{ background: #f1f5f9; }}
  </style>
  <script>
function openTab(evt, tabName) {{
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tab-content");
  for (i = 0; i < tabcontent.length; i++) {{
    tabcontent[i].className = tabcontent[i].className.replace(" active", "");
  }}
  tablinks = document.getElementsByClassName("tab-btn");
  for (i = 0; i < tablinks.length; i++) {{
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }}
  document.getElementById(tabName).className += " active";
  evt.currentTarget.className += " active";
}}
  </script>
</head>
<body>
  <div class="main-header">
    <img src="{favicon}" class="symbol-logo" onerror="this.src='{favicon}'">
    <div class="header-info">
      <h1>{html_lib.escape(symbol)} 量化仪表盘</h1>
      <div class="meta">最后更新: {html_lib.escape(timestamp)} • PHASE 3 引擎</div>
    </div>
  </div>

  <div class="tab-nav">
    <button class="tab-btn active" onclick="openTab(event, 'Latest')">🔍 实时监控</button>
    <button class="tab-btn" onclick="openTab(event, 'Analysis')">📘 基准分析</button>
    <button class="tab-btn" onclick="openTab(event, 'History')">📜 历史记录</button>
  </div>

  <div id="Latest" class="tab-content active">
    <div class="monitor-grid">
      <div class="card" style="border-top:4px solid var(--accent);">
        <div class="card-header"><span>决策状态</span> <span class="tag {decision_tag_class}">{html_lib.escape(decision)}</span></div>
        <div class="card-body">
          <div class="metric-row"><span class="metric-label">P(long)</span> <span class="metric-value">{p_long:.1%}</span></div>
          <div class="metric-row"><span class="metric-label">P(short)</span> <span class="metric-value">{p_short:.1%}</span></div>
          <div class="metric-row"><span class="metric-label">Confidence</span> <span class="metric-value">{analysis.get("confidence", 0.0):.1%}</span></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span>运行概览</span></div>
        <div class="card-body">
          <div class="metric-row"><span class="metric-label">Symbol</span> <span class="metric-value">{html_lib.escape(symbol)}</span></div>
          <div class="metric-row"><span class="metric-label">Date</span> <span class="metric-value">{html_lib.escape(date)}</span></div>
          <div class="metric-row"><span class="metric-label">Strategy Mode</span> <span class="metric-value">{html_lib.escape(analysis.get("strategy_run_mode", ""))}</span></div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span>策略推荐</span></div>
      <div class="card-body">
        <div class="strategy-container">
          {strategy_cards_html}
        </div>
      </div>
    </div>
  </div>

  <div id="Analysis" class="tab-content">
    <div class="card">
      <div class="card-header"><span>初始分析报告 (T0)</span></div>
      <div class="card-body">
        <div class="markdown-body">
          {report_html}
        </div>
      </div>
    </div>
  </div>

  <div id="History" class="tab-content">
    <div class="card">
      <div class="card-header"><span>快照历史</span></div>
      <div class="card-body">
        <p>暂无历史记录</p>
      </div>
    </div>
  </div>
</body>
</html>
"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(html)
    
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

    def _log_step(self, step: str, message: str) -> None:
        """Print pipeline progress to console with upgraded format."""
        now = datetime.now().strftime("%H:%M:%S")
        match = re.search(r"(\\d+)", step)
        step_num = match.group(1) if match else step
        step_label = f"{step_num}/{self.total_steps}" if str(step_num).isdigit() else step
        title = message
        divider = "┈" * 90
        print(f"🎯 [{step_label}] {title}")
        print("-" * 80)
        print(f"{now} | INFO     | 📍 Step {step_label}: {title}")
        print(divider)
        print(f"⚙️ [CODE: {title}] 开始执行")
        print(f"   {title}")
        print(f"{now} | INFO     | 🔧 [{title}] 开始执行")

    def _summarize_result(self, result: Any) -> Dict[str, Any]:
        """Summarize result type/size for logging."""
        if result is None:
            return {"type": "None", "count": 0}
        if isinstance(result, dict):
            return {"type": "dict", "count": len(result)}
        if isinstance(result, (list, tuple)):
            return {"type": "list", "count": len(result)}
        if hasattr(result, "__dict__"):
            return {"type": "object", "count": len(result.__dict__)}
        return {"type": type(result).__name__, "count": 0}

    def _log_step_done(self, title: str, result: Any = None) -> None:
        """Print step completion with summary."""
        now = datetime.now().strftime("%H:%M:%S")
        summary = self._summarize_result(result) if result is not None else None
        print("================================================================================")
        print(f"  ✓ [CODE: {title}] 执行成功")
        print("================================================================================")
        if summary is not None:
            print(f"  📋 结果类型: {summary['type']} (共 {summary['count']} 个字段)")
        print(f"{now} | SUCCESS  | ✅ [{title}] 执行完成")
        print(f"✅ {title} 完成")
    
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

        candidates = analysis.get("candidates", [])
        strategy_mode = analysis.get("strategy_run_mode", "decision_only")
        lines.extend([
            f"  Strategy Run Mode: {strategy_mode}",
            f"  Candidates Evaluated: {len(candidates)}",
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

        # Final report link (LLM)
        if analysis.get("final_report_html"):
            lines.extend([
                f"───────────────────────────────────────────────────────────────",
                f"  FINAL REPORT (LLM)",
                f"───────────────────────────────────────────────────────────────",
                f"",
                f"  Report: {analysis['final_report_html']}",
                f"",
            ])
        
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
        AAPL_i_2025-01-05 -> runtime/inputs/2025-01-05/AAPL_i_2025-01-05.json
        AAPL_o_2025-01-05 -> runtime/outputs/AAPL/2025-01-05/AAPL_o_2025-01-05.json
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
        stem = Path(name).stem
        parts = stem.split("_")
        if len(parts) >= 3 and parts[-2] == "i":
            date = parts[-1]
            dated_path = Path(runtime_dir) / "inputs" / date / name
            legacy_path = Path(runtime_dir) / "inputs" / name
            if dated_path.exists() or not legacy_path.exists():
                return str(dated_path)
        return str(Path(runtime_dir) / "inputs" / name)
    else:  # output
        stem = Path(name).stem
        symbol = None
        date = None
        parts = stem.split("_")
        if len(parts) >= 3 and parts[-2] == "o":
            symbol = parts[0].upper()
            date = parts[-1]
        if symbol and date:
            return str(Path(runtime_dir) / "outputs" / symbol / date / name)
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
