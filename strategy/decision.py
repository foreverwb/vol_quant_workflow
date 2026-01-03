"""
决策引擎模块
根据评分结果生成交易决策
"""
from typing import Dict, List, Optional
import bisect

from core.types import (
    Scores,
    Features,
    Decision,
    Confidence,
    Probability,
    DecisionResult,
)
from core.constants import DECISION_THRESHOLDS, SCORE_TO_PROB_MAP


def score_to_probability(score: float) -> float:
    """
    将评分转换为概率
    使用预设的校准映射表
    """
    scores = [s for s, p in SCORE_TO_PROB_MAP]
    probs = [p for s, p in SCORE_TO_PROB_MAP]
    
    if score <= scores[0]:
        return probs[0]
    if score >= scores[-1]:
        return probs[-1]
    
    # 线性插值
    idx = bisect.bisect_left(scores, score)
    if idx == 0:
        return probs[0]
    
    s1, s2 = scores[idx - 1], scores[idx]
    p1, p2 = probs[idx - 1], probs[idx]
    
    ratio = (score - s1) / (s2 - s1)
    return p1 + ratio * (p2 - p1)


def calculate_probability_distribution(scores: Scores) -> Probability:
    """
    计算三分类概率分布
    """
    long_score = max(scores.long_vol_score, 0)
    short_score = max(scores.short_vol_score, 0)
    
    p_long = score_to_probability(long_score)
    p_short = score_to_probability(short_score)
    
    # 归一化
    total = p_long + p_short + 0.3  # 0.3 为 hold 基准
    p_long = p_long / total
    p_short = p_short / total
    p_hold = 1 - p_long - p_short
    
    # 如果两者都很弱，增加 hold 概率
    if long_score < 0.5 and short_score < 0.5:
        p_hold = max(p_hold, 0.5)
        remaining = 1 - p_hold
        if p_long + p_short > 0:
            p_long = p_long / (p_long + p_short) * remaining
            p_short = remaining - p_long
        else:
            p_long = remaining / 2
            p_short = remaining / 2
    
    return Probability(
        p_long=round(p_long, 4),
        p_short=round(p_short, 4),
        p_hold=round(p_hold, 4)
    )


def determine_confidence(scores: Scores, prob: Probability) -> Confidence:
    """
    确定决策置信度
    """
    score_diff = scores.score_diff
    max_prob = max(prob.p_long, prob.p_short, prob.p_hold)
    
    if score_diff > 1.5 and max_prob > 0.6:
        return Confidence.HIGH
    elif score_diff > 0.8 and max_prob > 0.5:
        return Confidence.MEDIUM
    else:
        return Confidence.LOW


def make_decision(
    scores: Scores,
    features: Features,
    force_direction: Optional[str] = None
) -> DecisionResult:
    """
    生成交易决策
    
    Args:
        scores: 评分结果
        features: 特征
        force_direction: 强制方向 (可选)
        
    Returns:
        DecisionResult
    """
    # 计算概率
    prob = calculate_probability_distribution(scores)
    
    # 确定决策
    thresholds = DECISION_THRESHOLDS
    
    if force_direction == "long":
        decision = Decision.LONG_VOL
    elif force_direction == "short":
        decision = Decision.SHORT_VOL
    else:
        # 规则决策
        if (scores.long_vol_score >= thresholds["long_vol"]["score_min"] and
            prob.p_long >= thresholds["long_vol"]["prob_min"] and
            scores.short_vol_score < thresholds["long_vol"]["counter_max"]):
            decision = Decision.LONG_VOL
            
        elif (scores.short_vol_score >= thresholds["short_vol"]["score_min"] and
              prob.p_short >= thresholds["short_vol"]["prob_min"] and
              scores.long_vol_score < thresholds["short_vol"]["counter_max"]):
            decision = Decision.SHORT_VOL
            
        else:
            decision = Decision.HOLD
    
    # 置信度
    confidence = determine_confidence(scores, prob)
    
    # 生成理由
    rationale = generate_rationale(scores, features, decision)
    
    # 关键因素
    key_factors = extract_key_factors(scores, features)
    
    # 风险提示
    risk_notes = generate_risk_notes(features, decision)
    
    # 建议策略
    suggested_strategy = suggest_strategy_type(decision, features)
    
    return DecisionResult(
        decision=decision,
        probability=prob,
        confidence=confidence,
        rationale=rationale,
        key_factors=key_factors,
        risk_notes=risk_notes,
        suggested_strategy=suggested_strategy
    )


def generate_rationale(
    scores: Scores,
    features: Features,
    decision: Decision
) -> str:
    """生成决策理由"""
    parts = []
    
    if decision == Decision.LONG_VOL:
        parts.append(f"LongVolScore ({scores.long_vol_score:.2f}) 达到阈值")
        if features.vrp_selected and features.vrp_selected < 0:
            parts.append(f"VRP 为负 ({features.vrp_selected:.1f}%)")
        if features.net_gex_regime and features.net_gex_regime.value == "negative":
            parts.append("负 GEX 环境支持波动")
            
    elif decision == Decision.SHORT_VOL:
        parts.append(f"ShortVolScore ({scores.short_vol_score:.2f}) 达到阈值")
        if features.vrp_selected and features.vrp_selected > 0:
            parts.append(f"VRP 为正 ({features.vrp_selected:.1f}%)")
        if features.net_gex_regime and features.net_gex_regime.value == "positive":
            parts.append("正 GEX 环境压制波动")
            
    else:
        parts.append("信号强度不足")
        parts.append(f"Long={scores.long_vol_score:.2f}, Short={scores.short_vol_score:.2f}")
    
    return "；".join(parts)


def extract_key_factors(scores: Scores, features: Features) -> List[str]:
    """提取关键决策因素"""
    factors = []
    
    # 从信号分解中找前 5 个贡献最大的
    if scores.signal_breakdown:
        sorted_signals = sorted(
            scores.signal_breakdown.items(),
            key=lambda x: abs(x[1].contribution_long) + abs(x[1].contribution_short),
            reverse=True
        )[:5]
        
        for name, signal in sorted_signals:
            if signal.contribution_long > 0.05:
                factors.append(f"{name} 支持 long vol (+{signal.contribution_long:.2f})")
            elif signal.contribution_short > 0.05:
                factors.append(f"{name} 支持 short vol (+{signal.contribution_short:.2f})")
    
    return factors[:5]


def generate_risk_notes(features: Features, decision: Decision) -> List[str]:
    """生成风险提示"""
    notes = []
    
    if features.is_pin_risk:
        notes.append("接近 Gamma Wall，存在 Pin 风险")
    
    if features.liquidity_score and features.liquidity_score < 50:
        notes.append("流动性较差，执行滑点风险高")
    
    if features.vov_level and features.vov_level >= 2:
        notes.append("VoV 较高，波动率本身不稳定")
    
    if decision == Decision.SHORT_VOL:
        notes.append("做空波动率风险无限，需严格止损")
    
    if not notes:
        notes.append("注意重大事件可能导致波动率跳升")
    
    return notes[:3]


def suggest_strategy_type(decision: Decision, features: Features) -> str:
    """建议策略类型"""
    if decision == Decision.LONG_VOL:
        if features.term_regime and features.term_regime.value == "backwardation":
            return "Calendar Spread (买近卖远)"
        else:
            return "Long Straddle 或 Long Strangle"
            
    elif decision == Decision.SHORT_VOL:
        if features.net_gex_regime and features.net_gex_regime.value == "positive":
            return "Iron Condor"
        else:
            return "Credit Spread"
            
    else:
        return "观望等待"
