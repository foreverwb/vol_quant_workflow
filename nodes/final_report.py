"""
FinalReport 节点 (#8001)
汇总所有分析结果并生成完整的可执行策略报告
"""
import json
from typing import Dict, Any

from .base import LLMNodeBase, NodeResult, register_node

# 支持两种运行方式
try:
    from ..prompts import FINAL_REPORT_PROMPT
except ImportError:
    from prompts import FINAL_REPORT_PROMPT


@register_node("final_report")
class FinalReportNode(LLMNodeBase):
    """
    最终决策报告节点
    
    汇总数据校验、特征计算、信号打分、概率校准、
    策略映射、行权价计算、Edge估算的所有结果，
    生成结构化的 Markdown 决策报告。
    """
    
    async def execute(
        self,
        core_fields: Dict[str, Any],
        features: Dict[str, Any],
        scores: Dict[str, Any],
        probability: Dict[str, Any],
        strategies: Dict[str, Any]
    ) -> NodeResult:
        """
        生成最终决策报告
        
        Args:
            core_fields: 核心字段数据
            features: 特征计算结果
            scores: 信号评分结果
            probability: 概率校准结果
            strategies: 策略方案（含行权价与 Edge 估算）
            
        Returns:
            NodeResult，text 字段为 Markdown 报告
        """
        try:
            # 格式化用户提示
            user_content = FINAL_REPORT_PROMPT.format_user(
                core_fields=json.dumps(core_fields, ensure_ascii=False, indent=2),
                features=json.dumps(features, ensure_ascii=False, indent=2),
                scores=json.dumps(scores, ensure_ascii=False, indent=2),
                probability=json.dumps(probability, ensure_ascii=False, indent=2),
                strategies=json.dumps(strategies, ensure_ascii=False, indent=2)
            )
            
            response = await self.client.chat(
                system_prompt=FINAL_REPORT_PROMPT.system,
                user_prompt=user_content
            )
            
            if response.success:
                return NodeResult(
                    success=True,
                    text=response.content,
                    metadata={
                        "symbol": core_fields.get("symbol", ""),
                        "direction": probability.get("decision_gate", {}).get("final_direction", ""),
                        "strategies_count": len(strategies.get("strategies", []))
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
