"""
策略映射Agent
"""
import json
from agents.base_agent import BaseAgent
from models.data_models import (
    Strategy, StrategyTier, StrategyEntry, StrategyExit,
    StrategyMapping, Direction, OptionLeg, OptionType, OptionAction
)
from typing import List, Dict, Any

class StrategyMappingAgent(BaseAgent):
    """策略映射Agent"""
    
    def __init__(self):
        super().__init__("strategy_mapping")
    
    async def run(
        self,
        direction: Direction,
        long_score: float,
        short_score: float
    ) -> StrategyMapping:
        """
        生成策略方案
        
        Args:
            direction: 交易方向
            long_score: 做多波动率评分
            short_score: 做空波动率评分
        """
        
        strategies = []
        
        if direction == Direction.LONG_VOL:
            # 做多波动率策略
            strategies = self._generate_long_vol_strategies(long_score)
        
        elif direction == Direction.SHORT_VOL:
            # 做空波动率策略
            strategies = self._generate_short_vol_strategies(short_score)
        
        return StrategyMapping(
            symbol="",  # 在workflow中填充
            direction=direction,
            strategies=strategies
        )
    
    def _generate_long_vol_strategies(self, score: float) -> List[Strategy]:
        """生成做多波动率策略"""
        strategies = []
        
        # 进取版 - Long Straddle
        strategies.append(Strategy(
            tier=StrategyTier.AGGRESSIVE,
            structure="Long Straddle",
            dte="20天" if score >= 2.0 else "30天",
            legs=[
                OptionLeg(
                    type=OptionType.CALL,
                    action=OptionAction.BUY,
                    strike="ATM",
                    delta=0.5,
                    rationale="买ATM Call"
                ),
                OptionLeg(
                    type=OptionType.PUT,
                    action=OptionAction.BUY,
                    strike="ATM",
                    delta=-0.5,
                    rationale="买ATM Put"
                )
            ],
            entry=StrategyEntry(
                trigger="Spot < VOL_TRIGGER 或刚下破",
                timing="市场开盘后5-15分钟，RV≥IV×0.6",
                condition="IV抬升状态"
            ),
            exit=StrategyExit(
                profit_target="50-70% max profit",
                stop_loss="15-20% max loss",
                time_decay="T-5天平仓",
                regime_change="重返触发线之上"
            ),
            description="双向Straddle，适合大波动预期"
        ))
        
        # 均衡版 - Calendar Spread
        strategies.append(Strategy(
            tier=StrategyTier.BALANCED,
            structure="Calendar Spread",
            dte="45天",
            legs=[
                OptionLeg(
                    type=OptionType.CALL,
                    action=OptionAction.SELL,
                    strike="ATM",
                    rationale="卖近月ATM Call"
                ),
                OptionLeg(
                    type=OptionType.CALL,
                    action=OptionAction.BUY,
                    strike="ATM + 5%",
                    rationale="买次近月Call"
                )
            ],
            entry=StrategyEntry(
                trigger="Term Slope ≤ 0",
                timing="事件前2-3周",
                condition="预期事件后IV回落"
            ),
            exit=StrategyExit(
                profit_target="收取50-70% credit",
                stop_loss="失效反向时间衰减",
                time_decay="T-30天滚动",
                regime_change="Term Structure反向"
            ),
            description="时间价值套利，适合中性预期"
        ))
        
        return strategies
    
    def _generate_short_vol_strategies(self, score: float) -> List[Strategy]:
        """生成做空波动率策略"""
        strategies = []
        
        # 保守版 - Iron Condor
        strategies.append(Strategy(
            tier=StrategyTier.CONSERVATIVE,
            structure="Iron Condor",
            dte="30天",
            legs=[
                OptionLeg(
                    type=OptionType.CALL,
                    action=OptionAction.SELL,
                    strike="Δ 0.15",
                    delta=0.15,
                    rationale="卖OTM Call"
                ),
                OptionLeg(
                    type=OptionType.CALL,
                    action=OptionAction.BUY,
                    strike="Δ 0.05",
                    delta=0.05,
                    rationale="买保护Call"
                ),
                OptionLeg(
                    type=OptionType.PUT,
                    action=OptionAction.SELL,
                    strike="Δ -0.15",
                    delta=-0.15,
                    rationale="卖OTM Put"
                ),
                OptionLeg(
                    type=OptionType.PUT,
                    action=OptionAction.BUY,
                    strike="Δ -0.05",
                    delta=-0.05,
                    rationale="买保护Put"
                )
            ],
            entry=StrategyEntry(
                trigger="Spot ≥ VOL_TRIGGER",
                timing="盘前或盘中RIM≤0.4",
                condition="GammaWallProx ≤ 1%"
            ),
            exit=StrategyExit(
                profit_target="收取50-70% credit即平",
                stop_loss="跌破下支撑或突破gamma wall",
                time_decay="T-10天平仓",
                regime_change="触发线下穿"
            ),
            description="固定收益策略，高胜率"
        ))
        
        # 均衡版 - Credit Spread
        strategies.append(Strategy(
            tier=StrategyTier.BALANCED,
            structure="Credit Vertical",
            dte="45天",
            legs=[
                OptionLeg(
                    type=OptionType.CALL,
                    action=OptionAction.SELL,
                    strike="Δ 0.20",
                    delta=0.20,
                    rationale="卖Call"
                ),
                OptionLeg(
                    type=OptionType.CALL,
                    action=OptionAction.BUY,
                    strike="Δ 0.10",
                    delta=0.10,
                    rationale="买保护Call"
                )
            ],
            entry=StrategyEntry(
                trigger="贴Gamma Wall ±0.5-1.0%",
                timing="市场开盘后",
                condition="正GEX环境"
            ),
            exit=StrategyExit(
                profit_target="收取50% credit",
                stop_loss="失效",
                time_decay="T-7天平仓",
                regime_change="Gamma Wall突破"
            ),
            description="盘中收租，低风险"
        ))
        
        return strategies
