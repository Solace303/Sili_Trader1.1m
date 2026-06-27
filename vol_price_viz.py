from helpers import Utils
from strategy import (
    BOSCRTStrategy,
    analyze_trend_in_range
)
from user_indicators.sam_market_structure import compute

import pandas as pd


# ==========================================================
# CONFIG
# ==========================================================

CSV_PATH = (
    "/run/media/solace/ABBA-2E35/"
    "My_Code/Sili-Trader1.1m/"
    "forex_data/BTCUSDz_M5.csv"
)

OUTPUT_PATH = (
    "/run/media/solace/ABBA-2E35/"
    "My_Code/Sili-Trader1.1m/"
    "forex_data/volume_crt_analysis.csv"
)


# ==========================================================
# LOAD DATA
# ==========================================================

df = pd.read_csv(
    CSV_PATH,
    parse_dates=["time"]
)

df.set_index(
    "time",
    inplace=True
)

df.sort_index(
    inplace=True
)

print(
    f"Loaded {len(df)} candles"
)

# ==========================================================
# BOS EVENTS
# ==========================================================

sms_result = compute(df)

events = sms_result["events"]

results = []

# ==========================================================
# LOOP THROUGH EVERY BOS
# ==========================================================

for event in events:

    if event["type"] != "BOS":
        continue

    direction = event["direction"]

    bos_from_time = pd.to_datetime(
        event["from_time"],
        unit="s",
        utc=True
    )

    # ------------------------------------------------------
    # BOS candle must exist
    # ------------------------------------------------------

    if bos_from_time not in df.index:
        continue

    # ------------------------------------------------------
    # BOS candle must exist
    # ------------------------------------------------------

    if bos_from_time not in df.index:
        continue

    bos_idx = df.index.get_loc(
        bos_from_time
    )

    # ------------------------------------------------------
    # Get BOS candle + neighbors
    # ------------------------------------------------------

    candidate_volumes = []

    # Left candle
    if bos_idx > 0:

        candidate_volumes.append(
            (
                df.index[bos_idx - 1],
                df.iloc[bos_idx - 1]["volume"]
            )
        )

    # BOS candle
    candidate_volumes.append(
        (
            df.index[bos_idx],
            df.iloc[bos_idx]["volume"]
        )
    )

    # Right candle
    if bos_idx < len(df) - 1:

        candidate_volumes.append(
            (
                df.index[bos_idx + 1],
                df.iloc[bos_idx + 1]["volume"]
            )
        )

    # ------------------------------------------------------
    # Use highest volume
    # ------------------------------------------------------

    selected_time, bos_volume = max(
        candidate_volumes,
        key=lambda x: x[1]
    )

    selected_offset = (
        bos_idx
        - df.index.get_loc(selected_time)
    )


    # ======================================================
    # FIND TREND RANGE
    # ======================================================

    try:

        trend_range = Utils.find_trend_range_from_bos(
            df.loc[:bos_from_time]
        )

        if trend_range is None:
            continue

        (
            start_time,
            end_time,
            bos_cluster_direction,
            bos_count
        ) = trend_range

    except Exception:
        continue

    # ======================================================
    # ATR TREND ANALYSIS
    # ======================================================

    try:

        trend_result = analyze_trend_in_range(
            df=df,
            start_time=start_time,
            end_time=end_time,
            timeframe="M5",
            plot=False
        )

        if trend_result is None:
            continue

    except Exception:
        continue

    atr_direction = trend_result[
        "trend_direction"
    ]

    # ======================================================
    # BOS / ATR ALIGNMENT FILTER
    # ======================================================

    valid = (
        (direction == "UP"
         and atr_direction == "Uptrend")
        or
        (direction == "DOWN"
         and atr_direction == "Downtrend")
    )

    if not valid:
        continue

    # ======================================================
    # FIND FIRST CRT
    # ======================================================

    strategy = BOSCRTStrategy(
        "BTCUSDz"
    )

    strategy.last_bos = {
        "direction": direction
    }

    bos_idx = df.index.get_loc(
        bos_from_time
    )

    crt_found = False

    for i in range(
        bos_idx + 1,
        len(df)
    ):

        test_df = df.iloc[: i + 1]

        signal = strategy.crt_confirmation(
            test_df
        )

        if signal is None:
            continue

        crt_candle = df.iloc[i]

        crt_time = crt_candle.name

        crt_volume = crt_candle["volume"]

        volume_change_pct = (
            (bos_volume - crt_volume)
            / bos_volume
         * 100)

        results.append({

        "bos_direction":
        direction,

        "atr_direction":
        atr_direction,

        "bos_count":
        bos_count,

        "bos_time":
        bos_from_time,

        "selected_volume_time":
        selected_time,

        "crt_time":
        crt_time,

        "bos_volume":
        bos_volume,

        "crt_volume":
        crt_volume,

        "volume_change_pct":
        volume_change_pct,

        "signal":
        signal,

        "trend_start":
        start_time,

        "trend_end":
        end_time

    })

        crt_found = True
        break

# ==========================================================
# SAVE RESULTS
# ==========================================================

results_df = pd.DataFrame(results)

results_df.to_csv(
    OUTPUT_PATH,
    index=False
)

print(
    f"\nSaved "
    f"{len(results_df)} records"
)

print(
    f"\nOutput:"
)

print(OUTPUT_PATH)

# ==========================================================
# QUICK STATS
# ==========================================================

if not results_df.empty:

    print("\n========== SUMMARY ==========")

    print(
        results_df[
            "volume_change_pct"
        ].describe()
    )

    print("\nMaximum Increase")

    print(
        results_df.loc[
            results_df[
                "volume_change_pct"
            ].idxmax()
        ]
    )

    print("\nMaximum Decrease")

    print(
        results_df.loc[
            results_df[
                "volume_change_pct"
            ].idxmin()
        ]
    )