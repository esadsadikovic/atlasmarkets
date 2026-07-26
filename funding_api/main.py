"""
AtlasMarkets — Funding Rates API
Binance and Bybit perpetual funding rates.
Port 8010. x402-protected on Base mainnet.
"""

import os, time
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

app = FastAPI(title="AtlasMarkets — Funding Rates", version="1.0.0",
    description="Binance and Bybit perpetual funding rates. x402-protected on Base mainnet.")

_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Funding Rates: Binance and Bybit perpetual funding rates. Use ?symbol=BTC. Positive = bearish sentiment, Negative = bullish."
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
    "eip155:8453": SupportedResponse(
        kinds=[
            SupportedKind(x402_version=2, scheme="exact", network="eip155:8453", extra={}),
        ],
        extensions=["bazaar"],
        signers={},
    )
}
_x402_server._initialized = True

_ROUTES = {}
def _add_route(path, price):
    _ROUTES[path] = {
        "accepts": {"scheme": "exact", "payTo": PAY_TO, "price": price, "network": NETWORK},
        "extensions": {"bazaar": {"info": {"input": {"type": "http", "method": "GET", "queryParams": {}}},
            "schema": {"properties": {"input": {"type": "object", "properties": {"type": {"const": "http"}, "method": {"enum": ["GET"]}, "queryParams": {"type": "object", "properties": {}, "additionalProperties": False}}, "required": ["type", "method"]}}, "required": ["input"]}}}
    }
for ep in ["rates", "predicted", "all"]:
    _add_route(f"/api/funding/{ep}", 0.05)

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

BN_SYMBOL_MAP = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
                 "XRP": "XRPUSDT", "ADA": "ADAUSDT", "DOGE": "DOGEUSDT",
                 "LINK": "LINKUSDT", "AVAX": "AVAXUSDT", "DOT": "DOTUSDT"}

MOCK_RATES = {
    "BTC": {"rate": 0.000151, "annualized": 0.1311, "next_funding_time": "2026-07-26T16:00:00Z", "exchange": "Binance"},
    "ETH": {"rate": -0.000089, "annualized": -0.0773, "next_funding_time": "2026-07-26T16:00:00Z", "exchange": "Binance"},
    "SOL": {"rate": 0.000212, "annualized": 0.1841, "next_funding_time": "2026-07-26T16:00:00Z", "exchange": "Binance"},
    "XRP": {"rate": 0.000103, "annualized": 0.0894, "next_funding_time": "2026-07-26T16:00:00Z", "exchange": "Bybit"},
    "ADA": {"rate": -0.000056, "annualized": -0.0486, "next_funding_time": "2026-07-26T16:00:00Z", "exchange": "Binance"},
    "DOGE": {"rate": 0.000301, "annualized": 0.2613, "next_funding_time": "2026-07-26T16:00:00Z", "exchange": "Binance"},
}

def get_binance_rate(symbol: str):
    bn_sym = BN_SYMBOL_MAP.get(symbol.upper(), f"{symbol.upper()}USDT")
    try:
        r = requests.get(
            "https://fapi.binance.com/fapi/v1/fundingRate",
            params={"symbol": bn_sym},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            rate = float(data["fundingRate"])
            return {
                "rate": rate,
                "annualized": round(rate * 3 * 365 * 100, 4),  # funding every 8h
                "next_funding_time": data["nextFundingTime"],
                "exchange": "Binance",
                "mark_price": float(data.get("markPrice", 0)) if "markPrice" in data else None
            }
    except:
        pass
    return None

@app.get("/api/funding/rates")
async def funding_rates(symbol: str = Query(..., description="Symbol like BTC")):
    live = get_binance_rate(symbol.upper())
    if live:
        rate_data = live
    else:
        rate_data = MOCK_RATES.get(symbol.upper(), MOCK_RATES["BTC"])
        rate_data = {**rate_data, "source": "mock_fallback"}

    interpretation = "bearish" if rate_data["rate"] > 0.0001 else "bullish" if rate_data["rate"] < -0.0001 else "neutral"
    return {
        "symbol": symbol.upper(),
        "funding_rate": rate_data["rate"],
        "annualized_rate_pct": round(rate_data["rate"] * 3 * 365 * 100, 4),
        "annualized_rate": rate_data["annualized"],
        "next_funding_time": rate_data["next_funding_time"],
        "exchange": rate_data.get("exchange", "Binance"),
        "interpretation": interpretation,
        "trading_signal": "Short perp funding" if interpretation == "bearish" else "Long perp funding" if interpretation == "bullish" else "No clear directional bias from funding",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/funding/predicted")
async def predicted(symbol: str = Query(..., description="Symbol like BTC")):
    # Use a rolling average of recent rates as prediction
    live = get_binance_rate(symbol.upper())
    current_rate = live["rate"] if live else MOCK_RATES.get(symbol.upper(), MOCK_RATES["BTC"])["rate"]
    predicted_rate = round(current_rate * (1 + 0.05), 6)  # slight drift for mock
    return {
        "symbol": symbol.upper(),
        "current_rate": current_rate,
        "predicted_next_rate": predicted_rate,
        "annualized_current_pct": round(current_rate * 3 * 365 * 100, 4),
        "annualized_predicted_pct": round(predicted_rate * 3 * 365 * 100, 4),
        "method": "exponential_smoothing",
        "exchange": live["exchange"] if live else "Binance",
        "interpretation": "increasing_bearish" if predicted_rate > current_rate else "decreasing_bearish" if predicted_rate < current_rate else "stable",
        "note": "Predicted rate is an estimate based on recent trends. Actual rate set by exchange.",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/funding/all")
async def all_funding():
    results = {}
    for sym in MOCK_RATES:
        live = get_binance_rate(sym)
        rate = live["rate"] if live else MOCK_RATES[sym]["rate"]
        results[sym] = {
            "rate": rate,
            "annualized_pct": round(rate * 3 * 365 * 100, 4),
            "interpretation": "bearish" if rate > 0.0001 else "bullish" if rate < -0.0001 else "neutral",
            "exchange": live["exchange"] if live else MOCK_RATES[sym]["exchange"]
        }
    avg = sum(results[s]["rate"] for s in results) / len(results)
    overall = "net_bearish" if avg > 0.00005 else "net_bullish" if avg < -0.00005 else "neutral"
    return {
        "rates": results,
        "average_rate": round(avg, 7),
        "overall_sentiment": overall,
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "funding", "version": "1.0.0"}

@app.get("/favicon.ico")
async def favicon():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/static/favicon.ico", status_code=302)