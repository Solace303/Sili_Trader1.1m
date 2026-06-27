# =========================================================
# trade_journal_live_test.py
# =========================================================
#
# LIVE TEST FOR UPDATED trade_journal.py
#
# TESTS:
# 1. MT5 connection
# 2. Closed deal fetching
# 3. Balance reconstruction
# 4. True weighted entry prices
# 5. True exit prices
# 6. Journal CSV writing
# 7. Streak/risk tracking
#
# =========================================================

import logging
import csv
import os

from data import CandleFetcher
from trade_journal import TradeJournal

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

logger = logging.getLogger(__name__)

# =========================================================
# CONFIG
# =========================================================

CSV_FILE = (
    "/run/media/solace/ABBA-2E35/"
    "My_Code/Sili-Trader1.1m/"
    "forex_data/trade_journal.csv"
)

# =========================================================
# DISPLAY CSV
# =========================================================

def show_latest_csv_rows(
    filename,
    rows=10
):

    if not os.path.exists(filename):

        print("\n[-] CSV file does not exist")
        return

    with open(filename, "r") as f:

        reader = list(csv.reader(f))

        if len(reader) <= 1:

            print("\n[-] CSV contains no trade data")
            return

        print("\n" + "=" * 80)
        print("LATEST CSV ROWS")
        print("=" * 80)

        for row in reader[-rows:]:

            print(row)

        print("=" * 80)

# =========================================================
# MAIN TEST
# =========================================================

def main():

    print("\n" + "=" * 80)
    print("LIVE MT5 TRADE JOURNAL TEST")
    print("=" * 80)

    # =====================================================
    # INITIALIZE FETCHER
    # =====================================================

    try:

        fetcher = CandleFetcher()

        fetcher.start_price_stream()

        print("[+] CandleFetcher initialized")

    except Exception as e:

        print(
            f"[-] Failed to initialize "
            f"CandleFetcher: {e}"
        )

        return

    # =====================================================
    # INITIALIZE JOURNAL
    # =====================================================

    try:

        journal = TradeJournal(
            fetcher=fetcher,
            filename=CSV_FILE
        )

        print("[+] TradeJournal initialized")

    except Exception as e:

        print(
            f"[-] Failed to initialize "
            f"TradeJournal: {e}"
        )

        return

    # =====================================================
    # FETCH CLOSED DEALS
    # =====================================================

    print("\n" + "=" * 80)
    print("FETCHING CLOSED DEALS")
    print("=" * 80)

    deals = journal._fetch_closed_deals()

    if not deals:

        print("[-] No closed deals found")

        return

    print(
        f"[+] Closed deals fetched: "
        f"{len(deals)}"
    )

    # =====================================================
    # DISPLAY DEALS
    # =====================================================

    print("\n" + "=" * 80)
    print("DEAL INSPECTION")
    print("=" * 80)

    for d in deals[-10:]:

        print("\n" + "-" * 80)

        print(
            f"Ticket: "
            f"{d['ticket']}"
        )

        print(
            f"Timestamp: "
            f"{d['timestamp']}"
        )

        print(
            f"Pair: "
            f"{d['pair']}"
        )

        print(
            f"Side: "
            f"{d['side']}"
        )

        print(
            f"Entry Price: "
            f"{d['entry_price']}"
        )

        print(
            f"Exit Price: "
            f"{d['exit_price']}"
        )

        print(
            f"P/L: "
            f"{d['pl']}"
        )

        print(
            f"Balance Before: "
            f"{d['balance_before']}"
        )

        print(
            f"Balance After: "
            f"{d['balance_after']}"
        )

    # =====================================================
    # RUN JOURNAL UPDATE
    # =====================================================

    print("\n" + "=" * 80)
    print("RUNNING JOURNAL UPDATE")
    print("=" * 80)

    old_ticket = journal.last_deal_ticket

    print(
        f"Old Last Ticket: "
        f"{old_ticket}"
    )

    journal.update()

    print(
        f"New Last Ticket: "
        f"{journal.last_deal_ticket}"
    )

    # =====================================================
    # DISPLAY MEMORY STATE
    # =====================================================

    print("\n" + "=" * 80)
    print("MEMORY STATE")
    print("=" * 80)

    print(
        f"Loss Streaks:\n"
        f"{journal.loss_streaks}"
    )

    print(
        f"\nRisk Map:\n"
        f"{journal.current_risk_map}"
    )

    print(
        f"\nDrawdown Start Balances:\n"
        f"{journal.drawdown_start_balance}"
    )

    # =====================================================
    # SHOW CSV RESULTS
    # =====================================================

    show_latest_csv_rows(
        CSV_FILE,
        rows=15
    )

    # =====================================================
    # RECONSTRUCTION VERIFICATION
    # =====================================================

    print("\n" + "=" * 80)
    print("BALANCE RECONSTRUCTION VERIFICATION")
    print("=" * 80)

    if len(deals) >= 2:

        latest = deals[-1]

        print(
            f"Most Recent Balance After: "
            f"{latest['balance_after']}"
        )

        print(
            f"Most Recent Net P/L: "
            f"{latest['pl']}"
        )

        reconstructed = (

            latest["balance_after"]

            - latest["pl"]
        )

        print(
            f"Reconstructed Previous Balance: "
            f"{reconstructed}"
        )

        print(
            f"Stored Previous Balance: "
            f"{latest['balance_before']}"
        )

    # =====================================================
    # FINISHED
    # =====================================================

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()