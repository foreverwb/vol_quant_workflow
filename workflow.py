"""
Volatility Quant Workflow - 主工作流类
精简版：仅包含公共接口，核心逻辑委托给子模块
"""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .config import WorkflowConfig, ModelConfig
from .core import (
    WorkflowContext,
    WorkflowStatus,
    ClientManager,
    SimpleLogger,
    SimpleErrorCollector,
)
from .core.pipeline import PipelineExecutor
from .core.result_builder import ResultBuilder
from .core.meso_handler import MesoHandler


class VolatilityWorkflow:
    """波动率量化策略工作流 - 主入口类"""
    
    def __init__(
        self,
        config: WorkflowConfig,
        logger: Optional[Any] = None,
        error_collector: Optional[Any] = None,
    ):
        self.config = config
        self.logger = logger or SimpleLogger()
        self.error_collector = error_collector or SimpleErrorCollector()
        
        # 初始化上下文
        self.context = WorkflowContext(
            config=config,
            logger=self.logger,
            error_collector=self.error_collector,
        )
        
        # 初始化客户端管理器
        self.client_manager = ClientManager(config, self.logger)
        
        # 初始化子组件
        self._pipeline = PipelineExecutor(self)
        self._result_builder = ResultBuilder(self)
        self._meso_handler = MesoHandler(self)
        
        # 状态追踪
        self._initialized = False
        self._closed = False
    
    async def initialize(self) -> None:
        """初始化工作流"""
        if self._initialized:
            return
        
        try:
            await self.client_manager.initialize()
            self._initialized = True
            self.logger.info("Workflow initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize workflow: {e}")
            raise
    
    async def run(
        self,
        user_input: str = "",
        files: Optional[List[str]] = None,
        meso_context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        运行工作流主入口
        
        Args:
            user_input: 用户输入的查询
            files: 上传的文件列表
            meso_context: Meso平台上下文（可选）
            options: 运行选项（可选）
        
        Returns:
            工作流执行结果
        """
        if self._closed:
            raise RuntimeError("Workflow has been closed")
        
        if not self._initialized:
            await self.initialize()
        
        # 重置上下文状态
        self.context.reset()
        self.context.user_input = user_input
        self.context.uploaded_files = files or []
        self.context.start_time = datetime.now()
        
        # 应用 Meso 上下文
        if meso_context:
            self._meso_handler.apply_context(meso_context)
        
        # 合并选项
        default_opts = getattr(self.config, 'default_options', {}) or {}
        run_options = {**default_opts, **(options or {})}
        
        try:
            # 执行流水线
            result = await self._pipeline.execute(run_options)
            
            # 构建最终结果
            return self._result_builder.build_success_result(result)
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            return self._result_builder.build_error_result(e)
        
        finally:
            self.context.end_time = datetime.now()
    
    def run_sync(
        self,
        user_input: str = "",
        files: Optional[List[str]] = None,
        meso_context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """同步运行工作流"""
        return asyncio.run(self.run(user_input, files, meso_context, options))
    
    async def run_batch(
        self,
        inputs: List[str],
        meso_context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 3,
    ) -> List[Dict[str, Any]]:
        """批量运行工作流"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_single(user_input: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.run(user_input, None, meso_context, options)
        
        tasks = [run_single(inp) for inp in inputs]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def reset(self) -> None:
        """重置工作流状态"""
        self.context.reset()
        self.error_collector.clear()
        self.logger.info("Workflow state reset")
    
    async def close(self) -> None:
        """关闭工作流，释放资源"""
        if self._closed:
            return
        
        try:
            await self.client_manager.close()
            self._closed = True
            self.logger.info("Workflow closed")
        except Exception as e:
            self.logger.error(f"Error closing workflow: {e}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()
    
    # ==================== 属性访问器 ====================
    
    @property
    def status(self) -> WorkflowStatus:
        """获取当前工作流状态"""
        return self.context.status
    
    @property
    def is_running(self) -> bool:
        """工作流是否正在运行"""
        return self.context.status == WorkflowStatus.RUNNING
    
    @property
    def execution_time(self) -> Optional[float]:
        """获取执行时间（秒）"""
        if self.context.start_time and self.context.end_time:
            return (self.context.end_time - self.context.start_time).total_seconds()
        return None
    
    @property
    def errors(self) -> List[Dict[str, Any]]:
        """获取错误列表"""
        return self.error_collector.get_errors()
    
    # ==================== 调试方法 ====================
    
    def get_debug_info(self) -> Dict[str, Any]:
        """获取调试信息"""
        model_name = "unknown"
        if self.config.model_config:
            model_name = getattr(self.config.model_config, 'name', 'unknown')
        
        return {
            "status": self.context.status.value,
            "current_step": self.context.current_step,
            "execution_time": self.execution_time,
            "errors": self.errors,
            "config": {
                "model": model_name,
                "max_retries": getattr(self.config, 'max_retries', 3),
            },
        }
    
    def get_step_results(self) -> Dict[str, Any]:
        """获取各步骤的执行结果"""
        return self.context.step_results.copy()


# ==================== 批量处理器 ====================

# 从 core 导入 BatchProcessor
from .core.batch_processor import BatchProcessor


# ==================== 便捷函数 ====================

def create_workflow(
    api_base: str = "",
    api_key: str = "",
    model_name: str = "gpt-4o",
    vision_model_name: Optional[str] = None,
    temperature: float = 0.7,
    **kwargs,
) -> VolatilityWorkflow:
    """便捷函数：创建工作流实例"""
    from .factory import create_workflow as factory_create
    return factory_create(
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        vision_model_name=vision_model_name,
        temperature=temperature,
        **kwargs,
    )


async def run_workflow(
    user_input: str,
    config: Optional[WorkflowConfig] = None,
    meso_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """便捷函数：一次性运行工作流"""
    cfg = config or WorkflowConfig()
    
    async with VolatilityWorkflow(cfg) as workflow:
        return await workflow.run(user_input, meso_context=meso_context)