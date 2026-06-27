import sys
import time
import logging
from data import CandleFetcher
from trade_journal import TradeJournal
from risk_manager import RiskManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def main():

    print("****"*5 + " MT5 RISK CALCULATOR " + "****"*5)
    print("Adaptive MT5 lot size calculator with dynamic risk management.\n")

    # ==========================
    # LOADING ANIMATION
    # ==========================
    base_text = "Initializing system components"

    for _ in range(3):
        for i in range(6):
            sys.stdout.write(f"\r{base_text}{'.'*i}".ljust(len(base_text)+5))
            sys.stdout.flush()
            time.sleep(0.1)

    # ==========================
    # DEFAULTS
    # ==========================
    default_inst = "EURUSDz"
    default_entry = 1.17911
    default_sl = 1.17379
    default_tp = 1.18500
    default_lot = "micro"
    default_type = "BUY"

    print("\nEnter trade details (Press Enter for defaults):\n")

    INSTRUMENT = input(f"INSTRUMENT [default: {default_inst}]: ") or default_inst

    val_entry = input(f"ENTRY PRICE [default: {default_entry}]: ")
    ENTRY_PRICE = float(val_entry) if val_entry else default_entry

    val_sl = input(f"STOP LOSS [default: {default_sl}]: ")
    STOP_LOSS = float(val_sl) if val_sl else default_sl

    val_tp = input(f"TAKE PROFIT [default: {default_tp}]: ")
    TAKE_PROFIT = float(val_tp) if val_tp else default_tp

    LOT_TYPE = input(f"LOT TYPE [default: {default_lot}]: ") or default_lot

    trade_type = input(f"TRADE TYPE (BUY/SELL) [default: {default_type}]: ") or default_type
    trade_type = trade_type.upper()

    # ==========================
    # VALIDATE TP
    # ==========================
    if trade_type == "BUY" and TAKE_PROFIT <= ENTRY_PRICE:
        print("❌ Invalid TP for BUY (TP must be above entry)")
        return

    if trade_type == "SELL" and TAKE_PROFIT >= ENTRY_PRICE:
        print("❌ Invalid TP for SELL (TP must be below entry)")
        return

    print(f"\nInitializing MT5 system for {INSTRUMENT}...")

    # ==========================
    # INIT SYSTEM
    # ==========================
    fetcher = CandleFetcher()

    try:
        fetcher.start_price_stream()
        time.sleep(2)

    except Exception as e:
        logger.error(f"Failed to start price stream: {e}")
        return

    journal = TradeJournal(fetcher)

    current_streak = journal.get_current_streak(INSTRUMENT)
    current_risk = journal.get_pair_risk(INSTRUMENT)

    logger.info(
        f"Loaded history for {INSTRUMENT}: "
        f"Streak={current_streak}, "
        f"Next Risk={current_risk:.4f}"
    )

    risk = RiskManager(fetcher, journal)

    # ==========================
    # COMPUTE PARAMETERS
    # ==========================
    params = risk.compute_trade_parameters(
        instrument=INSTRUMENT,
        entry=ENTRY_PRICE,
        stop=STOP_LOSS,
        take_profit=TAKE_PROFIT,
        trade_type=trade_type,
        lot_type=LOT_TYPE
    )

    print(f"\r{base_text}... Done!")

    # ==========================
    # HANDLE REJECTION
    # ==========================
    if params is None:
        print("\n" + "="*40)
        print("🚫 TRADE REJECTED")
        print("="*40)
        print("Reason: Risk-to-Reward ratio below 1:1")
        print("="*40)
        return

    # ==========================
    # PIP DISTANCE
    # ==========================
    pip_mult = 100 if "JPY" in INSTRUMENT else 10000

    pip_distance = abs(
        ENTRY_PRICE - STOP_LOSS
    ) * pip_mult

    # ==========================
    # DISPLAY RESULTS
    # ==========================
    print("\n" + "="*40)
    print(f"TRADE PARAMETERS: {INSTRUMENT}")
    print("="*40)
    print(f"Trade Type:       {trade_type}")
    print(f"Entry Price:      {ENTRY_PRICE}")
    print(f"Stop Loss:        {STOP_LOSS}")
    print(f"Take Profit:      {TAKE_PROFIT}")
    print(f"Pip Distance:     {pip_distance:.1f} pips")
    print("-"*40)
    print(f"Loss Streak:      {current_streak}")
    print(
        f"Active Risk %:    "
        f"{params['risk_percent']:.4f} "
        f"({params['risk_percent']*100:.2f}%)"
    )
    print(f"Lots:             {params['lots']}")
    print(f"Units:            {params['units']}")
    print("-"*40)
    print(f"Risk Amount:      {params['risk_amount']:.2f}")
    print(f"Potential Profit: {params['potential_profit']:.2f}")
    print(f"Risk:Reward:      {params['risk_reward_ratio']}")
    print("="*40)

if __name__ == "__main__":
    main()