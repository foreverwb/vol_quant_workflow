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
        core_fields: 核心字段数据
        env_vars: 环境变量
        
    Returns:
        特征字典
    """
    # 提取核心字段
    spot = core_fields.get('spot', 0)
    vol_trigger = core_fields.get('vol_trigger', 0)
    iv_event_w = core_fields.get('iv_event_w_atm', 0)
    iv_m1 = core_fields.get('iv_m1_atm', 0)
    iv_m2 = core_fields.get('iv_m2_atm', 0)
    hv10 = core_fields.get('hv10', 0)
    hv20 = core_fields.get('hv20', 0)
    hv60 = core_fields.get('hv60', 0)
    vex_net = core_fields.get('vex_net', 0)
    vanna_atm = core_fields.get('vanna_atm', 0)
    term_slope = core_fields.get('term_slope', 0)
    put_skew_25 = core_fields.get('put_skew_25', 0)
    call_skew_25 = core_fields.get('call_skew_25', 0)
    spread_atm = core_fields.get('spread_atm', 0)
    ask_premium = core_fields.get('ask_premium_atm', 0)
    
    # 计算VRP (Variance Risk Premium)
    vrp_ew = iv_event_w - hv10 if iv_event_w and hv10 else 0
    vrp_30 = iv_m1 - hv20 if iv_m1 and hv20 else 0
    
    # 选择VRP: 事件/短窗用vrp_ew, 常规用vrp_30
    vrp_sel = vrp_ew if vrp_ew else vrp_30
    
    # 计算期限结构斜率和曲率
    if iv_m1 and iv_m2:
        term_curv = (iv_m2 - iv_m1) - term_slope if term_slope else 0
    else:
        term_curv = 0
    
    # Skew不对称性
    skew_asym = put_skew_25 - call_skew_25 if put_skew_25 and call_skew_25 else 0
    
    # GEX Level (根据VOL TRIGGER判定)
    if spot and vol_trigger:
        if spot < vol_trigger:
            gex_level = 1  # 负Gamma区域，利于做多波动
        elif spot >= vol_trigger:
            gex_level = -1  # 正Gamma区域，波动受抑制
        else:
            gex_level = 0
    else:
        gex_level = 0
    
    # Pin风险
    gamma_wall_prox = core_fields.get('gamma_wall_prox', 1)
    pin_risk = -1 if (gamma_wall_prox <= 0.005 and gex_level < 0) else 0
    
    # RV动量
    rv_momo = (hv10 / hv60 - 1) if (hv10 and hv60 and hv60 > 0) else 0
    
    features = {
        'vrp_sel': round(vrp_sel, 4),
        'vrp_ew': round(vrp_ew, 4),
        'vrp_30': round(vrp_30, 4),
        'term_slope': round(term_slope, 4) if term_slope else 0,
        'term_curv': round(term_curv, 4),
        'skew_asym': round(skew_asym, 4),
        'gex_level': gex_level,
        'pin_risk': pin_risk,
        'vex_net': vex_net,
        'vanna_atm': vanna_atm,
        'rv_momo': round(rv_momo, 4),
        'spread_atm': spread_atm,
        'ask_premium_atm': ask_premium
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
            'status': 'success'
        }
        
        return CodeNodeResult(success=True, result=result)
        
    except Exception as e:
        return CodeNodeResult(
            success=False,
            result={'error': True, 'message': str(e)},
            error=str(e)
        )
