#=====================================
#Test code for Depth of Market
#=====================================

import time
from pprint import pprint
from data import CandleFetcher

fetcher=CandleFetcher()

fetcher.stream_running=True

fetcher.start_dom_stream("GBPUSD")

while True:
    try:
        dom=fetcher.get_dom("GBPUSD")

        pprint(dom)

    except KeyboardInterrupt:
        break

fetcher.shutdown()