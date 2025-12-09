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
class NodeModelMapping:
    """
    节点模型映射配置
    
    定义每个节点使用哪个模型，支持多模型流程编排
    
    使用方式:
        mapping = NodeModelMapping(
            router="gpt-4o-mini",           # 轻量级任务用小模型
            data_validator="gpt-4o",        # 视觉任务用强模型
            strategy_mapper="claude-3-opus", # 复杂推理用最强模型
        )
    """
    # LLM 节点模型配置 (值为模型名称或 ModelConfig 实例)
    router: Optional[str] = None
    command_generator: Optional[str] = None
    data_validator: Optional[str] = None  # 通常需要视觉能力
    probability_calibrator: Optional[str] = None
    strategy_mapper: Optional[str] = None
    final_report: Optional[str] = None
    
    # 默认模型 (未指定的节点使用此模型)
    default_model: str = "gpt-4o"
    default_vision_model: str = "gpt-4o"  # 视觉节点默认模型
    
    # 节点是否需要视觉能力的映射
    _vision_nodes: tuple = ("data_validator",)
    
    def get_model_for_node(self, node_name: str) -> str:
        """
        获取指定节点应使用的模型名称
        
        Args:
            node_name: 节点名称 (如 "router", "data_validator")
            
        Returns:
            模型名称
        """
        # 获取节点特定配置
        model = getattr(self, node_name, None)
        
        if model:
            return model
        
        # 使用默认模型
        if node_name in self._vision_nodes:
            return self.default_vision_model
        return self.default_model
    
    def is_vision_node(self, node_name: str) -> bool:
        """判断节点是否需要视觉能力"""
        return node_name in self._vision_nodes
    
    def to_dict(self) -> Dict[str, str]:
        """导出所有节点的模型配置"""
        nodes = ["router", "command_generator", "data_validator", 
                 "probability_calibrator", "strategy_mapper", "final_report"]
        return {node: self.get_model_for_node(node) for node in nodes}


@dataclass 
class WorkflowConfig:
    """
    工作流配置参数
    包含决策阈值、因子权重、系统配置等
    """
    # === Meso 系统集成配置 ===
    MESO_ENABLED: bool = True  # 是否启用 Meso 上下文
    MESO_API_URL: str = "http://localhost:5000"  # Meso API 地址
    MESO_TIMEOUT: int = 10  # API 超时时间（秒）
    
    # === 决策阈值 ===
    LONG_THRESHOLD: float = 65.0
    SHORT_THRESHOLD: float = 35.0
    PROB_FLOOR: float = 25.0
    PROB_CEILING: float = 75.0
    
    # === 因子权重 ===
    FACTOR_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "gamma_exposure": 0.25,
        "vol_trigger_proximity": 0.20,
        "iv_skew": 0.15,
        "term_structure": 0.15,
        "hv_iv_spread": 0.10,
        "vanna_exposure": 0.10,
        "event_risk": 0.05
    })
    
    # === Z-Score 阈值 ===
    ZSCORE_EXTREME: float = 2.0
    ZSCORE_MODERATE: float = 1.0
    ZSCORE_STD: float = 1.0  # 自适应标准差 (由市场上下文动态调整)
    
    # === DTE 配置 ===
    DTE_MIN: int = 5
    DTE_MAX: int = 45
    DTE_RECOMMENDED: int = 21  # 推荐 DTE
    
    # === 风险限制 ===
    MAX_STRATEGIES: int = 3
    MAX_LEGS_PER_STRATEGY: int = 4
    DELTA_RANGE: tuple = (-0.40, 0.40)
    
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
            新的 WorkflowConfig 实例
        """
        import copy
        new_config = copy.deepcopy(self)
        
        # 应用阈值调整
        if dynamic_config.adjusted_thresholds:
            t = dynamic_config.adjusted_thresholds
            if 'long' in t:
                new_config.LONG_THRESHOLD = t['long']
            if 'short' in t:
                new_config.SHORT_THRESHOLD = t['short']
        
        # 应用因子权重
        if dynamic_config.factor_weights:
            new_config.FACTOR_WEIGHTS = dynamic_config.factor_weights
        
        # 应用 Z-Score 标准差
        if dynamic_config.zscore_std:
            new_config.ZSCORE_STD = dynamic_config.zscore_std
        
        # 应用 DTE 建议
        if dynamic_config.dte_suggestion:
            new_config.DTE_RECOMMENDED = dynamic_config.dte_suggestion
        
        return new_config
    
    @classmethod
    def from_env(cls) -> 'WorkflowConfig':
        """从环境变量加载配置"""
        config = cls()
        
        # Meso 配置
        if os.getenv('MESO_ENABLED'):
            config.MESO_ENABLED = os.getenv('MESO_ENABLED', '').lower() == 'true'
        if os.getenv('MESO_API_URL'):
            config.MESO_API_URL = os.getenv('MESO_API_URL')
        
        # 阈值配置
        if os.getenv('LONG_THRESHOLD'):
            config.LONG_THRESHOLD = float(os.getenv('LONG_THRESHOLD'))
        if os.getenv('SHORT_THRESHOLD'):
            config.SHORT_THRESHOLD = float(os.getenv('SHORT_THRESHOLD'))
            
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
DEFAULT_NODE_MODEL_MAPPING = NodeModelMapping()