"""
路由Agent - 判断输入类型
"""
from agents.base_agent import BaseAgent
from typing import Dict, Any

class RouterAgent(BaseAgent):
    """路由Agent"""
    
    def __init__(self):
        super().__init__("router")
    
    async def run(
        self,
        query: str,
        files: list = None
    ) -> Dict[str, Any]:
        """
        判断输入类型
        
        Returns:
            {
                "type": "VARIABLES" | "DATA" | "INVALID",
                "raw_output": "...",
                "confidence": 0.0-1.0
            }
        """
        # 构建用户消息
        user_msg = query
        if files:
            user_msg += f"\n【上传文件】\n{len(files)} 个文件"
        
        # 调用LLM
        result = await self.call_llm(
            user_message=user_msg,
            images=files if files else None
        )
        
        if result.get("error"):
            return {
                "type": "INVALID",
                "error": result.get("message")
            }
        
        content = result.get("content", "").strip().upper()
        
        # 简单置信度判断
        if content in ["VARIABLES", "DATA", "INVALID"]:
            return {
                "type": content,
                "raw_output": content,
                "confidence": 0.9
            }
        
        # 模糊匹配
        if "VARIABLE" in content:
            return {"type": "VARIABLES", "confidence": 0.7}
        elif "DATA" in content or "图" in content:
            return {"type": "DATA", "confidence": 0.7}
        else:
            return {"type": "INVALID", "confidence": 0.5}
