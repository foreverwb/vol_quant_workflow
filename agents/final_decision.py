"""
最终决策Agent - 生成完整报告
"""
from agents.base_agent import BaseAgent
from models.data_models import AnalysisResult
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class FinalDecisionAgent(BaseAgent):
    """最终决策Agent"""
    
    def __init__(self):
        super().__init__("final_decision")
    
    async def generate_report(
        self,
        analysis_result: AnalysisResult
    ) -> str:
        """生成最终决策报告"""
        
        # 组织数据
        validation = analysis_result.validation
        features = analysis_result.features
        signals = analysis_result.signals
        scores = analysis_result.scores
        probability = analysis_result.probability
        decision = analysis_result.decision
        strategies = analysis_result.strategies
        
        # 构建Markdown报告
        report = f"""# 波动率交易决策报告

**标的**: {validation.core_fields.symbol} | **现价**: ${validation.core_fields.spot:.2f} | **VOL TRIGGER**: ${validation.core_fields.vol_trigger:.2f}  
**分析时间**: {validation.timestamp} (ET)

---

## 1. 核心结论

**决策方向**: {decision.final_direction.value}  
**概率**: {probability.p_long:.1%} (做多) / {probability.p_short:.1%} (做空) | 置信度: {probability.confidence}  

**主要理由**:
- VRP (事件周): {features.vrp_ew:.4f} - {"正VRP表示IV > HV，做多波动率有利" if features.vrp_ew > 0 else "负VRP表示IV < HV，做空波动率有利"}
- GEX Level: {features.gex_level} - {"负GEX环境，趋势倾向" if features.gex_level < 0 else "正GEX环境，区间倾向"}
- Pin Risk: {features.pin_risk} - {"存在Pin风险" if features.pin_risk < 0 else "无明显Pin风险"}

---

## 2. 市场状态分析

### Gamma Regime

- **VOL TRIGGER**: ${validation.core_fields.vol_trigger:.2f}
- **现价位置**: {validation.core_fields.spot_vs_trigger.upper()} (距离: {abs(validation.core_fields.spot - validation.core_fields.vol_trigger):.2f})
- **NET-GEX符号**: {validation.core_fields.net_gex_sign.upper()}
- **解读**: Spot {validation.core_fields.spot_vs_trigger} VOL TRIGGER意味着 {self._interpret_gex(validation.core_fields.net_gex_sign)}

### 关键位

- **Gamma Wall**: ${validation.core_fields.gamma_wall:.2f} (距离: {validation.core_fields.gamma_wall_prox:.2%})
- **Call Wall**: ${validation.core_fields.call_wall:.2f} (若有)
- **Put Wall**: ${validation.core_fields.put_wall:.2f} (若有)

---

## 3. 信号评分分解

### 做多波动率评分: {scores.long_vol_score:.3f}

**成分分解**:
- VRP: {scores.score_breakdown['long']['vrp']:.3f}
- GEX: {scores.score_breakdown['long']['gex']:.3f}
- VEX: {scores.score_breakdown['long']['vex']:.3f}
- Carry: {scores.score_breakdown['long']['carry']:.3f}
- Skew: {scores.score_breakdown['long']['skew']:.3f}

### 做空波动率评分: {scores.short_vol_score:.3f}

**成分分解**:
- VRP: {scores.score_breakdown['short']['vrp']:.3f}
- GEX: {scores.score_breakdown['short']['gex']:.3f}
- Carry: {scores.score_breakdown['short']['carry']:.3f}

---

## 4. 推荐策略

"""
        
        if strategies and strategies.strategies:
            for i, strategy in enumerate(strategies.strategies, 1):
                report += f"""### {i}. {strategy.tier.value} - {strategy.structure}

**描述**: {strategy.description}

**参数**:
- DTE: {strategy.dte}
- 行权区间:
"""
                for j, leg in enumerate(strategy.legs, 1):
                    strike_info = f"${leg.strike_calculated:.2f}" if leg.strike_calculated else leg.strike
                    report += f"  - Leg {j}: {leg.action.value.upper()} {leg.type.value.upper()} @ {strike_info}"
                    if leg.calculation_method:
                        report += f" (方法: {leg.calculation_method})"
                    report += "\n"
                
                report += f"""
**入场**:
- 触发: {strategy.entry.trigger}
- 时机: {strategy.entry.timing}
- 条件: {strategy.entry.condition}

**退出**:
- 止盈: {strategy.exit.profit_target}
- 止损: {strategy.exit.stop_loss}
- 时间: {strategy.exit.time_decay}
- Regime变化: {strategy.exit.regime_change}

**Edge估算**:
- 胜率: {strategy.edge_estimate.win_rate}
- 盈亏比: {strategy.edge_estimate.rr_ratio}
- 期望收益: {strategy.edge_estimate.ev}
- 满足门槛: {'✅ 是' if strategy.edge_estimate.meets_threshold else '❌ 否'}

---

"""
        
        report += """## 5. 风险提示

- **流动性**: """
        
        if validation.core_fields.spread_atm:
            report += f"ATM Spread = {validation.core_fields.spread_atm:.2%} - "
            if validation.core_fields.spread_atm > 0.01:
                report += "流动性一般，需警惕滑点风险\n"
            else:
                report += "流动性充足\n"
        else:
            report += "未知\n"
        
        report += f"- **Pin风险**: {self._interpret_pin_risk(features.pin_risk)}\n"
        report += f"- **事件风险**: 已跨越事件周期\n"
        
        report += """
## 6. 监控要点

**强化关注**:
- VOL TRIGGER 跨越 ("""
        report += f"${validation.core_fields.vol_trigger:.2f})\n"
        report += f"- Gamma Wall 突破 (${validation.core_fields.gamma_wall:.2f})\n"
        report += """- 5-15分钟RIM变化
- Spread 扩大 >50%

**退出触发**:
- Spot 穿越 VOL TRIGGER (反向方向)
- GammaWallProx < 0.5%
- IV 扩张 > 25%

---

**报告生成**: """ + analysis_result.timestamp

        return report
    
    @staticmethod
    def _interpret_gex(net_gex_sign: str) -> str:
        """解释GEX含义"""
        if net_gex_sign.lower() == "negative":
            return "负GEX环境，市场具有趋势性，做多波动率有利"
        elif net_gex_sign.lower() == "positive":
            return "正GEX环境，市场具有区间性，做空波动率有利"
        else:
            return "中性GEX环境，市场易翻转"
    
    @staticmethod
    def _interpret_pin_risk(pin_risk: int) -> str:
        """解释Pin风险"""
        if pin_risk < 0:
            return "存在明显Pin风险，可能影响期权delta对冲效果"
        else:
            return "暂无明显Pin风险"
