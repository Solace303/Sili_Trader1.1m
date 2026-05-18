# =========================================================
# trade_journal_test.py (MT5 VERSION)
# Compact + Clean + Fully Commented
# =========================================================
import time
import logging
from data import CandleFetcher
from trade_journal import TradeJournal
from risk_manager import RiskManager
# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO)
# =========================================================
# MAIN
# =========================================================
def main():
    # -----------------------------------------------------
    # INITIALIZE FETCHER + STREAM
    # -----------------------------------------------------
    fetcher=CandleFetcher()
    fetcher.start_price_stream()
    # -----------------------------------------------------
    # INITIALIZE JOURNAL + RISK ENGINE
    # -----------------------------------------------------
    journal=TradeJournal(fetcher)
    risk=RiskManager(fetcher,journal)
    print("\n🚀 MT5 Risk Engine Started...\n")
    # -----------------------------------------------------
    # TEST PAIR
    # MT5 format example:
    # EURUSD / GBPUSD / XAUUSD
    # -----------------------------------------------------
    test_pair="EURUSD"
    while True:
        try:
            # -------------------------------------------------
            # UPDATE TRADE JOURNAL
            # Sync latest MT5 closed trades
            # -------------------------------------------------
            journal.update()
            # -------------------------------------------------
            # GET CURRENT DYNAMIC RISK
            # -------------------------------------------------
            current_risk=journal.get_pair_risk(test_pair)
            # -------------------------------------------------
            # GET LIVE PRICE
            # -------------------------------------------------
            entry=float(fetcher.get_current_price(test_pair))
            # -------------------------------------------------
            # DEFINE TRADE TYPE
            # Later connect this to strategy signals
            # -------------------------------------------------
            trade_type="BUY"
            # ------------------------------------------------
            # DEFINE SL / TP
            # -------------------------------------------------
            if trade_type=="BUY":
                stop=entry-0.0050
                take_profit=entry+0.0050
            else:
                stop=entry+0.0050
                take_profit=entry-0.0050
            # -------------------------------------------------
            # COMPUTE RISK PARAMETERS
            # -------------------------------------------------
            params=risk.compute_trade_parameters(
                instrument=test_pair,
                entry=entry,
                stop=stop,
                take_profit=take_profit,
                trade_type=trade_type
            )
            # -------------------------------------------------
            # DISPLAY HEADER
            # -------------------------------------------------
            print("\n==============================")
            print(f"PAIR: {test_pair}")
            print(f"TRADE TYPE: {trade_type}")
            print(f"ENTRY: {entry:.5f}")
            print(f"STOP LOSS: {stop:.5f}")
            print(f"TAKE PROFIT: {take_profit:.5f}")
            print(f"CURRENT RISK %: {current_risk:.4f}")
            # -------------------------------------------------
            # HANDLE FILTERED TRADE
            # -------------------------------------------------
            if params is None:
                print("🚫 TRADE REJECTED (R:R < 1)")
                print("==============================\n")
                time.sleep(5)
                continue
            # -------------------------------------------------
            # DISPLAY FINAL RISK DATA
            # -------------------------------------------------
            print(f"LOTS: {params['lots']}")
            print(f"UNITS: {params['units']}")
            print(f"RISK AMOUNT: {params['risk_amount']:.2f}")
            print(f"POTENTIAL PROFIT: {params['potential_profit']:.2f}")
            print(f"RISK:REWARD: {params['risk_reward_ratio']}")
            print("==============================\n")
        except Exception as e:
            print(f"[ERROR] {e}")
# =========================================================
# ENTRY POINT
# =========================================================
if __name__=="__main__":
    main()