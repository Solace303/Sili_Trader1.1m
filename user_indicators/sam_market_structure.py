"""
sam_market_structure.py
Compact MT5 Version
"""

from __future__ import annotations
import numpy as np
import pandas as pd

# =========================================
# HELPERS
# =========================================
def _utc(ts):

    t=pd.Timestamp(ts)

    t=(
        t.tz_localize("UTC")
        if t.tzinfo is None
        else t.tz_convert("UTC")
    )

    return int(t.timestamp())

def _times(df):

    if isinstance(df.index,pd.DatetimeIndex):

        return df.index.tolist()

    if "time" in df.columns:

        return pd.to_datetime(df["time"]).tolist()

    return df.index.tolist()

# =========================================
# SWINGS
# =========================================
def _swings(h,l,lb,rb):

    sh=[]
    sl=[]

    for i in range(lb,len(h)-rb):

        if (
            h[i]>=h[i-lb:i].max()
            and h[i]>=h[i+1:i+rb+1].max()
        ):

            sh.append(i)

        if (
            l[i]<=l[i-lb:i].min()
            and l[i]<=l[i+1:i+rb+1].min()
        ):

            sl.append(i)

    return sh,sl

# =========================================
# LABEL SWINGS
# =========================================
def _labels(bars,data,bull,bear,high=True):

    out={}
    prev=None

    for b in bars:

        val=float(data[b])

        out[b]=(
            bull
            if prev is None or val>prev
            else bear
        )

        prev=val

    return out

# =========================================
# NEAREST LEFT SWING
# =========================================
def _nearest(arr,bar):

    vals=[x for x in arr if x<bar]

    return vals[-1] if vals else None

# =========================================
# STOP BAR
# =========================================
def _stop(ref, level, data, bull=True):

    for i in range(ref + 1, len(data)):

        if bull:
            if data[i] >= level:
                return i

        else:
            if data[i] <= level:
                return i

    return None

# =========================================
# MAIN
# =========================================
def compute(df,params=None):

    params=params or {}

    lb=max(1,int(params.get("pivot_lb",5)))

    rb=max(1,int(params.get("pivot_rb",5)))

    if len(df)<lb+rb+2:
 
        return {"events":[],"markers":[]}

    # -------------------------------------
    # COLORS
    # -------------------------------------
    bull_bos=params.get("bull_bos_color","#26a69a")

    bear_bos=params.get("bear_bos_color","#ef5350")

    bull_choch=params.get("bull_choch_color","#00bcd4")

    bear_choch=params.get("bear_choch_color","#ff9800")

    # -------------------------------------
    # DATA
    # -------------------------------------
    t=_times(df)

    h=df["high"].values.astype(float)

    l=df["low"].values.astype(float)

    # -------------------------------------
    # DETECT SWINGS
    # -------------------------------------
    sh,sl=_swings(h,l,lb,rb)

    hl=_labels(sh,h,"HH","LH")

    ll=_labels(sl,l,"HL","LL")

    # =====================================
    # MARKERS
    # =====================================
    markers=[]

    for b,x in hl.items():

        markers.append({

            "time":_utc(t[b]),

            "position":"aboveBar",

            "color":"#26a69a"
            if x=="HH"
            else "#ef5350",

            "shape":"circle",

            "size":1,

            "text":x
        })

    for b,x in ll.items():

        markers.append({

            "time":_utc(t[b]),

            "position":"belowBar",

            "color":"#26a69a"
            if x=="HL"
            else "#ef5350",

            "shape":"circle",

            "size":1,

            "text":x
        })

    # =====================================
    # BOS / CHOCH
    # =====================================
    events=[]

    trend=None

    # -------------------------------------
    # BEARISH
    # -------------------------------------
    for i in range(1,len(sh)):

        prev=sh[i-1]

        curr=sh[i]

        if h[curr]>=h[prev]:

            continue

        ref=_nearest(sl,curr)

        if ref is None:

            continue

        level=float(l[ref])

        stop=_stop(ref,level,l,False)
        
        if stop is None:

            continue

        typ=(
            "ChoCh"
            if trend=="UP"
            else "BOS"
        )

        trend="DOWN"

        events.append({

            "type":typ,

            "direction":"DOWN",

            "level":level,

            "from_time":_utc(t[ref]),

            "to_time":_utc(t[stop]),

            "break_time":_utc(t[stop]),

            "marker_position":"belowBar",

            "color":(
                bear_bos
                if typ=="BOS"
                else bear_choch
            )
        })

    # -------------------------------------
    # BULLISH
    # -------------------------------------
    for i in range(1,len(sl)):

        prev=sl[i-1]

        curr=sl[i]

        if l[curr]<=l[prev]:

            continue

        ref=_nearest(sh,curr)

        if ref is None:

            continue

        level=float(h[ref])

        stop=_stop(ref,level,h)
        
        if stop is None:

            continue

        typ=(
            "ChoCh"
            if trend=="DOWN"
            else "BOS"
        )

        trend="UP"

        events.append({

            "type":typ,

            "direction":"UP",

            "level":level,

            "from_time":_utc(t[ref]),

            "to_time":_utc(t[stop]),

            "break_time":_utc(t[stop]),

            "marker_position":"aboveBar",

            "color":(
                bull_bos
                if typ=="BOS"
                else bull_choch
            )
        })

    events.sort(key=lambda x:x["from_time"])

    markers.sort(key=lambda x:x["time"])

    return {
        "events":events,
        "markers":markers
    }

# =========================================
# INDICATOR REGISTRY
# =========================================
INDICATORS={

    "BoS/ChoCh (MT5)":{

        "fn":compute,

        "type":"events",

        "pane":"price",

        "color":"#26a69a",

        "params_def":{

            "pivot_lb":{
                "type":"int",
                "default":5,
                "min":1,
                "max":50
            },

            "pivot_rb":{
                "type":"int",
                "default":5,
                "min":1,
                "max":50
            },

            "breakout_confirm":{
                "type":"select",
                "default":"H/L",
                "options":[
                    "H/L",
                    "Close"
                ]
            }
        },

        "series_def":[]
    }
}