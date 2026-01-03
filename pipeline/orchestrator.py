"""
流程编排模块
统一管理分析流程
"""
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import os

from core.types import (
    MarketData,
    Features,
    Scores,
    DecisionResult,
    Strategy,
    EdgeMetrics,
    AnalysisResult,
    EventType,
)
from core.exceptions import PipelineError
from utils import load_and_validate, DataLoader
from analysis import calculate_all_features, calculate_scores
from analysis.monte_carlo import simulate_strategy_pnl, calculate_edge_metrics
from strategy import make_decision, generate_strategy


class Stage(Enum):
    """流程阶段"""
    LOAD_DATA = "load_data"
    VALIDATE = "validate"
    CALCULATE_FEATURES = "calculate_features"
    CALCULATE_SCORES = "calculate_scores"
    MAKE_DECISION = "make_decision"
    GENERATE_STRATEGY = "generate_strategy"
    ESTIMATE_EDGE = "estimate_edge"
    GENERATE_OUTPUT = "generate_output"


@dataclass
class StageResult:
    """阶段结果"""
    stage: Stage
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class PipelineContext:
    """流程上下文"""
    symbol: str
    event_type: EventType = EventType.NONE
    is_event: bool = False
    
    # 中间结果
    raw_data: Dict[str, Any] = field(default_factory=dict)
    market_data: Optional[MarketData] = None
    validations: Dict[str, Any] = field(default_factory=dict)
    validation_summary: Dict[str, Any] = field(default_factory=dict)
    features: Optional[Features] = None
    scores: Optional[Scores] = None
    decision: Optional[DecisionResult] = None
    strategy: Optional[Strategy] = None
    edge: Optional[EdgeMetrics] = None
    
    # 元信息
    stage_results: List[StageResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PipelineOrchestrator:
    """流程编排器"""
    
    def __init__(
        self,
        data_dir: str = "data/input",
        output_dir: str = "data/output"
    ):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.hooks: Dict[str, List[Callable]] = {
            "before_stage": [],
            "after_stage": [],
            "on_error": [],
        }
    
    def add_hook(self, event: str, callback: Callable):
        """添加钩子"""
        if event in self.hooks:
            self.hooks[event].append(callback)
    
    def _trigger_hooks(self, event: str, *args, **kwargs):
        """触发钩子"""
        for callback in self.hooks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception:
                pass  # 钩子错误不影响主流程
    
    def run(
        self,
        symbol: str,
        event_type: str = "none",
        data_file: Optional[str] = None,
        iv: float = 0.28,
        hv: float = 0.25,
        skip_edge: bool = False
    ) -> PipelineContext:
        """
        执行完整分析流程
        
        Args:
            symbol: 标的代码
            event_type: 事件类型
            data_file: 数据文件路径
            iv: 隐含波动率 (用于蒙特卡洛)
            hv: 历史波动率 (用于蒙特卡洛)
            skip_edge: 是否跳过 Edge 计算
            
        Returns:
            PipelineContext
        """
        ctx = PipelineContext(
            symbol=symbol.upper(),
            event_type=EventType(event_type) if event_type else EventType.NONE,
            is_event=event_type not in [None, "none"],
            started_at=datetime.now()
        )
        
        stages = [
            (Stage.LOAD_DATA, lambda: self._stage_load_data(ctx, data_file)),
            (Stage.VALIDATE, lambda: self._stage_validate(ctx)),
            (Stage.CALCULATE_FEATURES, lambda: self._stage_calculate_features(ctx)),
            (Stage.CALCULATE_SCORES, lambda: self._stage_calculate_scores(ctx)),
            (Stage.MAKE_DECISION, lambda: self._stage_make_decision(ctx)),
            (Stage.GENERATE_STRATEGY, lambda: self._stage_generate_strategy(ctx)),
        ]
        
        if not skip_edge:
            stages.append(
                (Stage.ESTIMATE_EDGE, lambda: self._stage_estimate_edge(ctx, iv, hv))
            )
        
        # 执行各阶段
        for stage, executor in stages:
            self._trigger_hooks("before_stage", stage, ctx)
            
            start_time = datetime.now()
            try:
                result = executor()
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                stage_result = StageResult(
                    stage=stage,
                    success=True,
                    data=result,
                    duration_ms=duration
                )
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                stage_result = StageResult(
                    stage=stage,
                    success=False,
                    error=str(e),
                    duration_ms=duration
                )
                self._trigger_hooks("on_error", stage, e, ctx)
                ctx.stage_results.append(stage_result)
                break
            
            ctx.stage_results.append(stage_result)
            self._trigger_hooks("after_stage", stage, stage_result, ctx)
        
        ctx.completed_at = datetime.now()
        return ctx
    
    def _stage_load_data(
        self,
        ctx: PipelineContext,
        data_file: Optional[str]
    ) -> MarketData:
        """加载数据阶段"""
        loader = DataLoader(self.data_dir)
        
        market_data, validations, summary = loader.load_market_data(
            ctx.symbol,
            data_file
        )
        
        ctx.market_data = market_data
        ctx.validations = validations
        ctx.validation_summary = summary
        
        return market_data
    
    def _stage_validate(self, ctx: PipelineContext) -> Dict[str, Any]:
        """校验阶段"""
        # 数据已在 load_data 中校验
        summary = ctx.validation_summary
        
        if not summary.get("is_usable", False):
            raise PipelineError(
                Stage.VALIDATE.value,
                f"Data not usable, missing critical fields: {summary.get('missing_critical', [])}"
            )
        
        return summary
    
    def _stage_calculate_features(self, ctx: PipelineContext) -> Features:
        """计算特征阶段"""
        features = calculate_all_features(
            ctx.market_data,
            is_event=ctx.is_event
        )
        ctx.features = features
        return features
    
    def _stage_calculate_scores(self, ctx: PipelineContext) -> Scores:
        """计算评分阶段"""
        is_single_stock = ctx.symbol not in ["SPY", "QQQ", "IWM", "DIA", "SPX", "NDX"]
        
        scores = calculate_scores(
            ctx.features,
            ctx.market_data,
            is_single_stock=is_single_stock
        )
        ctx.scores = scores
        return scores
    
    def _stage_make_decision(self, ctx: PipelineContext) -> DecisionResult:
        """决策阶段"""
        decision = make_decision(
            ctx.scores,
            ctx.features
        )
        ctx.decision = decision
        return decision
    
    def _stage_generate_strategy(self, ctx: PipelineContext) -> Strategy:
        """生成策略阶段"""
        strategy = generate_strategy(
            ctx.decision,
            ctx.features,
            ctx.market_data,
            is_event=ctx.is_event
        )
        ctx.strategy = strategy
        return strategy
    
    def _stage_estimate_edge(
        self,
        ctx: PipelineContext,
        iv: float,
        hv: float
    ) -> EdgeMetrics:
        """估计 Edge 阶段"""
        dte = ctx.strategy.dte_optimal
        
        pnl_dist, stats = simulate_strategy_pnl(
            ctx.strategy,
            ctx.market_data.spot,
            iv,
            days=dte
        )
        
        edge = calculate_edge_metrics(pnl_dist, stats)
        ctx.edge = edge
        return edge
    
    def run_update(
        self,
        symbol: str,
        data_file: Optional[str] = None
    ) -> PipelineContext:
        """
        执行更新流程 (仅计算到评分)
        用于实时监控
        """
        return self.run(
            symbol=symbol,
            data_file=data_file,
            skip_edge=True
        )


def create_pipeline(
    data_dir: str = "data/input",
    output_dir: str = "data/output"
) -> PipelineOrchestrator:
    """创建流程编排器实例"""
    return PipelineOrchestrator(data_dir, output_dir)
