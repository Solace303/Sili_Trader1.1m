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
        filename="/run/media/solace/ABBA-2E35/My_Code/Sili-Trader1.1m/forex_data/trade_journal.csv"
    ):

        self.fetcher = fetcher

        self.filename = filename

        # -------------------------------------------------
        # STATE
        # -------------------------------------------------

        self.loss_streaks = {}

        self.drawdown_start_balance = {}

        self.current_risk_map = {}

        # -------------------------------------------------
        # MODIFIED:
        # TRACK ALL CSV TICKETS
        # -------------------------------------------------

        self.logged_tickets = set()

        # -------------------------------------------------
        # MT5 TICKET TRACKING
        # -------------------------------------------------

        self.last_deal_ticket = 0

        # -------------------------------------------------
        # MODIFIED:
        # CURRENT BALANCE CACHE
        # USED FOR HISTORICAL RECONSTRUCTION
        # -------------------------------------------------

        self.current_balance = None

        # -------------------------------------------------
        # INIT
        # -------------------------------------------------

        self._initialize_file()

        self._load_state()

    # =====================================================
    # INITIALIZE CSV
    # =====================================================

    def _initialize_file(self):

        if (
            not os.path.exists(self.filename)
            or
            os.path.getsize(self.filename) == 0
        ):

            with open(
                self.filename,
                "w",
                newline=""
            ) as f:

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

                    ticket = deal["ticket"]

                    # ---------------------------------
                    # DUPLICATE FILTER
                    # ---------------------------------

                    # -------------------------------------------------
                    # MODIFIED:
                    # SKIP ONLY IF ALREADY IN CSV
                    # -------------------------------------------------
                    if ticket in self.logged_tickets:
                        continue

                    pl = deal["pl"]

                    # ---------------------------------
                    # IGNORE ZERO PROFIT
                    # ---------------------------------

                    if pl == 0:
                        continue

                    pair = deal["pair"]

                    # -------------------------------------------------
                    # MODIFIED:
                    # USE RECONSTRUCTED BALANCE
                    # INSTEAD OF CURRENT ACCOUNT BALANCE
                    # -------------------------------------------------

                    balance = deal["balance_after"]

                    timestamp = deal["timestamp"]

                    side = deal["side"]

                    entry_price = (
                        deal["entry_price"]
                    )

                    exit_price = (
                        deal["exit_price"]
                    )

                    # ---------------------------------
                    # STREAK UPDATE
                    # ---------------------------------

                    outcome, streak = (
                        self._update_streak(
                            pair,
                            pl,
                            deal["balance_after"],
                            deal["balance_before"]
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

                        self.drawdown_start_balance.get(
                            pair
                        ),

                        next_risk
                    ])

                    # ---------------------------------
                    # TRACK WRITTEN TICKET
                    # ---------------------------------

                    self.logged_tickets.add(
                        ticket
                    )

                    # ---------------------------------
                    # UPDATE LAST TICKET
                    # ---------------------------------

                    self.last_deal_ticket = max(
                        self.last_deal_ticket,
                        ticket
                    )

                    logger.info(
                        f"[JOURNAL] Logged trade "
                        f"{ticket} | "
                        f"{pair} | "
                        f"P/L={pl}"
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

            # -----------------------------------------
            # FETCH ALL DEAL HISTORY
            # -----------------------------------------

            date_from = datetime(2000, 1, 1)

            date_to = datetime.now()

            deals = (
                self.fetcher.client.history_deals_get(
                    date_from,
                    date_to
                )
            )

            if deals is None:

                logger.error(
                    "[FETCH ERROR] "
                    "Failed to fetch MT5 history"
                )

                return []

            # -------------------------------------------------
            # MODIFIED:
            # GET CURRENT ACCOUNT BALANCE
            # -------------------------------------------------

            account = (
                self.fetcher.client.account_info()
            )

            if account is None:

                logger.error(
                    "[FETCH ERROR] "
                    "Failed to fetch account info"
                )

                return []

            current_balance = float(
                account.balance
            )

            self.current_balance = current_balance

            # -------------------------------------------------
            # MODIFIED:
            # SORT NEWEST -> OLDEST
            # FOR BALANCE RECONSTRUCTION
            # -------------------------------------------------

            deals = sorted(
                deals,
                key=lambda d: d.time,
                reverse=True
            )

            running_balance = current_balance

            closed_deals = []

            # -----------------------------------------
            # PROCESS DEALS
            # -----------------------------------------

            for d in deals:

                try:

                    # ---------------------------------
                    # ONLY CLOSED DEALS
                    # DEAL_ENTRY_OUT = 1
                    # ---------------------------------

                    if d.entry != 1:
                        continue

                    # ---------------------------------
                    # IGNORE ZERO P/L
                    # ---------------------------------

                    if float(d.profit) == 0:
                        continue

                    # ---------------------------------
                    # DETERMINE SIDE
                    # ---------------------------------

                    if d.type == 0:

                        side = "BUY"

                    elif d.type == 1:

                        side = "SELL"

                    else:

                        side = "UNKNOWN"

                    # =================================================
                    # MODIFIED:
                    # TRUE NET P/L
                    # =================================================

                    net_pl = (

                        float(d.profit)

                        + float(d.swap)

                        + float(d.commission)

                        - float(d.fee)
                    )

                    # =================================================
                    # MODIFIED:
                    # GET POSITION DEALS
                    # =================================================

                    position_deals = (
                        self.fetcher.client.history_deals_get(
                            position=d.position_id
                        )
                    )

                    if not position_deals:
                        continue

                    # ---------------------------------------------
                    # SORT POSITION DEALS
                    # ---------------------------------------------

                    position_deals = sorted(
                        position_deals,
                        key=lambda x: x.time
                    )

                    # ---------------------------------------------
                    # ENTRY DEALS
                    # ---------------------------------------------

                    entry_deals = [

                        pd for pd in position_deals

                        if pd.entry == 0
                    ]

                    # ---------------------------------------------
                    # EXIT DEALS
                    # ---------------------------------------------

                    exit_deals = [

                        pd for pd in position_deals

                        if pd.entry == 1
                    ]

                    # =================================================
                    # MODIFIED:
                    # TRUE WEIGHTED ENTRY PRICE
                    # =================================================

                    total_volume = 0

                    weighted_sum = 0

                    for ed in entry_deals:

                        weighted_sum += (

                            float(ed.price)

                            * float(ed.volume)
                        )

                        total_volume += float(
                            ed.volume
                        )

                    if total_volume > 0:

                        entry_price = (
                            weighted_sum
                            / total_volume
                        )

                    else:

                        entry_price = float(
                            d.price
                        )

                    # =================================================
                    # MODIFIED:
                    # TRUE EXIT PRICE
                    # =================================================

                    if exit_deals:

                        exit_price = float(
                            exit_deals[-1].price
                        )

                    else:

                        exit_price = float(
                            d.price
                        )

                    # =================================================
                    # MODIFIED:
                    # BALANCE RECONSTRUCTION
                    # =================================================

                    balance_after = (
                        running_balance
                    )

                    balance_before = (
                        running_balance
                        - net_pl
                    )

                    # =================================================
                    # CLEAN LOCAL PYTHON DICT
                    # =================================================

                    deal = {

                        "ticket":
                        int(d.ticket),

                        "timestamp":
                        datetime.fromtimestamp(
                            d.time
                        ),

                        "pair":
                        d.symbol,

                        "side":
                        side,

                        "entry_price":
                        float(entry_price),

                        "exit_price":
                        float(exit_price),

                        "pl":
                        float(net_pl),

                        # -----------------------------------------
                        # MODIFIED:
                        # RECONSTRUCTED BALANCES
                        # -----------------------------------------

                        "balance_before":
                        float(balance_before),

                        "balance_after":
                        float(balance_after)
                    }

                    closed_deals.append(deal)

                    # =================================================
                    # MODIFIED:
                    # MOVE BACKWARD THROUGH HISTORY
                    # =================================================

                    running_balance = (
                        balance_before
                    )

                except Exception as e:

                    logger.error(
                        f"[DEAL PARSE ERROR] {e}"
                    )

            # -------------------------------------------------
            # MODIFIED:
            # RETURN OLDEST -> NEWEST
            # SO CSV WRITES CORRECTLY
            # -------------------------------------------------

            closed_deals.reverse()

            return closed_deals

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

                    ticket = int(
                        row["ticket"]
                    )

                    pair = row["pair"]

                    self.logged_tickets.add(ticket)
                    
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
                        row[
                            "next_risk_per_trade"
                        ]
                    )

                    self.current_risk_map[pair] = (
                        risk_val
                    )

                    # ---------------------------------
                    # RESTORE DD BALANCE
                    # ---------------------------------

                    if row[
                        "drawdown_start_balance"
                    ]:

                        self.drawdown_start_balance[
                            pair
                        ] = float(
                            row[
                                "drawdown_start_balance"
                            ]
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
        balance_after,
        balance_before
    ):

        if pair not in self.loss_streaks:

            self.loss_streaks[pair] = 0

            self.current_risk_map[pair] = (
                RISK_CONFIG[
                    "risk_per_trade"
                ]
            )

        # -------------------------------------------------
        # LOSS
        # -------------------------------------------------

        if pl < 0:

            self.loss_streaks[pair] += 1

            if (
                pair
                not in
                self.drawdown_start_balance
            ):

                self.drawdown_start_balance[
                    pair
                ] = balance_before

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
                    self.drawdown_start_balance[
                        pair
                    ]
                )

                recovery = (
                    balance_after - dd_balance
                )

                if (
                    recovery
                    >=
                    dd_balance
                    * RISK_CONFIG[
                        "recovery_trigger"
                    ]
                ):

                    self.loss_streaks[pair] = 0

                    self.current_risk_map[pair] = (
                        RISK_CONFIG[
                            "risk_per_trade"
                        ]
                    )

                    del self.drawdown_start_balance[
                        pair
                    ]

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

            return RISK_CONFIG[
                "risk_per_trade"
            ]

        try:

            with open(
                self.filename,
                "r"
            ) as f:

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
                        self.current_risk_map[
                            pair
                        ] = risk_val

                        return risk_val

        except Exception:
            pass

        return RISK_CONFIG[
            "risk_per_trade"
        ]

    # =====================================================
    # GET CURRENT STREAK
    # =====================================================

    def get_current_streak(self, pair):

        return self.loss_streaks.get(
            pair,
            0
        )