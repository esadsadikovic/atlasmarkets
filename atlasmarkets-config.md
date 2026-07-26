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