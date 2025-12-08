"""
波动率套利策略工作流引擎
编排所有节点的执行流程

支持上下文感知：
- 从 Meso 系统 (volatility_analysis) 获取市场上下文
- 动态调整决策阈值、因子权重、Z-Score 标准差
- 提供策略黑名单和 DTE 建议
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import sys

# 支持两种运行方式
try:
    from .config import ModelConfig, WorkflowConfig, FileUploadConfig
    from .utils.llm_client import LLMClient, create_llm_client
    from .core.context_loader import ContextLoader, MarketContext, DynamicConfig
    from .nodes import (
        RouterNode,
        CommandGeneratorNode, 
        DataValidatorNode,
        ProbabilityCalibratorNode,
        StrategyMapperNode,
        FinalReportNode,
        NodeFactory,
        code1_feature_calculation,
        code2_signal_scoring,
        code3_strike_calculation,
        code4_edge_estimation
    )
except ImportError:
    from config import ModelConfig, WorkflowConfig, FileUploadConfig
    from utils.llm_client import LLMClient, create_llm_client
    from core.context_loader import ContextLoader, MarketContext, DynamicConfig
    from nodes import (
        RouterNode,
        CommandGeneratorNode, 
        DataValidatorNode,
        ProbabilityCalibratorNode,
        StrategyMapperNode,
        FinalReportNode,
        NodeFactory,
        code1_feature_calculation,
        code2_signal_scoring,
        code3_strike_calculation,
        code4_edge_estimation
    )


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_INPUT = "waiting_input"


@dataclass
class WorkflowContext:
    """工作流上下文 - 存储中间结果"""
    # 输入数据
    user_input: str = ""
    uploaded_files: List[str] = field(default_factory=list)
    
    # 路由结果
    route_type: str = ""  # VARIABLES / DATA / INVALID
    
    # 命令清单
    commands: str = ""
    
    # ===== Meso 上下文 (新增) =====
    market_context: Optional[MarketContext] = None
    dynamic_config: Optional[DynamicConfig] = None
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
    
    # 元数据
    status: WorkflowStatus = WorkflowStatus.PENDING
    errors: List[str] = field(default_factory=list)
    timestamp: str = ""


class VolatilityWorkflow:
    """
    波动率套利策略工作流
    
    工作流程:
    0. [新增] ContextLoader -> 获取 Meso 上下文 (可选)
    1. Router -> 判断输入类型
    2a. VARIABLES路径: CommandGenerator -> 生成命令清单
    2b. DATA路径: DataValidator -> 数据校验
    3. FeatureCalculation -> 特征计算 (Code)
    4. SignalScoring -> 信号打分 (Code, 支持上下文感知)
    5. ProbabilityCalibrator -> 概率校准 (LLM)
    6. StrategyMapper -> 策略映射 (LLM, 支持策略黑名单)
    7. StrikeCalculation -> 行权价计算 (Code)
    8. EdgeEstimation -> Edge估算 (Code)
    9. FinalReport -> 生成决策报告 (LLM)
    """
    
    def __init__(
        self,
        model_config: ModelConfig,
        vision_model_config: Optional[ModelConfig] = None,
        workflow_config: Optional[WorkflowConfig] = None,
        file_config: Optional[FileUploadConfig] = None
    ):
        """
        初始化工作流
        
        Args:
            model_config: 文本模型配置
            vision_model_config: 视觉模型配置 (用于图表解析)
            workflow_config: 工作流参数配置
            file_config: 文件上传配置
        """
        self.model_config = model_config
        self.vision_model_config = vision_model_config or model_config
        self.workflow_config = workflow_config or WorkflowConfig()
        self.file_config = file_config or FileUploadConfig()
        
        # 创建LLM客户端
        self.text_client = LLMClient(model_config)
        self.vision_client = LLMClient(vision_model_config) if vision_model_config else self.text_client
        
        # 创建上下文加载器 (新增)
        self.context_loader = ContextLoader(self.workflow_config.MESO_API_URL)
        
        # 创建节点实例
        self._init_nodes()
        
        # 工作流上下文
        self.context = WorkflowContext()
        
        # 动态配置 (由 Meso 上下文生成)
        self._dynamic_workflow_config: Optional[WorkflowConfig] = None
    
    def _init_nodes(self):
        """初始化所有节点"""
        self.router = RouterNode(self.text_client, self.workflow_config)
        self.command_generator = CommandGeneratorNode(self.text_client, self.workflow_config)
        self.data_validator = DataValidatorNode(self.vision_client, self.workflow_config)
        self.probability_calibrator = ProbabilityCalibratorNode(self.text_client, self.workflow_config)
        self.strategy_mapper = StrategyMapperNode(self.text_client, self.workflow_config)
        self.final_report_node = FinalReportNode(self.text_client, self.workflow_config)
    
    def reset(self):
        """重置工作流状态"""
        self.context = WorkflowContext()
        self._dynamic_workflow_config = None
    
    async def _load_meso_context(self, symbol: str) -> Optional[MarketContext]:
        """
        从 Meso 系统加载市场上下文
        
        Args:
            symbol: 股票代码
            
        Returns:
            MarketContext 或 None
        """
        if not self.workflow_config.MESO_ENABLED:
            print("[Meso] 上下文感知已禁用")
            return None
            
        if not symbol:
            print("[Meso] 未提供 symbol，跳过上下文加载")
            return None
        
        try:
            print(f"[Meso] 正在从 {self.workflow_config.MESO_API_URL} 获取 {symbol} 上下文...")
            
            market_context = await self.context_loader.fetch_context(symbol)
            
            if market_context:
                print(self.context_loader.get_context_summary(market_context))
                
                # 生成动态配置
                dynamic_config = self.context_loader.generate_dynamic_config(
                    self.workflow_config, 
                    market_context
                )
                
                # 应用到工作流配置
                self._dynamic_workflow_config = self.workflow_config.apply_dynamic_config(dynamic_config)
                
                # 构建上下文参数 (传递给信号计算等)
                self.context.context_params = {
                    'vol_scale_factor': dynamic_config.vol_scale_factor,
                    'gex_signal_multiplier': dynamic_config.gex_signal_multiplier,
                    'vex_signal_multiplier': dynamic_config.vex_signal_multiplier,
                    'is_squeeze': market_context.is_squeeze,
                    'direction_score': market_context.direction_score,
                    'strategy_blacklist': list(dynamic_config.strategy_blacklist),
                    'suggested_dte_min': dynamic_config.suggested_dte_min,
                    'suggested_dte_max': dynamic_config.suggested_dte_max,
                    'dte_reason': dynamic_config.dte_reason,
                    'suggested_delta_bias': dynamic_config.suggested_delta_bias,
                    # 动态权重
                    'WEIGHT_VRP_LONG': dynamic_config.WEIGHT_VRP_LONG,
                    'WEIGHT_GEX_LONG': dynamic_config.WEIGHT_GEX_LONG,
                    'WEIGHT_VEX_LONG': dynamic_config.WEIGHT_VEX_LONG,
                    'WEIGHT_CARRY_LONG': dynamic_config.WEIGHT_CARRY_LONG,
                    'WEIGHT_SKEW_LONG': dynamic_config.WEIGHT_SKEW_LONG,
                    'WEIGHT_VRP_SHORT': dynamic_config.WEIGHT_VRP_SHORT,
                    'WEIGHT_GEX_SHORT': dynamic_config.WEIGHT_GEX_SHORT,
                    'WEIGHT_CARRY_SHORT': dynamic_config.WEIGHT_CARRY_SHORT,
                }
                
                print(f"[Meso] 动态配置已生成: Threshold_L={dynamic_config.DECISION_THRESHOLD_LONG:.2f}, "
                      f"Threshold_S={dynamic_config.DECISION_THRESHOLD_SHORT:.2f}, "
                      f"VolScale={dynamic_config.vol_scale_factor:.2f}")
                
                if dynamic_config.strategy_blacklist:
                    print(f"[Meso] 策略黑名单: {dynamic_config.strategy_blacklist}")
                
                self.context.market_context = market_context
                self.context.dynamic_config = dynamic_config
                
            else:
                print("[Meso] 未获取到上下文，使用默认配置")
                
            return market_context
            
        except Exception as e:
            print(f"[Meso] 加载上下文时出错: {e}，将使用默认配置")
            return None
    
    async def run(
        self,
        user_input: str = "",
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        运行完整工作流
        
        Args:
            user_input: 用户输入文本
            files: 上传的文件路径列表
            
        Returns:
            工作流执行结果
        """
        self.context.user_input = user_input
        self.context.uploaded_files = files or []
        self.context.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S ET")
        self.context.status = WorkflowStatus.RUNNING
        
        try:
            # Step 1: Router - 判断输入类型
            print("[Step 1] Running Router...")
            route_result = await self.router.execute(
                user_input=user_input,
                has_files=bool(files)
            )
            
            if not route_result.success:
                raise Exception(f"Router failed: {route_result.error}")
            
            self.context.route_type = route_result.text
            print(f"  Route type: {self.context.route_type}")
            
            # Step 2: 根据路由类型分支
            if self.context.route_type == "VARIABLES":
                # 生成命令清单
                print("[Step 2] Running CommandGenerator...")
                cmd_result = await self.command_generator.execute(user_input)
                
                if cmd_result.success:
                    self.context.commands = cmd_result.text
                    self.context.status = WorkflowStatus.WAITING_INPUT
                    return {
                        "status": "waiting_data",
                        "message": "已生成命令清单，请执行后回传图表数据",
                        "commands": self.context.commands
                    }
                else:
                    raise Exception(f"CommandGenerator failed: {cmd_result.error}")
            
            elif self.context.route_type == "DATA":
                # 继续数据分析流程
                return await self._run_analysis_pipeline()
            
            else:
                # 无效输入
                self.context.status = WorkflowStatus.FAILED
                return {
                    "status": "invalid",
                    "message": "无效输入，请提供标的信息或图表数据"
                }
                
        except Exception as e:
            self.context.status = WorkflowStatus.FAILED
            self.context.errors.append(str(e))
            return {
                "status": "error",
                "message": str(e),
                "errors": self.context.errors
            }
    
    async def _run_analysis_pipeline(self) -> Dict[str, Any]:
        """运行数据分析流水线"""
        
        # Step 3: DataValidator - 数据校验
        print("[Step 3] Running DataValidator...")
        validation_result = await self.data_validator.execute(
            files=self.context.uploaded_files
        )
        
        if not validation_result.success:
            raise Exception(f"DataValidator failed: {validation_result.error}")
        
        self.context.validation_result = validation_result.structured_output or {}
        self.context.core_fields = self.context.validation_result.get("core_fields", {})
        
        # ===== Step 3.5: 加载 Meso 上下文 (新增) =====
        symbol = self.context.validation_result.get("symbol", "")
        if symbol and self.workflow_config.MESO_ENABLED:
            print(f"[Step 3.5] Loading Meso Context for {symbol}...")
            await self._load_meso_context(symbol)
        
        # 获取生效的配置 (可能被 Meso 动态调整)
        effective_config = self._dynamic_workflow_config or self.workflow_config
        
        # 检查数据完整性
        status = self.context.validation_result.get("status", "")
        if status == "missing_data":
            missing = self.context.validation_result.get("missing_fields", [])
            return {
                "status": "missing_data",
                "message": "缺失关键数据，请补充",
                "missing_fields": missing,
                "validation_result": self.context.validation_result
            }
        
        # Step 4: FeatureCalculation - 特征计算 (Code)
        print("[Step 4] Running FeatureCalculation...")
        features_result = code1_feature_calculation(
            self.context.validation_result,
            effective_config.to_dict()  # 使用动态配置
        )
        
        if not features_result.success:
            raise Exception(f"FeatureCalculation failed: {features_result.error}")
        
        self.context.features_result = features_result.result
        
        # Step 5: SignalScoring - 信号打分 (Code, 支持上下文感知)
        print("[Step 5] Running SignalScoring...")
        
        # 传递上下文参数 (新增)
        # 注意：空字典应该传 None，避免误判
        context_params = self.context.context_params if self.context.context_params else None
        if context_params:
            print(f"  [Context-Aware] vol_scale={context_params.get('vol_scale_factor', 1.0):.2f}, "
                  f"gex_mult={context_params.get('gex_signal_multiplier', 1.0):.1f}")
        
        scores_result = code2_signal_scoring(
            self.context.features_result,
            effective_config.to_dict(),
            context_params  # 新增: 传递上下文参数
        )
        
        if not scores_result.success:
            raise Exception(f"SignalScoring failed: {scores_result.error}")
        
        self.context.scores_result = scores_result.result
        
        # Step 6: ProbabilityCalibrator - 概率校准 (LLM)
        print("[Step 6] Running ProbabilityCalibrator...")
        prob_result = await self.probability_calibrator.execute(
            scores_result=self.context.scores_result
        )
        
        if not prob_result.success:
            raise Exception(f"ProbabilityCalibrator failed: {prob_result.error}")
        
        self.context.probability_result = prob_result.structured_output or {}
        
        # 检查决策方向
        direction = self.context.probability_result.get("decision_gate", {}).get("final_direction", "")
        if direction == "观望":
            print("  Decision: 观望 (No action)")
            # 仍然生成报告但标记为观望
        
        # Step 7: StrategyMapper - 策略映射 (LLM, 支持策略黑名单)
        print("[Step 7] Running StrategyMapper...")
        
        # 传递上下文参数 (新增)
        if context_params and context_params.get('strategy_blacklist'):
            print(f"  [Context-Aware] 策略黑名单: {context_params.get('strategy_blacklist')}")
            print(f"  [Context-Aware] DTE建议: {context_params.get('suggested_dte_min')}-{context_params.get('suggested_dte_max')}D")
        
        strategy_result = await self.strategy_mapper.execute(
            probability_result=self.context.probability_result,
            core_fields=self.context.core_fields,
            features=self.context.features_result.get("features", {}),
            scores=self.context.scores_result,
            context_params=context_params  # 新增: 传递上下文参数
        )
        
        if not strategy_result.success:
            raise Exception(f"StrategyMapper failed: {strategy_result.error}")
        
        self.context.strategies_result = strategy_result.structured_output or {}
        
        # Step 8: StrikeCalculation - 行权价计算 (Code)
        print("[Step 8] Running StrikeCalculation...")
        strikes_result = code3_strike_calculation(
            self.context.strategies_result,
            self.context.validation_result,
            self.workflow_config.to_dict()
        )
        
        if not strikes_result.success:
            raise Exception(f"StrikeCalculation failed: {strikes_result.error}")
        
        self.context.strikes_result = strikes_result.result
        
        # Step 9: EdgeEstimation - Edge估算 (Code)
        print("[Step 9] Running EdgeEstimation...")
        edge_result = code4_edge_estimation(
            self.context.strikes_result,
            self.context.validation_result,
            self.workflow_config.to_dict()
        )
        
        if not edge_result.success:
            raise Exception(f"EdgeEstimation failed: {edge_result.error}")
        
        self.context.edge_result = edge_result.result
        
        # Step 10: FinalReport - 生成决策报告 (LLM)
        print("[Step 10] Running FinalReport...")
        report_result = await self.final_report_node.execute(
            core_fields=self.context.core_fields,
            features=self.context.features_result.get("features", {}),
            scores=self.context.scores_result,
            probability=self.context.probability_result,
            strategies=self.context.edge_result
        )
        
        if not report_result.success:
            raise Exception(f"FinalReport failed: {report_result.error}")
        
        self.context.final_report = report_result.text
        self.context.status = WorkflowStatus.COMPLETED
        
        print("[Workflow Completed]")
        
        # 构建 Meso 上下文摘要 (如果有)
        meso_summary = None
        if self.context.market_context:
            mc = self.context.market_context
            meso_summary = {
                "quadrant": mc.quadrant,
                "direction_score": mc.direction_score,
                "vol_score": mc.vol_score,
                "is_squeeze": mc.is_squeeze,
                "iv30": mc.iv30,
                "ivr": mc.ivr,
                "days_to_earnings": mc.days_to_earnings,
                "confidence": mc.confidence
            }
        
        dynamic_config_summary = None
        if self.context.dynamic_config:
            dc = self.context.dynamic_config
            dynamic_config_summary = {
                "threshold_long": dc.DECISION_THRESHOLD_LONG,
                "threshold_short": dc.DECISION_THRESHOLD_SHORT,
                "vol_scale_factor": dc.vol_scale_factor,
                "strategy_blacklist": list(dc.strategy_blacklist),
                "dte_range": f"{dc.suggested_dte_min}-{dc.suggested_dte_max}D",
                "dte_reason": dc.dte_reason
            }
        
        return {
            "status": "completed",
            "report": self.context.final_report,
            "summary": {
                "symbol": self.context.validation_result.get("symbol", ""),
                "direction": self.context.probability_result.get("decision_gate", {}).get("final_direction", ""),
                "long_score": self.context.scores_result.get("scores", {}).get("long_vol_score", 0),
                "short_score": self.context.scores_result.get("scores", {}).get("short_vol_score", 0),
                "strategies_count": len(self.context.edge_result.get("strategies_with_edge", []))
            },
            # 新增: Meso 上下文信息
            "meso_context": meso_summary,
            "dynamic_config": dynamic_config_summary,
            "context_aware": self.context.market_context is not None,
            "details": {
                "validation": self.context.validation_result,
                "features": self.context.features_result,
                "scores": self.context.scores_result,
                "probability": self.context.probability_result,
                "strategies": self.context.edge_result
            }
        }
    
    def run_sync(
        self,
        user_input: str = "",
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """同步运行工作流"""
        return asyncio.run(self.run(user_input, files))
    
    async def close(self):
        """关闭资源"""
        await self.text_client.close()
        if self.vision_client != self.text_client:
            await self.vision_client.close()


# ============================================================
# 批量处理支持
# ============================================================
class BatchProcessor:
    """
    批量处理器
    支持处理文件夹中的多份分析标的图表
    """
    
    def __init__(
        self,
        workflow: VolatilityWorkflow,
        output_dir: str = "./outputs"
    ):
        self.workflow = workflow
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def scan_folder(self, folder_path: str) -> Dict[str, List[str]]:
        """
        扫描文件夹，按标的分组图片
        
        支持的文件命名格式:
        - {SYMBOL}_{command}.png
        - {SYMBOL}_{command}_{timestamp}.png
        
        Returns:
            按标的分组的文件列表
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # 支持的图片扩展名
        valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        
        # 按标的分组
        grouped_files: Dict[str, List[str]] = {}
        
        for file in folder.iterdir():
            if file.suffix.lower() not in valid_extensions:
                continue
            
            # 从文件名提取标的代码 (假设格式: SYMBOL_xxx.png)
            name_parts = file.stem.split('_')
            if name_parts:
                symbol = name_parts[0].upper()
                if 1 <= len(symbol) <= 5 and symbol.isalpha():
                    if symbol not in grouped_files:
                        grouped_files[symbol] = []
                    grouped_files[symbol].append(str(file))
        
        return grouped_files
    
    async def process_folder(
        self,
        folder_path: str,
        min_files_per_symbol: int = 10
    ) -> Dict[str, Any]:
        """
        处理文件夹中的所有标的
        
        Args:
            folder_path: 图表文件夹路径
            min_files_per_symbol: 每个标的最少需要的图表数量
            
        Returns:
            处理结果汇总
        """
        grouped_files = self.scan_folder(folder_path)
        
        results = {
            "total_symbols": len(grouped_files),
            "processed": [],
            "skipped": [],
            "errors": []
        }
        
        for symbol, files in grouped_files.items():
            print(f"\n{'='*50}")
            print(f"Processing {symbol} ({len(files)} files)")
            print('='*50)
            
            if len(files) < min_files_per_symbol:
                results["skipped"].append({
                    "symbol": symbol,
                    "reason": f"Insufficient files ({len(files)} < {min_files_per_symbol})"
                })
                continue
            
            try:
                # 重置工作流
                self.workflow.reset()
                
                # 运行分析
                result = await self.workflow.run(files=files)
                
                # 保存报告
                if result.get("status") == "completed":
                    report_path = self.output_dir / f"{symbol}_report.md"
                    with open(report_path, "w", encoding="utf-8") as f:
                        f.write(result.get("report", ""))
                    
                    # 保存详细数据
                    data_path = self.output_dir / f"{symbol}_data.json"
                    with open(data_path, "w", encoding="utf-8") as f:
                        json.dump(result.get("details", {}), f, ensure_ascii=False, indent=2)
                    
                    results["processed"].append({
                        "symbol": symbol,
                        "report_path": str(report_path),
                        "data_path": str(data_path),
                        "summary": result.get("summary", {})
                    })
                else:
                    results["errors"].append({
                        "symbol": symbol,
                        "status": result.get("status"),
                        "message": result.get("message", "")
                    })
                    
            except Exception as e:
                results["errors"].append({
                    "symbol": symbol,
                    "error": str(e)
                })
        
        # 保存汇总
        summary_path = self.output_dir / "batch_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        return results
    
    def process_folder_sync(
        self,
        folder_path: str,
        min_files_per_symbol: int = 10
    ) -> Dict[str, Any]:
        """同步处理文件夹"""
        return asyncio.run(self.process_folder(folder_path, min_files_per_symbol))


# ============================================================
# 便捷函数
# ============================================================
def create_workflow(
    api_base: str,
    api_key: str = "",
    model_name: str = "default-model",
    vision_model_name: Optional[str] = None,
    temperature: float = 0.7,
    **kwargs
) -> VolatilityWorkflow:
    """
    快速创建工作流实例
    
    示例:
        # 使用单一模型
        workflow = create_workflow(
            api_base="https://api.openai.com/v1",
            api_key="sk-xxx",
            model_name="gpt-4o"
        )
        
        # 使用不同的视觉模型
        workflow = create_workflow(
            api_base="https://api.openai.com/v1",
            api_key="sk-xxx",
            model_name="gpt-4o-mini",
            vision_model_name="gpt-4o"
        )
    """
    # 文本模型配置
    model_config = ModelConfig(
        api_base=api_base,
        api_key=api_key,
        name=model_name,
        temperature=temperature,
        vision_enabled=False
    )
    
    # 视觉模型配置
    if vision_model_name:
        vision_config = ModelConfig(
            api_base=api_base,
            api_key=api_key,
            name=vision_model_name,
            temperature=temperature,
            vision_enabled=True,
            vision_detail="high"
        )
    else:
        # 使用同一模型，启用视觉
        vision_config = ModelConfig(
            api_base=api_base,
            api_key=api_key,
            name=model_name,
            temperature=temperature,
            vision_enabled=True,
            vision_detail="high"
        )
    
    return VolatilityWorkflow(
        model_config=model_config,
        vision_model_config=vision_config,
        workflow_config=WorkflowConfig.from_env()
    )
