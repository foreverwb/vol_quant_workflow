"""
行权价计算代码节点 (CODE3 / #7002)
根据策略描述计算具体行权价
"""
import re
from typing import Dict, Any, List
from . import CodeNodeResult, find_strike_by_delta


def calculate_strikes_from_strategy(
    strategy: Dict[str, Any], 
    core_fields: Dict[str, Any], 
    env_vars: Dict[str, Any]
) -> Dict[str, Any]:
    """
    为单个策略计算所有行权价
    
    支持的计算方法：
    1. Delta 法：根据目标 Delta 反推行权价
    2. 壁垒法：基于 Gamma Wall/Call Wall/Put Wall
    3. ATR 法：基于 ATR 计算距离
    4. 百分比法：基于现价的百分比偏移
    
    Args:
        strategy: 策略定义
        core_fields: 核心字段（含 spot, walls, iv 等）
        env_vars: 环境变量配置
        
    Returns:
        更新后的策略（含计算后的行权价）
    """
    spot = core_fields.get('spot', 0)
    gamma_wall = core_fields.get('gamma_wall', spot)
    call_wall = core_fields.get('call_wall', spot * 1.05)
    put_wall = core_fields.get('put_wall', spot * 0.95)
    iv_atm = core_fields.get('iv_event_w_atm', 0.25)
    
    # 解析 DTE
    dte_str = strategy.get('dte', '30天')
    dte_digits = ''.join(filter(str.isdigit, str(dte_str)))
    dte = int(dte_digits) if dte_digits else 30
    T = dte / 365
    r = float(env_vars.get('RISK_FREE_RATE', 0.05))
    
    # 从环境变量获取阈值
    gamma_wall_prox = float(env_vars.get('GAMMA_WALL_PROX_THRESHOLD', 0.5)) / 100
    
    updated_legs = []
    
    for leg in strategy.get('legs', []):
        leg_copy = leg.copy()
        action = leg.get('action', '')
        option_type = leg.get('type', '')
        delta_str = str(leg.get('delta', ''))
        strike_desc = str(leg.get('strike', ''))
        
        strike_calculated = None
        method_used = None
        
        # 方法1: Delta 法
        if 'Δ' in delta_str or 'delta' in delta_str.lower():
            try:
                target_delta = float(delta_str.replace('Δ', '').replace('delta', '').strip())
                if option_type == 'put' and target_delta > 0:
                    target_delta = -target_delta
                
                strike_calculated = find_strike_by_delta(
                    spot, target_delta, T, r, iv_atm, option_type
                )
                method_used = 'delta_method'
            except:
                pass
        
        # 方法2: 壁垒法
        if strike_calculated is None and ('wall' in strike_desc.lower() or '壁垒' in strike_desc):
            if 'gamma' in strike_desc.lower():
                if action == 'sell':
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
        
        # 方法3: ATR 法
        if strike_calculated is None and 'atr' in strike_desc.lower():
            atr = spot * 0.02  # 假设 ATR 为现价的 2%
            multiplier = 1.5
            
            if option_type == 'call':
                strike_calculated = round(spot + atr * multiplier, 2)
            else:
                strike_calculated = round(spot - atr * multiplier, 2)
            method_used = 'atr_method'
        
        # 方法4: 百分比法
        if strike_calculated is None:
            pct_match = re.search(r'([+-]?\d+\.?\d*)%', strike_desc)
            if pct_match:
                pct = float(pct_match.group(1)) / 100
                strike_calculated = round(spot * (1 + pct), 2)
                method_used = 'percentage_method'
        
        # 兜底: 使用 ATM
        if strike_calculated is None:
            strike_calculated = round(spot, 2)
            method_used = 'atm_fallback'
        
        leg_copy['strike_calculated'] = strike_calculated
        leg_copy['calculation_method'] = method_used
        updated_legs.append(leg_copy)
    
    strategy_copy = strategy.copy()
    strategy_copy['legs'] = updated_legs
    return strategy_copy


def code3_strike_calculation(
    strategies_json: Dict[str, Any], 
    core_fields_json: Dict[str, Any],
    env_vars: Dict[str, Any] = None
) -> CodeNodeResult:
    """
    CODE3 节点: 行权价计算
    
    Args:
        strategies_json: StrategyMapper 节点的输出
        core_fields_json: 核心字段数据
        env_vars: 环境变量配置
        
    Returns:
        CodeNodeResult 包含带行权价的策略
    """
    try:
        if env_vars is None:
            env_vars = {}
        
        # 兼容处理
        if isinstance(strategies_json, dict):
            strategies = strategies_json.get('strategies', [])
            symbol = strategies_json.get('symbol', '')
            direction = strategies_json.get('direction', '')
        else:
            strategies = strategies_json
            symbol = ''
            direction = ''
        
        core_fields = core_fields_json.get('core_fields', core_fields_json)
        
        updated_strategies = []
        for strategy in strategies:
            updated_strategy = calculate_strikes_from_strategy(strategy, core_fields, env_vars)
            updated_strategies.append(updated_strategy)
        
        result = {
            'symbol': symbol,
            'direction': direction,
            'strategies_with_strikes': updated_strategies,
            'status': 'success'
        }
        
        return CodeNodeResult(success=True, result=result)
        
    except Exception as e:
        return CodeNodeResult(
            success=False,
            result={'error': True, 'message': str(e)},
            error=str(e)
        )
