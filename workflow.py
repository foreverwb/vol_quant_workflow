"""
波动率套利策略工作流引擎

主入口模块，提供:
- VolatilityWorkflow: 工作流主类
- create_workflow: 快速创建函数
- create_workflow_from_config: 从配置文件创建
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

# 内部模块导入
try:
    from .config import ModelConfig, WorkflowConfig, FileUploadConfig, NodeModelMapping
    from .config.model_config_loader import ModelsConfig, load_models_config
    from .core import (
        WorkflowContext, 
        WorkflowStatus, 
        ClientManager,
        ContextLoader,
        MarketContext,
        DynamicConfig,
        BatchProcessor
    )
    from .nodes import (
        RouterNode,
        CommandGeneratorNode, 
        DataValidatorNode,
        ProbabilityCalibratorNode,
        StrategyMapperNode,
        FinalReportNode,
        code1_feature_calculation,
        code2_signal_scoring,
        code3_strike_calculation,
        code4_edge_estimation
    )
except ImportError:
    from config import ModelConfig, WorkflowConfig, FileUploadConfig, NodeModelMapping
    try:
        from config.model_config_loader import ModelsConfig, load_models_config
    except ImportError:
        ModelsConfig = None
        load_models_config = None
    from core import (
        WorkflowContext, 
        WorkflowStatus, 
        ClientManager,
        ContextLoader,
        MarketContext,
        DynamicConfig,
        BatchProcessor
    )
    from nodes import (
        RouterNode,
        CommandGeneratorNode, 
        DataValidatorNode,
        ProbabilityCalibratorNode,
        StrategyMapperNode,
        FinalReportNode,
        code1_feature_calculation,
        code2_signal_scoring,
        code3_strike_calculation,
        code4_edge_estimation
    )


class VolatilityWorkflow:
    """
    波动率套利策略工作流
    
    工作流程:
    1. Router -> 判断输入类型
    2a. VARIABLES路径: CommandGenerator -> 生成命令清单
    2b. DATA路径: DataValidator -> 数据校验
    3. FeatureCalculation -> 特征计算 (Code)
    4. SignalScoring -> 信号打分 (Code)
    5. ProbabilityCalibrator -> 概率校准 (LLM)
    6. StrategyMapper -> 策略映射 (LLM)
    7. StrikeCalculation -> 行权价计算 (Code)
    8. EdgeEstimation -> Edge估算 (Code)
    9. FinalReport -> 生成决策报告 (LLM)
    """
    
    def __init__(
        self,
        model_config: Optional[ModelConfig] = None,
        vision_model_config: Optional[ModelConfig] = None,
        workflow_config: Optional[WorkflowConfig] = None,
        file_config: Optional[FileUploadConfig] = None,
        node_model_mapping: Optional[NodeModelMapping] = None,
        models_config: Optional[ModelsConfig] = None,
        models_config_path: Optional[str] = None,
        env: Optional[str] = None
    ):
        """
        初始化工作流
        
        支持三种配置方式 (优先级从高到低):
        1. models_config / models_config_path: 从 YAML 配置
        2. node_model_mapping: 节点模型映射
        3. model_config: 默认配置
        """
        self.workflow_config = workflow_config or WorkflowConfig()
        self.file_config = file_config or FileUploadConfig()
        
        # 加载模型配置
        self._models_config: Optional[ModelsConfig] = None
        if models_config:
            self._models_config = models_config
        elif models_config_path or (ModelsConfig and load_models_config):
            try:
                self._models_config = load_models_config(models_config_path, env)
            except Exception as e:
                print(f"Warning: Failed to load models config: {e}")
        
        # 设置默认模型配置
        self.model_config = model_config or ModelConfig()
        if self._models_config and not model_config:
            self.model_config = ModelConfig(
                name=self._models_config.defaults.get('model', 'gpt-4o'),
                api_base=self._models_config.defaults.get('api_base', ''),
                api_key=self._models_config.defaults.get('api_key', ''),
                temperature=self._models_config.defaults.get('temperature', 0.7),
                max_tokens=self._models_config.defaults.get('max_tokens', 4096),
            )
        
        self.vision_model_config = vision_model_config or self.model_config
        
        # 创建客户端管理器
        self._client_manager = ClientManager(
            model_config=self.model_config,
            vision_model_config=self.vision_model_config,
            models_config=self._models_config,
            node_model_mapping=node_model_mapping
        )
        
        # 创建上下文加载器
        self.context_loader = ContextLoader(self.workflow_config.MESO_API_URL)
        
        # 初始化节点
        self._init_nodes()
        
        # 工作流上下文
        self.context = WorkflowContext()
        
        # 动态配置
        self._dynamic_workflow_config: Optional[WorkflowConfig] = None
    
    def _init_nodes(self):
        """初始化所有节点"""
        get_client = self._client_manager.get_client
        
        self.router = RouterNode(
            get_client("router"), 
            self.workflow_config
        )
        self.command_generator = CommandGeneratorNode(
            get_client("command_generator"), 
            self.workflow_config
        )
        self.data_validator = DataValidatorNode(
            get_client("data_validator"), 
            self.workflow_config
        )
        self.probability_calibrator = ProbabilityCalibratorNode(
            get_client("probability_calibrator"), 
            self.workflow_config
        )
        self.strategy_mapper = StrategyMapperNode(
            get_client("strategy_mapper"), 
            self.workflow_config
        )
        self.final_report_node = FinalReportNode(
            get_client("final_report"), 
            self.workflow_config
        )
    
    # ========== 类方法 ==========
    
    @classmethod
    def from_config(
        cls,
        config_path: Optional[str] = None,
        env: Optional[str] = None,
        workflow_config: Optional[WorkflowConfig] = None,
        **kwargs
    ) -> 'VolatilityWorkflow':
        """从 YAML 配置文件创建工作流实例"""
        return cls(
            models_config_path=config_path,
            env=env,
            workflow_config=workflow_config or WorkflowConfig.from_env(),
            **kwargs
        )
    
    # ========== 属性 ==========
    
    @property
    def text_client(self):
        """默认文本客户端 (向后兼容)"""
        return self._client_manager.text_client
    
    @property
    def vision_client(self):
        """默认视觉客户端 (向后兼容)"""
        return self._client_manager.vision_client
    
    # ========== 公共方法 ==========
    
    def reset(self):
        """重置工作流状态"""
        self.context = WorkflowContext()
        self._dynamic_workflow_config = None
    
    def get_models_summary(self) -> str:
        """获取模型配置摘要"""
        return self._client_manager.get_summary()
    
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
            # Step 1: Router
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
                return await self._handle_variables_route(user_input)
            elif self.context.route_type == "DATA":
                return await self._run_analysis_pipeline()
            else:
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
    
    def run_sync(
        self,
        user_input: str = "",
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """同步运行工作流"""
        return asyncio.run(self.run(user_input, files))
    
    async def close(self):
        """关闭所有资源"""
        await self._client_manager.close_all()
    
    # ========== 私有方法 ==========
    
    async def _handle_variables_route(self, user_input: str) -> Dict[str, Any]:
        """处理 VARIABLES 路由"""
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
    
    async def _run_analysis_pipeline(self) -> Dict[str, Any]:
        """运行数据分析流水线"""
        
        # Step 3: DataValidator
        print("[Step 3] Running DataValidator...")
        validation_result = await self.data_validator.execute(
            files=self.context.uploaded_files
        )
        
        if not validation_result.success:
            raise Exception(f"DataValidator failed: {validation_result.error}")
        
        self.context.validation_result = validation_result.structured_output or {}
        self.context.core_fields = self.context.validation_result.get("core_fields", {})
        
        # Step 3.5: 加载 Meso 上下文
        symbol = self.context.validation_result.get("symbol", "")
        if symbol and self.workflow_config.MESO_ENABLED:
            print(f"[Step 3.5] Loading Meso Context for {symbol}...")
            await self._load_meso_context(symbol)
        
        # 检查数据完整性
        status = self.context.validation_result.get("status", "")
        if status == "missing_data":
            return {
                "status": "missing_data",
                "message": "缺失关键数据，请补充",
                "missing_fields": self.context.validation_result.get("missing_fields", []),
                "validation_result": self.context.validation_result
            }
        
        # 获取生效配置
        effective_config = self._dynamic_workflow_config or self.workflow_config
        context_params = self.context.context_params or None
        
        # Step 4: FeatureCalculation
        print("[Step 4] Running FeatureCalculation...")
        features_result = code1_feature_calculation(
            self.context.validation_result,
            effective_config.to_dict()
        )
        if not features_result.success:
            raise Exception(f"FeatureCalculation failed: {features_result.error}")
        self.context.features_result = features_result.result
        
        # Step 5: SignalScoring
        print("[Step 5] Running SignalScoring...")
        scores_result = code2_signal_scoring(
            self.context.features_result,
            effective_config.to_dict(),
            context_params
        )
        if not scores_result.success:
            raise Exception(f"SignalScoring failed: {scores_result.error}")
        self.context.scores_result = scores_result.result
        
        # Step 6: ProbabilityCalibrator
        print("[Step 6] Running ProbabilityCalibrator...")
        prob_result = await self.probability_calibrator.execute(
            scores_result=self.context.scores_result
        )
        if not prob_result.success:
            raise Exception(f"ProbabilityCalibrator failed: {prob_result.error}")
        self.context.probability_result = prob_result.structured_output or {}
        
        # Step 7: StrategyMapper
        print("[Step 7] Running StrategyMapper...")
        strategy_result = await self.strategy_mapper.execute(
            probability_result=self.context.probability_result,
            core_fields=self.context.core_fields,
            features=self.context.features_result.get("features", {}),
            scores=self.context.scores_result,
            context_params=context_params
        )
        if not strategy_result.success:
            raise Exception(f"StrategyMapper failed: {strategy_result.error}")
        self.context.strategies_result = strategy_result.structured_output or {}
        
        # Step 8: StrikeCalculation
        print("[Step 8] Running StrikeCalculation...")
        strikes_result = code3_strike_calculation(
            self.context.strategies_result,
            self.context.validation_result,
            self.workflow_config.to_dict()
        )
        if not strikes_result.success:
            raise Exception(f"StrikeCalculation failed: {strikes_result.error}")
        self.context.strikes_result = strikes_result.result
        
        # Step 9: EdgeEstimation
        print("[Step 9] Running EdgeEstimation...")
        edge_result = code4_edge_estimation(
            self.context.strikes_result,
            self.context.validation_result,
            self.workflow_config.to_dict()
        )
        if not edge_result.success:
            raise Exception(f"EdgeEstimation failed: {edge_result.error}")
        self.context.edge_result = edge_result.result
        
        # Step 10: FinalReport
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
        
        return self._build_result()
    
    async def _load_meso_context(self, symbol: str) -> Optional[MarketContext]:
        """加载 Meso 上下文"""
        if not self.workflow_config.MESO_ENABLED or not symbol:
            return None
        
        try:
            market_context = await self.context_loader.fetch_context(symbol)
            
            if market_context:
                print(self.context_loader.get_context_summary(market_context))
                
                # 生成动态配置
                dynamic_config = self.context_loader.generate_dynamic_config(
                    self.workflow_config, 
                    market_context
                )
                
                self._dynamic_workflow_config = self.workflow_config.apply_dynamic_config(
                    dynamic_config
                )
                
                # 构建上下文参数
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
                    'WEIGHT_VRP_LONG': dynamic_config.WEIGHT_VRP_LONG,
                    'WEIGHT_GEX_LONG': dynamic_config.WEIGHT_GEX_LONG,
                    'WEIGHT_VEX_LONG': dynamic_config.WEIGHT_VEX_LONG,
                    'WEIGHT_CARRY_LONG': dynamic_config.WEIGHT_CARRY_LONG,
                    'WEIGHT_SKEW_LONG': dynamic_config.WEIGHT_SKEW_LONG,
                    'WEIGHT_VRP_SHORT': dynamic_config.WEIGHT_VRP_SHORT,
                    'WEIGHT_GEX_SHORT': dynamic_config.WEIGHT_GEX_SHORT,
                    'WEIGHT_CARRY_SHORT': dynamic_config.WEIGHT_CARRY_SHORT,
                }
                
                self.context.market_context = market_context
                self.context.dynamic_config = dynamic_config
                
            return market_context
            
        except Exception as e:
            print(f"[Meso] Error loading context: {e}")
            return None
    
    def _build_result(self) -> Dict[str, Any]:
        """构建最终结果"""
        # Meso 摘要
        meso_summary = None
        if self.context.market_context:
            mc = self.context.market_context
            meso_summary = {
                "quadrant": mc.quadrant,
                "direction_score": mc.direction_score,
                "vol_score": mc.vol_score,
                "is_squeeze": mc.is_squeeze,
            }
        
        return {
            "status": "completed",
            "report": self.context.final_report,
            "summary": self.context.get_summary(),
            "meso_context": meso_summary,
            "details": {
                "validation": self.context.validation_result,
                "features": self.context.features_result,
                "scores": self.context.scores_result,
                "probability": self.context.probability_result,
                "strategies": self.context.strategies_result,
                "strikes": self.context.strikes_result,
                "edge": self.context.edge_result,
            }
        }


# ============================================================
# 便捷函数
# ============================================================

def create_workflow(
    api_base: str,
    api_key: str = "",
    model_name: str = "gpt-4o",
    vision_model_name: Optional[str] = None,
    temperature: float = 0.7,
    node_model_mapping: Optional[NodeModelMapping] = None,
    **kwargs
) -> VolatilityWorkflow:
    """
    快速创建工作流实例
    
    Args:
        api_base: API 端点
        api_key: API 密钥
        model_name: 默认模型名称
        vision_model_name: 视觉模型名称
        temperature: 温度参数
        node_model_mapping: 节点模型映射
        
    Returns:
        VolatilityWorkflow 实例
    """
    model_config = ModelConfig(
        api_base=api_base,
        api_key=api_key,
        name=model_name,
        temperature=temperature,
        vision_enabled=False
    )
    
    vision_config = ModelConfig(
        api_base=api_base,
        api_key=api_key,
        name=vision_model_name or model_name,
        temperature=temperature,
        vision_enabled=True,
        vision_detail="high"
    )
    
    return VolatilityWorkflow(
        model_config=model_config,
        vision_model_config=vision_config,
        workflow_config=WorkflowConfig.from_env(),
        node_model_mapping=node_model_mapping
    )


def create_workflow_from_config(
    config_path: Optional[str] = None,
    env: Optional[str] = None,
    **kwargs
) -> VolatilityWorkflow:
    """
    从 YAML 配置文件创建工作流实例 (推荐)
    
    Args:
        config_path: 配置文件路径，默认 config/models.yaml
        env: 环境名称 (development/production)
        
    Returns:
        VolatilityWorkflow 实例
    """
    return VolatilityWorkflow.from_config(
        config_path=config_path,
        env=env,
        **kwargs
    )


# 导出
__all__ = [
    "VolatilityWorkflow",
    "WorkflowContext",
    "WorkflowStatus",
    "BatchProcessor",
    "create_workflow",
    "create_workflow_from_config",
]
