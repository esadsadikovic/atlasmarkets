"""
AtlasMarkets — Economic Calendar API
FOMC, CPI, NFP, Earnings events for AI agents.
Port 8009. x402-protected on Base mainnet.
"""

import os
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
from x402.http.middleware.fastapi import payment_middleware
from x402 import server
from x402.http import HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.extensions.bazaar import bazaar_resource_server_extension

app = FastAPI(title="AtlasMarkets — Economic Calendar", version="1.0.0",
    description="Economic calendar for AI agents. FOMC, CPI, NFP, earnings. x402-protected on Base mainnet.")

_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Economic Calendar: FOMC, CPI, NFP, earnings dates for AI agents making market-sensitive decisions."
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

_ROUTES = {}
def _add_route(path, price):
    _ROUTES[path] = {
        "accepts": {"scheme": "exact", "payTo": PAY_TO, "price": price, "network": NETWORK},
        "extensions": {"bazaar": {"info": {"input": {"type": "http", "method": "GET", "queryParams": {}}},
            "schema": {"properties": {"input": {"type": "object", "properties": {"type": {"const": "http"}, "method": {"enum": ["GET"]}, "queryParams": {"type": "object", "properties": {}, "additionalProperties": False}}, "required": ["type", "method"]}}, "required": ["input"]}}}
    }
for ep in ["events", "upcoming"]:
    _add_route(f"/api/calendar/{ep}", 0.05)
_add_route("/api/calendar/check", 0.02)

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

def _d(year, month, day):
    return datetime(year, month, day, tzinfo=timezone.utc)

ALL_EVENTS = [
    {"date": _d(2026,7,29), "name": "US GDP Q2 Advance", "country": "US", "impact": "HIGH", "previous": "0.3%", "forecast": "0.4%", "actual": None, "asset_class": ["BTC", "SPY"]},
    {"date": _d(2026,7,30), "name": "FOMC Rate Decision", "country": "US", "impact": "HIGH", "previous": "5.25%", "forecast": "5.25%", "actual": None, "asset_class": ["BTC", "ETH", "SPY", "EURUSD"]},
    {"date": _d(2026,7,30), "name": "FOMC Press Conference", "country": "US", "impact": "HIGH", "previous": None, "forecast": None, "actual": None, "asset_class": ["BTC", "ETH", "SPY", "EURUSD"]},
    {"date": _d(2026,8,1), "name": "US Non-Farm Payrolls (NFP)", "country": "US", "impact": "HIGH", "previous": "206K", "forecast": "185K", "actual": None, "asset_class": ["BTC", "SPY", "EURUSD", "Gold"]},
    {"date": _d(2026,8,1), "name": "US Unemployment Rate", "country": "US", "impact": "HIGH", "previous": "4.2%", "forecast": "4.1%", "actual": None, "asset_class": ["BTC", "SPY", "Gold"]},
    {"date": _d(2026,8,5), "name": "US CPI Month-over-Month", "country": "US", "impact": "HIGH", "previous": "-0.1%", "forecast": "0.2%", "actual": None, "asset_class": ["BTC", "SPY", "Gold"]},
    {"date": _d(2026,8,5), "name": "US CPI Year-over-Year", "country": "US", "impact": "HIGH", "previous": "2.97%", "forecast": "3.0%", "actual": None, "asset_class": ["BTC", "SPY", "Gold"]},
    {"date": _d(2026,8,6), "name": "ECB Rate Decision", "country": "EU", "impact": "HIGH", "previous": "4.25%", "forecast": "4.25%", "actual": None, "asset_class": ["EURUSD", "SPY", "BTC"]},
    {"date": _d(2026,8,8), "name": "US PPI Month-over-Month", "country": "US", "impact": "MEDIUM", "previous": "0.0%", "forecast": "0.2%", "actual": None, "asset_class": ["BTC", "SPY"]},
    {"date": _d(2026,8,10), "name": "US Consumer Confidence", "country": "US", "impact": "MEDIUM", "previous": "98.7", "forecast": "97.0", "actual": None, "asset_class": ["SPY", "BTC"]},
    {"date": _d(2026,8,12), "name": "US CPI (Final)", "country": "US", "impact": "MEDIUM", "previous": None, "forecast": None, "actual": None, "asset_class": ["BTC", "SPY", "Gold"]},
    {"date": _d(2026,8,13), "name": "US Producer Price Index", "country": "US", "impact": "MEDIUM", "previous": "0.0%", "forecast": "0.2%", "actual": None, "asset_class": ["BTC", "SPY"]},
    {"date": _d(2026,8,14), "name": "US Retail Sales", "country": "US", "impact": "HIGH", "previous": "0.1%", "forecast": "0.4%", "actual": None, "asset_class": ["SPY", "BTC"]},
    {"date": _d(2026,8,19), "name": "FOMC Minutes", "country": "US", "impact": "HIGH", "previous": None, "forecast": None, "actual": None, "asset_class": ["BTC", "ETH", "SPY", "EURUSD"]},
    {"date": _d(2026,8,21), "name": "US Initial Jobless Claims", "country": "US", "impact": "MEDIUM", "previous": "235K", "forecast": "230K", "actual": None, "asset_class": ["SPY", "BTC"]},
    {"date": _d(2026,8,26), "name": "US PCE Inflation", "country": "US", "impact": "HIGH", "previous": "2.6%", "forecast": "2.5%", "actual": None, "asset_class": ["BTC", "SPY", "Gold", "EURUSD"]},
    {"date": _d(2026,8,28), "name": "US GDP Q2 Final", "country": "US", "impact": "MEDIUM", "previous": None, "forecast": None, "actual": None, "asset_class": ["SPY", "BTC"]},
    {"date": _d(2026,8,29), "name": "US Michigan Consumer Sentiment", "country": "US", "impact": "MEDIUM", "previous": "68.0", "forecast": "67.5", "actual": None, "asset_class": ["SPY", "BTC"]},
    {"date": _d(2026,9,3), "name": "US ISM Manufacturing PMI", "country": "US", "impact": "HIGH", "previous": "48.5", "forecast": "49.0", "actual": None, "asset_class": ["SPY", "BTC", "Gold"]},
    {"date": _d(2026,9,5), "name": "US Non-Farm Payrolls (NFP)", "country": "US", "impact": "HIGH", "previous": "185K", "forecast": "175K", "actual": None, "asset_class": ["BTC", "SPY", "EURUSD", "Gold"]},
    {"date": _d(2026,9,7), "name": "FOMC Meeting", "country": "US", "impact": "HIGH", "previous": None, "forecast": "No change", "actual": None, "asset_class": ["BTC", "ETH", "SPY", "EURUSD"]},
    {"date": _d(2026,9,10), "name": "US CPI Month-over-Month", "country": "US", "impact": "HIGH", "previous": "0.2%", "forecast": "0.2%", "actual": None, "asset_class": ["BTC", "SPY", "Gold"]},
    {"date": _d(2026,9,17), "name": "FOMC Rate Decision", "country": "US", "impact": "HIGH", "previous": "5.25%", "forecast": "5.00%", "actual": None, "asset_class": ["BTC", "ETH", "SPY", "EURUSD"]},
    {"date": _d(2026,9,18), "name": "ECB Rate Decision", "country": "EU", "impact": "HIGH", "previous": "4.25%", "forecast": "3.75%", "actual": None, "asset_class": ["EURUSD", "BTC", "SPY"]},
]

@app.get("/api/calendar/events")
async def events(symbol: str = Query(None, description="Filter by symbol like BTC")):
    today = datetime.now(timezone.utc)
    future_events = [e for e in ALL_EVENTS if e["date"] >= today]
    if symbol:
        future_events = [e for e in future_events if symbol.upper() in e["asset_class"]]
    return {
        "events": [
            {**e, "date": e["date"].isoformat()} for e in sorted(future_events, key=lambda x: x["date"])
        ],
        "count": len(future_events),
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/calendar/upcoming")
async def upcoming(days: int = Query(7, description="Days ahead")):
    today = datetime.now(timezone.utc)
    end = today + timedelta(days=days)
    events = [e for e in ALL_EVENTS if today <= e["date"] <= end]
    high_impact = [e for e in events if e["impact"] == "HIGH"]
    return {
        "period_days": days,
        "events": [{**e, "date": e["date"].isoformat()} for e in sorted(events, key=lambda x: x["date"])],
        "total": len(events),
        "high_impact_count": len(high_impact),
        "high_impact_events": [{**e, "date": e["date"].isoformat()} for e in high_impact],
        "trading_note": "High-impact events can cause volatility spikes. AI agents should check preflight before trading around these dates.",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/calendar/check")
async def check_today():
    today = datetime.now(timezone.utc).date()
    today_events = [e for e in ALL_EVENTS if e["date"].date() == today]
    return {
        "today_events": [{**e, "date": e["date"].isoformat()} for e in today_events],
        "has_events_today": len(today_events) > 0,
        "impact_today": "HIGH" if any(e["impact"] == "HIGH" for e in today_events) else "MEDIUM" if any(e["impact"] == "MEDIUM" for e in today_events) else "LOW",
        "note": "Always check preflight before making decisions on high-impact event days." if today_events else "No major events today — standard trading conditions.",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "calendar", "version": "1.0.0"}

@app.get("/favicon.ico")
async def favicon():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/static/favicon.ico", status_code=302)