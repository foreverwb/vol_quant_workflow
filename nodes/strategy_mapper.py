"""
StrategyMapper 节点 (#7001)
根据决策方向生成可执行的期权策略

支持上下文感知：
- 策略黑名单 (Crash 风险禁用 Short Put 等)
- 动态 DTE 建议 (Squeeze/财报/高波动)
- Delta 偏好调整
"""
import json
from typing import Dict, Any, Optional, Set

from .base import LLMNodeBase, NodeResult, register_node

# 支持两种运行方式
try:
    from ..prompts import STRATEGY_MAPPER_PROMPT
    from ..schemas import get_schema
except ImportError:
    from prompts import STRATEGY_MAPPER_PROMPT
    from schemas import get_schema


@register_node("strategy_mapper")
class StrategyMapperNode(LLMNodeBase):
    """
    策略映射节点
    
    功能：
    1. 根据 decision_gate 的 final_direction 选择策略类型
    2. 生成三档策略（进取/均衡/保守）
    3. 估算每个策略的胜率、盈亏比、期望收益
    4. 确保所有策略满足 Edge 门槛
    5. [新增] 应用策略黑名单和动态 DTE
    """
    
    async def execute(
        self,
        probability_result: Dict[str, Any],
        core_fields: Dict[str, Any],
        features: Dict[str, Any],
        scores: Dict[str, Any],
        context_params: Optional[Dict[str, Any]] = None
    ) -> NodeResult:
        """
        执行策略映射
        
        Args:
            probability_result: 概率校准结果
            core_fields: 核心字段数据
            features: 特征计算结果
            scores: 信号评分结果
            context_params: Meso 上下文参数 (可选)
                - strategy_blacklist: 策略黑名单
                - suggested_dte_min/max: DTE 建议
                - dte_reason: DTE 原因
                - suggested_delta_bias: Delta 偏好
            
        Returns:
            NodeResult，structured_output 包含策略列表
        """
        try:
            # 获取配置参数
            edge_rr_threshold = self._get_config_value("EDGE_RR_THRESHOLD", 1.5)
            
            # 解析上下文参数
            ctx = context_params or {}
            strategy_blacklist = set(ctx.get('strategy_blacklist', []))
            suggested_dte_min = ctx.get('suggested_dte_min', 30)
            suggested_dte_max = ctx.get('suggested_dte_max', 45)
            dte_reason = ctx.get('dte_reason', '标准周期')
            delta_bias = ctx.get('suggested_delta_bias', 'neutral')
            is_squeeze = ctx.get('is_squeeze', False)
            
            # 构建上下文约束信息 (注入到 prompt)
            context_constraints = self._build_context_constraints(
                strategy_blacklist, 
                suggested_dte_min, 
                suggested_dte_max,
                dte_reason,
                delta_bias,
                is_squeeze
            )
            
            # 格式化 prompt
            system_content = STRATEGY_MAPPER_PROMPT.format_system(
                probability_result=json.dumps(probability_result, ensure_ascii=False),
                core_fields=json.dumps(core_fields, ensure_ascii=False),
                features=json.dumps(features, ensure_ascii=False),
                EDGE_RR_THRESHOLD=edge_rr_threshold,
                context_constraints=context_constraints  # 新增
            )
            
            user_content = STRATEGY_MAPPER_PROMPT.format_user(
                core_fields=json.dumps(core_fields, ensure_ascii=False),
                features=json.dumps(features, ensure_ascii=False),
                scores=json.dumps(scores, ensure_ascii=False),
                probability_result=json.dumps(probability_result, ensure_ascii=False)
            )
            
            # 获取 schema
            schema = get_schema("strategy_mapper")
            
            response = await self.client.chat(
                system_prompt=system_content,
                user_prompt=user_content,
                json_schema=schema
            )
            
            if response.success:
                # 获取决策方向
                direction = "观望"
                if probability_result:
                    decision_gate = probability_result.get("decision_gate", {})
                    direction = decision_gate.get("final_direction", "观望")
                
                # 后处理：过滤黑名单策略
                structured_output = response.structured_output
                if structured_output and strategy_blacklist:
                    structured_output = self._filter_blacklisted_strategies(
                        structured_output, 
                        strategy_blacklist
                    )
                
                return NodeResult(
                    success=True,
                    text=response.content,
                    structured_output=structured_output,
                    metadata={
                        "direction": direction,
                        "edge_threshold": edge_rr_threshold,
                        "context_aware": bool(context_params),
                        "blacklist_applied": list(strategy_blacklist) if strategy_blacklist else [],
                        "dte_range": f"{suggested_dte_min}-{suggested_dte_max}D"
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
    
    def _build_context_constraints(
        self,
        blacklist: Set[str],
        dte_min: int,
        dte_max: int,
        dte_reason: str,
        delta_bias: str,
        is_squeeze: bool
    ) -> str:
        """构建上下文约束信息"""
        constraints = []
        
        # 策略黑名单
        if blacklist:
            blacklist_str = ", ".join(blacklist)
            constraints.append(f"【⚠️ 策略黑名单】以下策略被禁用: {blacklist_str}")
        
        # DTE 建议
        constraints.append(f"【DTE 建议】{dte_min}-{dte_max}天 ({dte_reason})")
        
        # Delta 偏好
        if delta_bias == "bullish":
            constraints.append("【Delta 偏好】偏多，优先选择正 Delta 结构")
        elif delta_bias == "bearish":
            constraints.append("【Delta 偏好】偏空，优先选择负 Delta 结构")
        
        # Squeeze 模式
        if is_squeeze:
            constraints.append("【🔥 Squeeze 模式】优先 Gamma 策略 (Long Call/Straddle)，缩短 DTE")
        
        return "\n".join(constraints) if constraints else "无特殊约束"
    
    def _filter_blacklisted_strategies(
        self, 
        output: Dict[str, Any], 
        blacklist: Set[str]
    ) -> Dict[str, Any]:
        """
        从输出中过滤黑名单策略
        
        策略名称映射:
        - short_put -> Short Put, Cash Secured Put
        - short_strangle -> Short Strangle
        - short_call -> Short Call, Covered Call
        - iron_condor -> Iron Condor
        """
        if not output or 'strategies' not in output:
            return output
        
        # 策略名称到黑名单 key 的映射
        name_to_key = {
            'short put': 'short_put',
            'cash secured put': 'short_put',
            'naked put': 'short_put',
            'short strangle': 'short_strangle',
            'strangle sell': 'short_strangle',
            'short call': 'short_call',
            'naked call': 'short_call',
            'covered call': 'covered_call',
            'iron condor': 'iron_condor',
            'short straddle': 'short_straddle',
        }
        
        filtered_strategies = []
        for strategy in output.get('strategies', []):
            strategy_name = strategy.get('name', '').lower()
            
            # 检查是否在黑名单中
            is_blacklisted = False
            for name_key, blacklist_key in name_to_key.items():
                if name_key in strategy_name and blacklist_key in blacklist:
                    is_blacklisted = True
                    print(f"  [Blacklist] 过滤策略: {strategy.get('name')}")
                    break
            
            if not is_blacklisted:
                filtered_strategies.append(strategy)
        
        output['strategies'] = filtered_strategies
        output['_blacklist_filtered'] = True
        
        return output
