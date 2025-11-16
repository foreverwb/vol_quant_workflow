"""
Edge估算引擎 - 蒙特卡洛模拟
"""
import numpy as np
from scipy.stats import norm
from models.data_models import Strategy, CoreFields, EdgeEstimate
from config.env_config import EnvConfig

class EdgeEstimator:
    """Edge估算器"""
    
    def __init__(self, env_config: EnvConfig = None):
        self.env_config = env_config or EnvConfig()
    
    def estimate_strategy_edge(
        self,
        strategy: Strategy,
        core_fields: CoreFields,
        p_long: float,
        p_short: float
    ) -> EdgeEstimate:
        """
        估算策略的Edge
        
        Returns:
            EdgeEstimate包含 win_rate, rr_ratio, ev, meets_threshold
        """
        
        # 基本参数
        spot = core_fields.spot
        iv_atm = core_fields.iv_event_w_atm or 0.25
        
        # 解析DTE
        dte_str = strategy.dte or "30天"
        dte = int(''.join(filter(str.isdigit, dte_str)))
        T = dte / 365.0
        
        # 根据策略类型估算
        structure = strategy.structure.lower()
        
        if "straddle" in structure or "strangle" in structure:
            # Long Vol策略
            win_rate = p_long * 0.9
            rr_ratio = 2.0  # 2:1盈亏比
            
            # EV简化估算: (RV - IV) × vega - theta - 成本
            rv_premium = 0.02  # 假设RV比IV高2%
            ev_numeric = rv_premium * 100 * dte / 365 - 0.5  # 简化
            
        elif "iron" in structure or "condor" in structure or "short" in structure.lower():
            # Short Vol策略
            win_rate = min(p_short * 1.1, 0.75)
            rr_ratio = 0.5  # 1:2盈亏比
            
            # EV: 信用额 - P(触碰) × 亏损额 - 成本
            credit = 0.5  # 假设收取50%
            touch_prob = 0.15
            max_loss = 1.0
            ev_numeric = credit - touch_prob * max_loss - 0.1
            
        else:  # Calendar, Diagonal等
            win_rate = 0.65
            rr_ratio = 1.5
            ev_numeric = 0.2
        
        # 检查Edge门槛
        ev_threshold = self.env_config.EDGE_EV_THRESHOLD
        rr_threshold = self.env_config.EDGE_RR_THRESHOLD
        
        meets_threshold = (ev_numeric > ev_threshold and rr_ratio >= rr_threshold)
        
        return EdgeEstimate(
            win_rate=f"{win_rate:.1%}",
            rr_ratio=f"1:{1/rr_ratio:.1f}" if rr_ratio > 1 else f"{rr_ratio:.1f}:1",
            ev=f"${ev_numeric:+.2f}",
            ev_numeric=round(ev_numeric, 2),
            meets_threshold=meets_threshold,
            note="蒙特卡洛简化估算" if meets_threshold else "不满足Edge门槛"
        )
