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
BACKTEST_DATA_DIR = "./Sili_Trader1.1m/forex_data"

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
    "EURUSDz",
    "GBPUSDz",
    "USDJPYz",
    "USDCADz",
    "USDCHFz",
    "EURGBPz",
    "EURJPYz",
    "GBPJPYz",
    "AUDJPYz",
    "NZDJPYz",
    "AUDCADz",
    "XAUUSDz",
]


BMA_CONFIG = {
    "instruments": "BTCUSDz",
    "monitor_tf": "M5",
}

# ================================
# CRT MULTI-TIMEFRAME CONFIG
# ================================
CRT_TIMEFRAMES = {
    "rdc_tf":          "H4",
    "manipulation_tf": "H1",
    "execution_tf":    "M15",
    "scalping_tf":     "M5",
}

# ================================
# LOOPBACK CANDLE CONFIG
# ================================
LOOPBACK_CANDLES = {
    "rdc_tf":          3,
    "manipulation_tf": 3,
    "execution_tf":    3,
    "scalping_tf":     3,
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

# ==============================================================================
# WARNING: Make sure you test the values  for min_threshold in a demo account and fine tune them 
# according to what works well for you before deploying live capital.
#Same applies to ATR_PERIOD
# ==============================================================================
# 
# REFERENCE SLOPE MINIMUM THRESHOLDS (ATR VOLATILITY FILTER)
# Use this matrix to select the appropriate baseline for your trading setup:
#
#   Timeframe  |  Min Slope Threshold (%)  |  Typical Strategy Style
#  ------------+---------------------------+----------------------------
#      M5      |           0.20%           |  Hyper-Scalping / Momentum
#      M15     |           0.15%           |  Scalping / Fast Intraday
#      H1      |           0.10%           |  Standard Day Trading
#      H4      |           0.05%           |  Swing Trading / Overnight
#
# ==============================================================================

# ==============================================================================
# STRATEGY CONFIGURATION AND ATR LOOKBACK WINDOW REFERENCE MATRIX
# ==============================================================================
"""
Use this structural guide to map the correct ATR settings inside your 
strategy parameter files based on your trading style:

+-----------------+-----------------------+------------------------+----------------------------------------------------+

| Trading Style   | Recommended Timeframe | Recommended ATR Period | Primary Strategy Use Case                          |
+-----------------+-----------------------+------------------------+----------------------------------------------------+

| Scalping        | M5 / M15              | 7 to 10                | Tightly tracking breakout and momentum speed.      |
| Day Trading     | M15 / H1              | 14                     | Placement of standard dynamic Stop Losses.         |
| Swing Trading   | H4 / D1               | 14 to 20               | Finding massive overarching market structural shifts|
| Range Detection | Any Timeframe         | 50 to 100              | Establishing baseline to verify if ATR is low.     |
+-----------------+-----------------------+------------------------+----------------------------------------------------+
"""


TREND_CONFIG = {
    "ATR_PERIOD": 10,
    "min_treshold_%": 0.09,
}

# ================================================
# WICK-TO-BODY RATIO REFERENCE TABLE
# ================================================
"""
Ratio (from config) | What it requires                          | Body as % of total candle range | Strength in your strategy
--------------------|-------------------------------------------|---------------------------------|----------------------------
0.5                 | Wick ≥ 50% of body size                   | ~67% (quite large body)         | Very easy to pass
1.0                 | Wick = body size                          | 50%                             | Moderate
2.0                 | Wick = 2× body size                       | 33%                             | Strong
3.0                 | Wick = 3× body size                       | 25%                             | Very strong
"""

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
    "recovery_trigger": 0.10,
    "max_drawdown":     0.15,
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
