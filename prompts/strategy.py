"""
Strategy selection prompts.
Templates for LLM-based strategy mapping and selection.
"""

from typing import Dict, Any, List


# === 策略选择系统提示词 ===
STRATEGY_SYSTEM_PROMPT = """你是一个专业的期权策略选择专家。

你的任务是根据市场环境和信号分析结果，从候选策略中选择最优策略。

策略分类：
1. 激进版 (Aggressive): 目标 RR >= 2:1
   - Long Straddle/Strangle
   - Bull Call Spread
   - Put Diagonal/Ratio

2. 均衡版 (Balanced): 目标 RR 1.2-1.8:1
   - Calendar Spread
   - Debit Vertical

3. 保守版 (Conservative): 目标 RR 0.8-1.2:1
   - Iron Condor
   - Short Strangle
   - Credit Spread

选择原则：
- 高概率 (>65%) + 强信号: 可选激进策略
- 中等概率 (55-65%): 优先均衡策略
- 保守概率 (~55%): 优先保守策略
- 事件周: 优先 Long Straddle
- Pin Risk: 优先 Iron Condor
- 高流动性要求: 优先简单结构

输出必须是 JSON 格式。"""


# === 策略选择用户提示词模板 ===
STRATEGY_USER_TEMPLATE = """请根据以下分析结果选择最优策略：

## 决策结果
- 方向: {decision}
- 置信度: {confidence:.1%}
- 是否优选: {is_preferred}

## 概率
- P(long): {p_long:.1%}
- P(short): {p_short:.1%}

## 市场环境
- 体制状态: {regime_state}
- 期限结构: {term_regime}
- 偏度状态: {skew_regime}
- 流动性: {liquidity_flag}
- 是否事件周: {is_event_week}
- Pin Risk: {is_pin_risk}

## 候选策略
{candidates_list}

请选择最优策略并输出 JSON：
```json
{{
  "selected_strategy": "<策略名称>",
  "tier": "<aggressive/balanced/conservative>",
  "rationale": "<选择理由>",
  "dte_range": [min, max],
  "delta_targets": {{"buy_call": <delta>, "buy_put": <delta>}},
  "risk_notes": ["注意事项1", "注意事项2"]
}}
```"""


# === 策略模板定义 ===
STRATEGY_TEMPLATES = {
    "long_straddle": {
        "name": "long_straddle",
        "direction": "long_vol",
        "tier": "aggressive",
        "description": "ATM Straddle - 事件周首选",
        "dte_range": [5, 20],
        "delta_targets": {"buy_call": 0.50, "buy_put": 0.50},
        "target_rr": (2.0, 3.0),
        "applicability": {
            "event_week": True,
            "regime": ["negative_gamma", "neutral"],
            "probability_min": 0.55,
        },
    },
    "long_strangle": {
        "name": "long_strangle",
        "direction": "long_vol",
        "tier": "aggressive",
        "description": "OTM Strangle - 低成本做多波动",
        "dte_range": [30, 45],
        "delta_targets": {"buy_call": 0.30, "buy_put": 0.30},
        "target_rr": (2.0, 4.0),
        "applicability": {
            "event_week": False,
            "regime": ["negative_gamma"],
            "probability_min": 0.60,
        },
    },
    "bull_call_spread": {
        "name": "bull_call_spread",
        "direction": "long_vol",
        "tier": "aggressive",
        "description": "方向性做多 + 做多波动",
        "dte_range": [14, 35],
        "delta_targets": {"buy_call": 0.55, "sell_call": 0.30},
        "target_rr": (2.0, 3.0),
        "applicability": {
            "regime": ["negative_gamma"],
            "probability_min": 0.60,
        },
    },
    "calendar_spread": {
        "name": "calendar_spread",
        "direction": "long_vol",
        "tier": "balanced",
        "description": "时间价差 - 期限结构套利",
        "dte_range": {"near": [14, 21], "far": [45, 60]},
        "delta_targets": {"atm": 0.50},
        "target_rr": (1.2, 1.8),
        "applicability": {
            "term_regime": ["backwardation", "steep_contango"],
            "probability_min": 0.55,
        },
    },
    "debit_vertical": {
        "name": "debit_vertical",
        "direction": "long_vol",
        "tier": "balanced",
        "description": "借方价差 - 有限风险做多",
        "dte_range": [21, 45],
        "delta_targets": {"buy": 0.60, "sell": 0.30},
        "target_rr": (1.2, 2.0),
        "applicability": {
            "regime": ["negative_gamma", "neutral"],
            "probability_min": 0.55,
        },
    },
    "iron_condor": {
        "name": "iron_condor",
        "direction": "short_vol",
        "tier": "conservative",
        "description": "铁鹰式 - 范围收益",
        "dte_range": [14, 45],
        "delta_targets": {
            "sell_call": 0.15,
            "buy_call": 0.05,
            "sell_put": 0.15,
            "buy_put": 0.05,
        },
        "target_rr": (0.8, 1.2),
        "applicability": {
            "regime": ["positive_gamma"],
            "probability_min": 0.65,
            "pin_risk_ok": True,
        },
    },
    "short_strangle": {
        "name": "short_strangle",
        "direction": "short_vol",
        "tier": "conservative",
        "description": "裸卖跨式 - 高胜率收益",
        "dte_range": [30, 45],
        "delta_targets": {"sell_call": 0.20, "sell_put": 0.20},
        "target_rr": (0.8, 1.0),
        "applicability": {
            "regime": ["positive_gamma"],
            "probability_min": 0.70,
            "rim_min": 0.4,
        },
    },
    "credit_spread": {
        "name": "credit_spread",
        "direction": "short_vol",
        "tier": "conservative",
        "description": "贷方价差 - 墙锚定",
        "dte_range": [14, 35],
        "delta_targets": {"sell": 0.20, "buy": 0.05},
        "target_rr": (0.8, 1.2),
        "applicability": {
            "regime": ["positive_gamma"],
            "wall_anchor": True,
            "probability_min": 0.60,
        },
    },
}


def format_strategy_prompt(
    decision: str,
    confidence: float,
    is_preferred: bool,
    probabilities: Dict[str, float],
    context: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> str:
    """
    Format strategy selection prompt.
    
    Args:
        decision: Decision classification (LONG_VOL/SHORT_VOL/STAND_ASIDE)
        confidence: Decision confidence
        is_preferred: Whether decision meets preferred thresholds
        probabilities: Dict with p_long and p_short
        context: Market context
        candidates: List of candidate strategy dicts
        
    Returns:
        Formatted prompt string
    """
    # Format candidates list
    candidates_list = ""
    for i, c in enumerate(candidates, 1):
        candidates_list += f"{i}. {c['name']} ({c['tier']})\n"
        candidates_list += f"   - DTE: {c.get('dte_range', 'N/A')}\n"
        candidates_list += f"   - Target RR: {c.get('target_rr', 'N/A')}\n"
    
    return STRATEGY_USER_TEMPLATE.format(
        decision=decision,
        confidence=confidence,
        is_preferred=is_preferred,
        p_long=probabilities.get("p_long", 0.5),
        p_short=probabilities.get("p_short", 0.5),
        regime_state=context.get("regime_state", "unknown"),
        term_regime=context.get("term_regime", "unknown"),
        skew_regime=context.get("skew_regime", "unknown"),
        liquidity_flag=context.get("liquidity_flag", "fair"),
        is_event_week=context.get("is_event_week", False),
        is_pin_risk=context.get("is_pin_risk", False),
        candidates_list=candidates_list,
    )


def get_strategy_system_prompt() -> str:
    """Get the system prompt for strategy selection."""
    return STRATEGY_SYSTEM_PROMPT


def get_strategy_templates() -> Dict[str, Dict[str, Any]]:
    """Get all strategy templates."""
    return STRATEGY_TEMPLATES.copy()


def get_strategy_template(name: str) -> Dict[str, Any]:
    """Get a specific strategy template."""
    return STRATEGY_TEMPLATES.get(name, {}).copy()
