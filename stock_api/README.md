# AtlasMarkets — Viking (Stock Market Signals API)

**Last updated:** 2026-07-22

## Growth Log
| Date | Change | Why | Linked to |
|------|--------|-----|-----------|
| 2026-07-22 | Created `main.py` — 5 endpoints (signals, decision, audit, forecast, risk) | Initial build, mirrors Anubis structure but for equities | [[AtlasMarkets]] |
| 2026-07-22 | Added `requirements.txt` | Project scaffolding for Railway deployment | [[AtlasMarkets]] |
| 2026-07-22 | Named Viking | Max chose Nordic explorer name to pair with Anubis | [[AtlasMarkets]] |

## Contents
- **main.py** — FastAPI server, port 8002. Endpoints: `/api/market/signals`, `/api/market/decision`, `/api/market/audit`, `/api/market/forecast`, `/api/market/risk`
- **requirements.txt** — Python dependencies

## Pricing (per call)
- Signals: $0.05
- Decision: $0.15
- Audit: $0.07
- Forecast: $0.05
- Risk: $0.02

## Data Source
Yahoo Finance free API (no key required). Real-time quotes for SPY, QQQ, DIA, AAPL, MSFT, GOOGL, AMZN, NVDA. Falls back to zero change if rate limited.

## Run
```bash
cd stock_api
pip install -r requirements.txt
python main.py
```