# =========================================================
# mt5_balance_reconstruction_test.py
# =========================================================
#
# TESTS:
# 1. Historical balance reconstruction
# 2. True entry price retrieval
# 3. True exit price retrieval
# 4. Position-based MT5 deal grouping
#
# =========================================================

from mt5linux import MetaTrader5

from datetime import datetime

from config import (
    MT5_ACCOUNT_ID,
    MT5_PASSWORD,
    MT5_SERVER
)

# =========================================================
# MT5 INIT
# =========================================================

mt5 = MetaTrader5()

if not mt5.initialize(
    login=MT5_ACCOUNT_ID,
    password=MT5_PASSWORD,
    server=MT5_SERVER
):

    print(
        f"[-] MT5 Initialize Failed: "
        f"{mt5.last_error()}"
    )

    quit()

print("[+] Connected to MT5")

# =========================================================
# GET CURRENT ACCOUNT BALANCE
# =========================================================

account_info = mt5.account_info()

if account_info is None:

    print("[-] Failed to fetch account info")

    mt5.shutdown()

    quit()

current_balance = float(
    account_info.balance
)

print(
    f"\nCurrent Account Balance: "
    f"{current_balance}"
)

# =========================================================
# FETCH FULL DEAL HISTORY
# =========================================================

date_from = datetime(2000, 1, 1)

date_to = datetime.now()

deals = mt5.history_deals_get(
    date_from,
    date_to
)

if deals is None:

    print(
        f"[-] Failed to fetch history: "
        f"{mt5.last_error()}"
    )

    mt5.shutdown()

    quit()

print(
    f"[+] Total MT5 Deals Found: "
    f"{len(deals)}"
)

# =========================================================
# SORT NEWEST -> OLDEST
# =========================================================

deals = sorted(
    deals,
    key=lambda d: d.time,
    reverse=True
)

# =========================================================
# BALANCE RECONSTRUCTION
# =========================================================

running_balance = current_balance

print("\n" + "=" * 80)
print("BALANCE RECONSTRUCTION TEST")
print("=" * 80)

for d in deals:

    try:

        # -------------------------------------------------
        # CLOSED DEALS ONLY
        # DEAL_ENTRY_OUT = 1
        # -------------------------------------------------

        if d.entry != 1:
            continue

        # -------------------------------------------------
        # NET P/L
        # -------------------------------------------------

        net_pl = (

            float(d.profit)

            + float(d.swap)

            + float(d.commission)

            - float(d.fee)
        )

        # -------------------------------------------------
        # GET ALL POSITION DEALS
        # -------------------------------------------------

        position_deals = mt5.history_deals_get(
            position=d.position_id
        )

        if not position_deals:
            continue

        # -------------------------------------------------
        # SORT POSITION DEALS
        # -------------------------------------------------

        position_deals = sorted(
            position_deals,
            key=lambda x: x.time
        )

        # -------------------------------------------------
        # ENTRY PRICE
        # -------------------------------------------------

        entry_deals = [

            pd for pd in position_deals

            if pd.entry == 0
        ]

        # -------------------------------------------------
        # EXIT DEALS
        # -------------------------------------------------

        exit_deals = [

            pd for pd in position_deals

            if pd.entry == 1
        ]

        # -------------------------------------------------
        # WEIGHTED ENTRY PRICE
        # -------------------------------------------------

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

            entry_price = None

        # -------------------------------------------------
        # EXIT PRICE
        # LAST EXIT DEAL
        # -------------------------------------------------

        if exit_deals:

            exit_price = float(
                exit_deals[-1].price
            )

        else:

            exit_price = None

        # -------------------------------------------------
        # RECONSTRUCT HISTORICAL BALANCE
        # -------------------------------------------------

        historical_balance = (
            running_balance - net_pl
        )

        # -------------------------------------------------
        # DISPLAY
        # -------------------------------------------------

        print("\n" + "-" * 80)

        print(
            f"Ticket: "
            f"{d.ticket}"
        )

        print(
            f"Position ID: "
            f"{d.position_id}"
        )

        print(
            f"Time: "
            f"{datetime.fromtimestamp(d.time)}"
        )

        print(
            f"Symbol: "
            f"{d.symbol}"
        )

        print(
            f"Deal Type: "
            f"{d.type}"
        )

        print(
            f"Volume: "
            f"{d.volume}"
        )

        print(
            f"Profit: "
            f"{d.profit}"
        )

        print(
            f"Swap: "
            f"{d.swap}"
        )

        print(
            f"Commission: "
            f"{d.commission}"
        )

        print(
            f"Fee: "
            f"{d.fee}"
        )

        print(
            f"Net P/L: "
            f"{net_pl}"
        )

        print(
            f"Weighted Entry Price: "
            f"{entry_price}"
        )

        print(
            f"Exit Price: "
            f"{exit_price}"
        )

        print(
            f"Balance AFTER Trade: "
            f"{running_balance}"
        )

        print(
            f"Balance BEFORE Trade: "
            f"{historical_balance}"
        )

        # -------------------------------------------------
        # MOVE BACKWARD
        # -------------------------------------------------

        running_balance = (
            historical_balance
        )

    except Exception as e:

        print(
            f"[ERROR] {e}"
        )

# =========================================================
# FINAL RESULT
# =========================================================

print("\n" + "=" * 80)
print("FINAL RECONSTRUCTED BALANCE")
print("=" * 80)

print(
    f"Earliest reconstructed balance: "
    f"{running_balance}"
)

# =========================================================
# SHUTDOWN
# =========================================================

mt5.shutdown()

print("\n[+] MT5 Shutdown Complete")