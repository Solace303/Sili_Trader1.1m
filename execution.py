"""
MT5 Trade Execution Engine for Sili_Trader.

This module replaces the OANDA execution layer with MT5 native trading
through mt5linux.

FEATURES:
- Market orders
- Buy Stop / Sell Stop pending orders
- Stop Loss / Take Profit support
- Open position detection
- Open trade inspection
- MT5-native request structure
- Symbol auto-selection

REQUIRES:
- MT5 terminal running in Wine
- mt5linux bridge server active
"""

import logging
from mt5linux import MetaTrader5

from config import (
    MT5_PATH,
    MT5_ACCOUNT_ID,
    MT5_PASSWORD,
    MT5_SERVER
)

logging.basicConfig(level=logging.INFO)


# =============================================================================
# TRADE EXECUTOR
# =============================================================================
class TradeExecutor:

    def __init__(self):

        self.client = MetaTrader5()

        # ---------------------------------------------------------------------
        # INITIALIZE TERMINAL
        # ---------------------------------------------------------------------
        initialized = self.client.initialize(MT5_PATH)

        if not initialized:

            raise RuntimeError(
                f"MT5 initialize failed: "
                f"{self.client.last_error()}"
            )

        # ---------------------------------------------------------------------
        # LOGIN
        # ---------------------------------------------------------------------
        login_success = self.client.login(
            MT5_ACCOUNT_ID,
            password=MT5_PASSWORD,
            server=MT5_SERVER
        )

        if not login_success:

            raise RuntimeError(
                f"MT5 login failed: "
                f"{self.client.last_error()}"
            )

        logging.info("[+] MT5 TradeExecutor connected")

    # =========================================================================
    # ENSURE SYMBOL AVAILABLE
    # =========================================================================
    def _ensure_symbol(self, instrument):

        symbol_info = self.client.symbol_info(instrument)

        if symbol_info is None:

            logging.error(
                f"Symbol {instrument} not found"
            )

            return False

        if not symbol_info.visible:

            success = self.client.symbol_select(
                instrument,
                True
            )

            if not success:

                logging.error(
                    f"Failed to enable symbol {instrument}"
                )

                return False

        return True

    # =========================================================================
    # INTERNAL ORDER SENDER
    # =========================================================================
    def _submit_order(self, request):

        result = self.client.order_send(request)

        if result is None:

            logging.error(
                f"MT5 order_send returned None"
            )

            return None

        if result.retcode != self.client.TRADE_RETCODE_DONE:

            logging.error(
                f"Order failed | "
                f"Retcode={result.retcode}"
            )

        return result

    # =========================================================================
    # MARKET ORDER
    # =========================================================================
    def place_market_order(
        self,
        instrument,
        volume,
        order_type,
        stop_loss=None,
        take_profit=None,
        deviation=20,
        comment="SiliTrader"
    ):

        if not self._ensure_symbol(instrument):
            return None

        tick = self.client.symbol_info_tick(instrument)

        if tick is None:

            logging.error(
                f"Failed to get tick for {instrument}"
            )

            return None

        # ---------------------------------------------------------------------
        # BUY / SELL PRICE
        # ---------------------------------------------------------------------
        if order_type == "BUY":

            mt5_type = self.client.ORDER_TYPE_BUY
            price = tick.ask

        elif order_type == "SELL":

            mt5_type = self.client.ORDER_TYPE_SELL
            price = tick.bid

        else:

            raise ValueError(
                "order_type must be BUY or SELL"
            )

        request = {

            "action": self.client.TRADE_ACTION_DEAL,

            "symbol": instrument,

            "volume": float(volume),

            "type": mt5_type,

            "price": price,

            "deviation": deviation,

            "magic": 20260516,

            "comment": comment,

            "type_time": self.client.ORDER_TIME_GTC,

            "type_filling": self.client.ORDER_FILLING_IOC,
        }

        # ---------------------------------------------------------------------
        # STOP LOSS
        # ---------------------------------------------------------------------
        if stop_loss is not None:
            request["sl"] = float(stop_loss)

        # ---------------------------------------------------------------------
        # TAKE PROFIT
        # ---------------------------------------------------------------------
        if take_profit is not None:
            request["tp"] = float(take_profit)

        return self._submit_order(request)

    # =========================================================================
    # PENDING STOP ORDER
    # =========================================================================
    def place_stop_order(
        self,
        instrument,
        volume,
        entry_price,
        order_type,
        stop_loss=None,
        take_profit=None,
        comment="SiliTrader"
    ):

        if not self._ensure_symbol(instrument):
            return None

        # ---------------------------------------------------------------------
        # ORDER TYPE
        # ---------------------------------------------------------------------
        if order_type == "BUY_STOP":

            mt5_type = self.client.ORDER_TYPE_BUY_STOP

        elif order_type == "SELL_STOP":

            mt5_type = self.client.ORDER_TYPE_SELL_STOP

        else:

            raise ValueError(
                "order_type must be BUY_STOP or SELL_STOP"
            )

        request = {

            "action": self.client.TRADE_ACTION_PENDING,

            "symbol": instrument,

            "volume": float(volume),

            "type": mt5_type,

            "price": float(entry_price),

            "magic": 20260516,

            "comment": comment,

            "type_time": self.client.ORDER_TIME_GTC,

            "type_filling": self.client.ORDER_FILLING_RETURN,
        }

        # ---------------------------------------------------------------------
        # STOP LOSS
        # ---------------------------------------------------------------------
        if stop_loss is not None:
            request["sl"] = float(stop_loss)

        # ---------------------------------------------------------------------
        # TAKE PROFIT
        # ---------------------------------------------------------------------
        if take_profit is not None:
            request["tp"] = float(take_profit)

        return self._submit_order(request)

    # =========================================================================
    # BUY MARKET
    # =========================================================================
    def buy_market(
        self,
        instrument,
        volume,
        stop_loss=None,
        take_profit=None
    ):

        logging.info(
            f"Placing BUY MARKET order "
            f"for {instrument}"
        )

        return self.place_market_order(
            instrument=instrument,
            volume=abs(volume),
            order_type="BUY",
            stop_loss=stop_loss,
            take_profit=take_profit
        )

    # =========================================================================
    # SELL MARKET
    # =========================================================================
    def sell_market(
        self,
        instrument,
        volume,
        stop_loss=None,
        take_profit=None
    ):

        logging.info(
            f"Placing SELL MARKET order "
            f"for {instrument}"
        )

        return self.place_market_order(
            instrument=instrument,
            volume=abs(volume),
            order_type="SELL",
            stop_loss=stop_loss,
            take_profit=take_profit
        )

    # =========================================================================
    # BUY STOP
    # =========================================================================
    def buy_stop(
        self,
        instrument,
        volume,
        entry_price,
        stop_loss=None,
        take_profit=None
    ):

        logging.info(
            f"Placing BUY STOP "
            f"for {instrument}"
        )

        return self.place_stop_order(
            instrument=instrument,
            volume=abs(volume),
            entry_price=entry_price,
            order_type="BUY_STOP",
            stop_loss=stop_loss,
            take_profit=take_profit
        )

    # =========================================================================
    # SELL STOP
    # =========================================================================
    def sell_stop(
        self,
        instrument,
        volume,
        entry_price,
        stop_loss=None,
        take_profit=None
    ):

        logging.info(
            f"Placing SELL STOP "
            f"for {instrument}"
        )

        return self.place_stop_order(
            instrument=instrument,
            volume=abs(volume),
            entry_price=entry_price,
            order_type="SELL_STOP",
            stop_loss=stop_loss,
            take_profit=take_profit
        )

    # =========================================================================
    # GET OPEN POSITIONS
    # =========================================================================
    def get_open_positions(self):

        positions = self.client.positions_get()

        if positions is None:
            return []

        return positions

    # =========================================================================
    # CHECK IF POSITION EXISTS
    # =========================================================================
    def has_open_position(self, instrument):

        positions = self.client.positions_get(
            symbol=instrument
        )

        if positions is None:
            return False

        return len(positions) > 0

    # =========================================================================
    # GET OPEN TRADES
    # =========================================================================
    def get_open_trades(self):

        positions = self.client.positions_get()

        if positions is None:
            return []

        return positions

    # =========================================================================
    # GET TRADE DETAILS
    # =========================================================================
    def get_open_trade_details(self, instrument):

        positions = self.client.positions_get(
            symbol=instrument
        )

        if positions is None or len(positions) == 0:
            return None

        pos = positions[0]

        return {

            "ticket": pos.ticket,

            "symbol": pos.symbol,

            "type": (
                "BUY"
                if pos.type == self.client.POSITION_TYPE_BUY
                else "SELL"
            ),

            "volume": pos.volume,

            "price": pos.price_open,

            "current_price": pos.price_current,

            "sl": pos.sl,

            "tp": pos.tp,

            "profit": pos.profit,
        }

    # =========================================================================
    # CLOSE POSITION
    # =========================================================================
    def close_position(self, ticket):

        position = self.client.positions_get(
            ticket=ticket
        )

        if not position:

            logging.error(
                f"Position {ticket} not found"
            )

            return None

        position = position[0]

        symbol = position.symbol
        volume = position.volume

        tick = self.client.symbol_info_tick(symbol)

        if position.type == self.client.POSITION_TYPE_BUY:

            order_type = self.client.ORDER_TYPE_SELL
            price = tick.bid

        else:

            order_type = self.client.ORDER_TYPE_BUY
            price = tick.ask

        request = {

            "action": self.client.TRADE_ACTION_DEAL,

            "symbol": symbol,

            "volume": volume,

            "type": order_type,

            "position": ticket,

            "price": price,

            "deviation": 20,

            "magic": 20260516,

            "comment": "Close Position",

            "type_time": self.client.ORDER_TIME_GTC,

            "type_filling": self.client.ORDER_FILLING_IOC,
        }

        return self._submit_order(request)

    # =========================================================================
    # SHUTDOWN
    # =========================================================================
    def shutdown(self):

        try:
            self.client.shutdown()

        except Exception:
            pass