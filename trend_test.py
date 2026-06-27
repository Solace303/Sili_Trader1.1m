from data import CandleFetcher
from strategy import analyze_trend_in_range
from helpers import Utils
from config import BMA_CONFIG

fetcher = CandleFetcher()

candle_data = fetcher.get_candles(
    instrument=BMA_CONFIG["instruments"],
    granularity=BMA_CONFIG["monitor_tf"],
    count=1320 #5 days data
)

result = Utils.find_trend_range_from_bos(candle_data)

if result is None:

    print("No BOS found")
    exit()

start_time, end_time, direction, bos_count = result

print(f"Direction : {direction}")
print(f"BOS Count : {bos_count}")
print(f"Start Time: {start_time}")
print(f"End Time  : {end_time}") 

trend = analyze_trend_in_range(
    df=candle_data,
    start_time=start_time,
    end_time=end_time,
    timeframe=BMA_CONFIG["monitor_tf"],
    price_column="close",
    plot=True
)

print(trend)