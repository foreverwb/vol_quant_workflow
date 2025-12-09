"""
ProbabilityCalibrator 节点 Prompt (#6001)
将信号评分转化为可执行的概率判断和方向决策
"""
from .base import PromptTemplate, register_prompt


PROBABILITY_CALIBRATOR_PROMPT = register_prompt(PromptTemplate(
    name="probability_calibrator",
    description="将信号评分转化为概率判断和三分类方向决策",
    
    system="""你是概率校准模块，负责将量化信号转化为可交易的概率判断。

## 输入数据
- LongVolScore (L): 做多波动率综合评分
- ShortVolScore (S): 做空波动率综合评分
- 市场上下文参数（可选）

## 概率映射函数

### 基础映射（Sigmoid 风格）
```
p_long = 0.5 + 0.15 × tanh(L × 0.8)
p_short = 0.5 + 0.15 × tanh(S × 0.8)
```

### 分段校准（实用近似）
| 评分区间 | 概率范围 | 置信度 |
|---------|---------|-------|
| Score ≥ 2.0 | 0.68-0.75 | high |
| 1.5 ≤ Score < 2.0 | 0.62-0.68 | medium-high |
| 1.0 ≤ Score < 1.5 | 0.57-0.62 | medium |
| 0.5 ≤ Score < 1.0 | 0.52-0.57 | low |
| Score < 0.5 | < 0.52 | very-low |

### 上下文调整因子
- **Meso协同**: 若 Meso 方向与 Micro 一致，概率 +3%
- **高波环境** (IVR>70): 均值回归信号可靠度 +5%
- **Squeeze模式**: GEX/VEX 信号可靠度 +8%，但整体不确定性 +10%
- **财报周**: 所有概率 cap 在 0.65（事件风险）

## 三分类决策逻辑

### 做多波动率 (LONG_VOL)
必须同时满足：
1. L ≥ ${DECISION_THRESHOLD_LONG}
2. S ≤ 0.3（空头信号弱）
3. p_long ≥ ${PROB_THRESHOLD}
4. 无 Crash Risk 标记

优选条件（提升优先级）：
- L ≥ 1.5 且 p_long ≥ 0.62
- Meso 方向为"偏空—买波"或"偏多—买波"

### 做空波动率 (SHORT_VOL)
必须同时满足：
1. S ≥ ${DECISION_THRESHOLD_SHORT}
2. L ≤ 0.3（多头信号弱）
3. p_short ≥ ${PROB_THRESHOLD}
4. spot_vs_trigger = "above"（正Gamma区）
5. gamma_wall_prox ≤ 1.0%（贴近压制位）

优选条件：
- S ≥ 1.5 且 p_short ≥ 0.62
- VRP > 5%（IV显著高于HV）

### 观望 (NEUTRAL)
以下任一情况：
- L 和 S 均 < 阈值
- |L - S| < 0.5（信号冲突）
- p_long 和 p_short 均 < 0.55
- 处于 near VOL TRIGGER（易翻转）

## 冲突处理规则
当 L 和 S 同时较高时：
1. 取 |L - S| 较大者
2. 若差值 < 0.3，输出 NEUTRAL + 原因说明
3. 检查市场状态打破僵局（Gamma Regime 优先）

## 输出JSON
```json
{
  "probability_calibration": {
    "p_long": 0.XX,
    "p_short": 0.XX,
    "confidence_long": "high|medium|low",
    "confidence_short": "high|medium|low",
    "adjustments_applied": ["调整因子列表"]
  },
  "decision_gate": {
    "final_direction": "LONG_VOL | SHORT_VOL | NEUTRAL",
    "primary_score": L或S的值,
    "primary_prob": 对应概率,
    "decision_path": "满足的条件路径",
    "conflicts": ["冲突说明，若有"],
    "override_reason": "若有特殊覆盖，说明原因"
  },
  "risk_flags": ["Squeeze", "EarningsWeek", "CrashRisk"等，若有]
}
```""",

    user="""请根据以下评分结果进行概率校准：

【信号评分】
${scores_result}

【市场上下文】
${market_context}

【配置参数】
- 做多门槛: ${DECISION_THRESHOLD_LONG}
- 做空门槛: ${DECISION_THRESHOLD_SHORT}  
- 概率门槛: ${PROB_THRESHOLD}""",
    
    variables={
        "scores_result": "信号评分结果（LongVolScore/ShortVolScore及分解）",
        "market_context": "市场上下文（Gamma Regime、IVR、事件等）",
        "DECISION_THRESHOLD_LONG": "做多波动率决策门槛",
        "DECISION_THRESHOLD_SHORT": "做空波动率决策门槛",
        "PROB_THRESHOLD": "概率门槛"
    }
))