"""
常量定义模块
包含所有配置常量、默认值、阈值
支持从 .env 文件覆盖默认值
"""
import os
from typing import Dict, List, Tuple
from pathlib import Path

# =============================================================================
# 环境变量加载
# =============================================================================

def _load_env():
    """加载 .env 文件"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

_load_env()

def _get_float(key: str, default: float) -> float:
    """从环境变量获取 float"""
    return float(os.environ.get(key, default))

def _get_int(key: str, default: int) -> int:
    """从环境变量获取 int"""
    return int(os.environ.get(key, default))

def _get_str(key: str, default: str) -> str:
    """从环境变量获取 str"""
    return os.environ.get(key, default)

# =============================================================================
# 评分权重
# =============================================================================

WEIGHTS_LONG_VOL: Dict[str, float] = {
    "vrp": _get_float("WEIGHT_VRP_LONG", 0.25),
    "gex": _get_float("WEIGHT_GEX_LONG", 0.18),
    "vex": _get_float("WEIGHT_VEX_LONG", 0.18),
    "carry": _get_float("WEIGHT_CARRY_LONG", 0.08),
    "skew": _get_float("WEIGHT_SKEW_LONG", 0.08),
    "vanna": 0.05,
    "rv": 0.06,
    "liq": 0.10,
    "vov": 0.07,
    "vix_ts": 0.05,
    "rim": 0.05,
    "compress": 0.05,
    "eir": 0.04,
}

WEIGHTS_SHORT_VOL: Dict[str, float] = {
    "vrp": _get_float("WEIGHT_VRP_SHORT", 0.30),
    "gex": _get_float("WEIGHT_GEX_SHORT", 0.12),
    "vex": 0.12,
    "carry": _get_float("WEIGHT_CARRY_SHORT", 0.18),
    "skew": 0.08,
    "rv": 0.05,
    "liq": 0.10,
    "vov": 0.07,
    "vix_ts": 0.05,
    "rim": 0.05,
    "compress": 0.05,
    "eir": 0.06,
    "corr_idx": 0.05,
    "flow_putcrowd": 0.04,
}

# =============================================================================
# 决策阈值
# =============================================================================

DECISION_THRESHOLDS = {
    "long_vol": {
        "score_min": _get_float("DECISION_THRESHOLD_LONG", 1.0),
        "score_preferred": 1.5,
        "counter_max": 0.30,
        "prob_min": _get_float("PROB_THRESHOLD", 0.55),
        "prob_preferred": 0.60,
    },
    "short_vol": {
        "score_min": _get_float("DECISION_THRESHOLD_SHORT", 1.0),
        "score_preferred": 1.5,
        "counter_max": 0.30,
        "prob_min": _get_float("PROB_THRESHOLD", 0.55),
        "prob_preferred": 0.60,
    },
}

# =============================================================================
# 概率门槛 (按 L/S 分数等级)
# =============================================================================

PROB_THRESHOLDS = {
    "L1_0": _get_float("PROB_LONG_L1_0", 0.55),  # L >= 1.0
    "L1_5": _get_float("PROB_LONG_L1_5", 0.60),  # L >= 1.5
    "L2_0": _get_float("PROB_LONG_L2_0", 0.65),  # L >= 2.0
}

# =============================================================================
# Edge 阈值
# =============================================================================

EDGE_THRESHOLDS = {
    "min_reward_risk": _get_float("EDGE_RR_THRESHOLD", 1.5),
    "target_reward_risk": 2.0,
    "min_win_rate": 0.40,
    "max_loss_pct": 0.02,
    "min_ev": _get_float("EDGE_EV_THRESHOLD", 0),
    "min_ev_positive": True,
}

# =============================================================================
# GEX 配置
# =============================================================================

GEX_CONFIG = {
    "vol_trigger_neutral_pct": _get_float("TRIGGER_NEUTRAL_PCT", 0.002),  # ±0.2% 视为中性
    "gamma_wall_pin_pct": _get_float("GAMMA_WALL_PROX_THRESHOLD", 0.005),  # 0.5% 内视为 pin risk
    "near_wall_pct": 0.01,  # 1% 内视为接近
}

# =============================================================================
# VRP 配置
# =============================================================================

VRP_CONFIG = {
    "long_bias_threshold": -3.0,  # VRP < -3% → long bias
    "short_bias_threshold": 3.0,  # VRP > 3% → short bias
}

# =============================================================================
# 期限结构配置
# =============================================================================

TERM_STRUCTURE_CONFIG = {
    "backwardation_threshold": 2.0,  # slope > 2% → backwardation
    "contango_threshold": -2.0,  # slope < -2% → contango
}

# =============================================================================
# RV 配置
# =============================================================================

RV_CONFIG = {
    "annualization_factor": 252,
    "method": "yang_zhang",  # yang_zhang, close_to_close, parkinson
    "windows": [10, 20, 60],
}

# =============================================================================
# RIM 配置 (Realized Intraday Momentum)
# =============================================================================

RIM_CONFIG = {
    "active_threshold": _get_float("RIM_ACTIVE_THRESHOLD", 0.6),  # RIM >= 0.6 视为盘中动能有效
    "weak_threshold": _get_float("RIM_WEAK_THRESHOLD", 0.4),      # RIM <= 0.4 偏弱
}

# =============================================================================
# 蒙特卡洛配置
# =============================================================================

MONTE_CARLO_CONFIG = {
    "n_simulations": _get_int("MONTE_CARLO_SIMULATIONS", 10000),
    "confidence_level": 0.95,
    "random_seed": 42,
    "default_risk_free_rate": _get_float("RISK_FREE_RATE", 0.05),
}

# =============================================================================
# 策略配置
# =============================================================================

STRATEGY_CONFIG = {
    "dte_ranges": {
        "event": (5, 20),
        "non_event": (30, 45),
        "long_cycle": (45, 90),
    },
    "delta_targets": {
        "atm": 0.50,
        "otm_aggressive": 0.35,
        "otm_conservative": 0.20,
        "wing": 0.10,
    },
    "spread_widths": {
        "narrow": 5,
        "standard": 10,
        "wide": 15,
    },
}

# =============================================================================
# 日志配置
# =============================================================================

LOG_CONFIG = {
    "level": _get_str("LOG_LEVEL", "INFO"),
    "file": _get_str("LOG_FILE", "vol_quant.log"),
}

# =============================================================================
# 字段校验范围
# =============================================================================

FIELD_RANGES: Dict[str, Tuple[float, float]] = {
    "SPOT_PRICE": (0.01, 100000),
    "VOL_TRIGGER": (0.01, 100000),
    "GAMMA_WALL": (0.01, 100000),
    "CALL_WALL": (0.01, 100000),
    "PUT_WALL": (0.01, 100000),
    "IV_ATM": (1, 500),
    "IV_FRONT": (1, 500),
    "IV_BACK": (1, 500),
    "IV_EVENT_W": (1, 500),
    "HV10": (1, 500),
    "HV20": (1, 500),
    "HV60": (1, 500),
    "PUT_SKEW_25": (-50, 50),
    "CALL_SKEW_25": (-50, 50),
    "VEX_NET": (-10, 10),
    "VANNA_ATM": (-1, 1),
    "SPREAD_ATM": (0, 50),
    "PCR_RATIO": (0.1, 10),
    "VVIX": (5, 100),
    "VIX9D": (5, 100),
    "VIX": (5, 100),
}

# =============================================================================
# 必填字段
# =============================================================================

REQUIRED_FIELDS = {
    "critical": [
        "SPOT_PRICE",
        "VOL_TRIGGER",
        "GAMMA_WALL",
        "IV_ATM",
        "HV20",
    ],
    "high": [
        "CALL_WALL",
        "PUT_WALL",
        "IV_FRONT",
        "IV_BACK",
        "VEX_NET",
        "HV10",
        "HV60",
    ],
    "optional": [
        "GAMMA_WALL_2",
        "MAX_PAIN",
        "VANNA_ATM",
        "PUT_SKEW_25",
        "CALL_SKEW_25",
        "SPREAD_ATM",
        "PCR_RATIO",
        "VVIX",
        "VIX9D",
        "VIX",
    ],
}

# =============================================================================
# gexbot 命令模板
# =============================================================================

GEXBOT_COMMANDS = {
    "standard": [
        "!trigger {symbol} 98",
        "!gexr {symbol} 15 98",
        "!vexn {symbol} 15 190 *",
        "!surface {symbol} ivmid 98",
        "!surface {symbol} ivask ntm 98",
        "!surface {symbol} spread atm 98",
        "!skew {symbol} ivmid atm 30",
    ],
    "minimal": [
        "!trigger {symbol} 98",
        "!gexr {symbol} 15 98",
        "!surface {symbol} ivmid 98",
    ],
    "diagnostic": [
        "!trigger {symbol} 98",
        "!gexr {symbol} 15 98",
        "!gexn {symbol}",
        "!vexn {symbol} 15 190 *",
        "!vanna {symbol}",
        "!surface {symbol} ivmid 98",
        "!surface {symbol} ivask ntm 98",
        "!surface {symbol} spread atm 98",
        "!skew {symbol} ivmid atm 30",
        "!pcr {symbol}",
    ],
    "event": [
        "!surface {symbol} extrinsic ntm 45 w",
        "!surface {symbol} theta atm 21 w",
    ],
}

# =============================================================================
# 冷启动概率校准
# =============================================================================

SCORE_TO_PROB_MAP: List[Tuple[float, float]] = [
    (0.0, 0.50),
    (0.5, 0.52),
    (1.0, PROB_THRESHOLDS["L1_0"]),
    (1.5, PROB_THRESHOLDS["L1_5"]),
    (2.0, PROB_THRESHOLDS["L2_0"]),
    (2.5, 0.70),
    (3.0, 0.75),
]

# =============================================================================
# 流动性评分配置
# =============================================================================

LIQUIDITY_CONFIG = {
    "spread_excellent": 0.02,  # < 2%
    "spread_good": 0.05,  # < 5%
    "spread_poor": 0.10,  # > 10%
    "spread_weight": 0.6,
    "volume_weight": 0.4,
}

# =============================================================================
# 输出文件模式
# =============================================================================

FILE_PATTERNS = {
    "data_template": "{symbol}.json",
    "commands": "{symbol}_commands_{date}.json",
    "validated": "{symbol}_validated_{date}.json",
    "features": "{symbol}_features_{date}.json",
    "scores": "{symbol}_scores_{date}.json",
    "decision": "{symbol}_decision_{date}.json",
    "strategy": "{symbol}_strategy_{date}.json",
    "edge": "{symbol}_edge_{date}.json",
    "report_json": "{symbol}_report_{date}.json",
    "report_txt": "{symbol}_report_{date}.txt",
    "dashboard": "dashboard_{date}_{symbol}.html",
}
