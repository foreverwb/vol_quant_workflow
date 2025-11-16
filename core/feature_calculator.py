"""
特征计算引擎
"""
import math
from models.data_models import CoreFields, Features
from config.env_config import EnvConfig

class FeatureCalculator:
    """特征计算器"""
    
    def __init__(self, env_config: EnvConfig = None):
        self.env_config = env_config or EnvConfig()
    
    def calculate(self, core_fields: CoreFields) -> Features:
        """计算所有特征"""
        
        # 提取核心字段
        spot = core_fields.spot or 0
        vol_trigger = core_fields.vol_trigger or 0
        iv_event_w = core_fields.iv_event_w_atm or 0
        iv_m1 = core_fields.iv_m1_atm or 0
        iv_m2 = core_fields.iv_m2_atm or 0
        hv10 = core_fields.hv10 or 0
        hv20 = core_fields.hv20 or 0
        hv60 = core_fields.hv60 or 0
        vex_net = core_fields.vex_net or 0
        vanna_atm = core_fields.vanna_atm or 0
        term_slope = core_fields.term_slope or 0
        put_skew_25 = core_fields.put_skew_25 or 0
        call_skew_25 = core_fields.call_skew_25 or 0
        spread_atm = core_fields.spread_atm or 0
        ask_premium = core_fields.ask_premium_atm or 0
        gamma_wall_prox = core_fields.gamma_wall_prox or 0
        
        # 1. VRP (Variance Risk Premium)
        vrp_ew = iv_event_w - hv10 if iv_event_w and hv10 else 0
        vrp_30 = iv_m1 - hv20 if iv_m1 and hv20 else 0
        
        # 2. Term Structure
        term_curv = 0
        if iv_m1 and iv_m2:
            term_curv = iv_m2 - 2*iv_m1 + iv_event_w if iv_event_w else 0
        
        # 3. Skew Asymmetry
        skew_asym = (put_skew_25 - call_skew_25) if put_skew_25 and call_skew_25 else 0
        
        # 4. RV Momentum
        rv_momo = (hv10 / hv60 - 1) if hv10 and hv60 and hv60 > 0 else 0
        
        # 5. GEX Level
        spot_vs_trigger = core_fields.spot_vs_trigger or 'unknown'
        if spot_vs_trigger == 'below':
            gex_level = 1  # 负GEX，趋势倾向
        elif spot_vs_trigger == 'above':
            gex_level = -1  # 正GEX，区间倾向
        else:
            gex_level = 0  # 中性
        
        # 6. Pin Risk
        trigger_neutral_pct = self.env_config.TRIGGER_NEUTRAL_PCT
        gamma_wall_prox_threshold = self.env_config.GAMMA_WALL_PROX_THRESHOLD
        
        pin_risk = 0
        if (gamma_wall_prox <= gamma_wall_prox_threshold and 
            spot_vs_trigger == 'above'):
            pin_risk = -1  # Pin风险，不利于做多波动
        
        return Features(
            vrp_ew=round(vrp_ew, 4),
            vrp_30=round(vrp_30, 4),
            term_slope=round(term_slope, 4),
            term_curv=round(term_curv, 4),
            skew_asym=round(skew_asym, 4),
            rv_momo=round(rv_momo, 4),
            gex_level=gex_level,
            pin_risk=pin_risk,
            vex_net=vex_net,
            vanna_atm=vanna_atm,
            spread_atm=spread_atm,
            ask_premium_atm=ask_premium,
            gamma_wall_prox=round(gamma_wall_prox, 4),
            vrp_sel=vrp_ew if abs(vrp_ew) > 0.001 else vrp_30
        )
