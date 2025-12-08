"""
信号打分代码节点 (CODE2 / #5001)
计算 LongVolScore 和 ShortVolScore

支持上下文感知：
- 动态 Z-Score 标准差 (根据 IV 水平自适应)
- 信号增强因子 (Squeeze 模式下放大 GEX/VEX)
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
    
    vol_scale = safe_float(ctx.get('vol_scale_factor'), 1.0)
    gex_mult = safe_float(ctx.get('gex_signal_multiplier'), 1.0)
    vex_mult = safe_float(ctx.get('vex_signal_multiplier'), 1.0)
    is_squeeze = bool(ctx.get('is_squeeze', False))
    meso_direction = safe_float(ctx.get('direction_score'), 0.0)
    
    # 确保 vol_scale 在合理范围
    vol_scale = max(0.1, min(5.0, vol_scale))
    
    # 提取特征
    vrp_sel = features.get('vrp_sel', 0)
    term_slope = features.get('term_slope', 0)
    term_curv = features.get('term_curv', 0)
    skew_asym = features.get('skew_asym', 0)
    gex_level = features.get('gex_level', 0)
    pin_risk = features.get('pin_risk', 0)
    vex_net = features.get('vex_net', 0)
    vanna_atm = features.get('vanna_atm', 0)
    rv_momo = features.get('rv_momo', 0)
    spread_atm = features.get('spread_atm', 0)
    ask_premium = features.get('ask_premium_atm', 0)
    
    # ===== 动态 Z-Score (自适应波动率) =====
    # 高波环境下 vol_scale > 1，std 放大，容忍度提高
    # 低波环境下 vol_scale < 1，std 收紧，信号更敏感
    
    # 标准化信号（多波动为正分）
    s_vrp = -z_score(vrp_sel, mean=0, std=0.05 * vol_scale)  # VRP高→做空波动，取负→多波动正分
    s_carry = -z_score(term_slope, mean=0, std=0.02 * vol_scale) - 0.5 * z_score(term_curv, mean=0, std=0.01 * vol_scale)
    s_skew = z_score(skew_asym, mean=0, std=0.05 * vol_scale)
    
    # ===== GEX/VEX 信号增强 (情境加权) =====
    # 基础 GEX 信号
    s_gex_base = gex_level + pin_risk  # gex_level已考虑方向，pin_risk为负
    
    # Squeeze 模式增强
    if is_squeeze and s_gex_base > 0:
        # 正向 GEX 在 Squeeze 模式下放大
        s_gex = s_gex_base * gex_mult
    elif is_squeeze and s_gex_base < 0:
        # 负向 GEX 在 Squeeze 模式下减弱 (逼空时负 GEX 信号不可靠)
        s_gex = s_gex_base * 0.5
    else:
        s_gex = s_gex_base
    
    # VEX 信号
    s_vex_base = z_score(-vex_net, mean=0, std=100 * vol_scale)  # VEX负→多波动
    s_vex = s_vex_base * vex_mult
    
    # Vanna 信号 (不受 Squeeze 增强)
    s_vanna = -z_score(abs(vanna_atm), mean=0, std=0.01 * vol_scale)  # |Vanna|大→不利
    
    # RV 动量
    s_rv = z_score(rv_momo, mean=0, std=0.2 * vol_scale)
    
    # 流动性惩罚 (不受波动率缩放)
    s_liq = -(max(0, z_score(spread_atm, mean=0.01, std=0.01)) + 
              0.5 * max(0, z_score(ask_premium, mean=0, std=0.02)))
    
    # ===== Meso 协同信号 (新增) =====
    # 当 Meso 和 Micro 方向一致时，增加确信度
    s_meso_alignment = 0.0
    if meso_direction != 0:
        # Meso 方向作为额外信号输入
        s_meso_alignment = meso_direction * 0.1  # 缩放到合理范围
    
    # 增强信号（简化版，默认0）
    s_vov = 0
    s_vix_ts = 0
    s_rim = 0
    s_compress = 0
    s_eir_long = 0
    s_eir_short = 0
    s_corr_idx = 0
    s_flow_putcrowd = 0
    
    signals = {
        's_vrp': round(s_vrp, 3),
        's_carry': round(s_carry, 3),
        's_skew': round(s_skew, 3),
        's_gex': round(s_gex, 3),
        's_vex': round(s_vex, 3),
        's_vanna': round(s_vanna, 3),
        's_rv': round(s_rv, 3),
        's_liq': round(s_liq, 3),
        's_meso_alignment': round(s_meso_alignment, 3),  # 新增
        's_vov': s_vov,
        's_vix_ts': s_vix_ts,
        's_rim': s_rim,
        's_compress': s_compress,
        's_eir_long': s_eir_long,
        's_eir_short': s_eir_short,
        's_corr_idx': s_corr_idx,
        's_flow_putcrowd': s_flow_putcrowd,
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
    
    Args:
        signals: 标准化信号
        env_vars: 环境变量（包含权重配置）
        context_params: 上下文参数 (可能包含动态权重)
        
    Returns:
        评分结果字典
    """
    ctx = context_params or {}
    
    # 做多波动率权重 (优先使用上下文动态权重)
    w_vrp_long = float(ctx.get('WEIGHT_VRP_LONG') or env_vars.get('WEIGHT_VRP_LONG', 0.25))
    w_gex_long = float(ctx.get('WEIGHT_GEX_LONG') or env_vars.get('WEIGHT_GEX_LONG', 0.18))
    w_vex_long = float(ctx.get('WEIGHT_VEX_LONG') or env_vars.get('WEIGHT_VEX_LONG', 0.18))
    w_carry_long = float(ctx.get('WEIGHT_CARRY_LONG') or env_vars.get('WEIGHT_CARRY_LONG', 0.08))
    w_skew_long = float(ctx.get('WEIGHT_SKEW_LONG') or env_vars.get('WEIGHT_SKEW_LONG', 0.08))
    
    # Meso 协同权重
    w_meso = 0.05  # Meso 信号占比
    
    # LongVolScore 计算
    long_vol_score = (
        w_vrp_long * signals['s_vrp'] +
        w_gex_long * signals['s_gex'] +
        w_vex_long * signals['s_vex'] +
        w_carry_long * signals['s_carry'] +
        w_skew_long * signals['s_skew'] +
        0.05 * signals['s_vanna'] +
        0.06 * signals['s_rv'] +
        0.10 * signals['s_liq'] +
        0.07 * signals['s_vov'] +
        0.05 * signals['s_vix_ts'] +
        0.05 * signals['s_rim'] +
        0.05 * signals['s_compress'] +
        0.04 * signals['s_eir_long'] +
        w_meso * signals.get('s_meso_alignment', 0)  # 新增 Meso 协同
    )
    
    # 做空波动率权重
    w_vrp_short = float(ctx.get('WEIGHT_VRP_SHORT') or env_vars.get('WEIGHT_VRP_SHORT', 0.30))
    w_gex_short = float(ctx.get('WEIGHT_GEX_SHORT') or env_vars.get('WEIGHT_GEX_SHORT', 0.12))
    w_carry_short = float(ctx.get('WEIGHT_CARRY_SHORT') or env_vars.get('WEIGHT_CARRY_SHORT', 0.18))
    
    # ShortVolScore 计算
    short_vol_score = (
        w_vrp_short * (-signals['s_vrp']) +
        w_gex_short * (-signals['s_gex']) +
        0.12 * (-signals['s_vex']) +
        w_carry_short * (-signals['s_carry']) +
        0.08 * (-signals['s_skew']) +
        0.05 * (-signals['s_rv']) +
        0.10 * signals['s_liq'] +
        0.07 * (-signals['s_vov']) +
        0.05 * (-signals['s_vix_ts']) +
        0.05 * (-signals['s_rim']) +
        0.05 * (-signals['s_compress']) +
        0.06 * signals['s_eir_short'] +
        0.05 * signals['s_corr_idx'] +
        0.04 * signals['s_flow_putcrowd'] +
        w_meso * (-signals.get('s_meso_alignment', 0))  # Meso 协同 (反向)
    )
    
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
                'meso': round(w_meso * signals.get('s_meso_alignment', 0), 3)
            },
            'short': {
                'vrp': round(w_vrp_short * (-signals['s_vrp']), 3),
                'gex': round(w_gex_short * (-signals['s_gex']), 3),
                'carry': round(w_carry_short * (-signals['s_carry']), 3)
            }
        },
        '_weights_used': {
            'long': {
                'vrp': w_vrp_long, 'gex': w_gex_long, 'vex': w_vex_long,
                'carry': w_carry_long, 'skew': w_skew_long
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
            - vol_scale_factor: 波动率缩放因子
            - gex_signal_multiplier: GEX 信号增强
            - vex_signal_multiplier: VEX 信号增强
            - is_squeeze: Squeeze 模式
            - direction_score: Meso 方向分数
            - WEIGHT_*: 动态权重覆盖
        
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
