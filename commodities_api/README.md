# AtlasMarkets — Pollux (Commodity Signals API)

**Last updated:** 2026-07-22

## Growth Log
| Date | Change | Why | Linked to |
|------|--------|-----|-----------|
| 2026-07-22 | Created `main.py` — 5 endpoints (signals, decision, audit, forecast, risk) | 4th API market vertical | [[AtlasMarkets]] |
| 2026-07-22 | Named Pollux | Max chose Greek god — twin of Castor, both known for trading/exchange of goods | [[AtlasMarkets]] |

## Contents
- **main.py** — FastAPI server, port 8004. Endpoints: `/api/commodities/signals`, `/api/commodities/decision`, `/api/commodities/audit`, `/api/commodities/forecast`, `/api/commodities/risk`
- **requirements.txt** — Python dependencies

## Pricing (per call)
- Signals: $0.05
- Decision: $0.15
- Audit: $0.07
- Forecast: $0.05
- Risk: $0.02

## Data Source
Yahoo Finance free API. Covers Gold, Silver, Crude Oil, Natural Gas, Platinum, Copper, Corn, Soybeans, Wheat, Cotton.

## Run
```bash
cd commodities_api
pip install -r requirements.txt
python main.py
```