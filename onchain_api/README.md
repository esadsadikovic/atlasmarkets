# AtlasMarkets — Dagon (On-Chain / DeFi Signals API)

**Last updated:** 2026-07-22

## Growth Log
| Date | Change | Why | Linked to |
|------|--------|-----|-----------|
| 2026-07-22 | Created `main.py` — 5 endpoints (signals, decision, audit, forecast, risk) | 5th API — on-chain data for AI agents | [[AtlasMarkets]] |
| 2026-07-22 | Named Dagon | Max chose Mesopotamian fish-god of water and knowledge — fits blockchain data | [[AtlasMarkets]] |

## Contents
- **main.py** — FastAPI server, port 8005. Endpoints: `/api/onchain/signals`, `/api/onchain/decision`, `/api/onchain/audit`, `/api/onchain/forecast`, `/api/onchain/risk`
- **requirements.txt** — Python dependencies

## Pricing (per call)
- Signals: $0.05
- Decision: $0.15
- Audit: $0.07
- Forecast: $0.05
- Risk: $0.02

## Data Source
- ETH gas: Etherscan free gas oracle
- BTC fees: mempool.space free API
- DeFi TVL: DeFiLlama free (no key)
- Whale alerts: simulated (real data needs Whale Alert paid API)

## Run
```bash
cd onchain_api
pip install -r requirements.txt
python main.py
```