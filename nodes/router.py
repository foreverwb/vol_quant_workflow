"""
路由节点 - 判断输入类型
"""
from datetime import datetime
from typing import Optional

try:
    from .base import BaseNode, NodeResult
    from ..core.logger import NodeLogger
except ImportError:
    from nodes.base import BaseNode, NodeResult
    from core.logger import NodeLogger


class RouterNode(BaseNode):
    """
    路由节点
    
    判断用户输入类型:
    - VARIABLES: 用户只提供了标的，需要生成命令清单
    - DATA: 用户上传了图表数据，可以开始分析
    - INVALID: 无效输入
    """
    
    NODE_NAME = "router"
    
    SYSTEM_PROMPT = """你是一个输入类型判断器。

根据用户输入判断类型：
1. VARIABLES - 用户提供了股票标的信息，但没有上传数据图表
2. DATA - 用户上传了数据截图/图表文件
3. INVALID - 无法识别的输入

只返回以下三个单词之一: VARIABLES, DATA, INVALID"""

    async def execute(
        self, 
        user_input: str = "",
        has_files: bool = False
    ) -> NodeResult:
        """
        执行路由判断
        
        Args:
            user_input: 用户输入文本
            has_files: 是否有上传文件
        """
        start_time = datetime.now()
        self._log_start(f"input='{user_input[:50]}...', has_files={has_files}")
        
        try:
            # 快速判断
            if has_files:
                result = NodeResult(
                    success=True, 
                    text="DATA",
                    metadata={"method": "quick_check"}
                )
                self.logger.info("快速判断: 检测到文件上传 -> DATA")
                self._log_end(result)
                return result
            
            if not user_input.strip():
                result = NodeResult(
                    success=True, 
                    text="INVALID",
                    metadata={"method": "quick_check"}
                )
                self.logger.info("快速判断: 空输入 -> INVALID")
                self._log_end(result)
                return result
            
            # LLM 判断
            self._log_llm_call(user_input)
            
            response = await self.llm_client.chat(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_input
            )
            
            # 记录 LLM 响应
            model_name = getattr(self.llm_client.config, 'name', 'unknown')
            self.logger.log_llm_response(response, model_name)
            
            # 解析结果
            route_type = response.strip().upper()
            if route_type not in ["VARIABLES", "DATA", "INVALID"]:
                self.logger.warning(f"LLM 返回非预期值: {route_type}, 默认为 INVALID")
                route_type = "INVALID"
            
            duration = (datetime.now() - start_time).total_seconds()
            result = NodeResult(
                success=True,
                text=route_type,
                duration=duration,
                model_used=model_name,
                metadata={"method": "llm"}
            )
            
            self._log_end(result)
            return result
            
        except Exception as e:
            self.logger.error(f"路由判断失败: {e}", exception=e)
            return NodeResult(success=False, error=str(e))