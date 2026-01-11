"""
Model Configuration - Multi-model orchestration support.
Allows different agents/nodes to use different LLM models.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import json

from .settings import get_settings

def _load_yaml(path: str) -> Dict[str, Any]:
    """Load YAML file (simple parser, no external dependency)."""
    result = {}
    current_section = None
    current_subsection = None
    
    with open(path, 'r') as f:
        for line in f:
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            # Determine indentation level
            indent = len(line) - len(line.lstrip())
            
            if ':' in stripped:
                key, _, value = stripped.partition(':')
                key = key.strip()
                value = value.strip()
                # Strip inline comments while preserving URLs
                if ' #' in value:
                    value = value.split(' #', 1)[0].strip()
                value = value.strip('"').strip("'")
                
                if indent == 0:
                    # Top-level key
                    current_section = key
                    current_subsection = None
                    if value:
                        result[key] = value
                    else:
                        result[key] = {}
                elif indent == 2 and current_section:
                    # Second-level key
                    current_subsection = key
                    if isinstance(result.get(current_section), dict):
                        if value:
                            result[current_section][key] = value
                        else:
                            result[current_section][key] = {}
                elif indent == 4 and current_section and current_subsection:
                    # Third-level key
                    if isinstance(result.get(current_section), dict):
                        if isinstance(result[current_section].get(current_subsection), dict):
                            # Convert value types
                            if value.lower() == 'true':
                                value = True
                            elif value.lower() == 'false':
                                value = False
                            elif value.replace('.', '').replace('-', '').isdigit():
                                value = float(value) if '.' in value else int(value)
                            result[current_section][current_subsection][key] = value
    
    return result


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 360
    top_p: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    supports_vision: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "top_p": self.top_p,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "supports_vision": self.supports_vision,
        }


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    retry_delay: float = 2.0
    exponential_backoff: bool = True


@dataclass
class CostTracking:
    """Cost tracking configuration."""
    enabled: bool = True
    alert_threshold_usd: float = 10.0


@dataclass
class ModelOrchestrator:
    """
    Multi-model orchestrator.
    Routes requests to appropriate models based on agent/node type.
    """
    default: ModelConfig = field(default_factory=ModelConfig)
    agents: Dict[str, ModelConfig] = field(default_factory=dict)
    retry: RetryConfig = field(default_factory=RetryConfig)
    cost_tracking: CostTracking = field(default_factory=CostTracking)
    log_api_calls: bool = True
    log_token_usage: bool = True
    log_latency: bool = True
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "ModelOrchestrator":
        """
        Load configuration from YAML file.
        
        Search order:
        1. Provided path
        2. ./model_config.yaml
        3. ./config/model_config.yaml
        4. ~/.vol_workflow/model_config.yaml
        """
        search_paths = [
            config_path,
            Path.cwd() / "model_config.yaml",
            Path.cwd() / "config" / "model_config.yaml",
            Path(__file__).parent / "model_config.yaml",
            Path(__file__).parent.parent / "model_config.yaml",
            Path.home() / ".vol_workflow" / "model_config.yaml",
        ]
        
        config_data = {}
        for path in search_paths:
            if path and Path(path).exists():
                config_data = _load_yaml(str(path))
                break
        
        if not config_data:
            # Return defaults
            return cls()
        
        settings = get_settings()
        # Parse default config
        default_data = config_data.get("default", {})
        default_config = ModelConfig(
            provider=default_data.get("provider", "openai"),
            model=default_data.get("model", "gpt-4"),
            api_key=default_data.get("api_key") or settings.llm.api_key or os.environ.get("DMXAPI_KEY") or os.environ.get("OPENAI_API_KEY"),
            base_url=default_data.get("base_url") or settings.llm.api_base,
            temperature=float(default_data.get("temperature", 0.3)),
            max_tokens=int(default_data.get("max_tokens", 4096)),
            timeout=int(default_data.get("timeout", 360)),
        )
        
        # Parse agent-specific configs
        agents = {}
        agents_data = config_data.get("agents", {})
        for agent_name, agent_data in agents_data.items():
            if isinstance(agent_data, dict):
                agents[agent_name] = ModelConfig(
                    provider=agent_data.get("provider", default_config.provider),
                    model=agent_data.get("model", default_config.model),
                    api_key=agent_data.get("api_key") or default_config.api_key,
                    base_url=agent_data.get("base_url") or default_config.base_url,
                    temperature=float(agent_data.get("temperature", default_config.temperature)),
                    max_tokens=int(agent_data.get("max_tokens", default_config.max_tokens)),
                    timeout=int(agent_data.get("timeout", default_config.timeout)),
                    top_p=float(agent_data.get("top_p", 1.0)),
                    presence_penalty=float(agent_data.get("presence_penalty", 0.0)),
                    frequency_penalty=float(agent_data.get("frequency_penalty", 0.0)),
                    supports_vision=agent_data.get("supports_vision", False),
                )
        
        # Parse retry config
        retry = RetryConfig(
            max_retries=int(config_data.get("max_retries", 3)),
            retry_delay=float(config_data.get("retry_delay", 2.0)),
            exponential_backoff=config_data.get("retry_exponential_backoff", True),
        )
        
        # Parse cost tracking
        cost_data = config_data.get("cost_tracking", {})
        cost_tracking = CostTracking(
            enabled=cost_data.get("enabled", True) if isinstance(cost_data, dict) else True,
            alert_threshold_usd=float(cost_data.get("alert_threshold_usd", 10.0)) if isinstance(cost_data, dict) else 10.0,
        )
        
        return cls(
            default=default_config,
            agents=agents,
            retry=retry,
            cost_tracking=cost_tracking,
            log_api_calls=config_data.get("log_api_calls", True),
            log_token_usage=config_data.get("log_token_usage", True),
            log_latency=config_data.get("log_latency", True),
        )
    
    def get_model(self, agent: Optional[str] = None) -> ModelConfig:
        """
        Get model configuration for an agent.
        
        Args:
            agent: Agent identifier (e.g., "agent3", "probability", "strategy")
                   If None, returns default config.
        
        Returns:
            ModelConfig for the specified agent
        """
        if agent and agent in self.agents:
            return self.agents[agent]
        return self.default
    
    def get_model_for_node(self, node_type: str) -> ModelConfig:
        """
        Get model configuration based on pipeline node type.
        
        Mapping:
        - probability -> agent5 (scene analysis)
        - strategy -> agent6 (strategy generation)
        - validation -> agent3 (data validation, vision)
        - report -> agent8 (final report)
        """
        node_agent_map = {
            "probability": "agent5",
            "calibration": "agent5",
            "strategy": "agent6",
            "strategy_selection": "agent6",
            "validation": "agent3",
            "data_validation": "agent3",
            "report": "agent8",
            "final_report": "agent8",
        }
        
        agent = node_agent_map.get(node_type)
        return self.get_model(agent)
    
    def list_agents(self) -> List[str]:
        """List all configured agents."""
        return list(self.agents.keys())


# Global orchestrator instance
_orchestrator: Optional[ModelOrchestrator] = None


def get_orchestrator(config_path: Optional[str] = None) -> ModelOrchestrator:
    """Get global orchestrator instance (singleton)."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ModelOrchestrator.load(config_path)
    return _orchestrator


def reload_orchestrator(config_path: Optional[str] = None) -> ModelOrchestrator:
    """Force reload orchestrator configuration."""
    global _orchestrator
    _orchestrator = ModelOrchestrator.load(config_path)
    return _orchestrator
