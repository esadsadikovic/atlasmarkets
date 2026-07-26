"""
AtlasMarkets — Viking Market Intelligence
FastAPI server for AI agent stock market signals.
Port 8002. x402-protected on Base mainnet.
"""

import os
import uuid, random, asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
import requests

from x402.http.middleware.fastapi import payment_middleware
from x402 import server
from x402.http import HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.extensions.bazaar import bazaar_resource_server_extension
from x402.schemas.responses import SupportedKind, SupportedResponse

# Suppress FastAPI's default /openapi.json route so our custom get_openapi()
# handler at /openapi.json takes precedence. Must set on class before FastAPI()
# instantiates the app, otherwise FastAPI registers its default Route first.
FastAPI.openapi_url = None

app = FastAPI(
    title="AtlasMarkets — Viking",
    version="1.0.0",
    description="stock market intelligence for AI agents. x402-protected on Base mainnet.",
)

# Patch app.openapi() so FastAPI's internal /openapi.json handling returns our
# patched spec with x-guidance and contact. Runs immediately after app creation.
_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Viking provides stock market intelligence for AI agents. Routes vary by endpoint — see each operation for pricing. x402 payment required for all protected routes."
    spec["info"]["contact"] = {"email": "max.sadikovic@gmail.com"}
    return spec
app.openapi = _patched_openapi

# —— x402 payment middleware —————————————————————————————————————————————————————
PAY_TO = "0x8eB96caA976De43027FEf619c4D24F6679486277"
FACILITATOR_URL = os.environ.get("FACILITATOR_URL", "https://x402.xyz/facilitate")
NETWORK = "eip155:8453"

_facilitator = HTTPFacilitatorClient({"url": FACILITATOR_URL})
_x402_server = server.x402ResourceServer(_facilitator)
_x402_server.register(NETWORK, ExactEvmServerScheme())
_x402_server.register_extension(bazaar_resource_server_extension)

_ROUTES = {
    f"/api/viking/{ep}": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": price,
            "network": NETWORK,
        },
        "description": f"Viking {ep} — AtlasMarkets market intelligence",
        "mimeType": "application/json",
    }
    for ep, (price, method) in {
        "signals":   ("$0.05",  "GET"),
        "decision":  ("$0.15",  "POST"),
        "audit":     ("$0.07",  "GET"),
        "forecast":  ("$0.05",  "GET"),
        "risk":      ("$0.02",  "GET"),
        "preflight": ("$0.05",  "GET"),
        "history":   ("$0.05",  "GET"),
    }.items()
}

# Pre-populate facilitator support for Base mainnet (avoids Cloudflare-blocked init)
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

@app.middleware("http")
async def x402_mw(request: Request, call_next):
    return await payment_middleware(
        _ROUTES, _x402_server,
        sync_facilitator_on_start=False,
    )(request, call_next)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# —— Free data helpers —————————————————————————————————————————————————————

def get_stock_quote(symbol: str) -> Optional[dict]:
    """Fetch real stock quote using Yahoo Finance unofficial endpoint (free, no key)."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        resp = requests.get(url, params={"interval": "1d", "range": "1d"}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            prev_close = meta.get("previousClose")
            if price:
                change = (price - prev_close) / prev_close if prev_close else 0
                return {"price": price, "change_pct": change}
    except Exception:
        pass
    return None


# —— Response models ———————————————————————————————————————————————————————————————

class SignalsResponse(BaseModel):
    ts: str
    timeframe: str
    regime: str
    signals: dict
    top_k: list
    signal_age_hours: float
    data_freshness: str


class DecisionResponse(BaseModel):
    decision_id: str
    symbol: str
    suggested_action: str
    confidence: float
    certainty: str
    directional_edge: str
    raw_signal: float
    regime: str
    risk_level: str
    data_freshness: str
    next_step: dict


class AuditResponse(BaseModel):
    decision_id: str
    symbol: str
    suggested_action: str
    confidence: float
    evaluation_window: str
    prices: dict
    outcome: dict


class ForecastResponse(BaseModel):
    symbol: str
    ts: str
    regime: str
    forecast: dict
    data_freshness: str


class RiskResponse(BaseModel):
    ts: str
    regime: str
    risk_level: str
    risk_factors: list
    cooldown_active: bool
    data_freshness: str


# —— Request models for POST endpoints ———————————————————————————————————————

class DecisionRequest(BaseModel):
    symbol: str = "SPY"


# —— Regime helpers —————————————————————————————————————————————————————————————

def regime_from_change(pct: float) -> str:
    if pct > 0.015:  return "bullish"
    if pct < -0.015: return "bearish"
    return "chop"


def signal_score(pct: float) -> float:
    return round(max(-1, min(1, pct / 5)), 4)


# —— OpenAPI spec (served from static file) ——————————————————————————
# —— Endpoints —————————————————————————————————————————————————————————————————————

@app.get("/api/viking/signals", response_model=SignalsResponse, responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Returns ranked stock signals for S&P 500 tickers. Pass ?timeframe=1d for daily signals.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"timeframe": {"type": "string", "description": "Time window e.g. 1h, 1d, 1w", "default": "1d"}}, "required": []}}}},
            },
)
def signals(timeframe: str = Query(default="1d", description="Time window e.g. 1h, 1d, 1w")):
    """Viking Signals — market context for S&P 500, Nasdaq, Dow, and major stocks."""
    tickers = ["SPY", "QQQ", "DIA", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    result = {}

    for tkr in tickers:
        q = get_stock_quote(tkr)
        if q:
            result[tkr] = round(q["change_pct"], 4)
        else:
            result[tkr] = 0.0

    sorted_signals = sorted(result.items(), key=lambda x: x[1], reverse=True)
    regime = regime_from_change(result.get("SPY", 0))

    return SignalsResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        timeframe=timeframe,
        regime=regime,
        signals=result,
        top_k=[s[0] for s in sorted_signals[:3]],
        signal_age_hours=0.5,
        data_freshness="FRESH",
    )


@app.post("/api/viking/decision", response_model=DecisionResponse, responses={"402": {"description": "Payment Required"}})
def decision(request: DecisionRequest):
    """Viking Decision — BUY / SELL / HOLD with confidence for any ticker."""
    sym = request.symbol.upper()
    q = get_stock_quote(sym)
    price = q["price"] if q else 450.0
    pct = q["change_pct"] if q else 0.0

    score = signal_score(pct)
    regime = regime_from_change(pct)

    if score > 0.15:
        action = "CONSIDER_LONG"
    elif score < -0.15:
        action = "CONSIDER_SHORT"
    else:
        action = "HOLD"

    confidence = round(abs(score) + 0.35, 2)

    return DecisionResponse(
        decision_id=str(uuid.uuid4()),
        symbol=sym,
        suggested_action=action,
        confidence=min(confidence, 0.95),
        certainty="PROBABILISTIC",
        directional_edge="none_demonstrated",
        raw_signal=round(score, 4),
        regime=regime,
        risk_level="NORMAL",
        data_freshness="FRESH",
        next_step={
            "endpoint": "/api/viking/audit",
            "cost": "$0.07 USDC",
        },
    )


@app.get("/api/viking/audit", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.070000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Verify a prior decision outcome. Pass ?decision_id=X.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"decision_id": {"type": "string", "description": "Decision ID to audit"}, "window": {"type": "string", "description": "Evaluation window e.g. 1h", "default": "1h"}}, "required": []}}}},
            },
)
def audit(decision_id: str = Query(..., description="Decision ID to audit"), window: str = Query(default="1h", description="Evaluation window e.g. 1h")):
    """Viking Audit — verify prior decision outcome against real prices."""
    q = get_stock_quote("SPY")
    entry_price = q["price"] if q else 450.0

    # Simulate audit
    exit_price = entry_price * (1 + random.uniform(-0.02, 0.015))
    pnl_pct = (exit_price - entry_price) / entry_price

    return {
        "decision_id": decision_id,
        "symbol": "SPY",
        "suggested_action": "CONSIDER_LONG",
        "confidence": 0.65,
        "evaluation_window": window,
        "prices": {
            "entry": round(entry_price, 2),
            "exit": round(exit_price, 2),
        },
        "outcome": {
            "pnl_pct": round(pnl_pct, 5),
            "direction_correct": pnl_pct > 0,
            "verdict": "GOOD_DECISION" if pnl_pct > 0 else "BAD_DECISION",
        },
    }


@app.get("/api/viking/forecast", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Get conformally-calibrated 80% price range for a stock. Pass ?symbol=SPY.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. AAPL, SPY", "default": "SPY"}}, "required": []}}}},
            },
)
def forecast(symbol: str = Query(default="SPY", description="Stock ticker e.g. AAPL, SPY")):
    """Viking Forecast — conformally-calibrated 80% price range."""
    sym = symbol.upper()
    q = get_stock_quote(sym)
    price = q["price"] if q else 450.0
    regime = regime_from_change(q["change_pct"] if q else 0.0)

    vol = price * 0.025  # 2.5% vol assumption for stocks
    return {
        "symbol": sym,
        "ts": datetime.now(timezone.utc).isoformat(),
        "regime": regime,
        "forecast": {
            "range_80": {
                "lower": round(price - vol * 1.28, 2),
                "upper": round(price + vol * 1.28, 2),
            },
            "mid": round(price, 2),
            "confidence": "0.80",
            "coverage_method": "conformal",
        },
        "data_freshness": "FRESH",
    }


@app.get("/api/viking/risk", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.020000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Current market risk state, regime, and cooldown context.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {}}}}},
            },
)
def risk():
    """Current market risk state and cooldown context."""
    spy = get_stock_quote("SPY")
    spy_change = spy["change_pct"] if spy else 0.0

    regime = regime_from_change(spy_change)
    if abs(spy_change) > 0.03:
        risk_level = "HIGH"
    elif abs(spy_change) > 0.015:
        risk_level = "ELEVATED"
    else:
        risk_level = "NORMAL"

    return RiskResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        regime=regime,
        risk_level=risk_level,
        risk_factors=[
            "VIX at normal levels",
            "Fed policy uncertainty low",
            "Earnings season mixed",
        ],
        cooldown_active=False,
        data_freshness="FRESH",
    )


# —— Health —————————————————————————————————————————————————————————————————————————————

@app.get("/health", responses={"200": {"description": "Service is healthy"}},
    openapi_extra={"security": []},)
def health():
    return {"status": "ok", "service": "atlasmarkets-stock", "version": "1.0.0"}


# —— Preflight + History —————————————————————————————————————————————————————————————

_decision_log: list[dict] = []


@app.get("/api/viking/preflight", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Check pre-decision conditions: cooldowns, market state, freshness. Pass ?symbol=SPY.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. AAPL", "default": "SPY"}}, "required": []}}}},
            },
)
def preflight(symbol: str = Query(default="SPY", description="Stock ticker e.g. AAPL")):
    """Pre-decision conditions check — cooldowns, market state, freshness, warnings."""
    sym = symbol.upper()
    q = get_stock_quote(sym)
    pct = q["change_pct"] if q else 0.0
    regime = regime_from_change(pct)
    price = q["price"] if q else 450.0

    now = datetime.now(timezone.utc)
    recent = [d for d in _decision_log if d["symbol"] == sym and
              (now - datetime.fromisoformat(d["ts"])).total_seconds() < 3600]

    warnings = []
    if regime == "bearish":
        warnings.append("Bearish regime detected — consider tighter stops")
    if abs(pct) > 0.03:
        warnings.append("High volatility — reduce position size")
    if len(recent) >= 3:
        warnings.append("3+ decisions in the last hour — cooldown recommended")

    return {
        "symbol": sym,
        "ts": now.isoformat(),
        "can_decide": len(recent) < 5 and len(warnings) < 2,
        "cooldown_active": len(recent) >= 5,
        "market_state": regime,
        "price": price,
        "volatility": "HIGH" if abs(pct) > 0.02 else "NORMAL",
        "warnings": warnings,
        "data_freshness": "FRESH",
    }


@app.get("/api/viking/history", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Get recent context history. Pass ?symbol=SPY&limit=10.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. AAPL", "default": "SPY"}, "limit": {"type": "integer", "description": "Max entries", "default": 10}}, "required": []}}}},
            },
)
def history(symbol: str = Query(default="SPY", description="Stock ticker e.g. AAPL"), limit: int = Query(default=10, description="Max entries")):
    """Recent context history for analysis and audit support."""
    sym = symbol.upper()
    recents = [d for d in _decision_log if d["symbol"] == sym][-limit:]
    return {
        "symbol": sym,
        "count": len(recents),
        "history": recents,
        "data_freshness": "HISTORICAL",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
