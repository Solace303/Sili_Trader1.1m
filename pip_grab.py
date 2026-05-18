import sys
from mt5linux import MetaTrader5

# --- SYSTEM DIRECTORY SETUP ---
MT5_PATH = "/home/solace/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe"
mt5 = MetaTrader5()

if not mt5.initialize(MT5_PATH):
    print("[-] Initialization Failed!")
    sys.exit()

def get_symbol_pip_value(symbol="EURUSD", lot_size=1.0):
    """
    Extracts contract metrics to calculate the precise pip value 
    for any given lot size.
    """
    # 1. Fetch data specifications from the active MT5 server
    info = mt5.symbol_info(symbol)
    
    if info is None:
        print(f"[-] Could not find symbol information for {symbol}")
        return None
        
    # 2. Extract technical parameters
    contract_size = info.trade_contract_size  # Usually 100,000 units
    tick_size = info.tick_size                # e.g., 0.00001 (Point value)
    
    # 3. Handle standard Forex definitions 
    # (A standard pip is 10 points/ticks on modern 5-digit platforms)
    is_jpy = "JPY" in symbol
    pip_size = 0.01 if is_jpy else 0.0001     # Defines the 4th/2nd decimal place standard
    
    # 4. Calculate dynamic tick value in your account currency
    # MT5 calculates this natively under info.trade_tick_value
    tick_value = info.trade_tick_value 
    
    # 5. Convert tick value to a standard Pip Value
    # Since 1 Pip = 10 Ticks/Points on a 5-digit broker:
    pip_value = (pip_size / tick_size) * tick_value * lot_size
    
    return pip_value

# --- EXECUTE THE TEST LOOP ---
target_symbol = "EURUSD"
test_lots = 0.10  # A Mini Lot size

calculated_pip = get_symbol_pip_value(target_symbol, test_lots)

if calculated_pip:
    print(f"\n================ PIP SPECIFICATION ================")
    print(f"Target Asset:       {target_symbol}")
    print(f"Execution Volume:   {test_lots} Lots (Mini Lot)")
    print(f"Value per Pip:      ${calculated_pip:.2f} USD")
    print("====================================================\n")

mt5.shutdown()
