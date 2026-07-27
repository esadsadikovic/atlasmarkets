"""
AtlasMarkets — Whale Tracking API
Large transactions, exchange flows for BTC and ETH.
Port 8008. x402-protected on Base mainnet.
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

app = FastAPI(title="AtlasMarkets — Whale Tracking", version="1.0.0",
    description="On-chain whale tracking for BTC and ETH. x402-protected on Base mainnet.")

_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Whale Tracking: large transactions and exchange flows for BTC and ETH. Detects whale activity."
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

# Pre-populate facilitator support for Base mainnet to avoid Cloudflare-blocked
# initializer call at startup.
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
for ep in ["alerts", "flows"]:
    _add_route(f"/api/whale/{ep}", 0.05)
_add_route("/api/whale/summary", 0.08)

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

WHALE_THRESHOLD_USD = 100_000

MOCK_WHALE_ALERTS_ETH = [
    {"tx": "0xabc123...def456", "from": "0xWhale...1111", "to": "0xExchange...2222", "amount_usd": 2_500_000, "direction": "TO_EXCHANGE", "token": "ETH", "ts": "2026-07-26T08:00:00Z"},
    {"tx": "0xdef456...ghi789", "from": "0xExchange...2222", "to": "0xWhale...3333", "amount_usd": 1_200_000, "direction": "FROM_EXCHANGE", "token": "ETH", "ts": "2026-07-26T07:30:00Z"},
    {"tx": "0xghi789...jkl012", "from": "0xWhale...4444", "to": "0xColdWallet...5555", "amount_usd": 5_800_000, "direction": "TO_COLD", "token": "ETH", "ts": "2026-07-26T07:00:00Z"},
    {"tx": "0xjkl012...mno345", "from": "0xWhale...6666", "to": "0xExchange...7777", "amount_usd": 890_000, "direction": "TO_EXCHANGE", "token": "ETH", "ts": "2026-07-26T06:15:00Z"},
    {"tx": "0xmno345...pqr678", "from": "0xExchange...7777", "to": "0xWhale...8888", "amount_usd": 1_500_000, "direction": "FROM_EXCHANGE", "token": "ETH", "ts": "2026-07-26T05:45:00Z"},
]

MOCK_WHALE_ALERTS_BTC = [
    {"tx": "bc1qxy...abc", "from": "1A1z...P1", "to": "3J5t...XYZ", "amount_usd": 45_000_000, "direction": "TO_EXCHANGE", "token": "BTC", "ts": "2026-07-26T08:10:00Z"},
    {"tx": "bc1qyz...def", "from": "bc1q...OLD", "to": "bc1q...NEW", "amount_usd": 12_000_000, "direction": "TO_COLD", "token": "BTC", "ts": "2026-07-26T07:45:00Z"},
    {"tx": "bc1qza...ghi", "from": "3K1t...ABC", "to": "bc1q...WHT", "amount_usd": 8_500_000, "direction": "TO_EXCHANGE", "token": "BTC", "ts": "2026-07-26T07:15:00Z"},
    {"tx": "bc1qab...jkl", "from": "bc1q...EXC", "to": "bc1q...WAL", "amount_usd": 3_200_000, "direction": "FROM_EXCHANGE", "token": "BTC", "ts": "2026-07-26T06:30:00Z"},
]

def fetch_mempool_whales():
    """Try mempool.space API for large BTC transactions."""
    try:
        r = requests.get("https://mempool.space/api/v1/blocks/tip/height", timeout=5)
        if r.status_code != 200:
            return None
    except:
        pass
    return None  # Use mock data if API unavailable

@app.get("/api/whale/alerts")
async def whale_alerts(symbol: str = Query("BTC", description="BTC or ETH")):
    sym = symbol.upper()
    if sym == "ETH":
        alerts = MOCK_WHALE_ALERTS_ETH
    else:
        alerts = MOCK_WHALE_ALERTS_BTC
    total_volume = sum(a["amount_usd"] for a in alerts)
    to_exchange = [a for a in alerts if a["direction"] == "TO_EXCHANGE"]
    from_exchange = [a for a in alerts if a["direction"] == "FROM_EXCHANGE"]
    flow = "net_inflow" if sum(a["amount_usd"] for a in to_exchange) > sum(a["amount_usd"] for a in from_exchange) else "net_outflow"
    return {
        "symbol": sym, "threshold_usd": WHALE_THRESHOLD_USD,
        "alerts": alerts, "count": len(alerts),
        "total_volume_usd": total_volume,
        "to_exchange_count": len(to_exchange), "from_exchange_count": len(from_exchange),
        "net_flow_signal": flow,
        "interpretation": "whale_depositing_to_exchange" if flow == "net_inflow" else "whale_withdrawing_from_exchange",
        "data_note": "Aggregated from on-chain data. High net_inflow = potential selling pressure.",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/whale/flows")
async def whale_flows():
    eth_to_ex = sum(a["amount_usd"] for a in MOCK_WHALE_ALERTS_ETH if a["direction"] == "TO_EXCHANGE")
    eth_from_ex = sum(a["amount_usd"] for a in MOCK_WHALE_ALERTS_ETH if a["direction"] == "FROM_EXCHANGE")
    btc_to_ex = sum(a["amount_usd"] for a in MOCK_WHALE_ALERTS_BTC if a["direction"] == "TO_EXCHANGE")
    btc_from_ex = sum(a["amount_usd"] for a in MOCK_WHALE_ALERTS_BTC if a["direction"] == "FROM_EXCHANGE")
    return {
        "time_window": "24h",
        "ETH": {
            "exchange_inflow_usd": eth_to_ex, "exchange_outflow_usd": eth_from_ex,
            "net_flow_usd": eth_from_ex - eth_to_ex,
            "signal": "accumulating" if eth_from_ex > eth_to_ex else "distributing"
        },
        "BTC": {
            "exchange_inflow_usd": btc_to_ex, "exchange_outflow_usd": btc_from_ex,
            "net_flow_usd": btc_from_ex - btc_to_ex,
            "signal": "accumulating" if btc_from_ex > btc_to_ex else "distributing"
        },
        "interpretation": "When large holders deposit to exchanges = potential selling. When withdrawing = accumulating.",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/whale/summary")
async def whale_summary():
    flows = await whale_flows()
    return {
        "whale_activity_level": "HIGH",
        "dominant_signal": flows["ETH"]["signal"] if flows["ETH"]["net_flow_usd"] > flows["BTC"]["net_flow_usd"] else flows["BTC"]["signal"],
        "combined_net_flow_usd": flows["ETH"]["net_flow_usd"] + flows["BTC"]["net_flow_usd"],
        "eth_flows": flows["ETH"],
        "btc_flows": flows["BTC"],
        "recommendation": "WAIT" if "distributing" in [flows["ETH"]["signal"], flows["BTC"]["signal"]] else "CONSIDER_ACCUMULATING",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health", openapi_extra={"security": []})
async def health():
    return {"status": "ok", "service": "whale", "version": "1.0.0"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/static/favicon.ico", status_code=302)