# =========================================================
# trade_journal.py (MT5 VERSION)
# =========================================================
import csv
import os
import logging
from datetime import datetime
from config import RISK_CONFIG

logger = logging.getLogger(__name__)

class TradeJournal:
    def __init__(
        self,
        fetcher,
        filename="trade_journal.csv"
    ):
        self.fetcher = fetcher
        self.filename = filename
        # ---------------------------------------
        # STATE
        # ---------------------------------------
        self.loss_streaks = {}
        self.drawdown_start_balance = {}
        self.current_risk_map = {}
        # MT5 ticket tracking
        self.last_deal_ticket = 0
        self._initialize_file()
        self._load_state()
    # =====================================================
    # INITIALIZE CSV
    # =====================================================
    def _initialize_file(self):
        if (not os.path.exists(self.filename) or os.path.getsize(self.filename) == 0):
            with open(self.filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "ticket",
                    "timestamp",
                    "pair",
                    "side",
                    "entry_price",
                    "exit_price",
                    "pl",
                    "balance",
                    "outcome",
                    "streak",
                    "drawdown_start_balance",
                    "next_risk_per_trade"
                ])
    # =====================================================
    # UPDATE JOURNAL
    # =====================================================
    def update(self):
        deals = self._fetch_closed_deals()
        if not deals:
            return
        with open(
            self.filename,
            "a",
            newline=""
        ) as f:

            writer = csv.writer(f)

            for deal in deals:

                try:

                    ticket = int(deal.ticket)

                    # ---------------------------------
                    # DUPLICATE FILTER
                    # ---------------------------------

                    if ticket <= self.last_deal_ticket:
                        continue

                    # ---------------------------------
                    # PROFIT FILTER
                    # ---------------------------------

                    pl = float(deal.profit)

                    if pl == 0:
                        continue

                    pair = deal.symbol

                    # ---------------------------------
                    # ACCOUNT BALANCE
                    # ---------------------------------

                    account = self.fetcher.get_account_summary()

                    balance = float(account["balance"])

                    # ---------------------------------
                    # TIMESTAMP
                    # ---------------------------------

                    timestamp = datetime.fromtimestamp(
                        deal.time
                    )

                    # ---------------------------------
                    # SIDE
                    # ---------------------------------

                    if deal.type == 0:
                        side = "BUY"

                    elif deal.type == 1:
                        side = "SELL"

                    else:
                        side = "UNKNOWN"

                    # ---------------------------------
                    # PRICES
                    # ---------------------------------

                    entry_price = float(deal.price)

                    exit_price = float(deal.price)

                    # ---------------------------------
                    # STREAK UPDATE
                    # ---------------------------------

                    outcome, streak = (
                        self._update_streak(
                            pair,
                            pl,
                            balance
                        )
                    )

                    next_risk = (
                        self.current_risk_map[pair]
                    )

                    # ---------------------------------
                    # WRITE CSV
                    # ---------------------------------

                    writer.writerow([
                        ticket,
                        timestamp,
                        pair,
                        side,
                        entry_price,
                        exit_price,
                        pl,
                        balance,
                        outcome,
                        streak,
                        self.drawdown_start_balance.get(pair),
                        next_risk
                    ])

                    # ---------------------------------
                    # UPDATE LAST TICKET
                    # ---------------------------------

                    self.last_deal_ticket = max(
                        self.last_deal_ticket,
                        ticket
                    )

                except Exception as e:

                    logger.error(
                        f"[JOURNAL ERROR] {e}"
                    )

    # =====================================================
    # FETCH CLOSED DEALS
    # =====================================================

    def _fetch_closed_deals(self):

        try:

            deals = self.fetcher.get_trade_history()

            if deals is None:
                return []

            return deals

        except Exception as e:

            logger.error(
                f"[FETCH ERROR] {e}"
            )

            return []

    # =====================================================
    # LOAD STATE FROM CSV
    # =====================================================

    def _load_state(self):

        if not os.path.exists(self.filename):
            return

        with open(self.filename, "r") as f:

            reader = csv.DictReader(f)

            for row in reader:

                try:

                    ticket = int(row["ticket"])

                    pair = row["pair"]

                    self.last_deal_ticket = max(
                        self.last_deal_ticket,
                        ticket
                    )

                    # ---------------------------------
                    # RESTORE STREAK
                    # ---------------------------------

                    self.loss_streaks[pair] = int(
                        row["streak"]
                    )

                    # ---------------------------------
                    # RESTORE RISK
                    # ---------------------------------

                    risk_val = float(
                        row["next_risk_per_trade"]
                    )

                    self.current_risk_map[pair] = risk_val

                    # ---------------------------------
                    # RESTORE DD BALANCE
                    # ---------------------------------

                    if row["drawdown_start_balance"]:

                        self.drawdown_start_balance[pair] = (
                            float(
                                row[
                                    "drawdown_start_balance"
                                ]
                            )
                        )

                except Exception:
                    continue

    # =====================================================
    # STREAK LOGIC
    # =====================================================

    def _update_streak(
        self,
        pair,
        pl,
        balance
    ):

        if pair not in self.loss_streaks:

            self.loss_streaks[pair] = 0

            self.current_risk_map[pair] = (
                RISK_CONFIG["risk_per_trade"]
            )

        # -------------------------------------------------
        # LOSS
        # -------------------------------------------------

        if pl < 0:

            self.loss_streaks[pair] += 1

            if pair not in self.drawdown_start_balance:

                self.drawdown_start_balance[pair] = (
                    balance
                )

            # halve risk
            self.current_risk_map[pair] *= 0.5

            return (
                "LOSS",
                self.loss_streaks[pair]
            )

        # -------------------------------------------------
        # WIN
        # -------------------------------------------------

        else:

            if pair in self.drawdown_start_balance:

                dd_balance = (
                    self.drawdown_start_balance[pair]
                )

                recovery = balance - dd_balance

                if (
                    recovery
                    >= dd_balance
                    * RISK_CONFIG["recovery_trigger"]
                ):

                    self.loss_streaks[pair] = 0

                    self.current_risk_map[pair] = (
                        RISK_CONFIG["risk_per_trade"]
                    )

                    del self.drawdown_start_balance[pair]

            return (
                "WIN",
                self.loss_streaks[pair]
            )

    # =====================================================
    # GET PAIR RISK
    # =====================================================

    def get_pair_risk(self, pair):

        # ---------------------------------------------
        # FAST PATH
        # ---------------------------------------------

        if pair in self.current_risk_map:

            return self.current_risk_map[pair]

        # ---------------------------------------------
        # CSV FALLBACK
        # ---------------------------------------------

        if not os.path.exists(self.filename):

            return RISK_CONFIG["risk_per_trade"]

        try:

            with open(self.filename, "r") as f:

                reader = list(
                    csv.DictReader(f)
                )

                for row in reversed(reader):

                    if row["pair"] == pair:

                        risk_val = float(
                            row[
                                "next_risk_per_trade"
                            ]
                        )

                        # sync memory
                        self.current_risk_map[pair] = (
                            risk_val
                        )

                        return risk_val

        except Exception:
            pass

        return RISK_CONFIG["risk_per_trade"]

    # =====================================================
    # GET CURRENT STREAK
    # =====================================================

    def get_current_streak(self, pair):

        return self.loss_streaks.get(pair, 0)