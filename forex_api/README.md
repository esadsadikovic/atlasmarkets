# AtlasMarkets — Apollo (Forex Signals API)

**Last updated:** 2026-07-22

## Growth Log
| Date | Change | Why | Linked to |
|------|--------|-----|-----------|
| 2026-07-22 | Created `main.py` — 5 endpoints (signals, decision, audit, forecast, risk) | 3rd API market vertical after Anubis (crypto) and Viking (stocks) | [[AtlasMarkets]] |
| 2026-07-22 | Named Apollo | Max chose Greek god — messenger and truth-teller, fits forex data | [[AtlasMarkets]] |

## Contents
- **main.py** — FastAPI server, port 8003. Endpoints: `/api/forex/signals`, `/api/forex/decision`, `/api/forex/audit`, `/api/forex/forecast`, `/api/forex/risk`
- **requirements.txt** — Python dependencies

## Pricing (per call)
- Signals: $0.05
- Decision: $0.15
- Audit: $0.07
- Forecast: $0.05
- Risk: $0.02

## Data Source
exchangerate-api.com free tier (no key). Covers EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, NZD/USD, EUR/GBP, EUR/JPY, GBP/JPY.

## Run
```bash
cd forex_api
pip install -r requirements.txt
python main.py
```