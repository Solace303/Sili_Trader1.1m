# =========================================================
# risk_manager.py (MT5 VERSION)
# =========================================================

import logging

from config import LOT_SIZE_CONFIG

logger = logging.getLogger(__name__)


class RiskManager:

    def __init__(self, fetcher, journal):

        self.fetcher = fetcher
        self.journal = journal

    # =====================================================
    # CURRENT PRICE
    # =====================================================

    def _mid(self, instrument):

        return float(
            self.fetcher.get_current_price(instrument)
        )

    # =====================================================
    # EXCHANGE RATE
    # =====================================================

    def _exchange_rate(self, from_ccy, to_ccy):

        if from_ccy == to_ccy:
            return 1.0

        try:
            return self._mid(f"{from_ccy}{to_ccy}")

        except:

            try:
                return 1 / self._mid(f"{to_ccy}{from_ccy}")

            except:

                # -----------------------------------------
                # Fallback through USD
                # -----------------------------------------

                a = self._mid(f"{from_ccy}USD")
                b = self._mid(f"USD{to_ccy}")

                return a * b

    # =====================================================
    # PIP SIZE
    # =====================================================

    def get_pip_size(self, instrument):

        # JPY pairs use 0.01
        if "JPY" in instrument:
            return 0.01

        return 0.0001

    # =====================================================
    # PIP VALUE
    # =====================================================

    def calculate_pip_value(
        self,
        instrument,
        account_currency,
        lot_type="standard"
    ):

        base = instrument[:3]
        quote = instrument[3:]

        pip_size = self.get_pip_size(instrument)

        contract_size = LOT_SIZE_CONFIG[lot_type]

        pip_value_quote = pip_size * contract_size

        rate = self._exchange_rate(
            quote,
            account_currency
        )

        return pip_value_quote * rate

    # =====================================================
    # LOT SIZE
    # =====================================================

    def calculate_lot_size(
        self,
        instrument,
        entry,
        stop,
        lot_type="standard"
    ):

        account = self.fetcher.get_account_summary()

        balance = account["balance"]

        currency = account["currency"]

        # ---------------------------------------------
        # Dynamic pair risk from journal
        # ---------------------------------------------

        risk_percent = self.journal.get_pair_risk(
            instrument
        )

        risk_amount = balance * risk_percent

        pip_size = self.get_pip_size(instrument)

        sl_pips = abs(entry - stop) / pip_size

        pip_value = self.calculate_pip_value(
            instrument,
            currency,
            lot_type
        )

        if sl_pips == 0:
            return 0

        lot_size = risk_amount / (
            sl_pips * pip_value
        )

        logger.info(
            f"[RISK] {instrument} | "
            f"risk={risk_percent:.4f} | "
            f"balance={balance} | "
            f"lot={lot_size}"
        )

        return round(lot_size, 2)

    # =====================================================
    # CALCULATE UNITS
    # =====================================================

    def calculate_units(
        self,
        lot_size,
        lot_type="standard"
    ):

        return int(
            lot_size * LOT_SIZE_CONFIG[lot_type]
        )

    # =====================================================
    # RISK AMOUNT
    # =====================================================

    def calculate_risk_amount(self, instrument):

        account = self.fetcher.get_account_summary()

        balance = account["balance"]

        risk_percent = self.journal.get_pair_risk(
            instrument
        )

        return balance * risk_percent

    # =====================================================
    # POTENTIAL PROFIT
    # =====================================================

    def calculate_potential_profit(
        self,
        entry,
        take_profit,
        position_size,
        trade_type
    ):

        if trade_type == "BUY":

            price_diff = (
                take_profit - entry
            )

        elif trade_type == "SELL":

            price_diff = (
                entry - take_profit
            )

        else:

            raise ValueError(
                "trade_type must be BUY or SELL"
            )

        return price_diff * position_size

    # =====================================================
    # MAIN PIPELINE
    # =====================================================

    def compute_trade_parameters(
        self,
        instrument,
        entry,
        stop,
        take_profit,
        trade_type,
        lot_type="standard"
    ):

        # ---------------------------------------------
        # LOT SIZE
        # ---------------------------------------------

        lot_size = self.calculate_lot_size(
            instrument,
            entry,
            stop,
            lot_type
        )

        # ---------------------------------------------
        # UNITS
        # ---------------------------------------------

        units = self.calculate_units(
            lot_size,
            lot_type
        )

        # ---------------------------------------------
        # RISK AMOUNT
        # ---------------------------------------------

        risk_amount = self.calculate_risk_amount(
            instrument
        )

        stop_distance = abs(entry - stop)

        if stop_distance == 0:
            return None

        # ---------------------------------------------
        # POSITION SIZE
        # ---------------------------------------------

        position_size = units

        # ---------------------------------------------
        # POTENTIAL PROFIT
        # ---------------------------------------------

        potential_profit = (
            self.calculate_potential_profit(
                entry,
                take_profit,
                position_size,
                trade_type
            )
        )

        if risk_amount == 0:
            return None

        # ---------------------------------------------
        # REWARD RATIO
        # ---------------------------------------------

        reward_ratio = (
            potential_profit / risk_amount
        )

        # ---------------------------------------------
        # MINIMUM RR FILTER
        # ---------------------------------------------

        if reward_ratio < 1.0:

            logger.info(
                f"[FILTER] Trade rejected "
                f"(R:R < 1) → {reward_ratio:.2f}"
            )

            return None

        rr_ratio = f"1:{round(reward_ratio, 2)}"

        # =================================================
        # FINAL RETURN
        # =================================================

        return {

            # -----------------------------------------
            # MT5 EXECUTION
            # -----------------------------------------

            "lots": lot_size,

            # -----------------------------------------
            # OPTIONAL LEGACY
            # -----------------------------------------

            "units": units,

            # -----------------------------------------
            # RISK INFO
            # -----------------------------------------

            "risk_percent": self.journal.get_pair_risk(
                instrument
            ),

            "risk_amount": risk_amount,

            "potential_profit": potential_profit,

            "risk_reward_ratio": rr_ratio,

            # -----------------------------------------
            # TRADE INFO
            # -----------------------------------------

            "trade_type": trade_type,

            "entry_price": entry,

            "stop_loss": stop,

            "take_profit": take_profit,
        }