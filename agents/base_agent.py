"""
Agent基类
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from config.model_config import ModelConfig, get_model_config
from config.prompts import PROMPTS
from config.schemas import SCHEMAS, get_schema
from llm.llm_client import get_llm_client
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.model_config = get_model_config(agent_name)
        self.prompt_config = PROMPTS.get(agent_name, {})
        self.llm_client = get_llm_client()
    
    @abstractmethod
    async def run(self, *args, **kwargs) -> Dict[str, Any]:
        """运行Agent"""
        pass
    
    async def call_llm(
        self,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        schema_name: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """调用LLM"""
        
        # 使用默认prompt
        system = system_prompt or self.prompt_config.get("system", "")
        user = user_message or self.prompt_config.get("user", "")
        
        # 获取schema
        schema = None
        if schema_name:
            schema = get_schema(schema_name)
        elif self.agent_name in SCHEMAS:
            schema = get_schema(self.agent_name)
        
        logger.info(f"调用LLM - Agent: {self.agent_name}")
        
        result = await self.llm_client.chat(
            system_prompt=system,
            user_message=user,
            model_config=self.model_config,
            structured_output=schema,
            images=images
        )
        
        return result
    
    def render_template(self, template: str, **kwargs) -> str:
        """模板渲染"""
        import re
        result = template
        
        for key, value in kwargs.items():
            pattern = f"{{{{#{key}#}}}}"
            result = result.replace(pattern, str(value))
        
        return result
