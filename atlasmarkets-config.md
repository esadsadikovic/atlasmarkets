# AtlasMarkets — Configuration Reference
# Last updated: 2026-07-26

## Live API URLs (Render)
- Anubis (Crypto):    https://atlasmarkets-anubis.onrender.com   → srv-d9hbk8mpbkes739qkg90
- Viking (Stocks):    https://atlasmarkets-viking.onrender.com   → srv-d9hbk8mpbkes739qkg9g
- Apollo (Forex):     https://atlasmarkets-apollo.onrender.com   → srv-d9hbk8mpbkes739qkgag
- Pollux (Commodities):https://atlasmarkets-pollux.onrender.com   → srv-d9hbk8mpbkes739qkga0
- Dagon (On-Chain):   https://atlasmarkets-dagon.onrender.com    → srv-d9hbk8mpbkes739qkgb0

## Website
- URL: https://atlasmarkets.com (or Render deploy URL)
- Source: AtlasMarkets/website/index.html

## x402scan Registration
All 5 APIs passed x402scan.com discovery inspection ✅
- Anubis: 0 errors
- Viking: 0 errors  
- Apollo: 0 errors
- Pollux: 0 errors
- Dagon: 0 errors

## x402 Configuration
- Facilitator: https://x402.xyz/facilitate (Base mainnet)
- Payment: USDC via x402 protocol on Base mainnet
- Wallet: [REDACTED - user manages privately]

## Endpoints per API (same for all 5)
- GET  /health              — unprotected, no payment
- GET  /api/{god}/signals   — $0.05
- POST /api/{god}/decision  — $0.15
- GET  /api/{god}/audit     — $0.07
- GET  /api/{god}/forecast  — $0.05
- GET  /api/{god}/risk      — $0.02
- GET  /api/{god}/preflight — $0.05
- GET  /api/{god}/history   — $0.05

## Render Service IDs (for API calls)
crypto:     srv-d9hbk8mpbkes739qkg90
stock:      srv-d9hbk8mpbkes739qkg9g
forex:      srv-d9hbk8mpbkes739qkgag
commodities:srv-d9hbk8mpbkes739qkga0
onchain:    srv-d9hbk8mpbkes739qkgb0

## GitHub Repo
https://github.com/esadsadikovic/atlasmarkets

## MCP Package
- npm: atlasmarkets-mcp
- Install: npx -y atlasmarkets-mcp
- Env: ATLASMARKETS_URL=https://atlasmarkets-anubis.onrender.com

---

## TITAN ADDENDUM (added 2026-07-27)

# AtlasMarkets — Titan Deployment Configuration

Last updated: 2026-07-27

## 6 Titan Services (x402-protected)

| # | Service Name | Service ID | URL | API Folder | Port |
|---|--------------|------------|-----|------------|------|
| 1 | atlasmarkets-titan001 | srv-d9j6m5f1dkcs73bo6lb0 | https://atlasmarkets-titan001-k3fd.onrender.com | indicators_api/ | 8006 |
| 2 | atlasmarkets-titan002 | srv-d9j6n3svikkc73di9amg | https://atlasmarkets-titan002-ns4m.onrender.com | sentiment_api/ | 8007 |
| 3 | atlasmarkets-titan003 | srv-d9j6ngf41pts73c80tpg | https://atlasmarkets-titan003-s174.onrender.com | whale_api/ | 8008 |
| 4 | atlasmarkets-titan004 | srv-d9j6o16rnols7389uv6g | https://atlasmarkets-titan004-upj5.onrender.com | calendar_api/ | 8009 |
| 5 | atlasmarkets-titan005 | srv-d9j6odbrjlhs73814pc0 | https://atlasmarkets-titan005-apf9.onrender.com | funding_api/ | 8010 |
| 6 | atlasmarkets-titan006 | srv-d9j6oqf41pts73c82l2g | https://atlasmarkets-titan006-30hz.onrender.com | options_api/ | 8011 |

All Titans return HTTP 402 with `payment-required` header on protected routes; 200 on /health; 302 on /favicon.ico.

## Docker Hub Images
- Repository: `mecomax/atlasmarkets-{api}:latest`
- Tags used: `:v3`, `:v4`, `:latest`
- Render pulls `latest` tag — keep it pointing to the current working build

## 5 Original APIs (Anubis + sub-brands, do not modify)

| Brand | Service Name | Service ID | URL | Port |
|-------|--------------|------------|-----|------|
| Anubis (crypto) | atlasmarkets-anubis | srv-d9hbk8mpbkes739qkg90 | https://atlasmarkets-anubis.onrender.com | 8001 |
| Viking (stocks) | atlasmarkets-viking | srv-d9hbk8mpbkes739qkg9g | https://atlasmarkets-viking.onrender.com | 8002 |
| Apollo (forex) | atlasmarkets-apollo | srv-d9hbk8mpbkes739qkgag | https://atlasmarkets-apollo.onrender.com | 8003 |
| Pollux (commodities) | atlasmarkets-pollux | srv-d9hbk8mpbkes739qkga0 | https://atlasmarkets-pollux.onrender.com | 8004 |
| Dagon (on-chain) | atlasmarkets-dagon | srv-d9hbk8mpbkes739qkgb0 | https://atlasmarkets-dagon.onrender.com | 8005 |

## Wallet & Payment
- Pay-to address: 0x8eB96caA976De43027FEf619c4D24F6679486277
- Network: eip155:8453 (Base mainnet)
- Asset: USDC (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)
- Facilitator: https://x402.xyz/facilitate

## Titan API Endpoints

### titan001 (indicators) — port 8006
- `GET /api/indicators/rsi?symbol=BTC&interval=1h` — $0.05
- `GET /api/indicators/macd?symbol=BTC&interval=1h` — $0.05
- `GET /api/indicators/bollinger?symbol=BTC&interval=1h` — $0.05
- `GET /api/indicators/ema?symbol=BTC&interval=1h` — $0.05
- `GET /api/indicators/all?symbol=BTC&interval=1h` — $0.10

### titan002 (sentiment) — port 8007
- `GET /api/sentiment/fear_greed` — $0.05
- `GET /api/sentiment/news` — $0.05
- `GET /api/sentiment/all` — $0.08

### titan003 (whale) — port 8008
- `GET /api/whale/alerts?symbol=BTC` — $0.05
- `GET /api/whale/flows?symbol=BTC` — $0.05
- `GET /api/whale/summary?symbol=BTC` — $0.08

### titan004 (calendar) — port 8009
- `GET /api/calendar/upcoming` — $0.05
- `GET /api/calendar/recent` — $0.05
- `GET /api/calendar/check?date=YYYY-MM-DD` — $0.02

### titan005 (funding) — port 8010
- `GET /api/funding/rates` — $0.05
- `GET /api/funding/predicted` — $0.05
- `GET /api/funding/all` — $0.05

### titan006 (options) — port 8011
- `GET /api/options/flow?symbol=BTC` — $0.05
- `GET /api/options/alerts?symbol=BTC` — $0.05
- `GET /api/options/iv?symbol=BTC` — $0.05

## Titan API Critical Code Pattern

All Titans use the EXACT x402 middleware pattern that Anubis uses (working reference). Key things that MUST be present:

1. **Nested `_supported_responses`** — must wrap in `{"eip155:8453": {"exact": SupportedResponse(...)}}`, not flat.
2. **`/health` endpoint** — must have `openapi_extra={"security": []}` to exclude from x402 probing.
3. **`/favicon.ico` endpoint** — must have `include_in_schema=False` to hide from OpenAPI.
4. **`sync_facilitator_on_start=False`** in `payment_middleware(...)` call (avoids Cloudflare-blocked startup call).
5. **Bazaar extension** — every route needs `"extensions": {"bazaar": {"info": {...}, "schema": {...}}}` with `type:http, method:GET, queryParams:{}` for GET endpoints.

## Secrets Location
- Render API key + GitHub PAT + wallet: stored in `C:/Users/43664/.hermes/luma-vault/06-Reference/AtlasMarkets/AtlasMarkets-Secrets.md`
- NEVER in conversation memory
- NEVER in this config file
