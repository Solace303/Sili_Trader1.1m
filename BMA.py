# ============================================================================================================
#This bot helps you biuld up  your account from 10 USD to 100 USD with 1% risk per trade and 1:2 or 1:1.5 RR.
#=============================================================================================================

import os
import time
import logging
from data import CandleFetcher
from config import (BMA_CONFIG)
logging.basicConfig(level=logging.INFO)
from strategy import analyze_trend_in_range
from helpers import Utils
from data import CandleFetcher
fetcher = CandleFetcher()

from strategy import (BOSCRTStrategy,detect_trend,)

def _mba(fetcher, watcher, pair):

    try:

        # =====================================================
        # FETCH H4 DATA
        # =====================================================

        df = fetcher.get_candles(
            instrument=BMA_CONFIG['instruments'],
            granularity=BMA_CONFIG['monitor_tf'],
            count=1320
        )

        if df is None or df.empty:

            logging.warning(f"[{pair}] No {BMA_CONFIG['monitor_tf']} candle data")
            return

        # =====================================================
        # BOS TREND STRUCTURE
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
        #======================================================
        # FIND TREND RANGE FROM BOS
        #======================================================
        
        result = Utils.find_trend_range_from_bos(df)
        
        if result is None:

            logging.info(f"[{pair}] No BOS found")
            return
        

        trend = analyze_trend_in_range(
            df=df,
            start_time=start_time,
            end_time=end_time,
            timeframe=BMA_CONFIG["monitor_tf"],
            price_column="close",
            plot=True
        )

        start_time, end_time, atr_direction, bos_count = result

        bos_direction = bos["direction"]

        logging.info(
            f"Direction : {atr_direction}"
            f"BOS Count : {bos_count}  |"
            f"Start Time: {start_time} |"
            f"End Time  : {end_time}"
        )
        logging.info(
            f"[{pair}] BOS DETECTED | "
            f"Direction={bos_direction} | "
            f"Level={bos['level']}"
        )
        if bos_direction == "DOWN" and atr_direction == "Downtrend":
            logging.info(f"[{pair}] ATR and BOS direction match: {atr_direction}")
        elif bos_direction == "UP" and atr_direction == "Uptrend":
            logging.info(f"[{pair}] ATR and BOS direction match: {atr_direction}")
        else:
            logging.info(
                f"[{pair}] ATR and BOS direction mismatch: "
                f"ATR={atr_direction} | BOS={bos_direction}"
                f"HOLD YOUR CASH AND WAIT PATIENTLY PLEASE"
            )
            return
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

        price_data = fetcher.get_current_price(pair)

        if price_data is None:

            logging.error(
                f"[{pair}] Failed to fetch live price"
            )

            return

        current_price = price_data["mid"]

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
        
if __name__ == "__main__":
    symbol = BMA_INSTRUMENT

    price_data = fetcher.get_current_price(symbol)

    if price_data is None:

        print(
            f"[-] Failed to get price for {symbol} please check symbol name  and update the config file or broker connection"
        )

        real_symbol = fetcher.find_symbol(symbol)

        if real_symbol:

            print(
                f"[+] Found broker symbol: "
                f"{real_symbol}"
            )

            # ---------------------------------
            # REPLACE SYMBOL IN MEMORY
            # ---------------------------------
            symbol = real_symbol

            # retry
            price_data = fetcher.get_current_price(
                symbol
            )

        else:

            print(
                f"[-] Could not find matching symbol"
            )

    if price_data:

        current_price = price_data["mid"]

        print(
            f"Current price for "
            f"{symbol} = "
            f"{current_price}"
        )