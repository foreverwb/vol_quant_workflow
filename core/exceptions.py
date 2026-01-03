"""
自定义异常模块
"""

class VolAnalyzerError(Exception):
    """基础异常类"""
    pass


class DataValidationError(VolAnalyzerError):
    """数据校验错误"""
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Field '{field}': {message}")


class MissingCriticalFieldError(DataValidationError):
    """缺少关键字段"""
    def __init__(self, field: str):
        super().__init__(field, "Critical field is missing")


class InvalidFieldValueError(DataValidationError):
    """字段值无效"""
    def __init__(self, field: str, value, expected_range=None):
        msg = f"Invalid value {value}"
        if expected_range:
            msg += f", expected range: {expected_range}"
        super().__init__(field, msg)


class ConfigurationError(VolAnalyzerError):
    """配置错误"""
    pass


class LLMError(VolAnalyzerError):
    """LLM 调用错误"""
    pass


class LLMConnectionError(LLMError):
    """LLM 连接错误"""
    pass


class LLMResponseError(LLMError):
    """LLM 响应解析错误"""
    pass


class StrategyError(VolAnalyzerError):
    """策略生成错误"""
    pass


class InsufficientDataError(VolAnalyzerError):
    """数据不足"""
    def __init__(self, missing_fields: list):
        self.missing_fields = missing_fields
        super().__init__(f"Insufficient data, missing: {missing_fields}")


class SimulationError(VolAnalyzerError):
    """模拟计算错误"""
    pass


class PipelineError(VolAnalyzerError):
    """流程执行错误"""
    def __init__(self, stage: str, message: str):
        self.stage = stage
        super().__init__(f"Pipeline error at '{stage}': {message}")
