"""
波动率套利策略工作流 - 配置文件
支持通用模型配置，不指定具体厂商
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os


@dataclass
class ModelConfig:
    """
    通用模型配置 - 支持任意模型厂商
    """
    # 基本配置
    name: str = "default-model"
    api_base: str = ""  # API端点地址
    api_key: str = ""   # API密钥（可从环境变量读取）
    
    # 模型参数
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # 高级配置
    timeout: int = 120
    retry_count: int = 3
    stream: bool = False
    
    # 视觉能力（用于图表解析）
    vision_enabled: bool = False
    vision_detail: str = "high"  # low, high, auto
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "api_base": self.api_base,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "timeout": self.timeout,
            "stream": self.stream,
            "vision_enabled": self.vision_enabled,
            "vision_detail": self.vision_detail,
        }


@dataclass 
class WorkflowConfig:
    """
    工作流配置 - 包含所有环境变量
    """
    # Meso 系统 API (volatility_analysis)
    MESO_API_URL: str = "http://localhost:8668"
    MESO_ENABLED: bool = True  # 是否启用 Meso 上下文感知
    
    # 蒙特卡洛模拟
    MONTE_CARLO_SIMULATIONS: int = 10000
    
    # 无风险利率（用于BS模型）
    RISK_FREE_RATE: float = 0.05
    
    # 做多波动率概率门槛
    PROB_LONG_L1_0: float = 0.55  # L>=1.0时
    PROB_LONG_L1_5: float = 0.60  # L>=1.5时
    PROB_LONG_L2_0: float = 0.65  # L>=2.0时
    
    # 做多波动率权重 (可被 DynamicConfig 覆盖)
    WEIGHT_VRP_LONG: float = 0.25
    WEIGHT_GEX_LONG: float = 0.18
    WEIGHT_VEX_LONG: float = 0.18
    WEIGHT_CARRY_LONG: float = 0.08
    WEIGHT_SKEW_LONG: float = 0.08
    
    # 做空波动率权重 (可被 DynamicConfig 覆盖)
    WEIGHT_VRP_SHORT: float = 0.30
    WEIGHT_GEX_SHORT: float = 0.12
    WEIGHT_CARRY_SHORT: float = 0.18
    
    # 决策门槛 (可被 DynamicConfig 覆盖)
    DECISION_THRESHOLD_LONG: float = 1.00
    DECISION_THRESHOLD_SHORT: float = 1.00
    PROB_THRESHOLD: float = 0.55
    
    # Edge门槛
    EDGE_EV_THRESHOLD: float = 0.0
    EDGE_RR_THRESHOLD: float = 1.5
    
    # VOL TRIGGER相关
    TRIGGER_NEUTRAL_PCT: float = 0.2
    GAMMA_WALL_PROX_THRESHOLD: float = 0.5
    
    # RIM阈值
    RIM_ACTIVE_THRESHOLD: float = 0.6
    RIM_WEAK_THRESHOLD: float = 0.4
    
    # Z-Score 基准波动率 (用于自适应缩放)
    ZSCORE_BASE_VOL: float = 20.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def apply_dynamic_config(self, dynamic_config) -> 'WorkflowConfig':
        """
        应用动态配置，返回新的 WorkflowConfig 实例
        
        Args:
            dynamic_config: DynamicConfig 实例
            
        Returns:
            新的 WorkflowConfig (不修改原实例)
        """
        from dataclasses import replace
        
        updates = {}
        
        # 应用阈值
        if hasattr(dynamic_config, 'DECISION_THRESHOLD_LONG'):
            updates['DECISION_THRESHOLD_LONG'] = dynamic_config.DECISION_THRESHOLD_LONG
        if hasattr(dynamic_config, 'DECISION_THRESHOLD_SHORT'):
            updates['DECISION_THRESHOLD_SHORT'] = dynamic_config.DECISION_THRESHOLD_SHORT
            
        # 应用权重
        for attr in ['WEIGHT_VRP_LONG', 'WEIGHT_GEX_LONG', 'WEIGHT_VEX_LONG', 
                     'WEIGHT_CARRY_LONG', 'WEIGHT_SKEW_LONG',
                     'WEIGHT_VRP_SHORT', 'WEIGHT_GEX_SHORT', 'WEIGHT_CARRY_SHORT']:
            if hasattr(dynamic_config, attr):
                updates[attr] = getattr(dynamic_config, attr)
        
        return replace(self, **updates)
    
    @classmethod
    def from_env(cls) -> 'WorkflowConfig':
        """从环境变量加载配置"""
        config = cls()
        for key in config.__dataclass_fields__:
            env_val = os.getenv(key)
            if env_val is not None:
                field_type = type(getattr(config, key))
                if field_type == bool:
                    setattr(config, key, env_val.lower() in ('true', '1', 'yes'))
                else:
                    setattr(config, key, field_type(env_val))
        return config


@dataclass
class FileUploadConfig:
    """文件上传配置"""
    allowed_extensions: list = field(default_factory=lambda: [
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'
    ])
    max_file_size_mb: int = 15
    max_batch_count: int = 20  # 支持>=10文件批量上传
    image_file_size_limit_mb: int = 10
    
    def is_valid_extension(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.allowed_extensions


# 默认配置实例
DEFAULT_MODEL_CONFIG = ModelConfig()
DEFAULT_WORKFLOW_CONFIG = WorkflowConfig()
DEFAULT_FILE_CONFIG = FileUploadConfig()
