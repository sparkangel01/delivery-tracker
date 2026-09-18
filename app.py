import os
import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

TWELVE_KEY = os.environ.get("TWELVE_DATA_API_KEY", "")
TWELVE_BASE = "https://api.twelvedata.com"

SYMBOL_MAP = {
    "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD", "USDJPY": "USD/JPY",
    "USDCHF": "USD/CHF", "AUDUSD": "AUD/USD", "NZDUSD": "NZD/USD",
    "USDCAD": "USD/CAD", "EURGBP": "EUR/GBP", "EURJPY": "EUR/JPY",
    "GBPJPY": "GBP/JPY", "AUDJPY": "AUD/JPY", "CADJPY": "CAD/JPY",
    "CHFJPY": "CHF/JPY", "NZDJPY": "NZD/JPY",
    "XAUUSD": "XAU/USD", "XAGUSD": "XAG/USD",
    "BTCUSD": "BTC/USD", "ETHUSD": "ETH/USD",
}


def normalize(symbol):
    s = symbol.upper().strip()
    if s in SYMBOL_MAP:
        return SYMBOL_MAP[s]
    if len(s) == 6 and s.isalpha():
        return f"{s[:3]}/{s[3:]}"
    return s


def get_ohlc(symbol, interval="4h", limit=300):
    if not TWELVE_KEY:
        raise ValueError("Add TWELVE_DATA_API_KEY on Render")

    td = normalize(symbol)
    td_interval = {"15m": "15min", "1h": "1h", "4h": "4h", "1d": "1day"}.get(interval, "4h")

    r = requests.get(f"{TWELVE_BASE}/time_series", params={
        "symbol": td, "interval": td_interval,
        "outputsize": limit, "apikey": TWELVE_KEY,
    }, timeout=20)

    data = r.json()
    if data.get("status") == "error":
        raise ValueError(data.get("message", "API error"))

    values = data.get("values")
    if not values:
        raise ValueError(f"No data for {symbol}")

    df = pd.DataFrame(values)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[["open", "high", "low", "close"]].dropna()


def compute_atr(df):
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(14).mean().bfill()


def find_swings(df, n=3):
    highs = df["high"].values
    lows = df["low"].values
    swings = []
    for i in range(n, len(df) - n):
        wh = highs[i - n:i + n + 1]
        wl = lows[i - n:i + n + 1]
        if highs[i] == wh.max() and np.sum(wh == highs[i]) == 1:
            swings.append((i, float(highs[i]), "high"))
        if lows[i] == wl.min() and np.sum(wl == lows[i]) == 1:
            swings.append((i, float(lows[i]), "low"))
    return swings


def find_bos(df):
    swings = find_swings(df)
    closes = df["close"].values
    bos = []
    last_high = None
    last_low = None
    for i, price, kind in swings:
        if kind == "high":
            if last_high is not None:
                seg = closes[last_high[0] + 1:i + 1]
                if len(seg) and seg.max() > last_high[1]:
                    bos.append(("bullish", last_high[1], i))
            last_high = (i, price)
        else:
            if last_low is not None:
                seg = closes[last_low[0] + 1:i + 1]
                if len(seg) and seg.min() < last_low[1]:
                    bos.append(("bearish", last_low[1], i))
            last_low = (i, price)
    return bos


def find_order_blocks(df):
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    opens = df["open"].values
    atr = compute_atr(df).values
    obs = []
    for i in range(2, len(df) - 2):
        if atr[i] <= 0 or abs(closes[i] - opens[i]) < atr[i] * 0.4:
            continue
        if closes[i] < opens[i]:
            if closes[i + 1] > highs[i] and closes[i + 2] > highs[i]:
                obs.append({"top": float(highs[i]), "bottom": float(lows[i]),
                            "kind": "bullish", "index": i})
        if closes[i] > opens[i]:
            if closes[i + 1] < lows[i] and closes[i + 2] < lows[i]:
                obs.append({"top": float(highs[i]), "bottom": float(lows[i]),
                            "kind": "bearish", "index": i})
    return obs


def build_signal(df):
    if len(df) < 30:
        return {"action": "WAIT", "entry": None, "sl": None, "tp1": None,
                "tp2": None, "reason": ["Not enough data"], "quality": 0}

    last = float(df["close"].iloc[-1])
    atr_series = compute_atr(df)
    atr = float(atr_series.iloc[-1])
    if atr <= 0:
        return {"action": "WAIT", "entry": None, "sl": None, "tp1": None,
                "tp2": None, "reason": ["ATR too low"], "quality": 0}

    atr_pct = atr / last if last > 0 else 0
    if atr_pct < 0.0015:
        return {"action": "WAIT", "entry": None, "sl": None, "tp1": None,
                "tp2": None, "reason": ["Market too quiet"], "quality": 0}

    bos = find_bos(df)
    if not bos:
        return {"action": "WAIT", "entry": None, "sl": None, "tp1": None,
                "tp2": None, "reason": ["No BOS"], "quality": 0}

    direction, level, bos_idx = bos[-1]
    bars_since = len(df) - 1 - bos_idx

    if bars_since > 20:
        return {"action": "WAIT", "entry": None, "sl": None, "tp1": None,
                "tp2": None, "reason": [f"Last BOS too old ({bars_since})"],
                "quality": 0}

    obs = find_order_blocks(df)
    matching = [o for o in obs if o["kind"] == direction
                and abs(((o["top"] + o["bottom"]) / 2) - last) < atr * 2.5]
    if not matching:
        return {"action": "WAIT", "entry": None, "sl": None, "tp1": None,
                "tp2": None, "reason": ["No OB near price"], "quality": 0}

    ob = matching[-1]
    if direction == "bullish":
        entry = ob["top"]
        sl = ob["bottom"] - atr * 0.3
        risk = entry - sl
        if risk <= 0:
            return {"action": "WAIT", "entry": None, "sl": None, "tp1": None,
                    "tp2": None, "reason": ["Invalid risk"], "quality": 0}
        tp1 = entry + risk * 1.5
        tp2 = entry + risk * 3
        action = "BUY"
    else:
        entry = ob["bottom"]
        sl = ob["top"] + atr * 0.3
        risk = sl - entry
        if risk <= 0:
            return {"action": "WAIT", "entry": None, "sl": None, "tp1": None,
                    "tp2": None, "reason": ["Invalid risk"], "quality": 0}
        tp1 = entry - risk * 1.5
        tp2 = entry - risk * 3
        action = "SELL"

    quality = 50
    if bars_since <= 10:
        quality += 15
    if abs(((ob["top"] + ob["bottom"]) / 2) - last) < atr * 1.0:
        quality += 15
    if atr_pct > 0.003:
        quality += 10

    return {
        "action": action,
        "entry": round(entry, 5),
        "sl": round(sl, 5),
        "tp1": round(tp1, 5),
        "tp2": round(tp2, 5),
        "reason": [
            f"{direction.title()} BOS · {bars_since} bars ago",
            f"Entry at {direction} Order Block",
        ],
        "quality": min(quality, 95),
    }


def evaluate_history(df):
    atr_series = compute_atr(df)
    bos = find_bos(df)
    results = []
    for direction, level, idx in bos[-10:]:
        try:
            atr = float(atr_series.iloc[idx])
            if atr <= 0:
                continue
            entry = float(df["close"].iloc[idx])
            if direction == "bullish":
                sl = entry - atr * 1.5
                risk = entry - sl
                tp1 = entry + risk * 1.5
                tp2 = entry + risk * 3
            else:
                sl = entry + atr * 1.5
                risk = sl - entry
                tp1 = entry - risk * 1.5
                tp2 = entry - risk * 3

            outcome = "ACTIVE"
            for _, c in df.iloc[idx + 1:].iterrows():
                if direction == "bullish":
                    if c["low"] <= sl:
                        outcome = "STOPPED"; break
                    if c["high"] >= tp2:
                        outcome = "TP2_HIT"; break
                    if c["high"] >= tp1 and outcome == "ACTIVE":
                        outcome = "TP1_HIT"
                else:
                    if c["high"] >= sl:
                        outcome = "STOPPED"; break
                    if c["low"] <= tp2:
                        outcome = "TP2_HIT"; break
                    if c["low"] <= tp1 and outcome == "ACTIVE":
                        outcome = "TP1_HIT"

            results.append({
                "time": df.index[idx].strftime("%m-%d %H:%M"),
                "direction": direction.upper(),
                "entry": round(entry, 5),
                "sl": round(sl, 5),
                "tp1": round(tp1, 5),
                "tp2": round(tp2, 5),
                "outcome": outcome,
            })
        except Exception:
            continue
    return results


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze")
def api_analyze():
    symbol = request.args.get("symbol", "EURUSD")
    interval = request.args.get("interval", "4h")
    try:
        df = get_ohlc(symbol, interval)
        signal = build_signal(df)
        history = evaluate_history(df)
        candles = [{
            "time": idx.strftime("%Y-%m-%d %H:%M"),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
        } for idx, r in df.iterrows()]
        return jsonify({
            "success": True,
            "candles": candles,
            "signal": signal,
            "history": history,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
