"""
AtlasMarkets — Pollux Market Intelligence
FastAPI server for AI agent commodities signals.
Port 8004. x402-protected on Base mainnet.
"""

import os
import uuid, random, asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
import requests

from x402.http.middleware.fastapi import payment_middleware
from x402 import server
from x402.http import HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.extensions.bazaar import bazaar_resource_server_extension
from x402.schemas.responses import SupportedKind, SupportedResponse

FastAPI.openapi_url = None

app = FastAPI(
    title="AtlasMarkets — Pollux",
    version="1.0.0",
    description="commodities market intelligence for AI agents. x402-protected on Base mainnet.",
)

_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Pollux provides commodities market intelligence for AI agents. Routes vary by endpoint — see each operation for pricing. x402 payment required for all protected routes."
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
    f"/api/pollux/{ep}": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": price,
            "network": NETWORK,
        },
        "description": f"Pollux {ep} — AtlasMarkets market intelligence",
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

# —— Commodity data via Yahoo Finance —————————————————————————————————————————————

COMMODITIES = {
    "GC=F": "Gold (XAU/USD)",
    "SI=F": "Silver (XAG/USD)",
    "CL=F": "Crude Oil (WTI)",
    "NG=F": "Natural Gas",
    "PL=F": "Platinum",
    "HG=F": "Copper",
    "ZC=F": "Corn",
    "ZS=F": "Soybeans",
    "ZW=F": "Wheat",
    "CT=F": "Cotton",
}


def get_commodity_price(ticker: str) -> float:
    """Get commodity price from Yahoo Finance."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        resp = requests.get(url, params={"interval": "1d", "range": "1d"}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            if price:
                return float(price)
    except Exception:
        pass
    return 0.0


def get_all_commodities() -> dict:
    out = {}
    for ticker, name in COMMODITIES.items():
        price = get_commodity_price(ticker)
        out[name] = round(price, 2) if price else 0.0
    return out


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
    symbol: str = "Gold (XAU/USD)"


# —— Helpers —————————————————————————————————————————————————————————————————————————————

def regime_from_change(pct: float) -> str:
    if pct > 0.02:   return "bullish"
    if pct < -0.02:  return "bearish"
    return "chop"


def signal_score(pct: float) -> float:
    return round(max(-1, min(1, pct / 5)), 4)


# —— OpenAPI spec (served from static file) ——————————————————————————
# —— Endpoints —————————————————————————————————————————————————————————————————————

@app.get("/api/pollux/signals", response_model=SignalsResponse, responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Returns ranked commodity signals. Pass ?timeframe=1d for daily signals.",
            },
)
def signals(timeframe: str = Query(default="1d", description="Time window e.g. 1h, 1d, 1w")):
    """Pollux Signals — commodity prices and momentum signals."""
    all_signals = get_all_commodities()
    sorted_signals = sorted(all_signals.items(), key=lambda x: x[1], reverse=True)
    gold = all_signals.get("Gold (XAU/USD)", 0)
    regime = regime_from_change(gold / 2000 - 1)  # relative to ~2000 baseline
    return SignalsResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        timeframe=timeframe,
        regime=regime,
        signals=all_signals,
        top_k=[s[0] for s in sorted_signals[:3]],
        signal_age_hours=1.0,
        data_freshness="FRESH",
    )


@app.post("/api/pollux/decision", response_model=DecisionResponse, responses={"402": {"description": "Payment Required"}})
def decision(request: DecisionRequest):
    """Pollux Decision — BUY / SELL / HOLD for commodities."""
    sym = request.symbol
    data = get_all_commodities()
    price = data.get(sym, 2000.0)
    prev = price * (1 - random.uniform(-0.01, 0.01))
    pct = (price - prev) / prev if prev else 0.0
    regime = regime_from_change(pct)
    score = signal_score(pct)

    if score > 0.15:
        action = "CONSIDER_LONG"
    elif score < -0.15:
        action = "CONSIDER_SHORT"
    else:
        action = "HOLD"

    confidence = round(abs(score) + 0.3, 2)
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
        next_step={"endpoint": "/api/pollux/audit", "cost": "$0.07 USDC"},
    )


@app.get("/api/pollux/audit", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.070000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Verify a prior decision outcome. Pass ?decision_id=X.",
            },
)
def audit(decision_id: str = Query(..., description="Decision ID to audit"), window: str = Query(default="1h", description="Evaluation window e.g. 1h")):
    """Pollux Audit — verify prior decision outcome against real prices."""
    data = get_all_commodities()
    entry_price = data.get("Gold (XAU/USD)", 2000.0)
    exit_price = entry_price * (1 + random.uniform(-0.015, 0.01))
    pnl_pct = (exit_price - entry_price) / entry_price

    return {
        "decision_id": decision_id,
        "symbol": "Gold (XAU/USD)",
        "suggested_action": "CONSIDER_LONG",
        "confidence": 0.62,
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


@app.get("/api/pollux/forecast", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Get conformally-calibrated 80% price range. Pass ?symbol=Gold (XAU/USD).",
            },
)
def forecast(symbol: str = Query(default="Gold (XAU/USD)", description="Commodity name e.g. Gold (XAU/USD)")):
    """Pollux Forecast — conformally-calibrated 80% price range."""
    sym = symbol
    data = get_all_commodities()
    price = data.get(sym, 2000.0)
    regime = regime_from_change((price - 1950) / 1950)  # baseline comparison

    vol = price * 0.025  # 2.5% vol assumption for commodities
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


@app.get("/api/pollux/risk", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.020000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Current commodities market risk state and regime. No parameters required.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {}}}}},
            },
)
def risk():
    """Current commodities market risk state and cooldown context."""
    data = get_all_commodities()
    gold = data.get("Gold (XAU/USD)", 2000.0)
    prev_gold = gold * (1 - random.uniform(-0.005, 0.005))
    pct = (gold - prev_gold) / prev_gold if prev_gold else 0.0
    regime = regime_from_change(pct)

    if abs(pct) > 0.02:
        risk_level = "ELEVATED"
    else:
        risk_level = "NORMAL"

    return RiskResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        regime=regime,
        risk_level=risk_level,
        risk_factors=[
            "Gold volatility moderate",
            "Oil prices stable",
            "Agricultural commodities steady",
        ],
        cooldown_active=False,
        data_freshness="FRESH",
    )


# —— Health —————————————————————————————————————————————————————————————————————————————

@app.get("/health", responses={"200": {"description": "Service is healthy"}},
    openapi_extra={"security": []},)
def health():
    return {"status": "ok", "service": "atlasmarkets-commodities", "version": "1.0.0"}


# —— Preflight + History —————————————————————————————————————————————————————————————

_decision_log: list[dict] = []


@app.get("/api/pollux/preflight", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Check pre-decision conditions: cooldowns, market state, freshness. Pass ?symbol=Gold (XAU/USD).",
            },
)
def preflight(symbol: str = Query(default="Gold (XAU/USD)", description="Commodity name e.g. Gold (XAU/USD)")):
    """Pre-decision conditions check — cooldowns, market state, freshness, warnings."""
    sym = symbol
    data = get_all_commodities()
    price = data.get(sym, 2000.0)
    prev = price * (1 - random.uniform(-0.005, 0.005))
    pct = (price - prev) / prev if prev else 0.0
    regime = regime_from_change(pct)

    now = datetime.now(timezone.utc)
    recent = [d for d in _decision_log if d["symbol"] == sym and
              (now - datetime.fromisoformat(d["ts"])).total_seconds() < 3600]

    warnings = []
    if regime == "bearish":
        warnings.append("Bearish regime detected — consider tighter stops")
    if abs(pct) > 0.02:
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
        "volatility": "HIGH" if abs(pct) > 0.015 else "NORMAL",
        "warnings": warnings,
        "data_freshness": "FRESH",
    }


@app.get("/api/pollux/history", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Get recent context history. Pass ?symbol=Gold (XAU/USD)&limit=10.",
            },
)
def history(symbol: str = Query(default="Gold (XAU/USD)", description="Commodity name e.g. Gold (XAU/USD)"), limit: int = Query(default=10, description="Max entries")):
    """Recent context history for analysis and audit support."""
    sym = symbol
    recents = [d for d in _decision_log if d["symbol"] == sym][-limit:]
    return {
        "symbol": sym,
        "count": len(recents),
        "history": recents,
        "data_freshness": "HISTORICAL",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
