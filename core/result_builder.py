"""
Result Builder - 工作流结果构建器
负责构建各种类型的返回结果
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime
import traceback

if TYPE_CHECKING:
    from ..workflow import VolatilityWorkflow


class ResultBuilder:
    """结果构建器 - 统一构建工作流返回结果"""
    
    def __init__(self, workflow: "VolatilityWorkflow"):
        self.workflow = workflow
        self.ctx = workflow.context
        self.logger = workflow.logger
    
    def build_success_result(self, pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
        """构建成功结果"""
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "execution_time_ms": self._get_execution_time_ms(),
            "user_input": self.ctx.user_input,
            
            # 核心结果
            "result": {
                "route": pipeline_result.get("route", {}),
                "strategy": pipeline_result.get("strategy", {}),
                "probabilities": pipeline_result.get("probabilities", {}),
                "report": pipeline_result.get("report", {}),
            },
            
            # 中间数据（可选，用于调试）
            "intermediate": {
                "command": pipeline_result.get("command", {}),
                "data": pipeline_result.get("data", {}),
            },
            
            # 元数据
            "metadata": self._build_metadata(),
        }
    
    def build_error_result(self, error: Exception) -> Dict[str, Any]:
        """构建错误结果"""
        error_info = self._extract_error_info(error)
        
        return {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "execution_time_ms": self._get_execution_time_ms(),
            "user_input": self.ctx.user_input,
            
            # 错误信息
            "error": error_info,
            
            # 部分结果（如果有）
            "partial_results": self._get_partial_results(),
            
            # 元数据
            "metadata": self._build_metadata(),
        }
    
    def build_validation_error(
        self, 
        error_type: str, 
        message: str,
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """构建验证错误结果"""
        return {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "execution_time_ms": self._get_execution_time_ms(),
            "user_input": self.ctx.user_input,
            
            "error": {
                "type": error_type,
                "message": message,
                "details": details or {},
                "step": self.ctx.current_step,
            },
            
            "metadata": self._build_metadata(),
        }
    
    def build_partial_result(
        self,
        completed_steps: List[str],
        failed_step: str,
        error: Optional[Exception] = None,
    ) -> Dict[str, Any]:
        """构建部分完成结果"""
        return {
            "success": False,
            "partial": True,
            "timestamp": datetime.now().isoformat(),
            "execution_time_ms": self._get_execution_time_ms(),
            "user_input": self.ctx.user_input,
            
            "completed_steps": completed_steps,
            "failed_step": failed_step,
            "error": self._extract_error_info(error) if error else None,
            
            "partial_results": self._get_partial_results(),
            "metadata": self._build_metadata(),
        }
    
    # ==================== 私有方法 ====================
    
    def _get_execution_time_ms(self) -> Optional[float]:
        """获取执行时间（毫秒）"""
        if self.ctx.start_time:
            end = self.ctx.end_time or datetime.now()
            return (end - self.ctx.start_time).total_seconds() * 1000
        return None
    
    def _build_metadata(self) -> Dict[str, Any]:
        """构建元数据"""
        return {
            "workflow_id": getattr(self.ctx, "workflow_id", None),
            "model": self.workflow.config.model_config.model_name,
            "status": self.ctx.status.value,
            "current_step": self.ctx.current_step,
            "meso_context_applied": bool(self.ctx.meso_context),
            "errors_count": len(self.workflow.error_collector.get_errors()),
        }
    
    def _extract_error_info(self, error: Exception) -> Dict[str, Any]:
        """提取错误信息"""
        return {
            "type": type(error).__name__,
            "message": str(error),
            "step": self.ctx.current_step,
            "traceback": traceback.format_exc() if self.workflow.config.debug else None,
        }
    
    def _get_partial_results(self) -> Dict[str, Any]:
        """获取已完成步骤的结果"""
        return {
            step: result
            for step, result in self.ctx.step_results.items()
            if result is not None
        }