"""
update handler - Lightweight monitoring command.

Usage: vol updated -i INPUT_FILE -c OUTPUT_FILE

ALLOWED operations:
- Regime/volatility/structure/liquidity metrics
- Regime change detection
- Alert generation

FORBIDDEN operations:
- Probability calculation
- Strategy generation
- Strike selection
"""

import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..core.schema import InputSchema, OutputSchema
from ..core.config import Config, get_config
from ..core.types import UpdateOutput
from ..features import FeatureCalculator
from ..features.regime import detect_regime_change


class UpdateHandler:
    """
    Handles the `update` CLI command for lightweight monitoring.
    
    This command is restricted to:
    - Reading current market state
    - Computing regime and key metrics
    - Detecting regime changes
    - Generating alerts
    
    It does NOT:
    - Calculate probabilities
    - Generate strategies
    - Select strikes
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize handler."""
        self.config = config or get_config()
        self.feature_calculator = FeatureCalculator()
    
    def execute(
        self,
        input_file: str,
        output_file: str,
    ) -> Dict[str, Any]:
        """
        Execute the update command.
        
        Args:
            input_file: Path to input JSON file
            output_file: Path to output JSON file (cache)
            
        Returns:
            Dictionary with execution results
        """
        # Load and validate input
        input_result = self._load_input(input_file)
        if not input_result["success"]:
            return input_result
        
        input_data = input_result["data"]
        
        # Load existing output (cache)
        output_data = self._load_output(output_file)
        
        # Compute lightweight features
        features = self.feature_calculator.calculate_for_update(input_data)
        
        # Detect regime change
        previous_regime = self._get_previous_regime(output_data)
        current_regime = features["regime"]["regime_state"]
        regime_change = detect_regime_change(current_regime, previous_regime)
        
        # Generate alerts
        alerts = self._generate_alerts(features, regime_change)
        
        # Build update record
        update_record = self._build_update_record(
            input_data, features, regime_change, alerts
        )
        
        # Append to output cache
        self._append_update(output_data, update_record)
        
        # Save output
        self._save_output(output_file, output_data)
        
        return {
            "success": True,
            "update": update_record,
            "regime_changed": regime_change["regime_changed"],
            "alerts": alerts,
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
            }
        
        return {
            "success": True,
            "data": data,
        }
    
    def _load_output(self, path: str) -> Dict[str, Any]:
        """Load output file or create skeleton."""
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Return empty skeleton
        return {
            "symbol": "",
            "date": "",
            "last_update": "",
            "updates": [],
            "full_analysis": None,
            "gexbot_commands": [],
        }
    
    def _get_previous_regime(self, output_data: Dict[str, Any]) -> str:
        """Get previous regime state from cache."""
        updates = output_data.get("updates", [])
        if updates:
            return updates[-1].get("regime_state", "neutral")
        return "neutral"
    
    def _generate_alerts(
        self,
        features: Dict[str, Any],
        regime_change: Dict[str, Any],
    ) -> List[str]:
        """Generate alerts based on current state."""
        alerts = []
        
        regime = features["regime"]
        
        # Regime flip alert
        if regime_change["regime_changed"]:
            if regime_change["significance"] == "major":
                alerts.append(f"REGIME FLIP: {regime_change['transition']}")
            else:
                alerts.append(f"Regime shift: {regime_change['transition']}")
        
        # Near-trigger alert
        trigger_dist_pct = regime.get("trigger_distance_pct", 1.0)
        if trigger_dist_pct <= 0.002:
            alerts.append(f"AT TRIGGER: {trigger_dist_pct:.2%} from VOL TRIGGER")
        elif trigger_dist_pct <= 0.005:
            alerts.append(f"Near trigger: {trigger_dist_pct:.2%} from VOL TRIGGER")
        
        # Pin risk alert
        if regime.get("is_pin_risk"):
            alerts.append("PIN RISK: Near gamma wall in positive gamma regime")
        
        # High flip risk
        if regime.get("flip_risk") == "high":
            alerts.append("High regime flip risk")
        
        # VRP alert
        vrp_30d = features.get("vrp_30d", 0)
        if vrp_30d < -0.05:
            alerts.append(f"VRP NEGATIVE: IV below HV by {abs(vrp_30d):.1%}")
        elif vrp_30d > 0.10:
            alerts.append(f"VRP HIGH: IV above HV by {vrp_30d:.1%}")
        
        return alerts
    
    def _build_update_record(
        self,
        input_data: Dict[str, Any],
        features: Dict[str, Any],
        regime_change: Dict[str, Any],
        alerts: List[str],
    ) -> Dict[str, Any]:
        """Build update record for cache."""
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        regime = features["regime"]
        
        return {
            "timestamp": now,
            "regime_state": regime["regime_state"],
            "regime_changed": regime_change["regime_changed"],
            "vol_trigger": input_data["regime"]["vol_trigger"],
            "spot": input_data["market"]["spot"],
            "gamma_wall_proximity_pct": regime["gamma_wall_proximity_pct"],
            "key_metrics": {
                "vrp_30d": features.get("vrp_30d", 0),
                "trigger_distance_pct": regime.get("trigger_distance_pct", 0),
                "flip_risk": regime.get("flip_risk", "low"),
                "net_gex_sign": regime["net_gex_sign"],
            },
            "alerts": alerts,
        }
    
    def _append_update(
        self,
        output_data: Dict[str, Any],
        update_record: Dict[str, Any],
    ) -> None:
        """Append update record to output cache."""
        if "updates" not in output_data:
            output_data["updates"] = []
        
        output_data["updates"].append(update_record)
        output_data["last_update"] = update_record["timestamp"]
    
    def _save_output(self, path: str, data: Dict[str, Any]) -> None:
        """Save output data to file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def format_output(self, result: Dict[str, Any]) -> str:
        """Format result for console output."""
        if not result["success"]:
            return f"ERROR: {result.get('error', 'Unknown error')}"
        
        update = result["update"]
        
        lines = [
            f"───────────────────────────────────────────────────────────────",
            f"  VOL UPDATE - {update['timestamp']}",
            f"───────────────────────────────────────────────────────────────",
            f"",
            f"  Spot:         {update['spot']:.2f}",
            f"  VOL TRIGGER:  {update['vol_trigger']:.2f}",
            f"  Regime:       {update['regime_state'].upper()}",
            f"  Trigger dist: {update['key_metrics']['trigger_distance_pct']:.2%}",
            f"  Wall prox:    {update['gamma_wall_proximity_pct']:.2%}",
            f"  VRP (30d):    {update['key_metrics']['vrp_30d']:.2%}",
            f"",
        ]
        
        if result["regime_changed"]:
            lines.append(f"  ⚠️  REGIME CHANGED")
        
        if result["alerts"]:
            lines.append(f"  ALERTS:")
            for alert in result["alerts"]:
                lines.append(f"    • {alert}")
            lines.append("")
        
        lines.extend([
            f"───────────────────────────────────────────────────────────────",
            f"  Update saved to: {result['output_file']}",
            f"───────────────────────────────────────────────────────────────",
        ])
        
        return "\n".join(lines)


def resolve_file_path(name: str, file_type: str, runtime_dir: str = "runtime") -> str:
    """
    Resolve simplified file name to full path.
    
    Examples:
        AAPL_i_2025-01-05 -> runtime/inputs/AAPL_i_2025-01-05.json
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
    """CLI entry point for update command."""
    parser = argparse.ArgumentParser(
        description="Lightweight update - regime monitoring only",
        usage="updated -i INPUT -c OUTPUT"
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
    
    args = parser.parse_args()
    
    # Resolve file paths
    input_path = resolve_file_path(args.input_file, "input", args.runtime_dir)
    output_path = resolve_file_path(args.output_file, "output", args.runtime_dir)
    
    handler = UpdateHandler()
    result = handler.execute(
        input_file=input_path,
        output_file=output_path,
    )
    
    print(handler.format_output(result))


if __name__ == "__main__":
    main()
