"""
行权价计算引擎 - 支持多种方法
"""
import re
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from models.data_models import CoreFields, OptionLeg, Strategy

class StrikeCalculator:
    """行权价计算器"""
    
    def __init__(self, env_config=None):
        self.env_config = env_config or {}
    
    @staticmethod
    def bs_delta(S: float, K: float, T: float, r: float, sigma: float, 
                 option_type: str) -> float:
        """Black-Scholes Delta"""
        if T <= 0:
            return 1.0 if (option_type == 'call' and S > K) else 0.0
        
        d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        
        if option_type == 'call':
            return norm.cdf(d1)
        else:  # put
            return norm.cdf(d1) - 1
    
    @staticmethod
    def find_strike_by_delta(S: float, target_delta: float, T: float, r: float,
                             sigma: float, option_type: str) -> float:
        """反推满足目标Delta的行权价"""
        
        def objective(K):
            return StrikeCalculator.bs_delta(S, K, T, r, sigma, option_type) - target_delta
        
        # 搜索范围
        try:
            strike = brentq(objective, S * 0.5, S * 1.5)
            return round(strike, 2)
        except:
            # 备用：线性近似
            if option_type == 'call':
                return round(S * (1 + (0.5 - target_delta) * 0.3), 2)
            else:
                return round(S * (1 - (0.5 - abs(target_delta)) * 0.3), 2)
    
    def calculate_strike(
        self,
        leg: OptionLeg,
        core_fields: CoreFields,
        dte: int
    ) -> float:
        """计算单个leg的行权价"""
        
        spot = core_fields.spot
        gamma_wall = core_fields.gamma_wall or spot
        call_wall = core_fields.call_wall or spot * 1.05
        put_wall = core_fields.put_wall or spot * 0.95
        iv_atm = core_fields.iv_event_w_atm or 0.25
        
        T = dte / 365.0
        r = float(self.env_config.get('RISK_FREE_RATE', 0.05))
        gamma_wall_prox = float(self.env_config.get('GAMMA_WALL_PROX_THRESHOLD', 0.005))
        
        strike_calculated = None
        method_used = None
        
        # 方法1: Delta法
        delta_str = leg.delta or ""
        if delta_str and ('Δ' in delta_str or 'delta' in delta_str.lower()):
            try:
                target_delta = float(
                    delta_str.replace('Δ', '').replace('delta', '').strip()
                )
                if leg.type == 'put' and target_delta > 0:
                    target_delta = -target_delta
                
                strike_calculated = self.find_strike_by_delta(
                    spot, target_delta, T, r, iv_atm, leg.type
                )
                method_used = 'delta_method'
            except:
                pass
        
        # 方法2: 壁垒法
        if strike_calculated is None:
            strike_desc = leg.strike or ""
            
            if 'gamma' in strike_desc.lower() or '壁垒' in strike_desc:
                if leg.action == 'sell':
                    strike_calculated = round(gamma_wall * (1 - gamma_wall_prox), 2)
                else:
                    strike_calculated = round(gamma_wall, 2)
                method_used = 'barrier_method_gamma'
            
            elif 'call' in strike_desc.lower():
                strike_calculated = round(call_wall * (1 - gamma_wall_prox), 2)
                method_used = 'barrier_method_call'
            
            elif 'put' in strike_desc.lower():
                strike_calculated = round(put_wall * (1 + gamma_wall_prox), 2)
                method_used = 'barrier_method_put'
        
        # 方法3: 百分比法
        if strike_calculated is None:
            strike_desc = leg.strike or ""
            pct_match = re.search(r'([+-]?\d+\.?\d*)%', strike_desc)
            if pct_match:
                pct = float(pct_match.group(1)) / 100
                strike_calculated = round(spot * (1 + pct), 2)
                method_used = 'percentage_method'
        
        # 方法4: ATM兜底
        if strike_calculated is None:
            strike_calculated = round(spot, 2)
            method_used = 'atm_fallback'
        
        return strike_calculated, method_used
    
    def update_strategy_strikes(
        self,
        strategy: Strategy,
        core_fields: CoreFields
    ) -> Strategy:
        """为策略计算所有行权价"""
        
        # 解析DTE
        dte_str = strategy.dte or "30天"
        dte = int(''.join(filter(str.isdigit, dte_str)))
        
        # 计算每条腿的行权价
        for leg in strategy.legs:
            strike, method = self.calculate_strike(leg, core_fields, dte)
            leg.strike_calculated = strike
            leg.calculation_method = method
        
        return strategy
