"""
Probability calibration prompts.
Templates for LLM-based probability estimation.
"""

from typing import Dict, Any


# === 概率校准系统提示词 ===
PROBABILITY_SYSTEM_PROMPT = """你是一个专业的期权波动率策略概率校准专家。

你的任务是根据给定的信号分数和市场环境，校准以下概率：
1. P(long): 做多波动率策略的胜率
2. P(short): 做空波动率策略的胜率

关键规则：
- 概率必须在 0.40 - 0.75 之间
- 信号分数越高，对应方向的概率越高
- 考虑市场环境因素进行调整
- 输出必须是 JSON 格式

你不需要解释理由，只需输出校准后的概率。"""


# === 概率校准用户提示词模板 ===
PROBABILITY_USER_TEMPLATE = """请根据以下信息校准概率：

## 信号分数
- Long Vol Score (L): {long_vol_score:.2f}
- Short Vol Score (S): {short_vol_score:.2f}

## 市场环境
- 体制状态: {regime_state}
- 距离 VOL TRIGGER: {trigger_distance_pct:.2%}
- 是否事件周: {is_event_week}
- 流动性状态: {liquidity_flag}

## 评分细节
- s_vrp: {s_vrp:.2f}
- s_gex: {s_gex:.2f}
- s_vex: {s_vex:.2f}
- s_carry: {s_carry:.2f}
- s_skew: {s_skew:.2f}

请输出 JSON 格式：
```json
{{
  "p_long": <0.40-0.75>,
  "p_short": <0.40-0.75>,
  "confidence": <0.0-1.0>,
  "adjustments": ["调整说明1", "调整说明2"]
}}
```"""


# === 冷启动概率映射提示词 ===
COLD_START_TEMPLATE = """基于历史经验，以下是分数到概率的冷启动映射：

Long Vol Score 映射:
- L >= 2.0: P(long) = 0.65-0.70
- L >= 1.5: P(long) = 0.60-0.65
- L >= 1.0: P(long) = 0.55-0.60
- L < 1.0: P(long) = 0.45-0.55

Short Vol Score 映射:
- S >= 2.0: P(short) = 0.65-0.70
- S >= 1.5: P(short) = 0.60-0.65
- S >= 1.0: P(short) = 0.55-0.60
- S < 1.0: P(short) = 0.45-0.55

环境调整因子:
- 事件周 + 负 Gamma: P(long) +3-5%
- 正 Gamma + Pin Risk: P(short) +3-5%
- 流动性差: 两边概率 -5%
- 距离 Trigger 很近 (<0.5%): 概率不确定性增加"""


def format_probability_prompt(
    long_vol_score: float,
    short_vol_score: float,
    context: Dict[str, Any],
    signal_breakdown: Dict[str, float] = None,
) -> str:
    """
    Format probability calibration prompt.
    
    Args:
        long_vol_score: Composite long vol score
        short_vol_score: Composite short vol score
        context: Market context dict
        signal_breakdown: Individual signal scores
        
    Returns:
        Formatted prompt string
    """
    signal_breakdown = signal_breakdown or {}
    
    return PROBABILITY_USER_TEMPLATE.format(
        long_vol_score=long_vol_score,
        short_vol_score=short_vol_score,
        regime_state=context.get("regime_state", "unknown"),
        trigger_distance_pct=context.get("trigger_distance_pct", 0),
        is_event_week=context.get("is_event_week", False),
        liquidity_flag=context.get("liquidity_flag", "fair"),
        s_vrp=signal_breakdown.get("s_vrp", 0),
        s_gex=signal_breakdown.get("s_gex", 0),
        s_vex=signal_breakdown.get("s_vex", 0),
        s_carry=signal_breakdown.get("s_carry", 0),
        s_skew=signal_breakdown.get("s_skew", 0),
    )


def get_probability_system_prompt() -> str:
    """Get the system prompt for probability calibration."""
    return PROBABILITY_SYSTEM_PROMPT


def get_cold_start_reference() -> str:
    """Get the cold start mapping reference."""
    return COLD_START_TEMPLATE
