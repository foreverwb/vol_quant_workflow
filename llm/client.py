"""
LLM Client - Unified interface for LLM API calls.
Supports multiple providers and models with automatic routing.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
import urllib.request
import urllib.error

from ..config import ModelConfig, get_orchestrator, get_settings


logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM API response container."""
    content: str
    model: str
    usage: Dict[str, int]
    latency_ms: float
    raw_response: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "latency_ms": self.latency_ms,
        }
    
    def parse_json(self) -> Optional[Dict[str, Any]]:
        """Parse content as JSON."""
        try:
            # Try to extract JSON from markdown code blocks
            content = self.content
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()
            
            return json.loads(content)
        except json.JSONDecodeError:
            return None


class LLMClient:
    """
    Unified LLM client with multi-model support.
    
    Usage:
        client = LLMClient()
        
        # Use default model
        response = client.chat("What is 2+2?")
        
        # Use specific agent model
        response = client.chat("Analyze this data", agent="agent5")
        
        # Use node-based routing
        response = client.chat("Calibrate probability", node_type="probability")
    """
    
    def __init__(self):
        """Initialize client with orchestrator and settings."""
        self.orchestrator = get_orchestrator()
        self.settings = get_settings()
        self._total_cost = 0.0
        self._request_count = 0
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        agent: Optional[str] = None,
        node_type: Optional[str] = None,
        model_override: Optional[ModelConfig] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        """
        Send a chat request to the LLM.
        
        Args:
            prompt: User message/prompt
            system_prompt: System message (optional)
            agent: Agent identifier for model routing (e.g., "agent3", "agent5")
            node_type: Pipeline node type for routing (e.g., "probability", "strategy")
            model_override: Override model config entirely
            temperature: Override temperature
            max_tokens: Override max tokens
            response_format: "json" for JSON mode
            
        Returns:
            LLMResponse with content and metadata
        """
        # Get model config
        if model_override:
            config = model_override
        elif node_type:
            config = self.orchestrator.get_model_for_node(node_type)
        elif agent:
            config = self.orchestrator.get_model(agent)
        else:
            config = self.orchestrator.default
        
        # Apply overrides
        temp = temperature if temperature is not None else config.temperature
        tokens = max_tokens if max_tokens is not None else config.max_tokens
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Build request
        request_body = {
            "model": config.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
        }
        
        if response_format == "json":
            request_body["response_format"] = {"type": "json_object"}
        
        # Make request with retry
        start_time = time.time()
        response = self._make_request(config, request_body)
        latency_ms = (time.time() - start_time) * 1000
        
        # Parse response
        content = response["choices"][0]["message"]["content"]
        usage = response.get("usage", {})
        
        # Log if enabled
        if self.orchestrator.log_api_calls:
            logger.info(f"LLM call: model={config.model}, latency={latency_ms:.0f}ms")
        if self.orchestrator.log_token_usage:
            logger.info(f"Token usage: {usage}")
        
        self._request_count += 1
        
        return LLMResponse(
            content=content,
            model=config.model,
            usage=usage,
            latency_ms=latency_ms,
            raw_response=response,
        )
    
    def chat_with_vision(
        self,
        prompt: str,
        image_url: str,
        system_prompt: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> LLMResponse:
        """
        Send a chat request with image input.
        
        Args:
            prompt: Text prompt
            image_url: URL or base64 data URL of image
            system_prompt: System message
            agent: Agent identifier (should be vision-capable)
            
        Returns:
            LLMResponse
        """
        # Get vision-capable model
        config = self.orchestrator.get_model(agent or "agent3")
        if not config.supports_vision:
            config = self.orchestrator.get_model("agent3")  # Fallback to agent3
        
        # Build messages with image
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": image_url}
                }
            ]
        })
        
        request_body = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        
        start_time = time.time()
        response = self._make_request(config, request_body)
        latency_ms = (time.time() - start_time) * 1000
        
        content = response["choices"][0]["message"]["content"]
        usage = response.get("usage", {})
        
        return LLMResponse(
            content=content,
            model=config.model,
            usage=usage,
            latency_ms=latency_ms,
            raw_response=response,
        )
    
    def _make_request(
        self,
        config: ModelConfig,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Make HTTP request to LLM API with retry logic.
        """
        url = f"{config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        }
        
        data = json.dumps(body).encode("utf-8")
        
        last_error = None
        for attempt in range(self.orchestrator.retry.max_retries):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                
                with urllib.request.urlopen(req, timeout=config.timeout) as resp:
                    response_data = json.loads(resp.read().decode("utf-8"))
                    return response_data
                    
            except urllib.error.HTTPError as e:
                last_error = e
                logger.warning(f"HTTP error {e.code} on attempt {attempt + 1}")
                if e.code >= 500:
                    # Server error, retry
                    delay = self.orchestrator.retry.retry_delay
                    if self.orchestrator.retry.exponential_backoff:
                        delay *= (2 ** attempt)
                    time.sleep(delay)
                else:
                    # Client error, don't retry
                    raise
                    
            except urllib.error.URLError as e:
                last_error = e
                logger.warning(f"URL error on attempt {attempt + 1}: {e}")
                delay = self.orchestrator.retry.retry_delay
                if self.orchestrator.retry.exponential_backoff:
                    delay *= (2 ** attempt)
                time.sleep(delay)
                
            except Exception as e:
                last_error = e
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")
                delay = self.orchestrator.retry.retry_delay
                time.sleep(delay)
        
        raise RuntimeError(f"LLM request failed after {self.orchestrator.retry.max_retries} attempts: {last_error}")
    
    @property
    def request_count(self) -> int:
        """Get total request count."""
        return self._request_count
    
    def reset_stats(self):
        """Reset usage statistics."""
        self._request_count = 0
        self._total_cost = 0.0


# Global client instance
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get global LLM client instance."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
