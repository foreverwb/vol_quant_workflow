"""
模型配置管理 - 支持多模型厂商
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ModelConfig:
    """通用模型配置"""
    
    # 基础配置
    model_name: str                    # 模型名称（如 Qwen3-8B）
    provider: Optional[str] = None     # 提供商（可选）
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    
    # 参数配置
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    
    # 功能开关
    vision_enabled: bool = False       # 是否支持图像
    structured_output: bool = False    # 是否支持结构化输出
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'model_name': self.model_name,
            'provider': self.provider,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'top_p': self.top_p,
            'vision_enabled': self.vision_enabled,
            'structured_output': self.structured_output
        }

# 预设配置
MODEL_PRESETS = {
    "router": ModelConfig(
        model_name="Qwen3-8B",
        temperature=0.3
    ),
    "data_validation": ModelConfig(
        model_name="Qwen3-VL-235B-A22B-Thinking",
        temperature=0.7,
        vision_enabled=True,
        structured_output=True
    ),
    "probability_calibration": ModelConfig(
        model_name="Qwen3-8B",
        temperature=0.7,
        structured_output=True
    ),
    "strategy_mapping": ModelConfig(
        model_name="Qwen3-8B",
        temperature=0.7,
        structured_output=True
    ),
    "final_decision": ModelConfig(
        model_name="Qwen3-8B",
        temperature=0.7
    ),
    "command_generator": ModelConfig(
        model_name="Qwen3-8B",
        temperature=0.3
    )
}

def get_model_config(agent_name: str) -> ModelConfig:
    """获取指定Agent的模型配置"""
    return MODEL_PRESETS.get(agent_name, MODEL_PRESETS["router"])
