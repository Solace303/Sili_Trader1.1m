"""Project configuration for Sili_Trader (MT5 Version)."""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# MT5 TERMINAL CONFIGURATION
# =============================================================================
MT5_PATH = "/home/solace/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe"

# =============================================================================
# MT5 ACCOUNT CONFIGURATION
# =============================================================================
MT5_ACCOUNT_ID = int(os.getenv("MT5_ACCOUNT_ID", 0))
MT5_PASSWORD   = os.getenv("MT5_PASSWORD")
MT5_SERVER     = os.getenv("MT5_SERVER")

# =============================================================================
# MT5 BRIDGE CONFIGURATION
# =============================================================================
MT5_HOST = "127.0.0.1"
MT5_PORT = 18812

# ================================
# ▶ MODE SWITCH ◀
# False → live trading via MT5
# True  → backtest replay from CSV
# ================================
BACKTEST_MODE = False

# ================================
# BACKTEST SETTINGS
# ================================
BACKTEST_DATA_DIR = "/run/media/solace/ABBA-2E35/My_Code/Sili_Trader/forex_data"

CHART_CANDLE_LIMIT = 120

# ================================
# MULTI-PAIR CONFIGURATION
# ================================
"""
IMPORTANT:
Broker symbols may differ.

Examples:
EURUSD
EURUSDm
EURUSD.a
EURUSD-pro

Update according to your broker.
"""

INSTRUMENTS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCAD",
    "USDCHF",
    "EURGBP",
    "EURJPY",
    "GBPJPY",
    "AUDJPY",
    "NZDJPY",
    "AUDCAD",
]

# ================================
# CRT MULTI-TIMEFRAME CONFIG
# ================================
CRT_TIMEFRAMES = {
    "rdc_tf":          "H4",
    "manipulation_tf": "H1",
    "execution_tf":    "M15",
}

# ================================
# LOOPBACK CANDLE CONFIG
# ================================
LOOPBACK_CANDLES = {
    "rdc_tf":          3,
    "manipulation_tf": 3,
    "execution_tf":    3,
    "test_tf":         500,
}

# ================================
# BACKTEST LOOP SPEED CONFIG
# ================================
# H4:H1:M15 = 4:1:0.25
BACKTEST_TIMEFRAME_RELATIVITY_SECONDS = {
    "H4":  16,
    "H1":  4,
    "M15": 1,
    "15M": 1,
}

# ================================
# TREND DETECTION SETTINGS
# ================================
TREND_CONFIG = {
    "reference_timeframe":   "4h",
    "threshold_mode":        "volatility",
    "volatility_multiplier": 2.0,
    "volatility_window":     50,
    "minimum_threshold":     0.0001,
}

# ================================================
# WICK REJECTION CONFIGURATION
# ================================================
WICK_REJECTION_CONFIG = {
    "lower_wick_to_body_threshold": 3.0,
    "upper_wick_to_body_threshold": 3.0,
}

# ================================
# RISK MANAGEMENT CONFIG
# ================================
RISK_CONFIG = {
    "risk_per_trade": 0.01,
    "min_risk":       0.005,
    "recovery_trigger": 0.25,
}

# =============================================================================
# MT5 LOT SIZE CONFIGURATION
# =============================================================================
"""
MT5 uses LOTS instead of UNITS.

1.00 = standard lot
0.10 = mini lot
0.01 = micro lot
0.001 = nano lot
"""

LOT_SIZE_CONFIG = {
    "standard": 1.0,
    "mini":     0.1,
    "micro":    0.01,
    "nano":     0.001,
}

# =============================================================================
# MT5 TIMEFRAME MAPPING
# =============================================================================
"""
Used later in data.py for copy_rates_from_pos()
"""

MT5_TIMEFRAME_MAP = {
    "M1":  "TIMEFRAME_M1",
    "M5":  "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1":  "TIMEFRAME_H1",
    "H4":  "TIMEFRAME_H4",
    "D1":  "TIMEFRAME_D1",
}