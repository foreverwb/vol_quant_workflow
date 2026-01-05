"""
Gexbot command generator - Creates formatted gexbot commands.
Per strategy specification, commands follow fixed parameter order.
"""

from typing import List, Optional
from ..core.constants import (
    DEFAULT_STRIKES,
    DEFAULT_DTE_GEX,
    DEFAULT_DTE_VEX,
    DEFAULT_DTE_TERM,
    DEFAULT_DTE_SKEW,
    DEFAULT_DTE_TRIGGER,
    EXPIRATION_FILTER_WEEKLY,
    EXPIRATION_FILTER_MONTHLY,
    EXPIRATION_FILTER_ALL,
)


class GexbotCommandGenerator:
    """
    Generates gexbot commands per specification.
    
    Command formats (fixed parameter order):
    - !gexn / !gexr: {SYMBOL} {strikes} {dte}
    - !vexn: {SYMBOL} {strikes} {dte} {expiration_filter}
    - !vanna: {SYMBOL} {contract_filter} {dte} {expiration_filter}
    - !term: {SYMBOL} {dte} {expiration_filter}
    - !skew: {SYMBOL} {metric} {contract_or_option} {dte} {expiration_filter}
    - !surface / !surf: {SYMBOL} {metric} {contract_filter} {dte} {expiration_filter}
    - !trigger: {SYMBOL} {dte}
    """
    
    def __init__(self, symbol: str):
        """Initialize with symbol."""
        self.symbol = symbol.upper()
    
    def generate_standard_suite(self) -> List[str]:
        """
        Generate standard command suite per spec.
        Returns list of commands, one per line.
        """
        commands = []
        
        # Exposure and sensitivity
        commands.append(f"!gexn {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_GEX}")
        commands.append(f"!gexr {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_GEX}")
        commands.append(f"!vexn {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_VEX} {EXPIRATION_FILTER_ALL}")
        commands.append(f"!vanna {self.symbol} atm {DEFAULT_DTE_VEX} {EXPIRATION_FILTER_ALL}")
        commands.append(f"!vanna {self.symbol} ntm 90")
        commands.append(f"!trigger {self.symbol} {DEFAULT_DTE_TRIGGER}")
        
        # Term structure and skew
        commands.append(f"!term {self.symbol} {DEFAULT_DTE_TERM} {EXPIRATION_FILTER_WEEKLY}")
        commands.append(f"!term {self.symbol} {DEFAULT_DTE_TERM} {EXPIRATION_FILTER_MONTHLY}")
        commands.append(f"!skew {self.symbol} ivmid atm {DEFAULT_DTE_SKEW}")
        commands.append(f"!skew {self.symbol} ivmid ntm {DEFAULT_DTE_SKEW}")
        commands.append(f"!skew {self.symbol} ivmid put {DEFAULT_DTE_SKEW} {EXPIRATION_FILTER_WEEKLY}")
        
        # Surface (baseline + liquidity)
        commands.append(f"!surface {self.symbol} ivmid {DEFAULT_DTE_GEX}")
        commands.append(f"!surface {self.symbol} ivmid ntm {DEFAULT_DTE_GEX}")
        commands.append(f"!surface {self.symbol} ivask ntm {DEFAULT_DTE_GEX}")
        commands.append(f"!surface {self.symbol} spread atm {DEFAULT_DTE_GEX}")
        commands.append(f"!surface {self.symbol} extrinsic ntm 45 {EXPIRATION_FILTER_WEEKLY}")
        
        # Structure-surface overlay
        commands.append(f"!surface {self.symbol} gex ntm {DEFAULT_DTE_GEX}")
        commands.append(f"!surface {self.symbol} vex ntm {DEFAULT_DTE_VEX}")
        
        return commands
    
    def generate_minimum_suite(self) -> List[str]:
        """
        Generate minimum required command suite.
        Per spec: trigger, gexr, vexn, ivmid surface, ivask, spread, skew
        """
        commands = [
            f"!trigger {self.symbol} {DEFAULT_DTE_TRIGGER}",
            f"!gexr {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_GEX}",
            f"!vexn {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_VEX} {EXPIRATION_FILTER_ALL}",
            f"!surface {self.symbol} ivmid {DEFAULT_DTE_GEX}",
            f"!surface {self.symbol} ivask ntm {DEFAULT_DTE_GEX}",
            f"!surface {self.symbol} spread atm {DEFAULT_DTE_GEX}",
            f"!skew {self.symbol} ivmid atm {DEFAULT_DTE_SKEW}",
        ]
        return commands
    
    def generate_event_suite(self) -> List[str]:
        """
        Generate event-specific command suite.
        Per spec: ivmid, extrinsic, theta, gex, vex, trigger
        """
        commands = [
            f"!trigger {self.symbol} {DEFAULT_DTE_TRIGGER}",
            f"!gexn {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_GEX}",
            f"!gexr {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_GEX}",
            f"!vexn {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_VEX} {EXPIRATION_FILTER_ALL}",
            f"!surface {self.symbol} ivmid {DEFAULT_DTE_GEX}",
            f"!surface {self.symbol} extrinsic ntm 45 {EXPIRATION_FILTER_WEEKLY}",
            f"!surface {self.symbol} theta atm 21 {EXPIRATION_FILTER_WEEKLY}",
        ]
        return commands
    
    def generate_intraday_suite(self) -> List[str]:
        """
        Generate intraday monitoring suite.
        Per spec: gamma, gex, spread, ivask, skew, trigger
        """
        commands = [
            f"!trigger {self.symbol} {DEFAULT_DTE_TRIGGER}",
            f"!gexr {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_GEX}",
            f"!surface {self.symbol} gamma atm 30 {EXPIRATION_FILTER_WEEKLY}",
            f"!surface {self.symbol} spread atm {DEFAULT_DTE_GEX}",
            f"!surface {self.symbol} ivask ntm {DEFAULT_DTE_GEX}",
            f"!skew {self.symbol} ivmid atm {DEFAULT_DTE_SKEW}",
        ]
        return commands
    
    def generate_post_event_suite(self) -> List[str]:
        """
        Generate post-event analysis suite.
        Per spec: ivmid, extrinsic, vex, theta, vanna, trigger
        """
        commands = [
            f"!trigger {self.symbol} {DEFAULT_DTE_TRIGGER}",
            f"!surface {self.symbol} ivmid {DEFAULT_DTE_GEX}",
            f"!surface {self.symbol} extrinsic ntm 45 {EXPIRATION_FILTER_WEEKLY}",
            f"!vexn {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_VEX} {EXPIRATION_FILTER_ALL}",
            f"!surface {self.symbol} theta atm 21 {EXPIRATION_FILTER_WEEKLY}",
            f"!vanna {self.symbol} atm {DEFAULT_DTE_VEX} {EXPIRATION_FILTER_ALL}",
        ]
        return commands
    
    def generate_long_term_suite(self) -> List[str]:
        """
        Generate long-term analysis suite.
        Per spec: term, vega, rho, vex
        """
        commands = [
            f"!term {self.symbol} {DEFAULT_DTE_TERM} {EXPIRATION_FILTER_WEEKLY}",
            f"!term {self.symbol} {DEFAULT_DTE_TERM} {EXPIRATION_FILTER_MONTHLY}",
            f"!surface {self.symbol} vega atm 60",
            f"!surface {self.symbol} rho atm {DEFAULT_DTE_VEX}",
            f"!vexn {self.symbol} {DEFAULT_STRIKES} {DEFAULT_DTE_VEX} {EXPIRATION_FILTER_ALL}",
        ]
        return commands
    
    def generate_diagnostic_suite(self) -> List[str]:
        """
        Generate extended diagnostic suite.
        Per spec: gamma, vega, theta, rho surfaces
        """
        commands = [
            f"!surface {self.symbol} gamma atm 30 {EXPIRATION_FILTER_WEEKLY}",
            f"!surface {self.symbol} vega atm 60",
            f"!surface {self.symbol} theta atm 21 {EXPIRATION_FILTER_WEEKLY}",
            f"!surface {self.symbol} rho atm {DEFAULT_DTE_VEX}",
        ]
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
            
        Returns:
            List of commands
        """
        context_map = {
            "standard": self.generate_standard_suite,
            "minimum": self.generate_minimum_suite,
            "event": self.generate_event_suite,
            "intraday": self.generate_intraday_suite,
            "post_event": self.generate_post_event_suite,
            "long_term": self.generate_long_term_suite,
        }
        
        generator = context_map.get(context, self.generate_standard_suite)
        commands = generator()
        
        if include_diagnostic:
            commands.extend(self.generate_diagnostic_suite())
        
        return commands
