# AtlasMarkets MCP Server

**Last updated:** 2026-07-22

## Growth Log
| Date | Change | Why | Linked to |
|------|--------|-----|-----------|
| 2026-07-22 | Created initial MCP server | Enables AI agents to call AtlasMarkets via MCP protocol | [[AtlasMarkets]] |
| 2026-07-22 | Fixed URL routing: `get_crypto_signals` → `/api/anubis/signals` | Anubis is the brand name for crypto signals (not Kronos) | [[AtlasMarkets/Anubis]] |

## What It Does
Wraps the AtlasMarkets API (Anubis for crypto, stock market API) as an MCP server so AI agents can discover and call it via the standard MCP protocol.

## Endpoints Exposed
- `get_crypto_signals` → `http://localhost:8001/api/anubis/signals`
- `get_crypto_decision` → `http://localhost:8001/api/anubis/decision`
- `get_crypto_audit` → `http://localhost:8001/api/anubis/audit`
- `get_crypto_forecast` → `http://localhost:8001/api/anubis/forecast`
- `get_crypto_risk` → `http://localhost:8001/api/anubis/risk`
- `get_stock_signals` → `http://localhost:8002/api/market/signals`
- `get_stock_decision` → `http://localhost:8002/api/market/decision`
- `get_stock_audit` → `http://localhost:8002/api/market/audit`
- `get_stock_forecast` → `http://localhost:8002/api/market/forecast`
- `get_stock_risk` → `http://localhost:8002/api/market/risk`

## Setup
```bash
npm install
npm start

# Or directly with npx (once published)
npx atlasmarkets-mcp
```

## Requirements
- Node.js >=18
- AtlasMarkets API servers running on ports 8001 (crypto) and 8002 (stock)
- `@modelcontextprotocol/sdk` (installed via npm install)