# =========================================================
# watcher.py (MT5 VERSION)
# =========================================================

import json
import os
import threading
import time
import pandas as pd
import logging
from risk_manager import RiskManager
from strategy import (
    range_percentage_to_price,
    range_price_to_percent
)
from execution import TradeExecutor
from trade_journal import TradeJournal

STATE_FILE = (
    "/run/media/solace/ABBA-2E35/My_Code/Sili-Trader1.1m/forex_data/watcher_state.json"
)
logger = logging.getLogger(__name__)

class Watcher:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.executor = TradeExecutor()
        self.journal = TradeJournal(fetcher)
        self.risk_manager = RiskManager(
            fetcher,
            self.journal
        )

        # pair -> {thread, state}
        self.active_watchers = {}
        self.logs = {}
        self.lock = threading.Lock()
    # =====================================================
    # SAVE STATE
    # =====================================================
    def save_state(self):
        with self.lock:
            os.makedirs(
                os.path.dirname(STATE_FILE),
                exist_ok=True
            )
            
            data = [
                info["state"]
                for info in self.active_watchers.values()
            ]

            with open(STATE_FILE, "w") as f:
                json.dump(
                    data,
                    f,
                    indent=4,
                    default=str
                )
    # =====================================================
    # LOAD STATE
    # =====================================================
    def load_state(self):
        if not os.path.exists(STATE_FILE):
            logger.info(
                "[STATE] No previous state found"
            )
            return
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        for state in data:
            # --------------------------------------------
            # SKIP CLOSED
            # ---------------------------------------------
            if state.get("status") == "CLOSED":
                logger.info(
                    f"[SKIP RESTORE] "
                    f"Closed trade for {state['pair']}"
                )
                continue
            pair = state["pair"]
            logger.info(
                f"[RESTORE] Restarting watcher "
                f"for {pair}"
            )

            self.start(
                pair=pair,
                trend_direction=state[
                    "trend_direction"],
                preceding_time=pd.to_datetime(
                    state["preceding_time"]),
                proceding_time=pd.to_datetime(
                    state["proceding_time"]),
                trade_type=state["trade_type"],
                pro_high=state["pro_high"],
                pro_low=state["pro_low"]
                        )
    # =====================================================
    # START WATCHER
    # =====================================================
    def start(
        self,
        pair,
        trend_direction,
        preceding_time,
        proceding_time,
        trade_type,
        pro_high,
        pro_low):
        # ---------------------------------------------
        # PREVENT DUPLICATES
        # ---------------------------------------------
        if pair in self.active_watchers:
            logger.info(
                f"[WATCHER] Already running "
                f"for {pair}"
            )
            return
        # =================================================
        # INITIAL STATE
        # =================================================
        state = {
            "pair": pair,
            "trade_type": trade_type,
            "trend_direction": trend_direction,
            "pro_high": pro_high,
            "pro_low": pro_low,
            "preceding_time": str(preceding_time),
            "proceding_time": str(proceding_time),
            "status": "WATCHING"
                }
        # =================================================
        # THREAD LOOP
        # =================================================
        def run():
            logger.info(
                f"[WATCHER STARTED] {pair}")
            df_log = pd.DataFrame(
                columns=[
                    "timestamp",
                    "preceding_time",
                    "proceding_time",
                    "entry_price",
                    "stop_loss",
                    "take_profit",
                    "result"
                ]
            )
            trade_open = False
            entry_price = None
            sl = None
            tp = None
            try:
                while True:
                    # =====================================
                    # CURRENT PRICE
                    # =====================================
                    current_price = (
                        self.fetcher
                        .get_current_price(pair)
                    )
                    if current_price is None:
                        time.sleep(1)
                        continue
                    current_price = float(
                        current_price
                    )
                    # =====================================
                    # DYNAMIC RANGE %
                    # =====================================
                    percent = (
                        range_price_to_percent(
                            price=current_price,
                            high=pro_high,
                            low=pro_low
                        )
                    )
                    # =====================================
                    # ENTRY LOGIC
                    # =====================================
                    if not trade_open:
                        # ---------------------------------
                        # MT5 POSITION SYNC
                        # ---------------------------------
                        if (self.executor.has_open_position(pair)):
                            details = (
                                self.executor.get_open_trade_details(pair)
                            )
                            if details:
                                entry_price = (
                                    details["price"]
                                )
                                sl = details["sl"]
                                tp = details["tp"]
                                trade_open = True
                                state["status"] = "OPEN"
                                state["entry_price"] = (entry_price)
                                state["sl"] = sl
                                state["tp"] = tp
                                self.save_state()
                                logger.info(
                                    f"[SYNC] {pair} | "
                                    f"Entry={entry_price} | "
                                    f"SL={sl} | TP={tp}"
                                )
                                continue
                        # ---------------------------------
                        # BUY ENTRY
                        # ---------------------------------
                        if (trade_type == "BUY"and 25 <= percent <= 35 and trend_direction == "Uptrend"):
                            tp = (range_percentage_to_price(75, pro_high, pro_low))
                            sl = pro_low
                            # -----------------------------
                            # MT5 RISK PARAMS
                            # -----------------------------
                            params = (
                                self.risk_manager.compute_trade_parameters(instrument=pair, entry=current_price, stop=sl, take_profit=tp, trade_type="BUY")
                            )

                            if params is None:
                                logger.info(
                                    f"[FILTERED] {pair}"
                                )
                                time.sleep(1)
                                continue
                            # -----------------------------
                            # EXECUTE BUY
                            # -----------------------------
                            result = (
                                self.executor.buy(pair=pair, lots=params["lots"], sl=sl, tp=tp)
                            )
                            if result:
                                entry_price = (
                                    current_price
                                )
                                trade_open = True
                                state["status"] = "OPEN"
                                state["entry_price"] = (
                                    entry_price
                                )
                                state["sl"] = sl
                                state["tp"] = tp
                                self.save_state()
                                logger.info(
                                    f"[BUY] {pair} @ "
                                    f"{entry_price} | "
                                    f"TP={tp} | SL={sl}"
                                )
                        # ---------------------------------
                        # SELL ENTRY
                        # ---------------------------------
                        elif (trade_type == "SELL" and 65 <= percent <= 75 and trend_direction == "Downtrend"):
                            tp = (range_percentage_to_price(25, pro_high, pro_low))
                            sl = pro_high
                            # -----------------------------
                            # MT5 RISK PARAMS
                            # -----------------------------
                            params = (
                                self.risk_manager.compute_trade_parameters(instrument=pair, entry=current_price, stop=sl, take_profit=tp, trade_type="SELL")
                            )
                            if params is None:
                                logger.info(
                                    f"[FILTERED] {pair}"
                                )
                                time.sleep(1)
                                continue
                            # -----------------------------
                            # EXECUTE SELL
                            # -----------------------------
                            result = (
                                self.executor.sell(pair=pair, lots=params["lots"], sl=sl, tp=tp)
                            )
                            if result:
                                entry_price = (current_price)
                                trade_open = True
                                state["status"] = "OPEN"
                                state["entry_price"] = (entry_price)
                                state["sl"] = sl
                                state["tp"] = tp
                                self.save_state()
                                logger.info(
                                    f"[SELL] {pair} @ "
                                    f"{entry_price} | "
                                    f"TP={tp} | SL={sl}"
                                )
                    # =====================================
                    # EXIT LOGIC
                    # =====================================
                    else:
                        # ---------------------------------
                        # BROKER-SIDE CHECK
                        # ---------------------------------
                        if not (self.executor.has_open_position(pair)):
                            logger.info(
                                f"[CLOSED] {pair}"
                            )
                            self.journal.update()
                            state["status"] = "CLOSED"
                            self.save_state()
                            break
                        # ---------------------------------
                        # MANUAL RESULT CHECK
                        # ---------------------------------
                        result = None
                        if trade_type == "BUY":
                            if current_price <= sl:
                                result = "LOSS"
                            elif current_price >= tp:
                                result = "WIN"
                        elif trade_type == "SELL":
                            if current_price >= sl:
                                result = "LOSS"
                            elif current_price <= tp:
                                result = "WIN"
                        if result:
                            logger.info(
                                f"[EXIT] {pair} "
                                f"→ {result}"
                            )
                            df_log.loc[len(df_log)] = [
                                pd.Timestamp.now(),
                                preceding_time,
                                proceding_time,
                                entry_price,
                                sl,
                                tp,
                                result
                            ]
                            self.logs[pair] = df_log
                            state["status"] = "CLOSED"
                            self.save_state()
                            break
            except Exception as e:
                logger.error(
                    f"[WATCHER ERROR] "
                    f"{pair}: {e}"
                )
            finally:
                logger.info(
                    f"[WATCHER STOPPED] {pair}"
                )
                with self.lock:
                    if pair in self.active_watchers:
                        del self.active_watchers[pair]
                self.save_state()
        # =================================================
        # START THREAD
        # =================================================
        thread = threading.Thread(
            target=run,
            daemon=True
        )
        self.active_watchers[pair] = {
            "thread": thread,
            "state": state
        }
        self.save_state()
        thread.start()