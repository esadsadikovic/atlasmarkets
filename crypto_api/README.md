# AtlasMarkets — Anubis (Crypto Market Signals API)

**Last updated:** 2026-07-22

## Growth Log
| Date | Change | Why | Linked to |
|------|--------|-----|-----------|
| 2026-07-22 | Created `main.py` — 5 endpoints (signals, decision, audit, forecast, risk) | Initial build, modeled after CoinOpAI Kronos but renamed Anubis | [[AtlasMarkets]] |
| 2026-07-22 | Added `requirements.txt`, `config.yaml` | Project scaffolding for Railway deployment | [[AtlasMarkets]] |
| 2026-07-22 | Renamed from Kronos to Anubis | Max chose the name — Egyptian guardian theme fits market watching | [[AtlasMarkets]] |

## Contents
- **main.py** — FastAPI server, port 8001. Endpoints: `/api/anubis/signals`, `/api/anubis/decision`, `/api/anubis/audit`, `/api/anubis/forecast`, `/api/anubis/risk`
- **requirements.txt** — Python dependencies
- **config.yaml** — API configuration

## Pricing (per call)
- Signals: $0.05
- Decision: $0.15
- Audit: $0.07
- Forecast: $0.05
- Risk: $0.02

## Data Source
CoinGecko free API (no key required). Falls back to realistic mock data if rate limited.

## Run
```bash
cd crypto_api
pip install -r requirements.txt
python main.py
```