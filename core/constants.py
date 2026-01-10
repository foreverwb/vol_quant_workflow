"""
Core constants derived from strategy specification.
All threshold values, weights, and decision boundaries.
"""

from enum import Enum
from typing import Final

# =============================================================================
# DECISION BOUNDARIES
# =============================================================================

class Decision(str, Enum):
    """Three-class decision output."""
    LONG_VOL = "LONG_VOL"
    SHORT_VOL = "SHORT_VOL"
    STAND_ASIDE = "STAND_ASIDE"


class StrategyTier(str, Enum):
    """Strategy aggressiveness tier."""
    AGGRESSIVE = "aggressive"      # Target RR >= 2:1
    BALANCED = "balanced"          # Target RR 1.2-1.8:1
    CONSERVATIVE = "conservative"  # Target RR 0.8-1.2:1


class RegimeState(str, Enum):
    """Market regime based on VOL TRIGGER."""
    POSITIVE_GAMMA = "positive_gamma"  # Spot >= VOL_TRIGGER, vol suppression
    NEGATIVE_GAMMA = "negative_gamma"  # Spot < VOL_TRIGGER, vol amplification
    NEUTRAL = "neutral"                # Within 0.2% of trigger, flip-prone


# =============================================================================
# SCORING THRESHOLDS
# =============================================================================

# Long Vol Decision Thresholds
LONG_VOL_SCORE_MIN: Final[float] = 1.00
LONG_VOL_SCORE_PREFERRED: Final[float] = 1.50
LONG_VOL_PROB_MIN: Final[float] = 0.55
LONG_VOL_PROB_PREFERRED: Final[float] = 0.60
LONG_VOL_OPPOSING_MAX: Final[float] = 0.30

# Short Vol Decision Thresholds  
SHORT_VOL_SCORE_MIN: Final[float] = 1.00
SHORT_VOL_SCORE_PREFERRED: Final[float] = 1.50
SHORT_VOL_PROB_MIN: Final[float] = 0.55
SHORT_VOL_PROB_PREFERRED: Final[float] = 0.60
SHORT_VOL_OPPOSING_MAX: Final[float] = 0.30

# Conservative threshold (requires higher probability)
CONSERVATIVE_PROB_MIN: Final[float] = 0.70


# =============================================================================
# EDGE / EV THRESHOLDS
# =============================================================================

# Minimum Edge requirements (hard gates)
EV_MIN_THRESHOLD: Final[float] = 0.0  # EV must be > 0
RR_MIN_THRESHOLD: Final[float] = 1.50  # Minimum reward:risk ratio
RR_TARGET_AGGRESSIVE: Final[float] = 2.00
RR_TARGET_BALANCED_MIN: Final[float] = 1.20
RR_TARGET_BALANCED_MAX: Final[float] = 1.80
RR_TARGET_CONSERVATIVE_MIN: Final[float] = 0.80
RR_TARGET_CONSERVATIVE_MAX: Final[float] = 1.20

# Liquidity gates
LIQUIDITY_SPREAD_PERCENTILE_MAX: Final[int] = 80
LIQUIDITY_IVASK_PERCENTILE_MAX: Final[int] = 80


# =============================================================================
# REGIME DETECTION (VOL TRIGGER)
# =============================================================================

# VOL TRIGGER proximity threshold for neutral regime
VOL_TRIGGER_NEUTRAL_PCT: Final[float] = 0.002  # 0.2%

# Gamma Wall proximity for pin detection
GAMMA_WALL_PIN_PCT: Final[float] = 0.005  # 0.5%
GAMMA_WALL_CREDIT_ANCHOR_PCT: Final[float] = 0.01  # 1.0%


# =============================================================================
# RIM (REALIZED/IMPLIED MOVE) THRESHOLDS
# =============================================================================

RIM_HIGH_THRESHOLD: Final[float] = 0.60  # Intraday momentum effective
RIM_LOW_THRESHOLD: Final[float] = 0.40   # Weak momentum, favor short vol


# =============================================================================
# SCORING WEIGHTS - LONG VOL
# =============================================================================

WEIGHT_LONG_VRP: Final[float] = 0.25
WEIGHT_LONG_GEX: Final[float] = 0.18
WEIGHT_LONG_VEX: Final[float] = 0.18
WEIGHT_LONG_CARRY: Final[float] = 0.08
WEIGHT_LONG_SKEW: Final[float] = 0.08
WEIGHT_LONG_VANNA: Final[float] = 0.05
WEIGHT_LONG_RV: Final[float] = 0.06
WEIGHT_LONG_LIQ: Final[float] = 0.10
WEIGHT_LONG_VOV: Final[float] = 0.07
WEIGHT_LONG_VIX_TS: Final[float] = 0.05
WEIGHT_LONG_RIM: Final[float] = 0.05
WEIGHT_LONG_COMPRESS: Final[float] = 0.05
WEIGHT_LONG_EIR: Final[float] = 0.04

# Single stock adjustment
SINGLE_STOCK_GEX_BOOST: Final[float] = 0.05
SINGLE_STOCK_VEX_BOOST: Final[float] = 0.05
SINGLE_STOCK_SKEW_BOOST: Final[float] = 0.05


# =============================================================================
# SCORING WEIGHTS - SHORT VOL
# =============================================================================

WEIGHT_SHORT_VRP: Final[float] = 0.30
WEIGHT_SHORT_GEX: Final[float] = 0.12
WEIGHT_SHORT_VEX: Final[float] = 0.12
WEIGHT_SHORT_CARRY: Final[float] = 0.18
WEIGHT_SHORT_SKEW: Final[float] = 0.08
WEIGHT_SHORT_RV: Final[float] = 0.05
WEIGHT_SHORT_LIQ: Final[float] = 0.10
WEIGHT_SHORT_VOV: Final[float] = 0.07
WEIGHT_SHORT_VIX_TS: Final[float] = 0.05
WEIGHT_SHORT_RIM: Final[float] = 0.05
WEIGHT_SHORT_COMPRESS: Final[float] = 0.05
WEIGHT_SHORT_EIR: Final[float] = 0.06
WEIGHT_SHORT_CORR_IDX: Final[float] = 0.05
WEIGHT_SHORT_FLOW_PUTCROWD: Final[float] = 0.04


# =============================================================================
# COLD START PROBABILITY PRIORS
# =============================================================================

# L score to probability mapping (cold start)
COLD_START_PROB_L_1_0: Final[tuple] = (0.55, 0.60)  # L >= 1.0
COLD_START_PROB_L_1_5: Final[tuple] = (0.60, 0.65)  # L >= 1.5
COLD_START_PROB_L_2_0: Final[tuple] = (0.65, 0.70)  # L >= 2.0

# S score to probability mapping (symmetric to L)
COLD_START_PROB_S_1_0: Final[tuple] = (0.55, 0.60)
COLD_START_PROB_S_1_5: Final[tuple] = (0.60, 0.65)
COLD_START_PROB_S_2_0: Final[tuple] = (0.65, 0.70)


# =============================================================================
# HV WINDOW MATCHING
# =============================================================================

# DTE to HV window mapping
HV_WINDOW_EVENT: Final[int] = 10      # Event week / 5-20 DTE
HV_WINDOW_FRONT_MONTH: Final[int] = 20  # Near month
HV_WINDOW_BACK_MONTH: Final[int] = 60   # Next near month


# =============================================================================
# DTE RANGES BY STRATEGY
# =============================================================================

# Long straddle/strangle
DTE_LONG_VOL_EVENT_MIN: Final[int] = 5
DTE_LONG_VOL_EVENT_MAX: Final[int] = 20
DTE_LONG_VOL_NON_EVENT_MIN: Final[int] = 30
DTE_LONG_VOL_NON_EVENT_MAX: Final[int] = 45

# Short vol (iron condor, credit spreads)
DTE_SHORT_VOL_MIN: Final[int] = 14
DTE_SHORT_VOL_MAX: Final[int] = 45

# Calendars / diagonals
DTE_CALENDAR_NEAR_MIN: Final[int] = 7
DTE_CALENDAR_NEAR_MAX: Final[int] = 21
DTE_CALENDAR_FAR_MIN: Final[int] = 30
DTE_CALENDAR_FAR_MAX: Final[int] = 60


# =============================================================================
# DELTA TARGETS BY STRATEGY
# =============================================================================

# Long vol deltas
DELTA_STRADDLE_ATM: Final[float] = 0.50
DELTA_STRANGLE_WING: Final[tuple] = (0.30, 0.35)

# Short vol deltas (credit spreads / iron condor)
DELTA_SHORT_SELL: Final[tuple] = (0.10, 0.20)
DELTA_SHORT_PROTECT: Final[tuple] = (0.03, 0.05)

# Debit spread deltas
DELTA_DEBIT_BUY: Final[tuple] = (0.30, 0.35)
DELTA_DEBIT_SELL: Final[tuple] = (0.15, 0.20)


# =============================================================================
# GEXBOT COMMAND DEFAULTS
# =============================================================================

DEFAULT_STRIKES: Final[int] = 15
DEFAULT_DTE_GEX: Final[int] = 98
DEFAULT_DTE_VEX: Final[int] = 190
DEFAULT_DTE_TERM: Final[int] = 365
DEFAULT_DTE_SKEW: Final[int] = 30
DEFAULT_DTE_TRIGGER: Final[int] = 98
DEFAULT_DTE_VANNA_ATM: Final[int] = 190
DEFAULT_DTE_VANNA_NTM: Final[int] = 90
DEFAULT_DTE_EXTRINSIC_NTM: Final[int] = 45
DEFAULT_DTE_THETA_ATM: Final[int] = 21
DEFAULT_DTE_GAMMA_SURFACE: Final[int] = 30
DEFAULT_DTE_VEGA_SURFACE: Final[int] = 60
EXPIRATION_FILTER_WEEKLY: Final[str] = "w"
EXPIRATION_FILTER_MONTHLY: Final[str] = "m"
EXPIRATION_FILTER_ALL: Final[str] = "*"


# =============================================================================
# SESSION CONSTRAINTS
# =============================================================================

US_RTH_START_ET: Final[str] = "09:30"
US_RTH_END_ET: Final[str] = "16:00"
EXCLUDE_0DTE: Final[bool] = True
ANNUALIZATION_FACTOR: Final[int] = 252
TRADING_MINUTES_PER_DAY: Final[int] = 390
