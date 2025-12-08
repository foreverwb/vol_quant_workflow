"""
DataValidator 节点 (#3001)
解析 gexbot 图表，提取核心字段
需要启用 vision 能力
"""
from typing import List, Dict, Any

from .base import LLMNodeBase, NodeResult, register_node

# 支持两种运行方式
try:
    from ..prompts import DATA_VALIDATOR_PROMPT
    from ..schemas import get_schema
except ImportError:
    from prompts import DATA_VALIDATOR_PROMPT
    from schemas import get_schema


@register_node("data_validator")
class DataValidatorNode(LLMNodeBase):
    """
    数据校验节点
    
    识别并提取 gexbot 图表中的关键数值：
    - VOL TRIGGER 相关
    - Gamma Walls
    - IV/HV 数据
    - 结构性指标
    
    需要启用 vision 能力来解析图表。
    """
    
    async def execute(self, files: List[str]) -> NodeResult:
        """
        执行数据校验
        
        Args:
            files: 图表文件路径列表
            
        Returns:
            NodeResult，structured_output 包含提取的核心字段
        """
        if not files:
            return NodeResult(
                success=False,
                text="",
                error="No files provided"
            )
        
        try:
            # 格式化文件列表
            files_text = "\n".join([f"- {f}" for f in files])
            user_content = DATA_VALIDATOR_PROMPT.format_user(files=files_text)
            
            # 获取 schema
            schema = get_schema("data_validator")
            
            # 使用视觉能力
            response = await self.client.chat(
                system_prompt=DATA_VALIDATOR_PROMPT.system,
                user_prompt=user_content,
                images=files,
                json_schema=schema
            )
            
            if response.success:
                return NodeResult(
                    success=True,
                    text=response.content,
                    structured_output=response.structured_output,
                    metadata={
                        "files_count": len(files),
                        "files": files
                    }
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
    
    def _extract_core_fields(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """从响应中提取核心字段"""
        if not response:
            return {}
        return response.get("core_fields", {})
    
    def _get_missing_fields(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取缺失字段列表"""
        if not response:
            return []
        return response.get("missing_fields", [])
