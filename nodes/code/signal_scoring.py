"""
信号打分代码节点 (CODE2 / #5001)
计算 LongVolScore 和 ShortVolScore

支持上下文感知：
- 动态 Z-Score 标准差 (根据 IV 水平自适应)
- 信号增强因子 (Squeeze 模式下放大 GEX/VEX)
- DEX/PCR/MaxPain 新信号整合
"""
from typing import Dict, Any, Optional
from . import CodeNodeResult, z_score


def calculate_signals(
    features: Dict[str, Any], 
    env_vars: Dict[str, Any],
    context_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    计算标准化信号
    
    Args:
        features: 特征字典
        env_vars: 环境变量
        context_params: 上下文参数 (来自 Meso 系统)
            - vol_scale_factor: 波动率缩放因子 (默认 1.0)
            - gex_signal_multiplier: GEX 信号增强 (默认 1.0)
            - vex_signal_multiplier: VEX 信号增强 (默认 1.0)
            - is_squeeze: Squeeze 模式标记
            - direction_score: Meso 方向分数
        
    Returns:
        标准化信号字典
    """
    # 解析上下文参数
    ctx = context_params or {}
    
    # 类型安全处理
    def safe_float(val, default=1.0):
        if val is None:
            return default
        try:
            return float(val)
        except (TypeError, ValueError):
            return default
    
    def safe_int(val, default=0):
        if val is None:
            return default
        try:
            return int(val)
        except (TypeError, ValueError):
            return default
    
    vol_scale = safe_float(ctx.get('vol_scale_factor'), 1.0)
    gex_mult = safe_float(ctx.get('gex_signal_multiplier'), 1.0)
    vex_mult = safe_float(ctx.get('vex_signal_multiplier'), 1.0)
    is_squeeze = bool(ctx.get('is_squeeze', False))
    meso_direction = safe_float(ctx.get('direction_score'), 0.0)
    
    # 确保 vol_scale 在合理范围
    vol_scale = max(0.1, min(5.0, vol_scale))
    
    # ==================== 提取特征 ====================
    
    # 核心特征
    vrp_sel = safe_float(features.get('vrp_sel'), 0)
    term_slope = safe_float(features.get('term_slope'), 0)
    term_curv = safe_float(features.get('term_curv'), 0)
    skew_asym = safe_float(features.get('skew_asym'), 0)
    gex_level = safe_int(features.get('gex_level'), 0)
    pin_risk = safe_int(features.get('pin_risk'), 0)
    vex_net = safe_float(features.get('vex_net'), 0)
    vanna_atm = safe_float(features.get('vanna_atm'), 0)
    rv_momo = safe_float(features.get('rv_momo'), 0)
    spread_atm = safe_float(features.get('spread_atm'), 0)
    ask_premium = safe_float(features.get('ask_premium_atm'), 0)
    
    # 新增特征
    dex_level = safe_int(features.get('dex_level'), 0)
    pcr_sentiment = safe_int(features.get('pcr_sentiment'), 0)
    max_pain_pull = safe_int(features.get('max_pain_pull'), 0)
    smile_curvature = safe_float(features.get('smile_curvature'), 0)
    vol_regime = safe_float(features.get('vol_regime'), 1.0)
    wall_asymmetry = safe_float(features.get('wall_asymmetry'), 0)
    
    # ==================== 信号计算 ====================
    
    # 1. VRP 信号（VRP 高 → 做空波动，取负 → 多波动正分）
    s_vrp = -z_score(vrp_sel, mean=0, std=0.05 * vol_scale)
    
    # 2. Carry 信号（期限结构）
    s_carry = -z_score(term_slope, mean=0, std=0.02 * vol_scale) \
              - 0.5 * z_score(term_curv, mean=0, std=0.01 * vol_scale)
    
    # 3. Skew 信号
    s_skew = z_score(skew_asym, mean=0, std=0.05 * vol_scale)
    
    # 4. GEX 信号（情境加权）
    s_gex_base = gex_level + pin_risk
    if is_squeeze and s_gex_base > 0:
        # 正向 GEX 在 Squeeze 模式下放大
        s_gex = s_gex_base * gex_mult * 1.5
    elif is_squeeze and s_gex_base < 0:
        # 负向 GEX 在 Squeeze 模式下减弱
        s_gex = s_gex_base * 0.5
    else:
        s_gex = s_gex_base * gex_mult
    
    # 5. VEX 信号（VEX 负 → 卖方主导 → 利于多波动）
    s_vex_base = z_score(-vex_net, mean=0, std=100 * vol_scale)
    s_vex = s_vex_base * vex_mult
    
    # 6. Vanna 信号（|Vanna| 大 → 波动不稳定）
    s_vanna = -z_score(abs(vanna_atm), mean=0, std=0.01 * vol_scale)
    
    # 7. RV 动量信号
    s_rv = z_score(rv_momo, mean=0, std=0.2 * vol_scale)
    
    # 8. 流动性惩罚（不受波动率缩放）
    s_liq = -(max(0, z_score(spread_atm, mean=0.01, std=0.01)) + 
              0.5 * max(0, z_score(ask_premium, mean=0, std=0.02)))
    
    # ==================== 新增信号 ====================
    
    # 9. DEX 方向信号（与 GEX 互补）
    # DEX 正 = 市场偏多，对做空波动有利（因为上涨时波动常收缩）
    s_dex = -dex_level * 0.5  # 多头市场 → 做空波动信号
    
    # 10. PCR 情绪信号
    # PCR 高（偏悲观）→ 恐慌对冲 → 利于做多波动
    # PCR 低（偏乐观）→ 过度自信 → 利于做空波动
    s_pcr = pcr_sentiment * 0.3  # 悲观时为负，转正利于多波动
    
    # 11. Max Pain 吸引信号
    # 接近 Max Pain → 波动可能收敛（到期日效应）
    s_maxpain = max_pain_pull * 0.4  # 接近时为负，做空波动信号
    
    # 12. 微笑曲率信号
    # 高曲率 → 尾部风险定价高 → 可能利于做多波动
    s_smile = z_score(smile_curvature, mean=0, std=0.1 * vol_scale) * 0.3
    
    # 13. 波动率体制信号
    # vol_regime > 1 表示短期波动率 > 长期，波动扩张中
    s_regime = z_score(vol_regime - 1, mean=0, std=0.2) * 0.5
    
    # 14. Wall 不对称信号
    # wall_asymmetry > 0 表示更靠近上方阻力，可能限制上涨
    s_wall = -z_score(wall_asymmetry, mean=0, std=0.03) * 0.3
    
    # 15. Meso 协同信号
    s_meso_alignment = 0.0
    if meso_direction != 0:
        s_meso_alignment = meso_direction * 0.15
    
    # ==================== 增强信号（可扩展）====================
    s_vov = 0       # VoV 信号
    s_vix_ts = 0    # VIX 期限结构
    s_rim = 0       # 盘中实现波动率
    s_compress = 0  # 压缩信号
    s_eir_long = 0  # 事件风险（多）
    s_eir_short = 0 # 事件风险（空）
    s_corr_idx = 0  # 相关性指数
    s_flow = 0      # 资金流向
    
    signals = {
        # 核心信号
        's_vrp': round(s_vrp, 3),
        's_carry': round(s_carry, 3),
        's_skew': round(s_skew, 3),
        's_gex': round(s_gex, 3),
        's_vex': round(s_vex, 3),
        's_vanna': round(s_vanna, 3),
        's_rv': round(s_rv, 3),
        's_liq': round(s_liq, 3),
        
        # 新增信号
        's_dex': round(s_dex, 3),
        's_pcr': round(s_pcr, 3),
        's_maxpain': round(s_maxpain, 3),
        's_smile': round(s_smile, 3),
        's_regime': round(s_regime, 3),
        's_wall': round(s_wall, 3),
        's_meso': round(s_meso_alignment, 3),
        
        # 扩展信号
        's_vov': s_vov,
        's_vix_ts': s_vix_ts,
        's_rim': s_rim,
        's_compress': s_compress,
        's_eir_long': s_eir_long,
        's_eir_short': s_eir_short,
        's_corr_idx': s_corr_idx,
        's_flow': s_flow,
        
        # 元信息
        '_context': {
            'vol_scale_factor': vol_scale,
            'gex_multiplier': gex_mult,
            'vex_multiplier': vex_mult,
            'is_squeeze': is_squeeze
        }
    }
    
    return signals


def calculate_scores(
    signals: Dict[str, Any], 
    env_vars: Dict[str, Any],
    context_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    计算 LongVolScore 和 ShortVolScore
    
    权重分配原则：
    - 核心因子（VRP, GEX, VEX）占 60%
    - 结构因子（Carry, Skew）占 15%
    - 新增因子（DEX, PCR, MaxPain等）占 15%
    - 辅助因子（流动性, Regime等）占 10%
    
    Args:
        signals: 标准化信号
        env_vars: 环境变量（包含权重配置）
        context_params: 上下文参数 (可能包含动态权重)
        
    Returns:
        评分结果字典
    """
    ctx = context_params or {}
    
    # ==================== 做多波动率权重 ====================
    # 核心权重（可从上下文覆盖）
    w_vrp_long = float(ctx.get('WEIGHT_VRP_LONG') or env_vars.get('WEIGHT_VRP_LONG', 0.22))
    w_gex_long = float(ctx.get('WEIGHT_GEX_LONG') or env_vars.get('WEIGHT_GEX_LONG', 0.18))
    w_vex_long = float(ctx.get('WEIGHT_VEX_LONG') or env_vars.get('WEIGHT_VEX_LONG', 0.15))
    w_carry_long = float(ctx.get('WEIGHT_CARRY_LONG') or env_vars.get('WEIGHT_CARRY_LONG', 0.08))
    w_skew_long = float(ctx.get('WEIGHT_SKEW_LONG') or env_vars.get('WEIGHT_SKEW_LONG', 0.07))
    
    # 新增权重
    w_dex = 0.05
    w_pcr = 0.04
    w_maxpain = 0.03
    w_smile = 0.03
    w_regime = 0.04
    w_meso = 0.05
    
    # 辅助权重
    w_vanna = 0.02
    w_rv = 0.03
    w_liq = 0.01
    
    # LongVolScore 计算
    long_vol_score = (
        w_vrp_long * signals['s_vrp'] +
        w_gex_long * signals['s_gex'] +
        w_vex_long * signals['s_vex'] +
        w_carry_long * signals['s_carry'] +
        w_skew_long * signals['s_skew'] +
        # 新增信号
        w_dex * (-signals['s_dex']) +  # DEX 偏空利于多波动
        w_pcr * (-signals['s_pcr']) +   # PCR 偏悲观利于多波动
        w_maxpain * (-signals['s_maxpain']) +  # 远离 MaxPain 利于多波动
        w_smile * signals['s_smile'] +
        w_regime * signals['s_regime'] +
        w_meso * signals['s_meso'] +
        # 辅助信号
        w_vanna * signals['s_vanna'] +
        w_rv * signals['s_rv'] +
        w_liq * signals['s_liq']
    )
    
    # ==================== 做空波动率权重 ====================
    w_vrp_short = float(ctx.get('WEIGHT_VRP_SHORT') or env_vars.get('WEIGHT_VRP_SHORT', 0.25))
    w_gex_short = float(ctx.get('WEIGHT_GEX_SHORT') or env_vars.get('WEIGHT_GEX_SHORT', 0.12))
    w_carry_short = float(ctx.get('WEIGHT_CARRY_SHORT') or env_vars.get('WEIGHT_CARRY_SHORT', 0.15))
    
    # ShortVolScore 计算
    short_vol_score = (
        w_vrp_short * (-signals['s_vrp']) +
        w_gex_short * (-signals['s_gex']) +
        0.10 * (-signals['s_vex']) +
        w_carry_short * (-signals['s_carry']) +
        0.06 * (-signals['s_skew']) +
        # 新增信号（反向）
        w_dex * signals['s_dex'] +      # DEX 偏多利于空波动
        w_pcr * signals['s_pcr'] +       # PCR 偏乐观利于空波动
        w_maxpain * signals['s_maxpain'] +  # 接近 MaxPain 利于空波动
        0.02 * (-signals['s_smile']) +
        0.03 * (-signals['s_regime']) +
        w_meso * (-signals['s_meso']) +
        # 辅助信号
        0.03 * (-signals['s_rv']) +
        0.02 * signals['s_liq']  # 流动性好利于空波动
    )
    
    # ==================== 评分分解 ====================
    return {
        'long_vol_score': round(long_vol_score, 3),
        'short_vol_score': round(short_vol_score, 3),
        'score_breakdown': {
            'long': {
                'vrp': round(w_vrp_long * signals['s_vrp'], 3),
                'gex': round(w_gex_long * signals['s_gex'], 3),
                'vex': round(w_vex_long * signals['s_vex'], 3),
                'carry': round(w_carry_long * signals['s_carry'], 3),
                'skew': round(w_skew_long * signals['s_skew'], 3),
                'dex': round(w_dex * (-signals['s_dex']), 3),
                'pcr': round(w_pcr * (-signals['s_pcr']), 3),
                'maxpain': round(w_maxpain * (-signals['s_maxpain']), 3),
                'regime': round(w_regime * signals['s_regime'], 3),
                'meso': round(w_meso * signals['s_meso'], 3)
            },
            'short': {
                'vrp': round(w_vrp_short * (-signals['s_vrp']), 3),
                'gex': round(w_gex_short * (-signals['s_gex']), 3),
                'carry': round(w_carry_short * (-signals['s_carry']), 3),
                'dex': round(w_dex * signals['s_dex'], 3),
                'pcr': round(w_pcr * signals['s_pcr'], 3),
                'maxpain': round(w_maxpain * signals['s_maxpain'], 3)
            }
        },
        '_weights_used': {
            'long': {
                'vrp': w_vrp_long, 'gex': w_gex_long, 'vex': w_vex_long,
                'carry': w_carry_long, 'skew': w_skew_long,
                'dex': w_dex, 'pcr': w_pcr, 'maxpain': w_maxpain,
                'regime': w_regime, 'meso': w_meso
            },
            'short': {
                'vrp': w_vrp_short, 'gex': w_gex_short, 'carry': w_carry_short
            }
        }
    }


def code2_signal_scoring(
    features_output: Dict[str, Any], 
    env_vars: Dict[str, Any] = None,
    context_params: Optional[Dict[str, Any]] = None
) -> CodeNodeResult:
    """
    CODE2 节点: 信号打分
    
    Args:
        features_output: 特征计算节点的输出
        env_vars: 环境变量配置
        context_params: Meso 上下文参数 (可选)
        
    Returns:
        CodeNodeResult 包含评分结果
    """
    try:
        if env_vars is None:
            env_vars = {}
        
        features = features_output.get('features', {})
        
        # 传递上下文参数
        signals = calculate_signals(features, env_vars, context_params)
        scores = calculate_scores(signals, env_vars, context_params)
        
        result = {
            'symbol': features_output.get('symbol', ''),
            'timestamp': features_output.get('timestamp', ''),
            'signals': signals,
            'scores': scores,
            'signal_count': len([k for k in signals if k.startswith('s_') and signals[k] != 0]),
            'status': 'success',
            '_context_aware': context_params is not None
        }
        
        return CodeNodeResult(success=True, result=result)
        
    except Exception as e:
        return CodeNodeResult(
            success=False,
            result={'error': True, 'message': str(e)},
            error=str(e)
        )