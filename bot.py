import os, time, json
from datetime import datetime, timezone
import ccxt

# -------- CONFIG --------
SYMBOL     = os.getenv("SYMBOL", "BTC/USDT")
TIMEFRAME  = os.getenv("TIMEFRAME", "5m")
SHORT_SMA  = int(os.getenv("SHORT_SMA", "9"))
LONG_SMA   = int(os.getenv("LONG_SMA", "21"))
QUOTE_SIZE = float(os.getenv("QUOTE_SIZE", "10"))   # USDT per buy
TESTNET    = os.getenv("TESTNET", "true").lower() == "true"

API_KEY    = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")
if not API_KEY or not API_SECRET:
    raise RuntimeError("Missing BYBIT_API_KEY / BYBIT_API_SECRET")

params = {"options": {"defaultType": "spot"}}
if TESTNET:
    params["urls"] = {"api": {"public": "https://api-testnet.bybit.com",
                              "private": "https://api-testnet.bybit.com"}}

ex = ccxt.bybit({"apiKey": API_KEY, "secret": API_SECRET, "enableRateLimit": True, **params})

def sma(vals, n): 
    return None if len(vals) < n else sum(vals[-n:]) / n

def main():
    ex.load_markets()
    ohlcv = ex.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=max(LONG_SMA*3, 200))
    closes = [c[4] for c in ohlcv]
    s_short, s_long, price = sma(closes, SHORT_SMA), sma(closes, LONG_SMA), closes[-1]

    m = ex.market(SYMBOL); base, quote = m["base"], m["quote"]
    bal = ex.fetch_balance()
    free_base  = bal.get(base, {}).get("free", 0) or 0.0
    free_quote = bal.get(quote, {}).get("free", 0) or 0.0
    pos = "LONG" if free_base * price > 5 else "FLAT"

    signal = "HOLD"
    if s_short and s_long:
        if s_short > s_long and pos == "FLAT": signal = "BUY"
        elif s_short < s_long and pos == "LONG": signal = "SELL"

    print(f"[{datetime.now(timezone.utc)}] {SYMBOL} P={price:.2f} sSMA={s_short:.2f} lSMA={s_long:.2f} pos={pos} sig={signal}")

    if signal == "BUY":
        spend = min(QUOTE_SIZE, free_quote)
        if spend >= 5:
            amt = float(ex.amount_to_precision(SYMBOL, spend / price))
            try: print("BUY:", ex.create_order(SYMBOL, "market", "buy", amt).get("id"))
            except Exception as e: print("BUY error:", e)
        else: print("Not enough USDT.")
    elif signal == "SELL":
        amt = float(ex.amount_to_precision(SYMBOL, free_base))
        if amt > 0:
            try: print("SELL:", ex.create_order(SYMBOL, "market", "sell", amt).get("id"))
            except Exception as e: print("SELL error:", e)
        else: print("No base asset.")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        print("Runtime error:", e); raise
