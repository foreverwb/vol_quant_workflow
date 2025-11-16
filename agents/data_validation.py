"""
数据校验Agent
"""
import json
from agents.base_agent import BaseAgent
from models.data_models import ValidationResult, CoreFields, MissingField
from typing import Dict, Any, List, Optional

class DataValidationAgent(BaseAgent):
    """数据校验Agent"""
    
    def __init__(self):
        super().__init__("data_validation")
    
    async def run(
        self,
        files: List[str],
        symbol: Optional[str] = None
    ) -> ValidationResult:
        """
        校验上传的图表数据
        
        Args:
            files: 图片文件列表
            symbol: 标的代码（可选）
        """
        # 调用视觉LLM进行数据提取
        result = await self.call_llm(
            images=files,
            schema_name="data_validation"
        )
        
        # 解析结果
        if result.get("error"):
            raise Exception(f"数据校验失败: {result.get('message')}")
        
        # 构建ValidationResult
        data = result
        
        core_fields_data = data.get("core_fields", {})
        core_fields = CoreFields(
            symbol=data.get("symbol", symbol or "UNKNOWN"),
            timestamp=data.get("timestamp", ""),
            vol_trigger=core_fields_data.get("vol_trigger", 0),
            spot=core_fields_data.get("spot", 0),
            net_gex_sign=core_fields_data.get("net_gex_sign", "neutral"),
            spot_vs_trigger=core_fields_data.get("spot_vs_trigger", "unknown"),
            gamma_wall=core_fields_data.get("gamma_wall"),
            call_wall=core_fields_data.get("call_wall"),
            put_wall=core_fields_data.get("put_wall"),
            gamma_wall_prox=core_fields_data.get("gamma_wall_prox", 0),
            iv_event_w_atm=core_fields_data.get("iv_event_w_atm"),
            iv_m1_atm=core_fields_data.get("iv_m1_atm"),
            iv_m2_atm=core_fields_data.get("iv_m2_atm"),
            hv10=core_fields_data.get("hv10"),
            hv20=core_fields_data.get("hv20"),
            hv60=core_fields_data.get("hv60"),
            vex_net=core_fields_data.get("vex_net"),
            vanna_atm=core_fields_data.get("vanna_atm"),
            term_slope=core_fields_data.get("term_slope"),
            put_skew_25=core_fields_data.get("put_skew_25"),
            call_skew_25=core_fields_data.get("call_skew_25"),
            spread_atm=core_fields_data.get("spread_atm"),
            ask_premium_atm=core_fields_data.get("ask_premium_atm")
        )
        
        missing_fields = [
            MissingField(
                field=mf.get("field"),
                priority=mf.get("priority"),
                command=mf.get("command"),
                alternative=mf.get("alternative")
            )
            for mf in data.get("missing_fields", [])
        ]
        
        return ValidationResult(
            symbol=core_fields.symbol,
            timestamp=data.get("timestamp", ""),
            status=data.get("status", "missing_data"),
            core_fields=core_fields,
            missing_fields=missing_fields,
            next_step=data.get("next_step", "request_missing_data")
        )
