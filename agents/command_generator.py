"""
命令生成Agent - 生成gexbot命令清单
"""
import json
import re
from agents.base_agent import BaseAgent
from config.schemas import SCHEMAS, get_schema
from config.prompts import PROMPTS
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class CommandGeneratorAgent(BaseAgent):
    """命令生成Agent"""
    
    def __init__(self):
        super().__init__("command_generator")
    
    async def run(self, query: str) -> Dict[str, Any]:
        """
        生成gexbot命令清单
        
        Args:
            query: 用户输入，包含标的代码、事件类型等信息
        
        Returns:
            包含命令清单的字典
        """
        
        # 获取schema
        schema = get_schema("command_generator")
        
        # 渲染用户消息模板
        user_prompt = PROMPTS.get("command_generator", {}).get("user", "")
        user_message = self.render_template(user_prompt, query=query)
        
        # 调用LLM
        result = await self.call_llm(
            user_message=user_message,
            schema_name="command_generator"
        )
        
        if result.get("error"):
            raise Exception(f"命令生成失败: {result.get('message')}")
        
        # 如果返回的是原始内容，需要解析
        if "raw_content" in result and isinstance(result["raw_content"], str):
            try:
                return json.loads(result["raw_content"])
            except json.JSONDecodeError:
                # 如果无法解析为JSON，返回原始结果
                return result
        
        return result
