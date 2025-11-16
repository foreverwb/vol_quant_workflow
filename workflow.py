"""
主工作流编排
"""
import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from models.data_models import (
    AnalysisResult, Direction, ValidationResult, CoreFields
)
from agents.router_agent import RouterAgent
from agents.data_validation_agent import DataValidationAgent
from agents.probability_calibration_agent import ProbabilityCalibrationAgent
from agents.strategy_mapping_agent import StrategyMappingAgent
from agents.command_generator_agent import CommandGeneratorAgent
from core.feature_calculator import FeatureCalculator
from core.signal_calculator import SignalCalculator
from core.strike_calculator import StrikeCalculator
from core.edge_estimator import EdgeEstimator
from config.env_config import EnvConfig
import logging

logger = logging.getLogger(__name__)

class VolatilityWorkflow:
    """波动率交易工作流"""
    
    def __init__(self, env_config: Optional[EnvConfig] = None):
        self.env_config = env_config or EnvConfig()
        
        # 初始化各Agent
        self.router_agent = RouterAgent()
        self.data_validation_agent = DataValidationAgent()
        self.probability_agent = ProbabilityCalibrationAgent()
        self.strategy_agent = StrategyMappingAgent()
        self.command_generator_agent = CommandGeneratorAgent()
        
        # 初始化计算引擎
        self.feature_calculator = FeatureCalculator(self.env_config)
        self.signal_calculator = SignalCalculator(self.env_config)
        self.strike_calculator = StrikeCalculator(self.env_config.to_dict())
        self.edge_estimator = EdgeEstimator(self.env_config)
    
    async def process_input(
        self,
        query: str,
        files: Optional[List[str]] = None,
        symbol: Optional[str] = None
    ) -> AnalysisResult:
        """
        处理用户输入 - 主工作流入口
        
        Args:
            query: 用户查询
            files: 上传的文件列表
            symbol: 标的代码
        """
        
        # 1. 路由判断
        logger.info("=" * 50)
        logger.info("STEP 1: 路由判断")
        logger.info("=" * 50)
        
        router_result = await self.router_agent.run(query, files)
        input_type = router_result.get("type")
        logger.info(f"输入类型: {input_type}")
        
        if input_type == "INVALID":
            raise ValueError(f"无效输入: {router_result.get('error', 'Unknown error')}")
        
        # DATA路径：处理上传的图表文件
        if input_type == "DATA":
            return await self._process_data_path(files, symbol)
        
        # VARIABLES路径：生成命令清单
        elif input_type == "VARIABLES":
            return await self._process_variables_path(query)
        
        else:
            raise ValueError(f"未知的输入类型: {input_type}")
    
    async def _process_data_path(
        self,
        files: List[str],
        symbol: Optional[str] = None
    ) -> AnalysisResult:
        """处理DATA路径 - 完整分析流程"""
        
        # 2. 数据校验
        logger.info("=" * 50)
        logger.info("STEP 2: 数据校验")
        logger.info("=" * 50)
        
        validation = await self.data_validation_agent.run(files, symbol)
        logger.info(f"校验状态: {validation.status}")
        
        if validation.status == "missing_data":
            logger.warning(f"缺失关键字段: {[mf.field for mf in validation.missing_fields]}")
            raise ValueError("数据不完整，请补充缺失字段")
        
        # 3. 特征计算
        logger.info("=" * 50)
        logger.info("STEP 3: 特征计算")
        logger.info("=" * 50)
        
        features = self.feature_calculator.calculate(validation.core_fields)
        logger.info(f"VRP (事件周): {features.vrp_ew:.4f}")
        logger.info(f"GEX Level: {features.gex_level}")
        logger.info(f"Pin Risk: {features.pin_risk}")
        
        # 4. 信号计算
        logger.info("=" * 50)
        logger.info("STEP 4: 信号计算")
        logger.info("=" * 50)
        
        signals = self.signal_calculator.calculate_signals(features)
        scores = self.signal_calculator.calculate_scores(signals)
        
        logger.info(f"LongVolScore: {scores.long_vol_score:.3f}")
        logger.info(f"ShortVolScore: {scores.short_vol_score:.3f}")
        logger.info(f"分解: {scores.score_breakdown}")
        
        # 5. 概率校准
        logger.info("=" * 50)
        logger.info("STEP 5: 概率校准")
        logger.info("=" * 50)
        
        probability, decision_gate = await self.probability_agent.run(
            scores,
            self.env_config.to_dict()
        )
        
        logger.info(f"做多波动率概率: {probability.p_long:.2%}")
        logger.info(f"做空波动率概率: {probability.p_short:.2%}")
        logger.info(f"最终方向: {decision_gate.final_direction.value}")
        
        # 6. 策略映射
        logger.info("=" * 50)
        logger.info("STEP 6: 策略映射")
        logger.info("=" * 50)
        
        strategy_mapping = await self.strategy_agent.run(
            decision_gate.final_direction,
            scores.long_vol_score,
            scores.short_vol_score
        )
        strategy_mapping.symbol = validation.core_fields.symbol
        
        logger.info(f"生成策略数: {len(strategy_mapping.strategies)}")
        for i, strat in enumerate(strategy_mapping.strategies):
            logger.info(f"  {i+1}. {strat.tier.value} - {strat.structure}")
        
        # 7. 行权价计算
        logger.info("=" * 50)
        logger.info("STEP 7: 行权价计算")
        logger.info("=" * 50)
        
        for strategy in strategy_mapping.strategies:
            self.strike_calculator.update_strategy_strikes(
                strategy,
                validation.core_fields
            )
            logger.info(f"{strategy.structure}:")
            for leg in strategy.legs:
                logger.info(f"  {leg.action.value} {leg.type.value}: "
                          f"{leg.strike_calculated} (方法: {leg.calculation_method})")
        
        # 8. Edge估算
        logger.info("=" * 50)
        logger.info("STEP 8: Edge估算")
        logger.info("=" * 50)
        
        for strategy in strategy_mapping.strategies:
            edge = self.edge_estimator.estimate_strategy_edge(
                strategy,
                validation.core_fields,
                probability.p_long,
                probability.p_short
            )
            strategy.edge_estimate = edge
            logger.info(f"{strategy.structure}: "
                      f"胜率={edge.win_rate}, 盈亏比={edge.rr_ratio}, "
                      f"EV={edge.ev}, 通过={edge.meets_threshold}")
        
        # 构建完整结果
        result = AnalysisResult(
            symbol=validation.core_fields.symbol,
            timestamp=validation.timestamp,
            validation=validation,
            features=features,
            signals=signals,
            scores=scores,
            probability=probability,
            decision=decision_gate,
            strategies=strategy_mapping
        )
        
        logger.info("=" * 50)
        logger.info("分析完成！")
        logger.info("=" * 50)
        
        return result
    
    async def _process_variables_path(self, query: str) -> AnalysisResult:
        """处理VARIABLES路径 - 生成命令清单"""
        
        logger.info("=" * 50)
        logger.info("VARIABLES路径: 生成gexbot命令清单")
        logger.info("=" * 50)
        
        commands = await self.command_generator_agent.run(query)
        
        result = AnalysisResult(
            symbol=commands.get("symbol", ""),
            timestamp=datetime.now().isoformat(),
            final_report=commands.get("commands_markdown", "")
        )
        
        return result
