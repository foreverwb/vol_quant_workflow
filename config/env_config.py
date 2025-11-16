"""
环境变量配置管理

架构说明：
- .env 文件：存储实际的配置值（用户需要维护）
- env_config.py：定义配置的数据结构和类型
- default_config：全局配置实例，自动从 .env 读取

使用方式：
1. 复制 .env.example 为 .env，填入实际的值
2. 在代码中导入 default_config
3. 如需自定义配置，创建 EnvConfig 实例

示例：
    from config.env_config import default_config
    print(default_config.RISK_FREE_RATE)  # 0.05
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv()


@dataclass
class EnvConfig:
    """
    环境变量配置类
    
    所有字段都会自动从 .env 文件中读取对应的环境变量
    如果环境变量不存在，使用括号中的默认值
    """
    
    # ======================== LLM配置 ========================
    LLM_API_BASE: str = os.getenv('LLM_API_BASE', 'http://localhost:8000')
    LLM_API_KEY: str = os.getenv('LLM_API_KEY', 'sk-default')
    
    # ======================== 蒙特卡洛模拟 ========================
    MONTE_CARLO_SIMULATIONS: int = int(
        os.getenv('MONTE_CARLO_SIMULATIONS', '10000')
    )
    
    # ======================== 无风险利率（BS模型） ========================
    RISK_FREE_RATE: float = float(
        os.getenv('RISK_FREE_RATE', '0.05')
    )
    
    # ======================== 概率门槛 ========================
    PROB_LONG_L1_0: float = float(
        os.getenv('PROB_LONG_L1_0', '0.55')
    )
    PROB_LONG_L1_5: float = float(
        os.getenv('PROB_LONG_L1_5', '0.60')
    )
    PROB_LONG_L2_0: float = float(
        os.getenv('PROB_LONG_L2_0', '0.65')
    )
    
    # ======================== 做多波动率权重（总和应为1.0） ========================
    WEIGHT_VRP_LONG: float = float(
        os.getenv('WEIGHT_VRP_LONG', '0.25')
    )
    WEIGHT_GEX_LONG: float = float(
        os.getenv('WEIGHT_GEX_LONG', '0.18')
    )
    WEIGHT_VEX_LONG: float = float(
        os.getenv('WEIGHT_VEX_LONG', '0.18')
    )
    WEIGHT_CARRY_LONG: float = float(
        os.getenv('WEIGHT_CARRY_LONG', '0.08')
    )
    WEIGHT_SKEW_LONG: float = float(
        os.getenv('WEIGHT_SKEW_LONG', '0.08')
    )
    
    # ======================== 做空波动率权重 ========================
    WEIGHT_VRP_SHORT: float = float(
        os.getenv('WEIGHT_VRP_SHORT', '0.30')
    )
    WEIGHT_GEX_SHORT: float = float(
        os.getenv('WEIGHT_GEX_SHORT', '0.12')
    )
    WEIGHT_CARRY_SHORT: float = float(
        os.getenv('WEIGHT_CARRY_SHORT', '0.18')
    )
    
    # ======================== 决策门槛 ========================
    DECISION_THRESHOLD_LONG: float = float(
        os.getenv('DECISION_THRESHOLD_LONG', '1.00')
    )
    DECISION_THRESHOLD_SHORT: float = float(
        os.getenv('DECISION_THRESHOLD_SHORT', '1.00')
    )
    PROB_THRESHOLD: float = float(
        os.getenv('PROB_THRESHOLD', '0.55')
    )
    
    # ======================== Edge门槛 ========================
    EDGE_EV_THRESHOLD: float = float(
        os.getenv('EDGE_EV_THRESHOLD', '0')
    )
    EDGE_RR_THRESHOLD: float = float(
        os.getenv('EDGE_RR_THRESHOLD', '1.5')
    )
    
    # ======================== 触发线相关 ========================
    TRIGGER_NEUTRAL_PCT: float = float(
        os.getenv('TRIGGER_NEUTRAL_PCT', '0.002')  # 0.2%
    )
    
    # ======================== Gamma Wall相关 ========================
    GAMMA_WALL_PROX_THRESHOLD: float = float(
        os.getenv('GAMMA_WALL_PROX_THRESHOLD', '0.005')  # 0.5%
    )
    
    # ======================== RIM指标 ========================
    RIM_ACTIVE_THRESHOLD: float = float(
        os.getenv('RIM_ACTIVE_THRESHOLD', '0.6')
    )
    RIM_WEAK_THRESHOLD: float = float(
        os.getenv('RIM_WEAK_THRESHOLD', '0.4')
    )
    
    # ======================== 日志配置 ========================
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'vol_quant.log')
    
    def to_dict(self) -> dict:
        """
        转换为字典格式
        
        Returns:
            包含所有配置的字典
        """
        return {
            key: getattr(self, key)
            for key in self.__dataclass_fields__
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EnvConfig':
        """
        从字典创建配置实例
        
        Args:
            data: 配置字典
        
        Returns:
            EnvConfig 实例
        """
        # 过滤出有效的字段
        valid_fields = {
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__
        }
        return cls(**valid_fields)
    
    def __repr__(self) -> str:
        """
        配置摘要
        """
        return f"""EnvConfig(
  LLM: {self.LLM_API_BASE}
  RISK_FREE_RATE: {self.RISK_FREE_RATE}
  WEIGHTS_LONG: VRP={self.WEIGHT_VRP_LONG}, GEX={self.WEIGHT_GEX_LONG}, VEX={self.WEIGHT_VEX_LONG}
  DECISION_THRESHOLD: LONG={self.DECISION_THRESHOLD_LONG}, SHORT={self.DECISION_THRESHOLD_SHORT}
  EDGE_RR_THRESHOLD: {self.EDGE_RR_THRESHOLD}
)"""


# ======================== 全局配置实例 ========================
# 在应用启动时创建，其他模块通过导入此实例来访问配置
default_config = EnvConfig()

# 打印配置摘要（仅在导入时）
# print(default_config)
