"""
字段校验模块
对输入数据进行校验、估计缺失值
"""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import asdict

from core.types import (
    FieldValidation,
    ValidationStatus,
    FieldPriority,
    DataStatus,
    MarketData,
)
from core.constants import FIELD_RANGES, REQUIRED_FIELDS
from core.exceptions import (
    DataValidationError,
    MissingCriticalFieldError,
    InvalidFieldValueError,
)


class FieldValidator:
    """字段校验器"""
    
    def __init__(self, symbol: str, spot_price: float):
        self.symbol = symbol
        self.spot_price = spot_price
        self.validations: Dict[str, FieldValidation] = {}
        
    def validate_field(
        self,
        field_name: str,
        value: Any,
        source: str = "collected"
    ) -> FieldValidation:
        """校验单个字段"""
        # 字符串类型字段
        string_fields = {"NET_GEX_SIGN", "NET_DEX_SIGN", "TIMESTAMP_ET", "SYMBOL"}
        
        if value is None:
            status = ValidationStatus.MISSING
            confidence = 0.0
            notes = "数据缺失"
        elif field_name in string_fields:
            status = ValidationStatus.VALID
            confidence = 1.0
            notes = None
        elif isinstance(value, (list, dict)):
            status = ValidationStatus.VALID
            confidence = 1.0
            notes = None
        elif isinstance(value, (int, float)):
            min_val, max_val = FIELD_RANGES.get(
                field_name, (-float('inf'), float('inf'))
            )
            if min_val <= value <= max_val:
                status = ValidationStatus.VALID
                confidence = 1.0
                notes = None
            else:
                status = ValidationStatus.INVALID
                confidence = 0.0
                notes = f"值 {value} 超出范围 [{min_val}, {max_val}]"
        else:
            try:
                numeric_value = float(value)
                min_val, max_val = FIELD_RANGES.get(
                    field_name, (-float('inf'), float('inf'))
                )
                if min_val <= numeric_value <= max_val:
                    value = numeric_value
                    status = ValidationStatus.VALID
                    confidence = 1.0
                    notes = None
                else:
                    status = ValidationStatus.INVALID
                    confidence = 0.0
                    notes = "值超出范围"
            except (ValueError, TypeError):
                status = ValidationStatus.VALID
                confidence = 0.8
                notes = "非数值类型"
        
        validation = FieldValidation(
            field_name=field_name,
            value=value,
            status=status,
            source=source,
            notes=notes,
            confidence=confidence
        )
        
        self.validations[field_name] = validation
        return validation
    
    def estimate_missing(self, field_name: str) -> Optional[FieldValidation]:
        """估计缺失字段值"""
        estimated_value = None
        notes = None
        
        # HV 估计
        if field_name == "HV10" and self._get_value("HV20"):
            hv20 = self._get_value("HV20")
            estimated_value = hv20 * 1.08
            notes = "由 HV20 * 1.08 估计"
            
        elif field_name == "HV60" and self._get_value("HV20"):
            hv20 = self._get_value("HV20")
            estimated_value = hv20 * 0.92
            notes = "由 HV20 * 0.92 估计"
            
        # IV 估计
        elif field_name == "IV_FRONT" and self._get_value("IV_ATM"):
            estimated_value = self._get_value("IV_ATM")
            notes = "使用 IV_ATM"
            
        elif field_name == "IV_BACK" and self._get_value("IV_FRONT"):
            estimated_value = self._get_value("IV_FRONT") * 0.95
            notes = "由 IV_FRONT * 0.95 估计"
        
        # 关键价位估计
        elif field_name == "VOL_TRIGGER":
            estimated_value = self.spot_price * 0.995
            notes = "使用 spot * 0.995 估计"
            
        elif field_name == "GAMMA_WALL":
            estimated_value = self.spot_price
            notes = "使用 spot 估计"
            
        elif field_name == "CALL_WALL":
            estimated_value = self.spot_price * 1.05
            notes = "使用 spot * 1.05 估计"
            
        elif field_name == "PUT_WALL":
            estimated_value = self.spot_price * 0.95
            notes = "使用 spot * 0.95 估计"
        
        # Term slope 估计
        elif field_name == "TERM_SLOPE":
            iv_front = self._get_value("IV_FRONT")
            iv_back = self._get_value("IV_BACK")
            if iv_front and iv_back:
                estimated_value = iv_front - iv_back
                notes = "由 IV_FRONT - IV_BACK 计算"
        
        if estimated_value is not None:
            validation = FieldValidation(
                field_name=field_name,
                value=estimated_value,
                status=ValidationStatus.ESTIMATED,
                source="estimated",
                notes=notes,
                confidence=0.6
            )
            self.validations[field_name] = validation
            return validation
        
        return None
    
    def _get_value(self, field_name: str) -> Optional[float]:
        """获取已校验字段的值"""
        if field_name in self.validations:
            v = self.validations[field_name]
            if v.status in [ValidationStatus.VALID, ValidationStatus.ESTIMATED]:
                return v.value
        return None
    
    def determine_gex_regime(self) -> str:
        """判断 GEX 环境"""
        spot = self.spot_price
        vol_trigger = self._get_value("VOL_TRIGGER")
        
        if vol_trigger is None:
            return "neutral"
        
        pct_diff = (spot - vol_trigger) / vol_trigger
        
        if pct_diff > 0.002:
            return "positive"
        elif pct_diff < -0.002:
            return "negative"
        else:
            return "neutral"
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """获取校验汇总"""
        total = len(self.validations)
        valid = sum(1 for v in self.validations.values() 
                   if v.status == ValidationStatus.VALID)
        missing = sum(1 for v in self.validations.values() 
                     if v.status == ValidationStatus.MISSING)
        estimated = sum(1 for v in self.validations.values() 
                       if v.status == ValidationStatus.ESTIMATED)
        invalid = sum(1 for v in self.validations.values() 
                     if v.status == ValidationStatus.INVALID)
        
        # 检查必填字段
        missing_critical = [
            f for f in REQUIRED_FIELDS["critical"]
            if f not in self.validations or 
            self.validations[f].status == ValidationStatus.MISSING
        ]
        
        missing_high = [
            f for f in REQUIRED_FIELDS["high"]
            if f not in self.validations or 
            self.validations[f].status == ValidationStatus.MISSING
        ]
        
        # 计算质量分数
        quality_score = (valid + estimated * 0.6) / max(total, 1) * 100
        
        # 平均置信度
        confidences = [v.confidence for v in self.validations.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # 确定状态
        if missing_critical:
            status = DataStatus.MISSING_CRITICAL
        elif missing_high:
            status = DataStatus.MISSING_HIGH
        elif missing > 0:
            status = DataStatus.MISSING_OPTIONAL
        else:
            status = DataStatus.DATA_READY
        
        return {
            "total_fields": total,
            "valid": valid,
            "missing": missing,
            "estimated": estimated,
            "invalid": invalid,
            "missing_critical": missing_critical,
            "missing_high": missing_high,
            "data_quality_score": round(quality_score, 2),
            "avg_confidence": round(avg_confidence, 3),
            "status": status,
            "is_usable": len(missing_critical) == 0,
        }


def validate_market_data(
    data: Dict[str, Any],
    symbol: str
) -> Tuple[Dict[str, FieldValidation], Dict[str, Any]]:
    """
    校验市场数据
    
    Args:
        data: 扁平化后的数据字典
        symbol: 标的代码
        
    Returns:
        (校验结果字典, 汇总信息)
    """
    spot_price = data.get("SPOT_PRICE", 0)
    
    if spot_price <= 0:
        raise MissingCriticalFieldError("SPOT_PRICE")
    
    validator = FieldValidator(symbol, spot_price)
    
    # 所有可能的字段
    all_fields = list(FIELD_RANGES.keys()) + [
        "NET_GEX_SIGN", "NET_DEX_SIGN", "TIMESTAMP_ET", "SYMBOL",
        "MAJOR_OI_STRIKES", "SMILE_CURVATURE"
    ]
    
    # 校验所有字段
    for field_name in all_fields:
        value = data.get(field_name)
        if value is not None:
            validator.validate_field(field_name, value, source="collected")
    
    # 估计缺失字段
    for field_name in all_fields:
        if (field_name not in validator.validations or 
            validator.validations[field_name].status == ValidationStatus.MISSING):
            validator.estimate_missing(field_name)
    
    # 添加 GEX regime
    gex_regime = validator.determine_gex_regime()
    validator.validations["NET_GEX_REGIME"] = FieldValidation(
        field_name="NET_GEX_REGIME",
        value=gex_regime,
        status=ValidationStatus.VALID,
        source="derived",
        confidence=1.0
    )
    
    summary = validator.get_validation_summary()
    
    return validator.validations, summary
