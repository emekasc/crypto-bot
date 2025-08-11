name: okx-debug
on:
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ccxt
      - name: Print secrets exist (not values)
        run: |
          python - << 'PY'
import os
need = ["OKX_API_KEY","OKX_API_SECRET","OKX_API_PASSPHRASE"]
print({k: bool(os.getenv(k)) for k in need})
PY
        env:
          OKX_API_KEY: ${{ secrets.OKX_API_KEY }}
          OKX_API_SECRET: ${{ secrets.OKX_API_SECRET }}
          OKX_API_PASSPHRASE: ${{ secrets.OKX_API_PASSPHRASE }}
      - name: OKX connect + balance (paper by default)
        env:
          OKX_API_KEY: ${{ secrets.OKX_API_KEY }}
          OKX_API_SECRET: ${{ secrets.OKX_API_SECRET }}
          OKX_API_PASSPHRASE: ${{ secrets.OKX_API_PASSPHRASE }}
        run: |
          python - << 'PY'
import os, ccxt, sys
ex = ccxt.okx({
  "apiKey": os.getenv("OKX_API_KEY"),
  "secret": os.getenv("OKX_API_SECRET"),
  "password": os.getenv("OKX_API_PASSPHRASE"),
  "enableRateLimit": True,
  "options": {"defaultType": "spot"},
})
ex.set_sandbox_mode(True)  # paper mode
try:
  ex.load_markets()
  bal = ex.fetch_balance()
  usdt = bal.get("USDT", {}).get("free")
  print("OKX connected. Free USDT (paper):", usdt)
except Exception as e:
  print("ERROR:", type(e).__name__, e)
  sys.exit(1)
PY
