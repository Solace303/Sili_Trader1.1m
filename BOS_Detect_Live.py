import sys
import pandas as pd
from datetime import datetime,UTC
from mt5linux import MetaTrader5
from user_indicators.sam_market_structure import compute

# =====================================
# MT5 CONFIG
# =====================================
MT5_PATH="/home/solace/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe"
SYMBOL="BTCUSDz"
TIMEFRAME=MetaTrader5.TIMEFRAME_M5
COUNT=1320 #2 days data

mt5=MetaTrader5()

if not mt5.initialize(MT5_PATH):
    print("[-] MT5 Initialization Failed!")
    sys.exit()

# =====================================
# FETCH MT5 CANDLES
# =====================================
def fetch_candles(symbol,timeframe,count=200):

    rates=mt5.copy_rates_from_pos(
        symbol,
        timeframe,
        0,
        count
    )

    if rates is None:
        print(f"[-] Failed to fetch: {symbol}")
        return pd.DataFrame()

    df=pd.DataFrame(rates)

    df["time"]=pd.to_datetime(
        df["time"],
        unit="s"
    )

    df.rename(
        columns={
            "tick_volume":"volume"
        },
        inplace=True
    )

    df.set_index(
        "time",
        inplace=True
    )

    return df[
        [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    ]

# =====================================
# FEATURE ENGINEERING
# =====================================
def add_features(df):

    df["candle_type"]="Neutral"

    df.loc[
        df["close"]>df["open"],
        "candle_type"
    ]="Bullish"

    df.loc[
        df["close"]<df["open"],
        "candle_type"
    ]="Bearish"

    df["body_size"]=(
        df["close"]-df["open"]
    ).abs()

    df["upper_wick"]=(
        df["high"]
        -df[
            ["open","close"]
        ].max(axis=1)
    )

    df["lower_wick"]=(
        df[
            ["open","close"]
        ].min(axis=1)
        -df["low"]
    )

    return df

# =====================================
# MAIN
# =====================================
def run():

    df=fetch_candles(
        SYMBOL,
        TIMEFRAME,
        COUNT
    )

    if df.empty:
        return

    df=add_features(df)

    params={
        "pivot_lb":5,
        "pivot_rb":5,
        "breakout_confirm":"Close",
        "show_bos":True,
        "show_choch":False,
        "show_hh_ll":False,
        "show_hl_lh":False
    }

    result=compute(
        df,
        params=params
    )

    events=result["events"]

    print("\n"+"="*40)
    print("BOS / CHoCH EVENTS")
    print("="*40)

    print(
        f"LB={params['pivot_lb']} | "
        f"RB={params['pivot_rb']}\n"
    )

    for e in events:

        print(
            f"{e['type']} "
            f"({e['direction']})"
        )

        print(f"Level: {e['level']}")

        print(
            f"From:  "
            f"{datetime.fromtimestamp(e['from_time'],UTC)}"
        )

        print(
            f"To:    "
            f"{datetime.fromtimestamp(e['to_time'],UTC)}"
        )

        print(
            f"Break: "
            f"{datetime.fromtimestamp(e['break_time'],UTC)}"
        )

        print("-"*40)

    print(
        f"\nTotal Events: "
        f"{len(events)}\n"
    )

# =====================================
# ENTRY
# =====================================
if __name__=="__main__":
    run()
    mt5.shutdown()