"""
CommandGenerator 节点 (#2001)
生成 gexbot 数据抓取命令清单
"""
from .base import LLMNodeBase, NodeResult, register_node

# 支持两种运行方式
try:
    from ..prompts import COMMAND_GENERATOR_PROMPT
except ImportError:
    from prompts import COMMAND_GENERATOR_PROMPT


@register_node("command_generator")
class CommandGeneratorNode(LLMNodeBase):
    """
    命令清单生成节点
    
    根据用户提供的变量信息（标的代码、事件类型、DTE等），
    生成标准化的 gexbot 数据抓取命令清单。
    """
    
    async def execute(self, user_input: str) -> NodeResult:
        """
        执行命令生成
        
        Args:
            user_input: 用户输入的变量信息
            
        Returns:
            NodeResult，text 字段为命令清单
        """
        if not user_input or not user_input.strip():
            return NodeResult(
                success=False,
                text="",
                error="Empty user input"
            )
        
        try:
            response = await self.client.chat(
                system_prompt=COMMAND_GENERATOR_PROMPT.system,
                user_prompt=user_input
            )
            
            if response.success:
                return NodeResult(
                    success=True,
                    text=response.content,
                    metadata={"input": user_input}
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
