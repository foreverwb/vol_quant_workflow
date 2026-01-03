"""
蒙特卡洛模拟模块
用于策略 Edge 估计
"""
import numpy as np
from typing import Tuple, Dict, Optional
from dataclasses import dataclass

from core.types import Strategy, EdgeMetrics, OptionLeg
from core.constants import MONTE_CARLO_CONFIG


@dataclass
class SimulationResult:
    """模拟结果"""
    paths: np.ndarray
    final_prices: np.ndarray
    pnl_distribution: np.ndarray
    statistics: Dict[str, float]


class GBMSimulator:
    """几何布朗运动模拟器"""
    
    def __init__(
        self,
        spot: float,
        iv: float,
        rf_rate: float = 0.05,
        n_simulations: int = None,
        random_seed: int = None
    ):
        self.spot = spot
        self.iv = iv
        self.rf_rate = rf_rate
        self.n_simulations = n_simulations or MONTE_CARLO_CONFIG["n_simulations"]
        
        if random_seed is not None:
            np.random.seed(random_seed)
    
    def simulate_paths(
        self,
        days: int,
        dt: float = 1/252
    ) -> np.ndarray:
        """
        模拟价格路径
        
        Args:
            days: 模拟天数
            dt: 时间步长 (年化)
            
        Returns:
            shape (n_simulations, days+1) 的价格矩阵
        """
        n_steps = days
        
        # 生成随机数
        z = np.random.standard_normal((self.n_simulations, n_steps))
        
        # GBM 公式
        drift = (self.rf_rate - 0.5 * self.iv ** 2) * dt
        diffusion = self.iv * np.sqrt(dt) * z
        
        # 累积收益率
        log_returns = drift + diffusion
        cumulative = np.cumsum(log_returns, axis=1)
        
        # 价格路径
        paths = np.zeros((self.n_simulations, n_steps + 1))
        paths[:, 0] = self.spot
        paths[:, 1:] = self.spot * np.exp(cumulative)
        
        return paths
    
    def simulate_terminal_prices(self, days: int) -> np.ndarray:
        """只模拟终端价格"""
        T = days / 252
        z = np.random.standard_normal(self.n_simulations)
        
        drift = (self.rf_rate - 0.5 * self.iv ** 2) * T
        diffusion = self.iv * np.sqrt(T) * z
        
        return self.spot * np.exp(drift + diffusion)


def calculate_option_payoff(
    final_prices: np.ndarray,
    leg: OptionLeg,
    premium: float = 0
) -> np.ndarray:
    """
    计算单腿期权收益
    
    Args:
        final_prices: 终端价格数组
        leg: 期权腿
        premium: 期权费
        
    Returns:
        收益数组
    """
    strike = leg.strike
    
    if leg.option_type == "call":
        intrinsic = np.maximum(final_prices - strike, 0)
    else:  # put
        intrinsic = np.maximum(strike - final_prices, 0)
    
    # 买方: 收益 - 权利金
    # 卖方: 权利金 - 收益
    if leg.action == "buy":
        pnl = intrinsic - premium
    else:  # sell
        pnl = premium - intrinsic
    
    return pnl * leg.quantity


def simulate_strategy_pnl(
    strategy: Strategy,
    spot: float,
    iv: float,
    days: int = 30,
    n_simulations: int = None
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    模拟策略 PnL 分布
    
    Returns:
        (pnl_distribution, statistics)
    """
    simulator = GBMSimulator(
        spot=spot,
        iv=iv,
        n_simulations=n_simulations or MONTE_CARLO_CONFIG["n_simulations"],
        random_seed=MONTE_CARLO_CONFIG.get("random_seed")
    )
    
    final_prices = simulator.simulate_terminal_prices(days)
    
    # 计算总 PnL
    total_pnl = np.zeros(len(final_prices))
    
    for leg in strategy.legs:
        # 估算权利金 (简化)
        premium = estimate_option_premium(spot, leg.strike, iv, days, leg.option_type)
        leg_pnl = calculate_option_payoff(final_prices, leg, premium)
        total_pnl += leg_pnl
    
    # 统计
    statistics = {
        "mean": float(np.mean(total_pnl)),
        "std": float(np.std(total_pnl)),
        "median": float(np.median(total_pnl)),
        "min": float(np.min(total_pnl)),
        "max": float(np.max(total_pnl)),
        "percentile_5": float(np.percentile(total_pnl, 5)),
        "percentile_95": float(np.percentile(total_pnl, 95)),
        "win_rate": float(np.mean(total_pnl > 0)),
        "avg_win": float(np.mean(total_pnl[total_pnl > 0])) if np.any(total_pnl > 0) else 0,
        "avg_loss": float(np.mean(total_pnl[total_pnl < 0])) if np.any(total_pnl < 0) else 0,
    }
    
    return total_pnl, statistics


def estimate_option_premium(
    spot: float,
    strike: float,
    iv: float,
    days: int,
    option_type: str
) -> float:
    """
    估算期权费 (Black-Scholes 简化)
    """
    from scipy.stats import norm
    
    T = days / 252
    if T <= 0:
        return 0
    
    rf = 0.05
    
    d1 = (np.log(spot / strike) + (rf + 0.5 * iv ** 2) * T) / (iv * np.sqrt(T))
    d2 = d1 - iv * np.sqrt(T)
    
    if option_type == "call":
        price = spot * norm.cdf(d1) - strike * np.exp(-rf * T) * norm.cdf(d2)
    else:
        price = strike * np.exp(-rf * T) * norm.cdf(-d2) - spot * norm.cdf(-d1)
    
    return max(price, 0)


def calculate_edge_metrics(
    pnl_distribution: np.ndarray,
    statistics: Dict[str, float],
    max_loss_threshold: float = None
) -> EdgeMetrics:
    """
    计算 Edge 指标
    """
    win_rate = statistics["win_rate"]
    avg_win = statistics["avg_win"]
    avg_loss = abs(statistics["avg_loss"]) if statistics["avg_loss"] != 0 else 1
    
    # 盈亏比
    reward_risk = avg_win / avg_loss if avg_loss > 0 else 0
    
    # 期望值
    ev = statistics["mean"]
    
    # 最大回撤 (近似)
    max_drawdown = abs(statistics["percentile_5"])
    
    # Sharpe ratio (简化)
    sharpe = ev / statistics["std"] if statistics["std"] > 0 else 0
    
    # 是否盈利
    is_profitable = ev > 0 and win_rate > 0.4
    
    # 置信区间
    n = len(pnl_distribution)
    se = statistics["std"] / np.sqrt(n)
    ci = (ev - 1.96 * se, ev + 1.96 * se)
    
    return EdgeMetrics(
        win_rate=round(win_rate, 4),
        avg_win=round(avg_win, 2),
        avg_loss=round(avg_loss, 2),
        expected_value=round(ev, 2),
        reward_risk=round(reward_risk, 2),
        max_drawdown=round(max_drawdown, 2),
        sharpe_ratio=round(sharpe, 2),
        is_profitable=is_profitable,
        confidence_interval=ci,
    )
