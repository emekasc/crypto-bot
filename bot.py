import os, json
from datetime import datetime, timezone
import ccxt

# ---- CONFIG ----
SYMBOL     = os.getenv("SYMBOL", "BTC/USDT")
TIMEFRAME  = os.getenv("TIMEFRAME", "5m")
SHORT_SMA  = int(os.getenv("SHORT_SMA", "9"))
LONG_SMA   = int(os.getenv("LONG_SMA", "21"))
QUOTE_SIZE = float(os.getenv("QUOTE_SIZE", "10"))    # USDT to spend per buy
TESTNET    = os.getenv("TESTNET", "true").lower() == "true"

# ---- OKX KEYS ----
API_KEY       = os.getenv("OKX_API_KEY")
API_SECRET    = os.getenv("OKX_API_SECRET")
API_PASSPHRASE= os.getenv("OKX_API_PASSPHRASE")
if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    raise RuntimeError("Missing OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE")

# ---- EXCHANGE ----
ex = ccxt.okx({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "password": API_PASSPHRASE,     # OKX calls it passphrase
    "enableRateLimit": True,
    "options": {"defaultType": "spot"}
})
# Use OKX Paper Trading when TESTNET = true
ex.set_sandbox_mode(TESTNET)

def sma(v, n): 
    return None if len(v) < n else sum(v[-n:]) / n

def main():
    ex.load_markets()
    if SYMBOL not in ex.markets:
        raise RuntimeError(f"Symbol {SYMBOL} not found on OKX.")
    ohlcv = ex.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=max(LONG_SMA*3, 200))
    closes = [c[4] for c in ohlcv]
    s_short, s_long, price = sma(closes, SHORT_SMA), sma(closes, LONG_SMA), closes[-1]

    m = ex.market(SYMBOL)
    base, quote = m["base"], m["quote"]

    bal = ex.fetch_balance()
    free_base  = float(bal.get(base, {}).get("free", 0) or 0)
    free_quote = float(bal.get(quote, {}).get("free", 0) or 0)
    pos = "LONG" if free_base * price > 5 else "FLAT"

    sig = "HOLD"
    if s_short and s_long:
        if s_short > s_long and pos == "FLAT": sig = "BUY"
        elif s_short < s_long and pos == "LONG": sig = "SELL"

    print(f"[{datetime.now(timezone.utc)}] {SYMBOL} P={price:.2f} sSMA={s_short:.2f} lSMA={s_long:.2f} pos={pos} sig={sig}")

    if sig == "BUY":
        spend = min(QUOTE_SIZE, free_quote)
        if spend >= 5:
            amt = float(ex.amount_to_precision(SYMBOL, spend / price))
            if amt > 0:
                o = ex.create_order(SYMBOL, "market", "buy", amt)
                print("BUY id:", o.get("id"))
            else:
                print("Amount too small after precision.")
        else:
            print("Not enough USDT.")
    elif sig == "SELL":
        amt = float(ex.amount_to_precision(SYMBOL, free_base))
        if amt > 0:
            o = ex.create_order(SYMBOL, "market", "sell", amt)
            print("SELL id:", o.get("id"))
        else:
            print("No base asset to sell.")

if __name__ == "__main__":
    main()
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
