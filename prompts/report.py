"""
Final report prompts.
Generates a concise markdown analysis report.
"""

from typing import Dict, Any, List


REPORT_SYSTEM_PROMPT = """你是一个专业的期权波动率策略分析师。
你的任务是根据给定的分析结果生成一份简洁的 Markdown 报告。
要求：
- 必须是 Markdown 格式
- 避免臆测，不确定处明确说明
- 只输出报告正文，不要附加其他说明
"""


REPORT_USER_TEMPLATE = """请生成报告，包含以下信息：

## 决策
- decision: {decision}
- confidence: {confidence:.1%}
- is_preferred: {is_preferred}

## 评分
- long_vol_score: {long_vol_score:.2f}
- short_vol_score: {short_vol_score:.2f}

## 概率
- p_long: {p_long:.1%}
- p_short: {p_short:.1%}
- method: {calibration_method}

## 信号摘要
{signal_summary}

## 候选策略数量
- candidates: {candidate_count}

## 选中策略
{selected_strategy}

请输出 Markdown 报告。
"""


def _format_signal_summary(signal_breakdown: Dict[str, Any]) -> str:
    lines = []
    for key, value in signal_breakdown.items():
        lines.append(f"- {key}: {value:+.3f}")
    return "\n".join(lines) if lines else "- (无)"


def _format_selected_strategy(selected_strategy: Dict[str, Any]) -> str:
    if not selected_strategy:
        return "- NO TRADE"
    lines = [
        f"- name: {selected_strategy.get('name')}",
        f"- tier: {selected_strategy.get('tier')}",
        f"- direction: {selected_strategy.get('direction')}",
        f"- dte_range: {selected_strategy.get('dte_range')}",
    ]
    return "\n".join(lines)


def format_report_prompt(analysis: Dict[str, Any]) -> str:
    """Format report prompt from analysis dict."""
    probabilities = analysis.get("probabilities", {})
    return REPORT_USER_TEMPLATE.format(
        decision=analysis.get("decision", "UNKNOWN"),
        confidence=analysis.get("confidence", 0.0),
        is_preferred=analysis.get("is_preferred", False),
        long_vol_score=analysis.get("scores", {}).get("long_vol_score", 0.0),
        short_vol_score=analysis.get("scores", {}).get("short_vol_score", 0.0),
        p_long=probabilities.get("p_long", 0.0),
        p_short=probabilities.get("p_short", 0.0),
        calibration_method=probabilities.get("calibration_method", "unknown"),
        signal_summary=_format_signal_summary(analysis.get("signal_breakdown", {})),
        candidate_count=len(analysis.get("candidates", [])),
        selected_strategy=_format_selected_strategy(analysis.get("selected_strategy")),
    )


def get_report_system_prompt() -> str:
    """Get the system prompt for final report."""
    return REPORT_SYSTEM_PROMPT
