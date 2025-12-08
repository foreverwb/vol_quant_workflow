"""
Router 节点
判断用户输入类型：VARIABLES / DATA / INVALID
"""
from typing import List

from .base import LLMNodeBase, NodeResult, register_node

# 支持两种运行方式
try:
    from ..prompts import ROUTER_PROMPT
except ImportError:
    from prompts import ROUTER_PROMPT


@register_node("router")
class RouterNode(LLMNodeBase):
    """
    Router 节点 - 判断输入类型
    
    输出:
        - VARIABLES: 用户提供标的代码、事件类型等变量信息
        - DATA: 用户回传 gexbot 图表数据
        - INVALID: 其他无效输入
    """
    
    async def execute(
        self,
        user_input: str = "",
        has_files: bool = False
    ) -> NodeResult:
        """
        执行路由判断
        
        Args:
            user_input: 用户输入文本
            has_files: 是否有文件上传
            
        Returns:
            NodeResult，text 字段为路由类型
        """
        # 如果有文件上传，直接返回 DATA
        if has_files:
            return NodeResult(
                success=True,
                text="DATA",
                metadata={"reason": "files_uploaded"}
            )
        
        # 如果没有输入，返回 INVALID
        if not user_input or not user_input.strip():
            return NodeResult(
                success=True,
                text="INVALID",
                metadata={"reason": "empty_input"}
            )
        
        try:
            # 调用 LLM 进行判断
            response = await self.client.chat(
                system_prompt=ROUTER_PROMPT.system,
                user_prompt=user_input
            )
            
            if response.success:
                # 清理输出，只保留关键词
                text = response.content.strip().upper()
                
                if "VARIABLES" in text:
                    route_type = "VARIABLES"
                elif "DATA" in text:
                    route_type = "DATA"
                else:
                    route_type = "INVALID"
                
                return NodeResult(
                    success=True,
                    text=route_type,
                    metadata={"raw_response": text}
                )
            
            return NodeResult(
                success=False,
                text="",
                error=response.error or "Unknown error"
            )
            
        except Exception as e:
            return NodeResult(
                success=False,
                text="",
                error=str(e)
            )
