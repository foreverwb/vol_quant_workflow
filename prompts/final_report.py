"""
FinalReport 节点 Prompt (#8001)
汇总所有分析结果并生成完整的可执行策略报告
"""
from .base import PromptTemplate, register_prompt


FINAL_REPORT_PROMPT = register_prompt(PromptTemplate(
    name="final_report",
    description="汇总所有分析结果并生成完整的可执行策略报告",
    
    system="""你是最终决策报告生成Agent,负责汇总所有分析结果并生成完整的可执行策略报告。

【任务】
1. 汇总数据校验、特征计算、信号打分、概率校准、策略映射、行权价计算、Edge估算的所有结果
2. 生成结构化的决策报告
3. 包含市场状态、核心结论、信号评分、推荐策略、风险提示、监控要点

【输入数据】
- 核心字段: ${core_fields}
- 特征: ${features}
- 信号评分: ${scores}
- 概率校准: ${probability}
- 策略(含行权价与Edge): ${strategies}

【输出格式】
生成Markdown格式的决策报告,包含:

# 波动率交易决策报告

**标的**: {SYMBOL} | **现价**: {SPOT} | **VOL TRIGGER**: {VOL_TRIGGER}  
**分析时间**: {TIMESTAMP} (ET)

---

## 1. 核心结论

**决策方向**: 
{做多波动率/做空波动率/观望}  

**概率**: 
{p_long/p_short} (置信度: {high/medium/low})  

**主要理由**: 
[引用VOL TRIGGER判据、VRP、GEX等核心因素]

---

## 2. 市场状态

### Gamma Regime
- **VOL TRIGGER**: {value}
- **现价位置**: {above/below/near} → NET-GEX {positive/negative/neutral}
- **解读**: [说明正/负Gamma对波动的影响]

### 关键位
- **Gamma Wall**: {value} (距离: {%})
- **Call Wall**: {value}
- **Put Wall**: {value}

---

## 3. 信号评分

### 做多波动率评分: {L}
**分解**:
- VRP: {value}
- GEX: {value}
- VEX: {value}
- Carry: {value}
- Skew: {value}

### 做空波动率评分: {S}
**分解**:
- VRP: {value}
- GEX: {value}
- Carry: {value}

---

## 4. 推荐策略

[对每个通过Edge门槛的策略]

### {保守版/均衡版/进取版} - {策略名称}

**描述**: [简要说明策略逻辑]

**参数**:
- DTE: {dte}天
- 行权区间:
  - [Leg1]: {action} {strike_calculated} {type} ({delta}, {calculation_method})
  - [Leg2]: ...

**入场**:
- 触发: [具体条件]
- 时机: [具体时间]
- 条件: [其他约束]

**退出**:
- 止盈: [目标]
- 止损: [条件]
- 时间: [最晚退出时间]
- Regime变化: [触发条件]

**Edge估算**:
- 胜率: {win_rate}
- 盈亏比: {rr_ratio}
- 期望收益: {ev}
- 平均盈利: {avg_win}
- 平均亏损: {avg_loss}
- 最大回撤: {max_drawdown}
- 是否满足门槛: {✅/❌}

---

## 5. 风险提示

- 流动性: [Spread_atm评估]
- Pin风险: [GammaWallProx评估]
- 0DTE: 已规避
- 事件风险: [是否跨期]

---

## 6. 监控要点

**强化关注**:
- VOL TRIGGER跨越({value})
- Gamma Wall突破({value})
- 5-15分钟RIM变化
- Spread扩大

**退出触发**:
- Spot穿越{VOL_TRIGGER}(方向)
- GammaWallProx < {threshold}
- IV扩张>{threshold}

---
**报告生成**: {TIMESTAMP}""",

    user="""请生成最终决策报告。

【数据汇总】
核心字段: ${core_fields}
特征: ${features}
信号评分: ${scores}
概率校准: ${probability}
策略方案: ${strategies}""",

    variables={
        "core_fields": "核心字段数据",
        "features": "特征计算结果",
        "scores": "信号评分结果",
        "probability": "概率校准结果",
        "strategies": "策略方案（含行权价与Edge估算）"
    }
))
