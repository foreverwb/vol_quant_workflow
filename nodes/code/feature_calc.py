"""
特征计算代码节点 (CODE1 / #4001)
计算波动率交易特征
"""
from typing import Dict, Any
from . import CodeNodeResult


def calculate_features(core_fields: Dict[str, Any], env_vars: Dict[str, Any]) -> Dict[str, Any]:
    """
    计算波动率交易特征
    
    Args:
        core_fields: 核心字段数据（支持嵌套结构或扁平结构）
        env_vars: 环境变量
        
    Returns:
        特征字典
    """
    # 兼容嵌套和扁平结构
    def get_field(name: str, default=0):
        # 先尝试扁平结构
        if name in core_fields:
            return core_fields.get(name) or default
        # 再尝试嵌套结构
        for group in ['gamma_regime', 'key_levels', 'iv_hv', 'structure']:
            if group in core_fields and isinstance(core_fields[group], dict):
                if name in core_fields[group]:
                    return core_fields[group].get(name) or default
        return default
    
    # 提取核心字段
    spot = get_field('spot', 0)
    vol_trigger = get_field('vol_trigger', 0)
    
    # IV/HV 数据
    iv_atm = get_field('iv_atm', 0) or get_field('iv_event_w_atm', 0) or get_field('iv_m1_atm', 0)
    iv_front = get_field('iv_front', 0) or get_field('iv_m1_atm', 0)
    iv_back = get_field('iv_back', 0) or get_field('iv_m2_atm', 0)
    hv10 = get_field('hv10', 0)
    hv20 = get_field('hv20', 0)
    hv60 = get_field('hv60', 0)
    
    # Greeks
    vex_net = get_field('vex_net', 0)
    vanna_atm = get_field('vanna_atm', 0)
    
    # 结构
    term_slope = get_field('term_slope', 0)
    put_skew_25 = get_field('put_skew_25', 0)
    call_skew_25 = get_field('call_skew_25', 0)
    spread_atm = get_field('spread_atm', 0)
    ask_premium = get_field('ask_premium_atm', 0)
    
    # 新增字段
    max_pain = get_field('max_pain', 0)
    net_dex_sign = get_field('net_dex_sign', 'neutral')
    pcr_ratio = get_field('pcr_ratio', 1.0)
    gamma_wall = get_field('gamma_wall', 0)
    call_wall = get_field('call_wall', 0)
    put_wall = get_field('put_wall', 0)
    smile_curvature = get_field('smile_curvature', 0)
    
    # ==================== 特征计算 ====================
    
    # 1. VRP (Variance Risk Premium)
    # 注意: 使用 is not None 而不是 truthiness 检查，因为 0 是有效值
    vrp_10 = iv_atm - hv10 if iv_atm is not None and hv10 is not None else 0
    vrp_20 = iv_atm - hv20 if iv_atm is not None and hv20 is not None else 0
    vrp_sel = vrp_10 if vrp_10 != 0 else vrp_20  # 优先用短期
    
    # 2. 期限结构特征
    if iv_front is not None and iv_back is not None:
        term_slope_calc = (iv_back - iv_front) / iv_front if iv_front > 0 else 0
        term_curv = (iv_back - iv_front) - term_slope if term_slope is not None else 0
    else:
        term_slope_calc = term_slope if term_slope is not None else 0
        term_curv = 0
    
    # 3. Skew 不对称性
    skew_asym = put_skew_25 - call_skew_25 if put_skew_25 is not None and call_skew_25 is not None else 0
    
    # 4. GEX Level (根据 VOL TRIGGER 判定)
    if spot and vol_trigger:
        trigger_distance = (spot - vol_trigger) / vol_trigger if vol_trigger > 0 else 0
        if trigger_distance < -0.002:  # below trigger
            gex_level = 1  # 负 Gamma 区域，利于做多波动
        elif trigger_distance > 0.002:  # above trigger
            gex_level = -1  # 正 Gamma 区域，波动受抑制
        else:  # near trigger
            gex_level = 0  # 中性，易翻转
    else:
        gex_level = 0
    
    # 5. DEX Level (方向性暴露)
    dex_map = {'bullish': 1, 'bearish': -1, 'neutral': 0, 'positive': 1, 'negative': -1}
    dex_level = dex_map.get(str(net_dex_sign).lower(), 0)
    
    # 6. Pin 风险（贴近 Gamma Wall）
    gamma_wall_prox = get_field('gamma_wall_prox', 1)
    pin_risk = -1 if (gamma_wall_prox <= 0.005 and gex_level < 0) else 0
    
    # 7. Max Pain 吸引力
    if spot and max_pain:
        max_pain_distance = abs(spot - max_pain) / spot if spot > 0 else 0
        max_pain_pull = -1 if max_pain_distance <= 0.02 else 0  # 2%内有吸引力
    else:
        max_pain_distance = 0
        max_pain_pull = 0
    
    # 8. PCR 情绪指标
    if pcr_ratio:
        if pcr_ratio > 1.2:
            pcr_sentiment = -1  # 偏悲观
        elif pcr_ratio < 0.8:
            pcr_sentiment = 1   # 偏乐观
        else:
            pcr_sentiment = 0   # 中性
    else:
        pcr_sentiment = 0
    
    # 9. RV 动量
    rv_momo = (hv10 / hv60 - 1) if (hv10 and hv60 and hv60 > 0) else 0
    
    # 10. 波动率体制
    vol_regime = hv20 / hv60 if (hv20 and hv60 and hv60 > 0) else 1.0
    
    # 11. 微笑曲率特征
    smile_feature = smile_curvature if smile_curvature else 0
    
    # 12. 支撑/阻力距离
    if spot and call_wall and put_wall:
        dist_to_call_wall = (call_wall - spot) / spot if spot > 0 else 0
        dist_to_put_wall = (spot - put_wall) / spot if spot > 0 else 0
        wall_asymmetry = dist_to_call_wall - dist_to_put_wall  # 正值=更靠近上方
    else:
        dist_to_call_wall = 0
        dist_to_put_wall = 0
        wall_asymmetry = 0
    
    features = {
        # VRP 相关
        'vrp_sel': round(vrp_sel, 4),
        'vrp_10': round(vrp_10, 4),
        'vrp_20': round(vrp_20, 4),
        
        # 期限结构
        'term_slope': round(term_slope_calc, 4),
        'term_curv': round(term_curv, 4),
        
        # Skew
        'skew_asym': round(skew_asym, 4),
        'smile_curvature': round(smile_feature, 4),
        
        # Gamma/Delta
        'gex_level': gex_level,
        'dex_level': dex_level,
        'pin_risk': pin_risk,
        
        # Greeks
        'vex_net': vex_net,
        'vanna_atm': vanna_atm,
        
        # 市场结构
        'max_pain_distance': round(max_pain_distance, 4),
        'max_pain_pull': max_pain_pull,
        'pcr_sentiment': pcr_sentiment,
        'pcr_ratio': round(pcr_ratio, 2) if pcr_ratio else None,
        
        # 波动率体制
        'rv_momo': round(rv_momo, 4),
        'vol_regime': round(vol_regime, 4),
        
        # 支撑/阻力
        'dist_to_call_wall': round(dist_to_call_wall, 4),
        'dist_to_put_wall': round(dist_to_put_wall, 4),
        'wall_asymmetry': round(wall_asymmetry, 4),
        
        # 流动性
        'spread_atm': spread_atm,
        'ask_premium_atm': ask_premium,
        
        # 元数据
        '_spot': spot,
        '_vol_trigger': vol_trigger,
        '_gamma_wall_prox': gamma_wall_prox
    }
    
    return features


def code1_feature_calculation(
    validation_output: Dict[str, Any], 
    env_vars: Dict[str, Any] = None
) -> CodeNodeResult:
    """
    CODE1 节点: 特征计算
    
    Args:
        validation_output: DataValidator 节点的输出
        env_vars: 环境变量配置
        
    Returns:
        CodeNodeResult 包含计算后的特征
    """
    try:
        if env_vars is None:
            env_vars = {}
            
        core_fields = validation_output.get('core_fields', {})
        features = calculate_features(core_fields, env_vars)
        
        result = {
            'symbol': validation_output.get('symbol', ''),
            'timestamp': validation_output.get('timestamp', ''),
            'features': features,
            'feature_count': len([k for k in features if not k.startswith('_')]),
            'status': 'success'
        }
        
        return CodeNodeResult(success=True, result=result)
        
    except Exception as e:
        return CodeNodeResult(
            success=False,
            result={'error': True, 'message': str(e)},
            error=str(e)
        )