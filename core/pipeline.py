"""
Pipeline Executor - 工作流流水线执行器
负责按顺序执行各个步骤
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from ..workflow import VolatilityWorkflow

from .context import WorkflowStatus


class StepType(Enum):
    """步骤类型"""
    ROUTER = "router"
    COMMAND_GENERATOR = "command_generator"
    DATA_FETCHER = "data_fetcher"
    DATA_VALIDATOR = "data_validator"
    PROBABILITY_CALIBRATOR = "probability_calibrator"
    STRATEGY_MAPPER = "strategy_mapper"
    CONSTRAINT_CHECKER = "constraint_checker"
    FINAL_REPORT = "final_report"


class PipelineExecutor:
    """流水线执行器 - 编排各步骤的执行"""
    
    def __init__(self, workflow: "VolatilityWorkflow"):
        self.workflow = workflow
        self.ctx = workflow.context
        self.logger = workflow.logger
        self.client = workflow.client_manager
    
    async def execute(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """执行完整流水线"""
        self.ctx.status = WorkflowStatus.RUNNING
        
        try:
            # Step 1: 路由判断
            route_result = await self._step_router()
            if route_result.get("route") == "INVALID":
                return self._build_invalid_result(route_result)
            
            # Step 2: 生成命令
            command = await self._step_command_generator(route_result)
            
            # Step 3: 获取数据
            raw_data = await self._step_data_fetcher(command)
            
            # Step 4: 验证数据
            validated_data = await self._step_data_validator(raw_data, command)
            if not validated_data.get("is_valid"):
                return self._build_data_error_result(validated_data)
            
            # Step 5: 概率校准
            probabilities = await self._step_probability_calibrator(validated_data)
            
            # Step 6: 策略映射
            strategy = await self._step_strategy_mapper(probabilities)
            
            # Step 7: 约束检查
            checked_strategy = await self._step_constraint_checker(strategy)
            
            # Step 8: 生成报告
            report = await self._step_final_report(checked_strategy, probabilities)
            
            self.ctx.status = WorkflowStatus.COMPLETED
            return {
                "success": True,
                "route": route_result,
                "command": command,
                "data": validated_data,
                "probabilities": probabilities,
                "strategy": checked_strategy,
                "report": report,
            }
            
        except Exception as e:
            self.ctx.status = WorkflowStatus.FAILED
            self.logger.error(f"Pipeline execution failed: {e}")
            raise
    
    # ==================== 步骤实现 ====================
    
    async def _step_router(self) -> Dict[str, Any]:
        """Step 1: 路由 - 判断用户意图"""
        self.ctx.current_step = StepType.ROUTER.value
        self.logger.info("Step 1: Running router...")
        
        from ..prompts.router import ROUTER_PROMPT
        from ..schemas.router import ROUTER_SCHEMA
        
        response = await self.client.chat_completion(
            messages=[
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": self.ctx.user_input},
            ],
            response_format={"type": "json_object", "schema": ROUTER_SCHEMA},
        )
        
        result = self._parse_json_response(response)
        self.ctx.step_results["router"] = result
        self.logger.info(f"Router result: {result.get('route')}")
        return result
    
    async def _step_command_generator(self, route_result: Dict) -> Dict[str, Any]:
        """Step 2: 生成数据获取命令"""
        self.ctx.current_step = StepType.COMMAND_GENERATOR.value
        self.logger.info("Step 2: Generating command...")
        
        from ..prompts.command_generator import COMMAND_GENERATOR_PROMPT
        from ..schemas.command_generator import COMMAND_SCHEMA
        
        prompt = COMMAND_GENERATOR_PROMPT.format(
            user_input=self.ctx.user_input,
            route_info=route_result,
            meso_context=self.ctx.meso_context or {},
        )
        
        response = await self.client.chat_completion(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": self.ctx.user_input},
            ],
            response_format={"type": "json_object", "schema": COMMAND_SCHEMA},
        )
        
        result = self._parse_json_response(response)
        self.ctx.step_results["command"] = result
        self.logger.info(f"Command generated: {result.get('command_type')}")
        return result
    
    async def _step_data_fetcher(self, command: Dict) -> Dict[str, Any]:
        """Step 3: 执行数据获取"""
        self.ctx.current_step = StepType.DATA_FETCHER.value
        self.logger.info("Step 3: Fetching data...")
        
        # 根据命令类型获取数据
        cmd_type = command.get("command_type", "")
        
        if cmd_type == "TERM_STRUCTURE":
            data = await self._fetch_term_structure(command)
        elif cmd_type == "SKEW":
            data = await self._fetch_skew(command)
        elif cmd_type == "SURFACE":
            data = await self._fetch_surface(command)
        elif cmd_type == "HISTORICAL":
            data = await self._fetch_historical(command)
        else:
            data = await self._fetch_generic(command)
        
        self.ctx.step_results["raw_data"] = data
        return data
    
    async def _step_data_validator(
        self, raw_data: Dict, command: Dict
    ) -> Dict[str, Any]:
        """Step 4: 验证和解析数据"""
        self.ctx.current_step = StepType.DATA_VALIDATOR.value
        self.logger.info("Step 4: Validating data...")
        
        from ..prompts.data_validator import DATA_VALIDATOR_PROMPT
        from ..schemas.data_validator import VALIDATOR_SCHEMA
        
        prompt = DATA_VALIDATOR_PROMPT.format(
            command=command,
            raw_data=raw_data,
        )
        
        response = await self.client.chat_completion(
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object", "schema": VALIDATOR_SCHEMA},
        )
        
        result = self._parse_json_response(response)
        self.ctx.step_results["validated_data"] = result
        return result
    
    async def _step_probability_calibrator(
        self, validated_data: Dict
    ) -> Dict[str, Any]:
        """Step 5: 概率校准"""
        self.ctx.current_step = StepType.PROBABILITY_CALIBRATOR.value
        self.logger.info("Step 5: Calibrating probabilities...")
        
        from ..prompts.probability_calibrator import PROBABILITY_CALIBRATOR_PROMPT
        from ..schemas.probability_calibrator import PROBABILITY_SCHEMA
        
        prompt = PROBABILITY_CALIBRATOR_PROMPT.format(
            data=validated_data,
            meso_context=self.ctx.meso_context or {},
        )
        
        response = await self.client.chat_completion(
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object", "schema": PROBABILITY_SCHEMA},
        )
        
        result = self._parse_json_response(response)
        self.ctx.step_results["probabilities"] = result
        self.logger.info(
            f"Probabilities: L={result.get('prob_long')}, S={result.get('prob_short')}"
        )
        return result
    
    async def _step_strategy_mapper(self, probabilities: Dict) -> Dict[str, Any]:
        """Step 6: 策略映射"""
        self.ctx.current_step = StepType.STRATEGY_MAPPER.value
        self.logger.info("Step 6: Mapping strategy...")
        
        from ..prompts.strategy_mapper import STRATEGY_MAPPER_PROMPT
        from ..schemas.strategy_mapper import STRATEGY_SCHEMA
        
        prompt = STRATEGY_MAPPER_PROMPT.format(
            probabilities=probabilities,
            validated_data=self.ctx.step_results.get("validated_data", {}),
            meso_context=self.ctx.meso_context or {},
        )
        
        response = await self.client.chat_completion(
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object", "schema": STRATEGY_SCHEMA},
        )
        
        result = self._parse_json_response(response)
        self.ctx.step_results["strategy"] = result
        self.logger.info(f"Strategy: {result.get('strategy_name')}")
        return result
    
    async def _step_constraint_checker(self, strategy: Dict) -> Dict[str, Any]:
        """Step 7: 约束检查"""
        self.ctx.current_step = StepType.CONSTRAINT_CHECKER.value
        self.logger.info("Step 7: Checking constraints...")
        
        # 检查黑名单
        symbol = self.ctx.step_results.get("command", {}).get("symbol", "")
        blacklist = self.workflow.config.blacklist or []
        
        if symbol.upper() in [s.upper() for s in blacklist]:
            strategy["blocked"] = True
            strategy["block_reason"] = f"{symbol} is in blacklist"
            self.logger.warning(f"Symbol {symbol} blocked by blacklist")
        
        # 检查仓位限制
        max_position = self.workflow.config.max_position_size
        if strategy.get("position_size", 0) > max_position:
            strategy["position_size"] = max_position
            strategy["size_capped"] = True
            self.logger.info(f"Position size capped to {max_position}")
        
        # 检查最小 edge
        min_edge = self.workflow.config.min_edge_threshold
        if strategy.get("edge", 0) < min_edge:
            strategy["low_edge_warning"] = True
            self.logger.warning(f"Edge {strategy.get('edge')} below threshold {min_edge}")
        
        self.ctx.step_results["checked_strategy"] = strategy
        return strategy
    
    async def _step_final_report(
        self, strategy: Dict, probabilities: Dict
    ) -> Dict[str, Any]:
        """Step 8: 生成最终报告"""
        self.ctx.current_step = StepType.FINAL_REPORT.value
        self.logger.info("Step 8: Generating final report...")
        
        from ..prompts.final_report import FINAL_REPORT_PROMPT
        from ..schemas.final_report import REPORT_SCHEMA
        
        prompt = FINAL_REPORT_PROMPT.format(
            user_input=self.ctx.user_input,
            strategy=strategy,
            probabilities=probabilities,
            validated_data=self.ctx.step_results.get("validated_data", {}),
            command=self.ctx.step_results.get("command", {}),
        )
        
        response = await self.client.chat_completion(
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object", "schema": REPORT_SCHEMA},
        )
        
        result = self._parse_json_response(response)
        self.ctx.step_results["report"] = result
        return result
    
    # ==================== 数据获取方法 ====================
    
    async def _fetch_term_structure(self, command: Dict) -> Dict:
        """获取期限结构数据"""
        # 实际实现会调用外部 API
        return {"type": "term_structure", "command": command, "data": {}}
    
    async def _fetch_skew(self, command: Dict) -> Dict:
        """获取偏度数据"""
        return {"type": "skew", "command": command, "data": {}}
    
    async def _fetch_surface(self, command: Dict) -> Dict:
        """获取波动率曲面数据"""
        return {"type": "surface", "command": command, "data": {}}
    
    async def _fetch_historical(self, command: Dict) -> Dict:
        """获取历史数据"""
        return {"type": "historical", "command": command, "data": {}}
    
    async def _fetch_generic(self, command: Dict) -> Dict:
        """通用数据获取"""
        return {"type": "generic", "command": command, "data": {}}
    
    # ==================== 辅助方法 ====================
    
    def _parse_json_response(self, response: Any) -> Dict[str, Any]:
        """解析 LLM JSON 响应"""
        import json
        
        if isinstance(response, dict):
            return response
        
        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, str):
                return json.loads(content)
            return content
        
        if isinstance(response, str):
            return json.loads(response)
        
        return {"raw": str(response)}
    
    def _build_invalid_result(self, route_result: Dict) -> Dict[str, Any]:
        """构建无效路由结果"""
        return {
            "success": False,
            "error_type": "INVALID_INPUT",
            "message": route_result.get("reason", "Invalid user input"),
            "route": route_result,
        }
    
    def _build_data_error_result(self, validated_data: Dict) -> Dict[str, Any]:
        """构建数据错误结果"""
        return {
            "success": False,
            "error_type": "DATA_VALIDATION_FAILED",
            "message": validated_data.get("error_message", "Data validation failed"),
            "data": validated_data,
        }