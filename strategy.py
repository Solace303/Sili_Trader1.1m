"""
Strategy utilities for Sili_Trader.

MT5 VERSION

This module is broker-agnostic and works with:
- MT5
- CSV backtesting
- Any pandas OHLCV dataframe source

No OANDA-specific dependencies remain.
"""

import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
from helpers import Utils
from config import TREND_CONFIG
from config import (
    LOOPBACK_CANDLES,
    TREND_CONFIG,
    WICK_REJECTION_CONFIG
)

from user_indicators.sam_market_structure import compute


# =============================================================================
# CRT / RDC DETECTION
# =============================================================================
def find_rdc(df: pd.DataFrame, pair: str, timeframe_key: str):

    """
    Detect CRT/RDC candle pair pattern.
    """

    try:
        loopback = LOOPBACK_CANDLES[timeframe_key]

    except KeyError:

        logging.error(
            f"Timeframe key '{timeframe_key}' not found."
        )

        return False

    logging.info(
        f"Analyzing {pair} on {timeframe_key} "
        f"with loopback={loopback}"
    )

    if len(df) < loopback + 1:

        logging.warning(
            f"Not enough candles for analysis "
            f"(need {loopback + 1}, got {len(df)})"
        )

        return False

    recent_candles = df.iloc[-(loopback + 1):]

    for i in range(1, len(recent_candles)):

        preceding_candle = recent_candles.iloc[i - 1]
        proceding_candle = recent_candles.iloc[i]

        body = proceding_candle["body_size"]

        # ---------------------------------------------------------------------
        # SAFE DIVISION
        # ---------------------------------------------------------------------
        if body > 0:

            lower_wick_to_body_ratio = (
                proceding_candle["lower_wick"] / body
            )

            upper_wick_to_body_ratio = (
                proceding_candle["upper_wick"] / body
            )

        else:

            lower_wick_to_body_ratio = 0
            upper_wick_to_body_ratio = 0

        lower_wick_threshold = (
            WICK_REJECTION_CONFIG[
                "lower_wick_to_body_threshold"
            ]
        )

        upper_wick_threshold = (
            WICK_REJECTION_CONFIG[
                "upper_wick_to_body_threshold"
            ]
        )

        is_pair_found = False

        # =====================================================================
        # PREVIOUS CANDLE = BEARISH
        # =====================================================================
        if preceding_candle["candle_type"] == "Bearish":

            # -------------------------------------------------------------
            # HIGH SWEEP
            # -------------------------------------------------------------
            if proceding_candle["high"] > preceding_candle["high"]:

                if (
                    proceding_candle["close"]
                    <= preceding_candle["open"]
                    and
                    upper_wick_to_body_ratio
                    <= upper_wick_threshold
                ):

                    is_pair_found = True

            # -------------------------------------------------------------
            # LOW SWEEP
            # -------------------------------------------------------------
            elif proceding_candle["low"] < preceding_candle["low"]:

                if (
                    proceding_candle["close"]
                    >= preceding_candle["close"]
                    and
                    lower_wick_to_body_ratio
                    <= lower_wick_threshold
                ):

                    is_pair_found = True

        # =====================================================================
        # PREVIOUS CANDLE = BULLISH
        # =====================================================================
        elif preceding_candle["candle_type"] == "Bullish":

            # -------------------------------------------------------------
            # HIGH SWEEP
            # -------------------------------------------------------------
            if proceding_candle["high"] > preceding_candle["high"]:

                if (
                    proceding_candle["close"]
                    <= preceding_candle["close"]
                    and
                    upper_wick_to_body_ratio
                    <= upper_wick_threshold
                ):

                    is_pair_found = True

            # -------------------------------------------------------------
            # LOW SWEEP
            # -------------------------------------------------------------
            elif proceding_candle["low"] < preceding_candle["low"]:

                if (
                    proceding_candle["close"]
                    >= preceding_candle["open"]
                    and
                    lower_wick_to_body_ratio
                    <= lower_wick_threshold
                ):

                    is_pair_found = True

        # =====================================================================
        # SIGNAL FOUND
        # =====================================================================
        if is_pair_found:

            proceeding_candle_type = (
                proceding_candle["candle_type"]
                if "candle_type" in proceding_candle.index
                else None
            )

            preceding_candle_type = (
                preceding_candle["candle_type"]
                if "candle_type" in preceding_candle.index
                else None
            )

            pre_high = preceding_candle["high"]
            pre_low = preceding_candle["low"]

            pro_high = proceding_candle["high"]
            pro_low = proceding_candle["low"]

            # -------------------------------------------------------------
            # DATETIME EXTRACTION
            # -------------------------------------------------------------
            pro_time = (
                proceding_candle["time"]
                if (
                    "time" in proceding_candle.index and
                    pd.notnull(proceding_candle["time"])
                )
                else proceding_candle.name
            )

            pre_time = (
                preceding_candle["time"]
                if (
                    "time" in preceding_candle.index and
                    pd.notnull(preceding_candle["time"])
                )
                else preceding_candle.name
            )

            logging.info(
                f"✅ Signal FOUND for {pair} on {timeframe_key}\n"
                f"Preceding: {pre_time}\n"
                f"Proceeding: {pro_time}\n"
                f"Proceeding Type: {proceeding_candle_type}"
            )

            return (
                True,
                pre_time,
                pro_time,
                proceeding_candle_type,
                pro_high,
                pro_low,
                pre_high,
                pre_low
            )

    return False


# =============================================================================
# SIMPLE STRUCTURE TREND DETECTION
# =============================================================================
def detect_trend(data):

    data = data.copy()

    data["HH"] = False
    data["LH"] = False
    data["HL"] = False
    data["LL"] = False

    data["Trend"] = "Sideways"

    for i in range(1, len(data)):

        # ---------------------------------------------------------------------
        # HIGHS
        # ---------------------------------------------------------------------
        if data["high"].iloc[i] > data["high"].iloc[i - 1]:

            data.iloc[
                i,
                data.columns.get_loc("HH")
            ] = True

        elif data["high"].iloc[i] < data["high"].iloc[i - 1]:

            data.iloc[
                i,
                data.columns.get_loc("LH")
            ] = True

        # ---------------------------------------------------------------------
        # LOWS
        # ---------------------------------------------------------------------
        if data["low"].iloc[i] > data["low"].iloc[i - 1]:

            data.iloc[
                i,
                data.columns.get_loc("HL")
            ] = True

        elif data["low"].iloc[i] < data["low"].iloc[i - 1]:

            data.iloc[
                i,
                data.columns.get_loc("LL")
            ] = True

        # ---------------------------------------------------------------------
        # TREND CLASSIFICATION
        # ---------------------------------------------------------------------
        if data["HL"].iloc[i] and data["HH"].iloc[i]:

            data.iloc[
                i,
                data.columns.get_loc("Trend")
            ] = "Uptrend"

        elif data["LH"].iloc[i] and data["LL"].iloc[i]:

            data.iloc[
                i,
                data.columns.get_loc("Trend")
            ] = "Downtrend"

        else:

            data.iloc[
                i,
                data.columns.get_loc("Trend")
            ] = data["Trend"].iloc[i - 1]

    return data


# =============================================================================
# TIMEFRAME → MINUTES
# =============================================================================
def timeframe_to_minutes(tf):

    tf = tf.lower()

    if "m" in tf:
        return int(tf.replace("m", ""))

    if "h" in tf:
        return int(tf.replace("h", "")) * 60

    if "d" in tf:
        return int(tf.replace("d", "")) * 1440

    raise ValueError(f"Unsupported timeframe: {tf}")


# =============================================================================
# WINDOW CALCULATION
# =============================================================================
def compute_window(timeframe):

    ref_tf = TREND_CONFIG["reference_timeframe"]

    base_minutes = timeframe_to_minutes(ref_tf)
    tf_minutes = timeframe_to_minutes(timeframe)

    window = int(base_minutes / tf_minutes)

    return max(window, 1)


# =============================================================================
# REGRESSION SLOPE
# =============================================================================
def rolling_normalized_slope(x):

    y = x.values

    X = np.arange(len(y)).reshape(-1, 1)

    model = LinearRegression()

    model.fit(X, y)

    slope = model.coef_[0]

    mean_price = np.mean(y)

    return slope / mean_price


# =============================================================================
# THRESHOLD CALCULATION
# =============================================================================
def compute_threshold(price):

    mode = TREND_CONFIG["threshold_mode"]

    # -------------------------------------------------------------------------
    # VOLATILITY MODE
    # -------------------------------------------------------------------------
    if mode == "volatility":

        vol_window = TREND_CONFIG["volatility_window"]

        volatility = (
            price.pct_change()
            .rolling(vol_window)
            .std()
        )

        threshold = np.maximum(
            TREND_CONFIG["minimum_threshold"],
            volatility * TREND_CONFIG["volatility_multiplier"]
        )

        return threshold

    # -------------------------------------------------------------------------
    # FIXED MODE
    # -------------------------------------------------------------------------
    elif mode == "fixed":

        return TREND_CONFIG["minimum_threshold"]

    else:
        raise ValueError("Invalid threshold_mode in config")


# =============================================================================
# MAIN TREND ANALYSIS
# =============================================================================
def trend_analysis(df, timeframe, price_column="close"):

    price = df[price_column]

    window = compute_window(timeframe)

    rolling_trend = price.rolling(window).apply(
        rolling_normalized_slope,
        raw=False
    )

    threshold = compute_threshold(price)

    trend_direction = np.where(
        rolling_trend > threshold,
        "Uptrend",
        np.where(
            rolling_trend < -threshold,
            "Downtrend",
            "Sideways"
        )
    )

    trend_df = pd.DataFrame({
        "price": price,
        "trend_strength": rolling_trend,
        "threshold": threshold,
        "trend_direction": trend_direction
    })

    return trend_df

# =============================================================================
# RANGE TREND ANALYSIS
# =============================================================================
def analyze_trend_in_range(
    df,
    start_time,
    end_time,
    timeframe='M15',
    price_column='close',
    plot=False
):

    mt5_to_pandas = {
        'M15': '15min',
        'M5': '5min',
        'M1': '1min',
        'H1': '1H',
        'H4': '4H',
        'D1': 'D'
    }

    pandas_timeframe = mt5_to_pandas.get(
        timeframe,
        timeframe
    )

    # =====================================================
    # RESAMPLE CLOSE PRICES
    # =====================================================

    price = (
        df[price_column]
        .resample(pandas_timeframe)
        .last()
        .dropna()
    )

    # =====================================================
    # RESAMPLE OHLC FOR ATR
    # =====================================================

    ohlc = (
        df[["high", "low", "close"]]
        .resample(pandas_timeframe)
        .agg({
            "high": "max",
            "low": "min",
            "close": "last"
        })
        .dropna()
    )

    parsed_start = pd.to_datetime(start_time)
    parsed_end = pd.to_datetime(end_time)

    price_slice = price.loc[
        parsed_start:
        parsed_end
    ]

    ohlc_slice = ohlc.loc[
        parsed_start:
        parsed_end
    ]

    if price_slice.empty:

        logging.warning(
            f"No data in specified range "
            f"{parsed_start} -> {parsed_end}"
        )

        return None

    # =====================================================
    # ATR CALCULATION
    # =====================================================

    if len(ohlc_slice) < TREND_CONFIG["ATR_PERIOD"] + 1:

        logging.warning(
            f"Need at least "
            f"{TREND_CONFIG['ATR_PERIOD'] + 1} candles "
            f"for ATR calculation"
        )

        return None

    atr = Utils.calculate_atr(
        ohlc_slice
    )

    if atr is None or atr <= 0:

        logging.warning(
            "Invalid ATR value"
        )

        return None

    # =====================================================
    # LINEAR REGRESSION
    # =====================================================

    y = price_slice.values

    X = np.arange(
        len(y)
    ).reshape(-1, 1)

    model = LinearRegression()

    model.fit(X, y)

    slope = model.coef_[0]

    mean_price = np.mean(y)

    normalized_slope = (
        slope / mean_price
    )

    # =====================================================
    # ATR NORMALIZED SLOPE
    # =====================================================

    atr_slope = (
        slope / atr
    )

    # =====================================================
    # TREND CLASSIFICATION
    # =====================================================

    if abs(atr_slope) < TREND_CONFIG["min_treshold_%"]:

        trend_direction = "Range"

    elif atr_slope > 0:

        trend_direction = "Uptrend"

    else:

        trend_direction = "Downtrend"

    # =====================================================
    # RESULT
    # =====================================================

    result = {

        "trend_direction":
        trend_direction,

        "normalized_slope":
        normalized_slope,

        "atr_slope":
        atr_slope,

        "atr":
        atr,

        "start_price":
        price_slice.iloc[0],

        "end_price":
        price_slice.iloc[-1],

        "candle_count":
        len(price_slice)
    }

    # =====================================================
    # PLOT
    # =====================================================

    if plot:

        trendline = model.predict(X)

        plt.figure(
            figsize=(12, 6)
        )

        plt.plot(
            price_slice.index,
            price_slice.values,
            label=f"Price ({timeframe})"
        )

        plt.plot(
            price_slice.index,
            trendline,
            linestyle='--',
            label=(
                f"Trendline "
                f"(ATR Slope="
                f"{atr_slope:.4f})"
            )
        )

        plt.title(
            f"Trend Analysis\n"
            f"{parsed_start} → "
            f"{parsed_end}\n"
            f"ATR={atr:.5f} | "
            f"{trend_direction}"
        )

        plt.xlabel("Date")

        plt.ylabel("Price")

        plt.grid(True)

        plt.legend()

        plt.tight_layout()

        plt.show()

    return result


# =============================================================================
# RANGE UTILITIES
# =============================================================================
def range_price_to_percent(price, high, low):

    if high == low:
        return None

    return ((price - low) * 100) / (high - low)


def range_percentage_to_price(percent, high, low):

    return (percent * (high - low) / 100) + low


# =============================================================================
# BOS + CRT STRATEGY
# =============================================================================
class BOSCRTStrategy:

    def __init__(self, pair: str):

        self.pair = pair
        self.last_bos = None

    # =========================================================================
    # STEP 1 — DETECT BOS
    # =========================================================================
    def detect_bos(self, df: pd.DataFrame):

        result = compute(df)

        events = result.get("events", [])

        if not events:
            return None

        last_event = events[-1]

        if last_event["type"] != "BOS":
            return None

        self.last_bos = {
            "direction": last_event["direction"],
            "level": last_event["level"],
            "time": last_event["break_time"]
        }

        return self.last_bos

    # =========================================================================
    # STEP 2 — PRICE AT LEVEL
    # =========================================================================
    def price_at_level(self, df: pd.DataFrame, tolerance=0.0005):

        if not self.last_bos:
            return False

        current_price = df.iloc[-1]["close"]

        level = self.last_bos["level"]

        return abs(current_price - level) <= tolerance

    # =========================================================================
    # STEP 3 — CRT CONFIRMATION
    # =========================================================================
    def crt_confirmation(self, df: pd.DataFrame):

        if len(df) < 2 or not self.last_bos:
            return None

        preceding_candle = df.iloc[-2]
        proceding_candle = df.iloc[-1]

        body = proceding_candle["body_size"]

        if body > 0:

            lower_wick_to_body_ratio = (
                proceding_candle["lower_wick"] / body
            )

            upper_wick_to_body_ratio = (
                proceding_candle["upper_wick"] / body
            )

        else:

            lower_wick_to_body_ratio = 0
            upper_wick_to_body_ratio = 0

        lower_wick_threshold = (
            WICK_REJECTION_CONFIG[
                "lower_wick_to_body_threshold"
            ]
        )

        upper_wick_threshold = (
            WICK_REJECTION_CONFIG[
                "upper_wick_to_body_threshold"
            ]
        )

        direction = self.last_bos["direction"]

        is_pair_found = False

        # ---------------------------------------------------------------------
        # BEARISH BOS
        # ---------------------------------------------------------------------
        if direction == "DOWN":

            if proceding_candle["high"] > preceding_candle["high"]:

                if (
                    proceding_candle["close"]
                    <= preceding_candle["open"]
                    and
                    upper_wick_to_body_ratio
                    <= upper_wick_threshold
                ):

                    is_pair_found = True

            if is_pair_found:
                return "SELL"

        # ---------------------------------------------------------------------
        # BULLISH BOS
        # ---------------------------------------------------------------------
        elif direction == "UP":

            if proceding_candle["low"] < preceding_candle["low"]:

                if (
                    proceding_candle["close"]
                    >= preceding_candle["open"]
                    and
                    lower_wick_to_body_ratio
                    <= lower_wick_threshold
                ):

                    is_pair_found = True

            if is_pair_found:
                return "BUY"

        return None