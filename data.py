"""
MT5 candle data fetcher for Sili_Trader.

This module replaces the OANDA REST API layer with native MT5 access
through mt5linux.

FEATURES:
- Fetches OHLCV candle data from MT5
- Supports multi-timeframe CRT analysis
- Live CSV append/update logic
- Tick-based price cache
- MT5 account integration
- Symbol visibility auto-handling

REQUIRES:
- MT5 terminal running in Wine
- mt5linux bridge server active
"""

import time
import logging
import threading
from pathlib import Path

import pandas as pd
from mt5linux import MetaTrader5

from config import (
    MT5_PATH,
    MT5_ACCOUNT_ID,
    MT5_PASSWORD,
    MT5_SERVER,
    INSTRUMENTS,
    BACKTEST_MODE,
    CRT_TIMEFRAMES,
)

logging.basicConfig(level=logging.INFO)


# =============================================================================
# TIMEFRAME NORMALIZATION
# =============================================================================
def _norm_tf(tf: str) -> str:
    s = str(tf).strip().upper()

    aliases = {
        "15M": "M15",
        "1H": "H1",
        "4H": "H4",
        "1D": "D1",
    }

    return aliases.get(s, s)


# =============================================================================
# MT5 TIMEFRAME MAPPING
# =============================================================================
MT5_TIMEFRAMES = {
    "M1":  MetaTrader5.TIMEFRAME_M1,
    "M5":  MetaTrader5.TIMEFRAME_M5,
    "M15": MetaTrader5.TIMEFRAME_M15,
    "M30": MetaTrader5.TIMEFRAME_M30,
    "H1":  MetaTrader5.TIMEFRAME_H1,
    "H4":  MetaTrader5.TIMEFRAME_H4,
    "D1":  MetaTrader5.TIMEFRAME_D1,
}


# =============================================================================
# CANDLE FETCHER
# =============================================================================
class CandleFetcher:
    """
    MT5 candle fetcher wrapper.
    """

    def __init__(self):

        # ---------------------------------------------------------------------
        # CONNECT TO MT5 BRIDGE
        # ---------------------------------------------------------------------
        self.client = MetaTrader5()

        if not self.client.initialize(MT5_PATH):
            raise RuntimeError(
                f"MT5 initialize failed: {self.client.last_error()}"
            )

        login_success = self.client.login(
            MT5_ACCOUNT_ID,
            password=MT5_PASSWORD,
            server=MT5_SERVER
        )

        if not login_success:
            raise RuntimeError(
                f"MT5 login failed: {self.client.last_error()}"
            )

        logging.info("[+] Connected to MT5 successfully")

        # ---------------------------------------------------------------------
        # PRICE CACHE
        # ---------------------------------------------------------------------
        self.price_cache = {}
        self.stream_running = False

        # ---------------------------------------------------------------------
        # STORAGE
        # ---------------------------------------------------------------------
        self.forex_data_dir = Path(
            "/run/media/solace/ABBA-2E35/My_Code/Sili-Trader1.1m/forex_data"
        )

        self.forex_data_dir.mkdir(parents=True, exist_ok=True)

        self.base_storage_granularity = _norm_tf(
            CRT_TIMEFRAMES.get("execution_tf", "M15")
        )

    # =========================================================================
    # FETCH CANDLES
    # =========================================================================
    def get_candles(self, instrument, granularity, count):

        gran_norm = _norm_tf(granularity)

        should_persist = (
            not BACKTEST_MODE and
            gran_norm == self.base_storage_granularity
        )

        fetch_count = count
        existing_df = None

        # ---------------------------------------------------------------------
        # LIVE CSV APPEND LOGIC
        # ---------------------------------------------------------------------
        if should_persist:

            output_file = self.forex_data_dir / f"{instrument}.csv"

            if output_file.exists():

                try:
                    existing_df = pd.read_csv(
                        output_file,
                        index_col="time",
                        parse_dates=["time"]
                    )

                    if not existing_df.empty:

                        last_saved_time = existing_df.index[-1]

                        tf_seconds = {
                            "M1": 60,
                            "M5": 300,
                            "M15": 900,
                            "M30": 1800,
                            "H1": 3600,
                            "H4": 14400,
                            "D1": 86400
                        }

                        seconds_per_candle = tf_seconds.get(
                            gran_norm,
                            3600
                        )

                        time_diff = (
                            pd.Timestamp.now(tz='UTC') -
                            last_saved_time
                        ).total_seconds()

                        estimated_missing = (
                            int(time_diff / seconds_per_candle) + 5
                        )

                        fetch_count = max(
                            count,
                            min(estimated_missing, 5000)
                        )

                        logging.info(
                            f"[{instrument}] "
                            f"Fetching ~{fetch_count} missing candles."
                        )

                except Exception as e:
                    logging.error(
                        f"[{instrument}] CSV read error: {e}"
                    )

        # ---------------------------------------------------------------------
        # ENSURE SYMBOL IS AVAILABLE
        # ---------------------------------------------------------------------
        symbol_info = self.client.symbol_info(instrument)

        if symbol_info is None:
            logging.error(f"[{instrument}] Symbol not found in MT5")
            return pd.DataFrame()

        if not symbol_info.visible:
            self.client.symbol_select(instrument, True)

        # ---------------------------------------------------------------------
        # FETCH MT5 RATES
        # ---------------------------------------------------------------------
        timeframe = MT5_TIMEFRAMES.get(gran_norm)

        if timeframe is None:
            logging.error(f"Unsupported timeframe: {gran_norm}")
            return pd.DataFrame()

        rates = self.client.copy_rates_from_pos(
            instrument,
            timeframe,
            0,
            fetch_count
        )

        if rates is None or len(rates) == 0:
            logging.error(
                f"[{instrument}] Failed to fetch MT5 candles"
            )
            return existing_df if existing_df is not None else pd.DataFrame()

        # ---------------------------------------------------------------------
        # CONVERT TO DATAFRAME
        # ---------------------------------------------------------------------
        df = pd.DataFrame(rates)

        df.rename(columns={
            "tick_volume": "volume"
        }, inplace=True)

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s",
            utc=True
        )

        df = df[
            ["time", "open", "high", "low", "close", "volume"]
        ]

        df.set_index("time", inplace=True)

        # ---------------------------------------------------------------------
        # MERGE & SAVE
        # ---------------------------------------------------------------------
        if should_persist:

            if existing_df is not None and not existing_df.empty:

                combined_df = pd.concat([existing_df, df])

                combined_df = combined_df[
                    ~combined_df.index.duplicated(keep='last')
                ]

                combined_df.sort_index(inplace=True)

                final_df = combined_df

            else:
                final_df = df

            final_df = self._enrich_dataframe(final_df)

            output_file = self.forex_data_dir / f"{instrument}.csv"

            final_df.to_csv(output_file, index=True)

            return final_df.tail(count)

        if not BACKTEST_MODE:
            return self._enrich_dataframe(df).tail(count)

        return self._enrich_dataframe(df)

    # =========================================================================
    # ENRICH DATAFRAME
    # =========================================================================
    def _enrich_dataframe(self, df):

        if df.empty:
            return df

        def detect_candle_type(row):

            if row["close"] > row["open"]:
                return "Bullish"

            elif row["close"] < row["open"]:
                return "Bearish"

            return "Neutral"

        def calculate_body_size(row):
            return abs(row["close"] - row["open"])

        def calculate_wick_lengths(row):

            upper_wick = (
                row["high"] -
                max(row["open"], row["close"])
            )

            lower_wick = (
                min(row["open"], row["close"]) -
                row["low"]
            )

            return upper_wick, lower_wick

        df["candle_type"] = df.apply(
            detect_candle_type,
            axis=1
        )

        df["body_size"] = df.apply(
            calculate_body_size,
            axis=1
        )

        df[["upper_wick", "lower_wick"]] = df.apply(
            calculate_wick_lengths,
            axis=1,
            result_type='expand'
        )

        return df

    # =========================================================================
    # ACCOUNT SUMMARY
    # =========================================================================
    def get_account_summary(self):

        info = self.client.account_info()

        if info is None:
            return None

        return {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "currency": info.currency,
            "leverage": info.leverage,
        }

    # =========================================================================
    # PIP SIZE
    # =========================================================================
    def get_pip_location(self, instrument):

        symbol_info = self.client.symbol_info(instrument)

        if symbol_info is None:
            return None

        return symbol_info.point

    # =========================================================================
    # CURRENT PRICE
    # =========================================================================
    def get_current_price(self, instrument):

        tick = self.client.symbol_info_tick(instrument)

        if tick is None:
            return None

        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "mid": (tick.bid + tick.ask) / 2,
            "spread": tick.ask - tick.bid,
            "time": pd.to_datetime(tick.time, unit="s", utc=True)
        }

    # =========================================================================
    # PRICE STREAM (POLLING LOOP)
    # =========================================================================
    def start_price_stream(self):

        if self.stream_running:
            return

        self.stream_running = True

        def stream():

            while self.stream_running:

                try:

                    for instrument in INSTRUMENTS:

                        tick = self.client.symbol_info_tick(instrument)

                        if tick is None:
                            continue

                        data = {
                            "time": pd.to_datetime(
                                tick.time,
                                unit="s",
                                utc=True
                            ),
                            "bid": tick.bid,
                            "ask": tick.ask,
                            "mid": (tick.bid + tick.ask) / 2,
                            "spread": tick.ask - tick.bid
                        }

                        df = pd.DataFrame([data])

                        df.set_index("time", inplace=True)

                        self.price_cache[instrument] = df

                    time.sleep(0.2)

                except Exception as e:
                    logging.error(f"Price stream error: {e}")
                    time.sleep(1)

        thread = threading.Thread(
            target=stream,
            daemon=True
        )

        thread.start()

    # =========================================================================
    # CLEAN SHUTDOWN
    # =========================================================================
    def shutdown(self):

        self.stream_running = False

        try:
            self.client.shutdown()
        except Exception:
            pass