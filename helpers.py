import pandas as pd
from config import TREND_CONFIG
from user_indicators.sam_market_structure import compute


ATR_PERIOD = TREND_CONFIG["ATR_PERIOD"]

class Utils:

    @staticmethod
    def calculate_atr(df):

        high_low = df["high"] - df["low"]

        high_prev = (
            df["high"] -
            df["close"].shift(1)
        ).abs()

        low_prev = (
            df["low"] -
            df["close"].shift(1)
        ).abs()

        tr = pd.concat(
            [
                high_low,
                high_prev,
                low_prev
            ],
            axis=1
        ).max(axis=1)

        return tr.tail(ATR_PERIOD).mean()
    
    def find_trend_range_from_bos(df):

        result = compute(df)

        events = result["events"]

        if not events:
            return None

        # ---------------------------------------
        # Keep BOS only
        # ---------------------------------------
        bos_events = [
            e for e in events
            if e["type"] == "BOS"
        ]

        if not bos_events:
            return None

        # ---------------------------------------
        # Latest BOS
        # ---------------------------------------
        latest_bos = bos_events[-1]

        target_direction = latest_bos["direction"]

        consecutive_bos = [latest_bos]

        # ---------------------------------------
        # Walk backwards through printed order
        # ---------------------------------------
        for event in reversed(bos_events[:-1]):

            if event["direction"] == target_direction:

                consecutive_bos.append(event)

            else:
                break

        # ---------------------------------------
        # More than one BOS same direction
        # ---------------------------------------
        if len(consecutive_bos) > 1:

            oldest_bos = consecutive_bos[-1]
            newest_bos = consecutive_bos[0]

            start_time = pd.to_datetime(
                oldest_bos["from_time"],
                unit="s",
                utc=True
            )

            end_time = pd.to_datetime(
                newest_bos["to_time"],
                unit="s",
                utc=True
            )

        # ---------------------------------------
        # Only one BOS
        # ---------------------------------------
        else:

            start_time = pd.to_datetime(
                latest_bos["from_time"],
                unit="s",
                utc=True
            )

            end_time = df.index[-1]

        return (
            start_time,
            end_time,
            target_direction,
            len(consecutive_bos)
        )