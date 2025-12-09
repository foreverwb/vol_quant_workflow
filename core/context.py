"""
工作流上下文定义

包含:
- WorkflowStatus: 工作流状态枚举
- WorkflowContext: 工作流上下文数据类
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

# 避免循环导入
try:
    from .context_loader import MarketContext, DynamicConfig
except ImportError:
    MarketContext = None
    DynamicConfig = None


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_INPUT = "waiting_input"


@dataclass
class WorkflowContext:
    """
    工作流上下文 - 存储中间结果
    
    在整个工作流执行过程中传递数据
    """
    # 配置引用
    config: Any = None  # WorkflowConfig
    logger: Any = None
    error_collector: Any = None
    
    # 输入数据
    user_input: str = ""
    uploaded_files: List[str] = field(default_factory=list)
    
    # 路由结果
    route_type: str = ""  # VARIABLES / DATA / INVALID
    
    # 命令清单
    commands: str = ""
    
    # ===== Meso 上下文 =====
    market_context: Optional[Any] = None  # MarketContext
    meso_context: Optional[Dict[str, Any]] = None  # Meso 平台上下文 (兼容别名)
    dynamic_config: Optional[Any] = None  # DynamicConfig
    context_params: Dict[str, Any] = field(default_factory=dict)
    
    # 数据校验结果 (#3001)
    validation_result: Dict[str, Any] = field(default_factory=dict)
    core_fields: Dict[str, Any] = field(default_factory=dict)
    
    # 特征计算结果 (#4001)
    features_result: Dict[str, Any] = field(default_factory=dict)
    
    # 信号打分结果 (#5001)
    scores_result: Dict[str, Any] = field(default_factory=dict)
    
    # 概率校准结果 (#6001)
    probability_result: Dict[str, Any] = field(default_factory=dict)
    
    # 策略映射结果 (#7001)
    strategies_result: Dict[str, Any] = field(default_factory=dict)
    
    # 行权价计算结果 (#7002)
    strikes_result: Dict[str, Any] = field(default_factory=dict)
    
    # Edge估算结果 (#7003)
    edge_result: Dict[str, Any] = field(default_factory=dict)
    
    # 最终报告 (#8001)
    final_report: str = ""
    
    # ===== 执行状态 =====
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: str = ""  # 当前执行步骤
    step_results: Dict[str, Any] = field(default_factory=dict)  # 各步骤结果
    
    # ===== 时间追踪 =====
    start_time: Optional[Any] = None  # datetime
    end_time: Optional[Any] = None  # datetime
    
    # ===== 错误记录 =====
    errors: List[str] = field(default_factory=list)
    timestamp: str = ""
    
    def reset(self):
        """重置上下文到初始状态"""
        self.user_input = ""
        self.uploaded_files = []
        self.route_type = ""
        self.commands = ""
        self.market_context = None
        self.meso_context = None
        self.dynamic_config = None
        self.context_params = {}
        self.validation_result = {}
        self.core_fields = {}
        self.features_result = {}
        self.scores_result = {}
        self.probability_result = {}
        self.strategies_result = {}
        self.strikes_result = {}
        self.edge_result = {}
        self.final_report = ""
        self.status = WorkflowStatus.PENDING
        self.current_step = ""
        self.step_results = {}
        self.start_time = None
        self.end_time = None
        self.errors = []
        self.timestamp = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_input": self.user_input,
            "route_type": self.route_type,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "has_market_context": self.market_context is not None,
            "validation_result": self.validation_result,
            "features_result": self.features_result,
            "scores_result": self.scores_result,
            "probability_result": self.probability_result,
            "strategies_result": self.strategies_result,
            "edge_result": self.edge_result,
            "errors": self.errors,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        summary = {
            "status": self.status.value,
            "route_type": self.route_type,
            "timestamp": self.timestamp,
        }
        
        if self.validation_result:
            summary["symbol"] = self.validation_result.get("symbol", "")
        
        if self.probability_result:
            decision = self.probability_result.get("decision_gate", {})
            summary["direction"] = decision.get("final_direction", "")
            summary["confidence"] = self.probability_result.get(
                "probability_calibration", {}
            ).get("confidence", "")
        
        if self.strategies_result:
            strategies = self.strategies_result.get("strategies", [])
            summary["strategy_count"] = len(strategies)
            summary["strategies"] = [s.get("name", "") for s in strategies]
        
        if self.errors:
            summary["errors"] = self.errors
        
        return summary