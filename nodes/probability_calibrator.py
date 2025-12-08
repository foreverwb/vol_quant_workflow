"""
ProbabilityCalibrator 节点 (#6001)
将 LongVolScore/ShortVolScore 转化为可信概率
"""
import json
from typing import Dict, Any

from .base import LLMNodeBase, NodeResult, register_node

# 支持两种运行方式
try:
    from ..prompts import PROBABILITY_CALIBRATOR_PROMPT
    from ..schemas import get_schema
except ImportError:
    from prompts import PROBABILITY_CALIBRATOR_PROMPT
    from schemas import get_schema


@register_node("probability_calibrator")
class ProbabilityCalibratorNode(LLMNodeBase):
    """
    概率校准节点
    
    功能：
    1. 根据评分计算做多/做空波动率的概率
    2. 应用三分类决策门槛
    3. 判定最终方向（做多波动率/做空波动率/观望）
    """
    
    async def execute(self, scores_result: Dict[str, Any]) -> NodeResult:
        """
        执行概率校准
        
        Args:
            scores_result: 信号评分结果
            
        Returns:
            NodeResult，structured_output 包含概率和决策方向
        """
        if not scores_result:
            return NodeResult(
                success=False,
                text="",
                error="Empty scores result"
            )
        
        try:
            # 获取配置参数
            decision_threshold_long = self._get_config_value(
                "DECISION_THRESHOLD_LONG", 1.0
            )
            decision_threshold_short = self._get_config_value(
                "DECISION_THRESHOLD_SHORT", 1.0
            )
            prob_threshold = self._get_config_value("PROB_THRESHOLD", 0.55)
            
            # 格式化输入
            scores_json = json.dumps(scores_result, ensure_ascii=False, indent=2)
            
            # 格式化 prompt
            system_content = PROBABILITY_CALIBRATOR_PROMPT.format_system(
                scores_result=scores_json,
                DECISION_THRESHOLD_LONG=decision_threshold_long,
                DECISION_THRESHOLD_SHORT=decision_threshold_short,
                PROB_THRESHOLD=prob_threshold
            )
            
            user_content = PROBABILITY_CALIBRATOR_PROMPT.format_user(
                scores_result=scores_json
            )
            
            # 获取 schema
            schema = get_schema("probability_calibrator")
            
            response = await self.client.chat(
                system_prompt=system_content,
                user_prompt=user_content,
                json_schema=schema
            )
            
            if response.success:
                return NodeResult(
                    success=True,
                    text=response.content,
                    structured_output=response.structured_output,
                    metadata={
                        "thresholds": {
                            "long": decision_threshold_long,
                            "short": decision_threshold_short,
                            "prob": prob_threshold
                        }
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
