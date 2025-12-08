"""
Edge 估算代码节点 (CODE4 / #7003)
使用蒙特卡洛模拟估算策略 Edge
"""
import math
import random
from typing import Dict, Any, List
from . import CodeNodeResult


def monte_carlo_edge_estimation(
    strategy: Dict[str, Any], 
    core_fields: Dict[str, Any],
    env_vars: Dict[str, Any]
) -> Dict[str, Any]:
    """
    蒙特卡洛模拟估算策略 Edge
    
    模拟路径生成使用 GBM（几何布朗运动），
    计算胜率、期望收益、盈亏比等指标。
    
    Args:
        strategy: 策略定义（含行权价）
        core_fields: 核心字段
        env_vars: 环境变量配置
        
    Returns:
        Edge 估算结果
    """
    n_simulations = int(env_vars.get('MONTE_CARLO_SIMULATIONS', 10000))
    
    spot = core_fields.get('spot', 100)
    iv_atm = core_fields.get('iv_event_w_atm', 0.25)
    
    # 获取策略参数
    dte_str = strategy.get('dte', '30天')
    dte_digits = ''.join(filter(str.isdigit, str(dte_str)))
    dte = int(dte_digits) if dte_digits else 30
    T = dte / 252  # 交易日
    
    # 模拟路径
    wins = 0
    total_pnl = 0
    pnls = []
    
    daily_vol = iv_atm / math.sqrt(252)
    
    for _ in range(n_simulations):
        # GBM 模拟
        price_path = spot
        for _ in range(dte):
            z = random.gauss(0, 1)
            price_path *= math.exp(-0.5 * daily_vol**2 + daily_vol * z)
        
        final_price = price_path
        
        # 计算策略 P&L
        pnl = 0
        for leg in strategy.get('legs', []):
            strike = leg.get('strike_calculated', spot)
            option_type = leg.get('type', 'call')
            action = leg.get('action', 'buy')
            quantity = leg.get('quantity', 1)
            
            # 期权内在价值
            if option_type == 'call':
                intrinsic = max(0, final_price - strike)
            else:
                intrinsic = max(0, strike - final_price)
            
            # 简化权利金估算 (BS 近似)
            premium = spot * iv_atm * math.sqrt(T) * 0.4
            
            if action == 'buy':
                leg_pnl = (intrinsic - premium) * quantity
            else:
                leg_pnl = (premium - intrinsic) * quantity
            
            pnl += leg_pnl
        
        pnls.append(pnl)
        total_pnl += pnl
        if pnl > 0:
            wins += 1
    
    # 统计结果
    win_rate = wins / n_simulations
    avg_pnl = total_pnl / n_simulations
    
    winning_pnls = [p for p in pnls if p > 0]
    losing_pnls = [p for p in pnls if p <= 0]
    
    avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
    avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
    
    # 盈亏比
    rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
    
    # 最大回撤（抽样计算）
    cumulative = 0
    peak = 0
    max_dd = 0
    for pnl in pnls[:1000]:
        cumulative += pnl
        peak = max(peak, cumulative)
        dd = peak - cumulative
        max_dd = max(max_dd, dd)
    
    # Edge 门槛检查
    ev_threshold = float(env_vars.get('EDGE_EV_THRESHOLD', 0))
    rr_threshold = float(env_vars.get('EDGE_RR_THRESHOLD', 1.5))
    
    meets_threshold = avg_pnl > ev_threshold and rr_ratio >= rr_threshold
    
    return {
        'win_rate': round(win_rate, 3),
        'ev': round(avg_pnl, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'rr_ratio': f"{round(rr_ratio, 2)}:1",
        'max_drawdown': round(max_dd, 2),
        'meets_threshold': meets_threshold,
        'simulations': n_simulations
    }


def code4_edge_estimation(
    strategies_json: Dict[str, Any], 
    core_fields_json: Dict[str, Any],
    env_vars: Dict[str, Any] = None
) -> CodeNodeResult:
    """
    CODE4 节点: Edge 估算（蒙特卡洛模拟）
    
    Args:
        strategies_json: 带行权价的策略列表
        core_fields_json: 核心字段数据
        env_vars: 环境变量配置
        
    Returns:
        CodeNodeResult 包含带 Edge 估算的策略
    """
    try:
        if env_vars is None:
            env_vars = {}
        
        # 兼容处理
        if isinstance(strategies_json, dict):
            strategies = strategies_json.get('strategies_with_strikes', 
                                            strategies_json.get('strategies', []))
            symbol = strategies_json.get('symbol', '')
            direction = strategies_json.get('direction', '')
        else:
            strategies = strategies_json
            symbol = ''
            direction = ''
        
        core_fields = core_fields_json.get('core_fields', core_fields_json)
        
        updated_strategies = []
        for strategy in strategies:
            edge = monte_carlo_edge_estimation(strategy, core_fields, env_vars)
            strategy_copy = strategy.copy()
            strategy_copy['edge_monte_carlo'] = edge
            updated_strategies.append(strategy_copy)
        
        result = {
            'symbol': symbol,
            'direction': direction,
            'strategies_with_edge': updated_strategies,
            'status': 'success'
        }
        
        return CodeNodeResult(success=True, result=result)
        
    except Exception as e:
        return CodeNodeResult(
            success=False,
            result={'error': True, 'message': str(e)},
            error=str(e)
        )
