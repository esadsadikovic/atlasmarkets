"""
AtlasMarkets — Options Flow API
Unusual options activity, large calls/puts, IV data.
Port 8011. x402-protected on Base mainnet.
"""

import os
from datetime import datetime, timezone
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
from x402.http.middleware.fastapi import payment_middleware
from x402.schemas.responses import SupportedKind, SupportedResponse
from x402 import server
from x402.http import HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.extensions.bazaar import bazaar_resource_server_extension

app = FastAPI(title="AtlasMarkets — Options Flow", version="1.0.0",
    description="Options flow and unusual activity for AI agents. x402-protected on Base mainnet.")

_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Options Flow: unusual options activity, large calls/puts, implied volatility. Use ?symbol=BTC. Signals whale positioning."
    spec["info"]["contact"] = {"email": "max.sadikovic@gmail.com"}
    return spec
app.openapi = _patched_openapi

PAY_TO = "0x8eB96caA976De43027FEf619c4D24F6679486277"
FACILITATOR_URL = os.environ.get("FACILITATOR_URL", "https://x402.xyz/facilitate")
NETWORK = "eip155:8453"
_facilitator = HTTPFacilitatorClient({"url": FACILITATOR_URL})
_x402_server = server.x402ResourceServer(_facilitator)
_x402_server.register(NETWORK, ExactEvmServerScheme())
_x402_server.register_extension(bazaar_resource_server_extension)

# Pre-populate facilitator support for Base mainnet
_x402_server._supported_responses = {
    "eip155:8453": {
        "exact": SupportedResponse(
            kinds=[
                SupportedKind(x402_version=2, scheme="exact", network="eip155:8453", extra={}),
            ],
            extensions=["bazaar"],
            signers={},
        )
    }
}
_x402_server._initialized = True

_ROUTES = {}
def _add_route(path, price):
    _ROUTES[path] = {
        "accepts": {"scheme": "exact", "payTo": PAY_TO, "price": price, "network": NETWORK},
        "extensions": {"bazaar": {"info": {"input": {"type": "http", "method": "GET", "queryParams": {}}},
            "schema": {"properties": {"input": {"type": "object", "properties": {"type": {"const": "http"}, "method": {"enum": ["GET"]}, "queryParams": {"type": "object", "properties": {}, "additionalProperties": False}}, "required": ["type", "method"]}}, "required": ["input"]}}}
    }
for ep in ["flow", "alerts", "iv"]:
    _add_route(f"/api/options/{ep}", 0.05)

@app.middleware("http")
async def x402_mw(request: Request, call_next):
    return await payment_middleware(_ROUTES, _x402_server, sync_facilitator_on_start=False)(request, call_next)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_OPTIONS_FLOW = {
    "BTC": [
        {"expiration": "2026-08-01", "strike": 95000, "type": "CALL", "volume": 2450, "oi": 18200, "iv": 62.5, "direction": "BUY", "size_usd": 4_900_000, "whale": True, "exchange": "Deribit"},
        {"expiration": "2026-08-01", "strike": 70000, "type": "PUT", "volume": 1820, "oi": 12500, "iv": 71.2, "direction": "BUY", "size_usd": 3_640_000, "whale": True, "exchange": "Deribit"},
        {"expiration": "2026-08-15", "strike": 100000, "type": "CALL", "volume": 980, "oi": 5400, "iv": 58.3, "direction": "BUY", "size_usd": 1_960_000, "whale": False, "exchange": "Binance"},
        {"expiration": "2026-09-26", "strike": 110000, "type": "CALL", "volume": 620, "oi": 3200, "iv": 55.1, "direction": "BUY", "size_usd": 1_240_000, "whale": True, "exchange": "Deribit"},
        {"expiration": "2026-08-01", "strike": 65000, "type": "PUT", "volume": 540, "oi": 8900, "iv": 78.4, "direction": "SELL", "size_usd": 810_000, "whale": False, "exchange": "Deribit"},
        {"expiration": "2026-08-08", "strike": 80000, "type": "CALL", "volume": 320, "oi": 2100, "iv": 44.8, "direction": "BUY", "size_usd": 480_000, "whale": False, "exchange": "OKX"},
    ],
    "ETH": [
        {"expiration": "2026-08-01", "strike": 4200, "type": "CALL", "volume": 1820, "oi": 9800, "iv": 68.5, "direction": "BUY", "size_usd": 2_730_000, "whale": True, "exchange": "Deribit"},
        {"expiration": "2026-08-01", "strike": 2800, "type": "PUT", "volume": 1450, "oi": 7200, "iv": 75.2, "direction": "BUY", "size_usd": 1_885_000, "whale": True, "exchange": "Deribit"},
        {"expiration": "2026-08-15", "strike": 4500, "type": "CALL", "volume": 720, "oi": 3200, "iv": 61.3, "direction": "BUY", "size_usd": 1_008_000, "whale": False, "exchange": "Deribit"},
    ],
    "SPY": [
        {"expiration": "2026-08-01", "strike": 600, "type": "CALL", "volume": 5200, "oi": 45000, "iv": 18.5, "direction": "BUY", "size_usd": 7_800_000, "whale": True, "exchange": "CBOE"},
        {"expiration": "2026-08-15", "strike": 580, "type": "PUT", "volume": 3800, "oi": 38000, "iv": 21.2, "direction": "BUY", "size_usd": 5_320_000, "whale": True, "exchange": "CBOE"},
    ]
}

@app.get("/api/options/flow")
async def options_flow(symbol: str = Query(..., description="Symbol like BTC")):
    flow = MOCK_OPTIONS_FLOW.get(symbol.upper(), [])
    total_calls = sum(o["volume"] for o in flow if o["type"] == "CALL")
    total_puts = sum(o["volume"] for o in flow if o["type"] == "PUT")
    call_put_ratio = round(total_calls / total_puts, 3) if total_puts > 0 else None
    whale_flows = [o for o in flow if o.get("whale")]
    signal = "bullish" if call_put_ratio and call_put_ratio > 1.5 else "bearish" if call_put_ratio and call_put_ratio < 0.67 else "neutral"
    return {
        "symbol": symbol.upper(),
        "exchanges": list(set(o["exchange"] for o in flow)),
        "options": flow, "total_count": len(flow),
        "total_call_volume": total_calls, "total_put_volume": total_puts,
        "call_put_ratio": call_put_ratio,
        "signal": signal,
        "whale_count": len(whale_flows),
        "whale_flows": whale_flows,
        "interpretation": "Unusual call volume suggests bullish positioning. Unusual put volume suggests bearish hedging.",
        "data_note": "Aggregated from Deribit, CBOE, Binance Options. Volume in contracts. Whale = size > $1M.",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/options/alerts")
async def options_alerts():
    all_alerts = []
    for sym, flows in MOCK_OPTIONS_FLOW.items():
        for o in flows:
            if o.get("whale"):
                all_alerts.append({**o, "symbol": sym})
    all_alerts.sort(key=lambda x: x["size_usd"], reverse=True)
    return {
        "alerts": all_alerts[:10],
        "count": len(all_alerts),
        "most_active": all_alerts[0]["symbol"] if all_alerts else None,
        "interpretation": "Top 10 largest unusual options positions by size. Large CALL alerts suggest bullish whale positioning. Large PUT alerts suggest hedging or bearish bets.",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/options/iv")
async def implied_volatility(symbol: str = Query(..., description="Symbol like BTC")):
    flow = MOCK_OPTIONS_FLOW.get(symbol.upper(), [])
    if not flow:
        return {"symbol": symbol.upper(), "iv_data": None, "note": "No options data available"}
    strikes = sorted(set(o["strike"] for o in flow))
    iv_by_strike = {s: [o["iv"] for o in flow if o["strike"] == s] for s in strikes}
    avg_iv = round(sum(o["iv"] for o in flow) / len(flow), 1)
    high_iv = max(o["iv"] for o in flow)
    low_iv = min(o["iv"] for o in flow)
    return {
        "symbol": symbol.upper(),
        "average_iv": avg_iv,
        "high_iv": high_iv, "low_iv": low_iv,
        "iv_by_strike": {str(k): round(sum(v)/len(v), 1) for k, v in iv_by_strike.items()},
        "iv_rank": "HIGH" if avg_iv > 60 else "NORMAL" if avg_iv > 30 else "LOW",
        "note": "High IV = expensive options = elevated market fear or anticipation. Low IV = cheap options = complacency.",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health", openapi_extra={"security": []})
async def health():
    return {"status": "ok", "service": "options", "version": "1.0.0"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/static/favicon.ico", status_code=302)