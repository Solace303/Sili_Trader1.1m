# =========================================================
# main.py (MT5 VERSION)
# =========================================================

import os
import time
import logging
from typing import Optional

import pandas as pd

from config import (
    INSTRUMENTS,
    CRT_TIMEFRAMES,
    BACKTEST_MODE,
    BACKTEST_TIMEFRAME_RELATIVITY_SECONDS,
)

from strategy import (
    BOSCRTStrategy,
    detect_trend,
)

from risk_manager import RiskManager
from trade_journal import TradeJournal

# =========================================================
# MODE IMPORTS
# =========================================================

if BACKTEST_MODE:

    import watcher as _watcher_module
    import backtest as _bt

    from backtest import (
        SimulatedTradeExecutor,
        BacktestCSVFetcher,
        candle_store,
        push_candles,
        _norm,
        BACKTEST_DATA_DIR,
        BACKTEST_STATE_FILE,
        BACKTEST_LOG_FILE,
        playback,
    )

    _watcher_module.STATE_FILE = BACKTEST_STATE_FILE
    _watcher_module.TradeExecutor = SimulatedTradeExecutor

else:

    from data import CandleFetcher

from watcher import Watcher


# =========================================================
# LOGGING
# =========================================================

def _setup_logging():

    handlers = [logging.StreamHandler()]

    if BACKTEST_MODE:

        os.makedirs(BACKTEST_DATA_DIR, exist_ok=True)

        handlers.append(
            logging.FileHandler(
                BACKTEST_LOG_FILE,
                mode="a",
                encoding="utf-8"
            )
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )


# =========================================================
# ANALYZE SINGLE PAIR
# =========================================================

def _analyze_pair(fetcher, watcher, pair):

    try:

        # =====================================================
        # FETCH H4 DATA
        # =====================================================

        df = fetcher.get_candles(
            instrument=pair,
            granularity="H4",
            count=500
        )

        if df is None or df.empty:

            logging.warning(f"[{pair}] No H4 candle data")
            return

        # =====================================================
        # TREND STRUCTURE
        # =====================================================

        df = detect_trend(df)

        # =====================================================
        # STRATEGY
        # =====================================================

        strategy = BOSCRTStrategy(pair)

        # =====================================================
        # DETECT BOS
        # =====================================================

        bos = strategy.detect_bos(df)

        if not bos:
            return

        direction = bos["direction"]

        logging.info(
            f"[{pair}] BOS DETECTED | "
            f"Direction={direction} | "
            f"Level={bos['level']}"
        )

        # =====================================================
        # CRT CONFIRMATION
        # =====================================================

        signal = strategy.crt_confirmation(df)

        if not signal:
            return

        logging.info(f"[{pair}] CRT SIGNAL = {signal}")

        # =====================================================
        # CURRENT PRICE
        # =====================================================

        current_price = float(
            fetcher.get_current_price(pair)
        )

        # =====================================================
        # LAST CANDLES
        # =====================================================

        preceding_candle = df.iloc[-2]
        proceding_candle = df.iloc[-1]

        # =====================================================
        # BUY SETUP
        # =====================================================

        if signal == "BUY":

            target_exit = None

            for i in range(len(df) - 2, 0, -1):

                row = df.iloc[i]

                if row.get("LH") or row.get("HH"):

                    target_exit = row["close"]
                    break

            if target_exit is None:
                return

            range_distance = abs(
                target_exit - proceding_candle["close"]
            )

            if range_distance == 0:
                return

            current_percent = (
                abs(current_price - proceding_candle["close"])
                / range_distance
            ) * 100

            if current_percent > 20:

                logging.info(
                    f"[{pair}] BUY skipped | "
                    f"Entry exceeded 20% threshold"
                )

                return

            stop_loss = proceding_candle["low"]

            # =================================================
            # RISK PARAMETERS
            # =================================================

            params = watcher.risk_manager.compute_trade_parameters(
                instrument=pair,
                entry=current_price,
                stop=stop_loss,
                take_profit=target_exit,
                trade_type="BUY"
            )

            if params is None:

                logging.info(
                    f"[{pair}] BUY rejected by RiskManager"
                )

                return

            # =================================================
            # EXECUTE BUY (MT5)
            # =================================================

            result = watcher.executor.buy(
                instrument=pair,
                volume=params["lots"],   # MT5 uses LOTS
                stop_loss=stop_loss,
                take_profit=target_exit
            )

            logging.info(
                f"[{pair}] BUY EXECUTED | "
                f"Entry={current_price} | "
                f"SL={stop_loss} | "
                f"TP={target_exit}"
            )

            logging.info(result)

        # =====================================================
        # SELL SETUP
        # =====================================================

        elif signal == "SELL":

            target_exit = None

            for i in range(len(df) - 2, 0, -1):

                row = df.iloc[i]

                if row.get("LL") or row.get("HL"):

                    target_exit = row["close"]
                    break

            if target_exit is None:
                return

            range_distance = abs(
                proceding_candle["close"] - target_exit
            )

            if range_distance == 0:
                return

            current_percent = (
                abs(proceding_candle["close"] - current_price)
                / range_distance
            ) * 100

            if current_percent > 20:

                logging.info(
                    f"[{pair}] SELL skipped | "
                    f"Entry exceeded 20% threshold"
                )

                return

            stop_loss = proceding_candle["high"]

            # =================================================
            # RISK PARAMETERS
            # =================================================

            params = watcher.risk_manager.compute_trade_parameters(
                instrument=pair,
                entry=current_price,
                stop=stop_loss,
                take_profit=target_exit,
                trade_type="SELL"
            )

            if params is None:

                logging.info(
                    f"[{pair}] SELL rejected by RiskManager"
                )

                return

            # =================================================
            # EXECUTE SELL (MT5)
            # =================================================

            result = watcher.executor.sell(
                instrument=pair,
                volume=params["lots"],
                stop_loss=stop_loss,
                take_profit=target_exit
            )

            logging.info(
                f"[{pair}] SELL EXECUTED | "
                f"Entry={current_price} | "
                f"SL={stop_loss} | "
                f"TP={target_exit}"
            )

            logging.info(result)

    except Exception as e:

        logging.error(
            f"[{pair}] ANALYSIS ERROR: {e}",
            exc_info=True
        )


# =========================================================
# MAIN RUN
# =========================================================

def run():

    _setup_logging()

    # =====================================================
    # BACKTEST MODE
    # =====================================================

    if BACKTEST_MODE:

        exec_tf = _norm(
            CRT_TIMEFRAMES.get("execution_tf", "M15")
        )

        base_sleep = float(
            BACKTEST_TIMEFRAME_RELATIVITY_SECONDS.get(
                exec_tf,
                1.0
            )
        )

        fetcher = BacktestCSVFetcher(
            data_dir=BACKTEST_DATA_DIR,
            instruments=INSTRUMENTS,
            base_granularity=exec_tf,
        )

        _bt.current_fetcher = fetcher

        if playback.start_ts or playback.end_ts:

            fetcher.apply_date_range(
                playback.start_ts,
                playback.end_ts
            )

    # =====================================================
    # LIVE MODE
    # =====================================================

    else:

        base_sleep = 60

        fetcher = CandleFetcher()

    # =====================================================
    # WATCHER
    # =====================================================

    watcher = Watcher(fetcher)

    fetcher.start_price_stream()

    watcher.load_state()

    pairs = (
        list(fetcher.market_data.keys())
        if BACKTEST_MODE
        else list(INSTRUMENTS)
    )

    logging.info("=" * 60)

    logging.info(
        f"{'BACKTEST' if BACKTEST_MODE else 'LIVE'} BOT STARTED"
    )

    logging.info(f"Pairs      : {pairs}")

    logging.info(f"Base sleep : {base_sleep}s")

    logging.info("=" * 60)

    # =====================================================
    # MAIN LOOP
    # =====================================================

    while True:

        try:

            # =============================================
            # ANALYZE EACH PAIR
            # =============================================

            for pair in pairs:

                # -----------------------------------------
                # Skip if open position already exists
                # -----------------------------------------

                if watcher.executor.has_open_position(pair):

                    logging.info(
                        f"[SKIP] Open position exists for {pair}"
                    )

                    continue

                logging.info(
                    f"\n{'=' * 50}\n"
                    f"Analyzing {pair}\n"
                    f"{'=' * 50}"
                )

                _analyze_pair(
                    fetcher,
                    watcher,
                    pair
                )

            logging.info(
                "⏳ Sleeping before next cycle...\n"
            )

            time.sleep(base_sleep)

        except Exception as e:

            logging.error(
                f"🔥 MAIN LOOP ERROR: {e}",
                exc_info=True
            )

            time.sleep(1)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    run()