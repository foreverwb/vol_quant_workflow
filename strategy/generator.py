"""
策略生成模块
根据决策结果生成具体期权策略
"""
from typing import List, Optional
from dataclasses import dataclass

from core.types import (
    Decision,
    DecisionResult,
    Features,
    MarketData,
    Strategy,
    StrategyType,
    RiskProfile,
    OptionLeg,
)
from core.constants import STRATEGY_CONFIG


def generate_strategy(
    decision: DecisionResult,
    features: Features,
    data: MarketData,
    is_event: bool = False
) -> Strategy:
    """
    生成交易策略
    
    Args:
        decision: 决策结果
        features: 特征
        data: 市场数据
        is_event: 是否为事件期
        
    Returns:
        Strategy 对象
    """
    if decision.decision == Decision.LONG_VOL:
        return generate_long_vol_strategy(features, data, is_event)
    elif decision.decision == Decision.SHORT_VOL:
        return generate_short_vol_strategy(features, data, is_event)
    else:
        return generate_hold_strategy(features, data)


def generate_long_vol_strategy(
    features: Features,
    data: MarketData,
    is_event: bool
) -> Strategy:
    """生成做多波动率策略"""
    spot = data.spot
    
    # 根据期限结构选择策略
    if features.term_regime and features.term_regime.value == "backwardation":
        # Calendar spread: 买近卖远
        strategy_type = StrategyType.CALENDAR_SPREAD
        name = "Calendar Spread (买近卖远)"
        rationale = "近月 IV 高于远月，可卖近买远获取 term roll"
        
        legs = [
            OptionLeg(
                action="sell",
                option_type="call",
                strike=round(spot / 5) * 5,
                delta=0.50,
                quantity=1
            ),
            OptionLeg(
                action="buy",
                option_type="call",
                strike=round(spot / 5) * 5,
                delta=0.50,
                quantity=1
            ),
        ]
        dte_min, dte_max = 5, 20
        
    else:
        # Long straddle
        strategy_type = StrategyType.LONG_STRADDLE
        name = "Long Straddle"
        rationale = "预期波动率上升，双向买入"
        
        atm_strike = round(spot / 5) * 5
        legs = [
            OptionLeg(
                action="buy",
                option_type="call",
                strike=atm_strike,
                delta=0.50,
                quantity=1
            ),
            OptionLeg(
                action="buy",
                option_type="put",
                strike=atm_strike,
                delta=-0.50,
                quantity=1
            ),
        ]
        
        if is_event:
            dte_min, dte_max = STRATEGY_CONFIG["dte_ranges"]["event"]
        else:
            dte_min, dte_max = STRATEGY_CONFIG["dte_ranges"]["non_event"]
    
    return Strategy(
        name=name,
        type=strategy_type,
        risk_profile=RiskProfile.BALANCED,
        rationale=rationale,
        legs=legs,
        dte_min=dte_min,
        dte_max=dte_max,
        dte_optimal=(dte_min + dte_max) // 2,
        entry_conditions=[
            "IV 低于历史平均",
            "VRP 为负或接近零",
            "预期有重大事件或波动催化剂"
        ],
        exit_conditions=[
            "达到 50% 利润",
            "标的大幅移动",
            "DTE < 5 且未盈利"
        ],
        max_loss=None,  # Long options: 损失有限于权利金
        target_profit=None,
        reward_risk=2.0
    )


def generate_short_vol_strategy(
    features: Features,
    data: MarketData,
    is_event: bool
) -> Strategy:
    """生成做空波动率策略"""
    spot = data.spot
    
    # 默认使用 Iron Condor
    call_wall = data.call_wall or spot * 1.05
    put_wall = data.put_wall or spot * 0.95
    
    # 计算行权价
    width = STRATEGY_CONFIG["spread_widths"]["standard"]
    
    short_put = round(put_wall / 5) * 5
    long_put = short_put - width
    short_call = round(call_wall / 5) * 5
    long_call = short_call + width
    
    legs = [
        OptionLeg(
            action="sell",
            option_type="put",
            strike=short_put,
            delta=-0.20,
            quantity=1
        ),
        OptionLeg(
            action="buy",
            option_type="put",
            strike=long_put,
            delta=-0.10,
            quantity=1
        ),
        OptionLeg(
            action="sell",
            option_type="call",
            strike=short_call,
            delta=0.20,
            quantity=1
        ),
        OptionLeg(
            action="buy",
            option_type="call",
            strike=long_call,
            delta=0.10,
            quantity=1
        ),
    ]
    
    if is_event:
        dte_min, dte_max = STRATEGY_CONFIG["dte_ranges"]["event"]
    else:
        dte_min, dte_max = STRATEGY_CONFIG["dte_ranges"]["non_event"]
    
    return Strategy(
        name="Iron Condor",
        type=StrategyType.IRON_CONDOR,
        risk_profile=RiskProfile.BALANCED,
        rationale="正 GEX 环境压制波动，VRP 为正，适合卖权",
        legs=legs,
        dte_min=dte_min,
        dte_max=dte_max,
        dte_optimal=(dte_min + dte_max) // 2,
        entry_conditions=[
            "IV > HV20",
            "正 GEX 环境",
            "无重大事件在 DTE 内"
        ],
        exit_conditions=[
            "达到 50% 利润",
            "触及任一短腿行权价",
            "DTE < 7"
        ],
        max_loss=float(width),  # Spread width
        target_profit=None,
        reward_risk=2.0
    )


def generate_hold_strategy(
    features: Features,
    data: MarketData
) -> Strategy:
    """生成观望策略"""
    spot = data.spot
    atm = round(spot / 5) * 5
    
    return Strategy(
        name="Calendar Spread (备选)",
        type=StrategyType.CALENDAR_SPREAD,
        risk_profile=RiskProfile.CONSERVATIVE,
        rationale="信号不明确，建议观望或小仓位 Calendar",
        legs=[
            OptionLeg(
                action="sell",
                option_type="call",
                strike=atm,
                delta=0.50,
                quantity=1
            ),
            OptionLeg(
                action="buy",
                option_type="call",
                strike=atm,
                delta=0.50,
                quantity=1
            ),
        ],
        dte_min=30,
        dte_max=60,
        dte_optimal=45,
        entry_conditions=[
            "等待方向明确",
            "小仓位试探"
        ],
        exit_conditions=[
            "信号明确后调整",
            "止损 50%"
        ],
        max_loss=None,
        target_profit=None,
        reward_risk=1.5
    )
