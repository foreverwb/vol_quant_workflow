"""
信号打分引擎
"""
from models.data_models import Features, Signals, Scores
from config.env_config import EnvConfig
from scipy.stats import norm

class SignalCalculator:
    """信号计算器"""
    
    def __init__(self, env_config: EnvConfig = None):
        self.env_config = env_config or EnvConfig()
    
    @staticmethod
    def z_score(x: float, mean: float = 0, std: float = 1) -> float:
        """Z-score标准化"""
        if std == 0:
            return 0
        return (x - mean) / std
    
    def calculate_signals(self, features: Features) -> Signals:
        """计算标准化信号"""
        
        vrp_sel = features.vrp_sel
        term_slope = features.term_slope
        term_curv = features.term_curv
        skew_asym = features.skew_asym
        gex_level = features.gex_level
        pin_risk = features.pin_risk
        vex_net = features.vex_net
        vanna_atm = features.vanna_atm
        rv_momo = features.rv_momo
        spread_atm = features.spread_atm
        ask_premium = features.ask_premium_atm
        
        # 标准化信号（多波动为正分）
        s_vrp = -self.z_score(vrp_sel, mean=0, std=0.05)
        s_carry = -self.z_score(term_slope, mean=0, std=0.02) - \
                  0.5 * self.z_score(term_curv, mean=0, std=0.01)
        s_skew = self.z_score(skew_asym, mean=0, std=0.05)
        s_gex = gex_level + pin_risk
        s_vex = self.z_score(-vex_net, mean=0, std=100)
        s_vanna = -self.z_score(abs(vanna_atm), mean=0, std=0.01)
        s_rv = self.z_score(rv_momo, mean=0, std=0.2)
        
        # 流动性惩罚
        s_liq = -(max(0, self.z_score(spread_atm, mean=0.01, std=0.01)) + 
                  0.5 * max(0, self.z_score(ask_premium, mean=0, std=0.02)))
        
        return Signals(
            s_vrp=round(s_vrp, 3),
            s_carry=round(s_carry, 3),
            s_skew=round(s_skew, 3),
            s_gex=round(s_gex, 3),
            s_vex=round(s_vex, 3),
            s_vanna=round(s_vanna, 3),
            s_rv=round(s_rv, 3),
            s_liq=round(s_liq, 3)
        )
    
    def calculate_scores(self, signals: Signals) -> Scores:
        """计算LongVolScore和ShortVolScore"""
        
        # 做多波动率权重
        w_vrp_long = self.env_config.WEIGHT_VRP_LONG
        w_gex_long = self.env_config.WEIGHT_GEX_LONG
        w_vex_long = self.env_config.WEIGHT_VEX_LONG
        w_carry_long = self.env_config.WEIGHT_CARRY_LONG
        w_skew_long = self.env_config.WEIGHT_SKEW_LONG
        
        # LongVolScore
        long_vol_score = (
            w_vrp_long * signals.s_vrp +
            w_gex_long * signals.s_gex +
            w_vex_long * signals.s_vex +
            w_carry_long * signals.s_carry +
            w_skew_long * signals.s_skew +
            0.05 * signals.s_vanna +
            0.06 * signals.s_rv +
            0.10 * signals.s_liq +
            0.07 * signals.s_vov +
            0.05 * signals.s_vix_ts +
            0.05 * signals.s_rim +
            0.05 * signals.s_compress +
            0.04 * signals.s_eir_long
        )
        
        # 做空波动率权重
        w_vrp_short = self.env_config.WEIGHT_VRP_SHORT
        w_gex_short = self.env_config.WEIGHT_GEX_SHORT
        w_carry_short = self.env_config.WEIGHT_CARRY_SHORT
        
        # ShortVolScore
        short_vol_score = (
            w_vrp_short * (-signals.s_vrp) +
            w_gex_short * (-signals.s_gex) +
            0.12 * (-signals.s_vex) +
            w_carry_short * (-signals.s_carry) +
            0.08 * (-signals.s_skew) +
            0.05 * (-signals.s_rv) +
            0.10 * signals.s_liq +
            0.07 * (-signals.s_vov) +
            0.05 * (-signals.s_vix_ts) +
            0.05 * (-signals.s_rim) +
            0.05 * (-signals.s_compress) +
            0.06 * signals.s_eir_short +
            0.05 * signals.s_corr_idx +
            0.04 * signals.s_flow_putcrowd
        )
        
        score_breakdown = {
            'long': {
                'vrp': round(w_vrp_long * signals.s_vrp, 3),
                'gex': round(w_gex_long * signals.s_gex, 3),
                'vex': round(w_vex_long * signals.s_vex, 3),
                'carry': round(w_carry_long * signals.s_carry, 3),
                'skew': round(w_skew_long * signals.s_skew, 3)
            },
            'short': {
                'vrp': round(w_vrp_short * (-signals.s_vrp), 3),
                'gex': round(w_gex_short * (-signals.s_gex), 3),
                'carry': round(w_carry_short * (-signals.s_carry), 3)
            }
        }
        
        return Scores(
            long_vol_score=round(long_vol_score, 3),
            short_vol_score=round(short_vol_score, 3),
            score_breakdown=score_breakdown
        )
