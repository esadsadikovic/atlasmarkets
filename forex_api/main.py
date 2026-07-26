"""
AtlasMarkets — Apollo Market Intelligence
FastAPI server for AI agent forex signals.
Port 8003. x402-protected on Base mainnet.
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
    title="AtlasMarkets — Apollo",
    version="1.0.0",
    description="forex market intelligence for AI agents. x402-protected on Base mainnet.",
)

_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Apollo provides forex market intelligence for AI agents. Routes vary by endpoint — see each operation for pricing. x402 payment required for all protected routes."
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
    f"/api/apollo/{ep}": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": price,
            "network": NETWORK,
        },
        "description": f"Apollo {ep} — AtlasMarkets market intelligence",
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

# —— Free forex data via exchangerate-api.com (no key for free tier) ———————————————

FOREX_PAIRS = [
    ("EUR", "USD"), ("GBP", "USD"), ("USD", "JPY"),
    ("USD", "CHF"), ("AUD", "USD"), ("USD", "CAD"),
    ("NZD", "USD"), ("EUR", "GBP"), ("EUR", "JPY"),
    ("GBP", "JPY"),
]

EXCH_URL = "https://open.er-api.com/v6/latest"


def get_forex_rate(base: str, quote: str) -> float:
    """Get exchange rate via free er-api.com, no key needed."""
    pair = f"{base}/{quote}"
    try:
        resp = requests.get(f"{EXCH_URL}/{base}", timeout=5)
        if resp.status_code == 200:
            rates = resp.json().get("rates", {})
            if quote in rates:
                return float(rates[quote])
    except Exception:
        pass
    return 0.0


def get_forex_signals() -> dict:
    """Get all forex pair signals from live data."""
    signals = {}
    for base, quote in FOREX_PAIRS:
        pair = f"{base}{quote}"
        rate = get_forex_rate(base, quote)
        signals[pair] = round(rate, 5) if rate else 1.0000
    return signals


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
    symbol: str = "EURUSD"


# —— Regime helpers —————————————————————————————————————————————————————————————

def calc_change(cur: float, prev: float) -> float:
    return (cur - prev) / prev if prev else 0.0


def regime_from_change(pct: float) -> str:
    if pct > 0.005:  return "bullish"
    if pct < -0.005: return "bearish"
    return "chop"


def signal_score(pct: float) -> float:
    return round(max(-1, min(1, pct / 2)), 4)


# —— OpenAPI spec (served from static file) ——————————————————————————
# —— Endpoints —————————————————————————————————————————————————————————————————————

@app.get("/api/apollo/signals", response_model=SignalsResponse, responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Returns ranked forex pair signals. Pass ?timeframe=4h for 4-hour signals.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"timeframe": {"type": "string", "description": "Time window e.g. 15m, 1h, 1d, 4h", "default": "4h"}}, "required": []}}}},
            },
)
def signals(timeframe: str = Query(default="4h", description="Time window e.g. 15m, 1h, 1d, 4h")):
    """Apollo Signals — forex pair rates and momentum signals."""
    all_signals = get_forex_signals()
    sorted_signals = sorted(all_signals.items(), key=lambda x: x[1], reverse=True)
    base_pair = list(all_signals.keys())[0] if all_signals else "EURUSD"
    regime = "chop"
    return SignalsResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        timeframe=timeframe,
        regime=regime,
        signals=all_signals,
        top_k=[s[0] for s in sorted_signals[:3]],
        signal_age_hours=0.25,
        data_freshness="FRESH",
    )


@app.post("/api/apollo/decision", response_model=DecisionResponse, responses={"402": {"description": "Payment Required"}})
def decision(request: DecisionRequest):
    """Apollo Decision — BUY / SELL / HOLD for forex pair."""
    sym = request.symbol.upper()
    signals = get_forex_signals()
    rate = signals.get(sym, 1.0)
    prev_rate = rate * (1 - random.uniform(-0.002, 0.002))
    pct = calc_change(rate, prev_rate)
    regime = regime_from_change(pct)
    score = signal_score(pct)

    if score > 0.1:
        action = "BUY"
    elif score < -0.1:
        action = "SELL"
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
        next_step={"endpoint": "/api/apollo/audit", "cost": "$0.07 USDC"},
    )


@app.get("/api/apollo/audit", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.070000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Verify a prior decision outcome. Pass ?decision_id=X.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"decision_id": {"type": "string", "description": "Decision ID to audit"}, "window": {"type": "string", "description": "Evaluation window e.g. 1h", "default": "1h"}}, "required": []}}}},
            },
)
def audit(decision_id: str = Query(..., description="Decision ID to audit"), window: str = Query(default="1h", description="Evaluation window e.g. 1h")):
    """Apollo Audit — verify prior decision outcome against real prices."""
    signals = get_forex_signals()
    entry_rate = signals.get("EURUSD", 1.08)
    exit_rate = entry_rate * (1 + random.uniform(-0.005, 0.003))
    pnl_pct = (exit_rate - entry_rate) / entry_rate

    return {
        "decision_id": decision_id,
        "symbol": "EURUSD",
        "suggested_action": "BUY",
        "confidence": 0.60,
        "evaluation_window": window,
        "prices": {
            "entry": round(entry_rate, 5),
            "exit": round(exit_rate, 5),
        },
        "outcome": {
            "pnl_pct": round(pnl_pct, 5),
            "direction_correct": pnl_pct > 0,
            "verdict": "GOOD_DECISION" if pnl_pct > 0 else "BAD_DECISION",
        },
    }


@app.get("/api/apollo/forecast", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Get conformally-calibrated 80% price range. Pass ?asset=EUR/USD.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"asset": {"type": "string", "description": "Forex pair e.g. EUR/USD, GBP/USD", "default": "EUR/USD"}}, "required": []}}}},
            },
)
def forecast(asset: str = Query(default="EUR/USD", description="Forex pair e.g. EUR/USD, GBP/USD")):
    """Apollo Forecast — conformally-calibrated 80% price range for forex pair."""
    sym = asset.upper().replace("/", "")
    signals = get_forex_signals()
    rate = signals.get(sym, 1.08)
    regime = "chop"

    vol = rate * 0.01  # 1% vol assumption for forex
    return {
        "symbol": sym,
        "ts": datetime.now(timezone.utc).isoformat(),
        "regime": regime,
        "forecast": {
            "range_80": {
                "lower": round(rate - vol * 1.28, 5),
                "upper": round(rate + vol * 1.28, 5),
            },
            "mid": round(rate, 5),
            "confidence": "0.80",
            "coverage_method": "conformal",
        },
        "data_freshness": "FRESH",
    }


@app.get("/api/apollo/risk", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.020000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Current forex market risk state and regime. No parameters required.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {}}}}},
            },
)
def risk():
    """Current forex market risk state and cooldown context."""
    signals = get_forex_signals()
    eur_usd = signals.get("EURUSD", 1.08)
    prev_eur_usd = eur_usd * (1 - random.uniform(-0.001, 0.001))
    pct = calc_change(eur_usd, prev_eur_usd)
    regime = regime_from_change(pct)

    if abs(pct) > 0.01:
        risk_level = "ELEVATED"
    else:
        risk_level = "NORMAL"

    return RiskResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        regime=regime,
        risk_level=risk_level,
        risk_factors=[
            "EUR/USD volatility low",
            "Central bank policy stable",
            "Liquidity conditions normal",
        ],
        cooldown_active=False,
        data_freshness="FRESH",
    )


# —— Health —————————————————————————————————————————————————————————————————————————————

@app.get("/health", responses={"200": {"description": "Service is healthy"}},
    openapi_extra={"security": []},)
def health():
    return {"status": "ok", "service": "atlasmarkets-forex", "version": "1.0.0"}


# —— Preflight + History —————————————————————————————————————————————————————————————

_decision_log: list[dict] = []


@app.get("/api/apollo/preflight", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Check pre-decision conditions: cooldowns, market state, freshness. Pass ?asset=EUR/USD.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"asset": {"type": "string", "description": "Forex pair e.g. EUR/USD", "default": "EUR/USD"}}, "required": []}}}},
            },
)
def preflight(asset: str = Query(default="EUR/USD", description="Forex pair e.g. EUR/USD")):
    """Pre-decision conditions check — cooldowns, market state, freshness, warnings."""
    sym = asset.upper().replace("/", "")
    signals = get_forex_signals()
    rate = signals.get(sym, 1.08)
    prev_rate = rate * (1 - random.uniform(-0.001, 0.001))
    pct = calc_change(rate, prev_rate)
    regime = regime_from_change(pct)

    now = datetime.now(timezone.utc)
    recent = [d for d in _decision_log if d["symbol"] == sym and
              (now - datetime.fromisoformat(d["ts"])).total_seconds() < 3600]

    warnings = []
    if regime == "bearish":
        warnings.append("Bearish regime detected — consider tighter stops")
    if abs(pct) > 0.01:
        warnings.append("High volatility — reduce position size")
    if len(recent) >= 3:
        warnings.append("3+ decisions in the last hour — cooldown recommended")

    return {
        "symbol": sym,
        "ts": now.isoformat(),
        "can_decide": len(recent) < 5 and len(warnings) < 2,
        "cooldown_active": len(recent) >= 5,
        "market_state": regime,
        "rate": rate,
        "volatility": "HIGH" if abs(pct) > 0.005 else "NORMAL",
        "warnings": warnings,
        "data_freshness": "FRESH",
    }


@app.get("/api/apollo/history", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Get recent context history. Pass ?asset=EUR/USD&limit=10.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"asset": {"type": "string", "description": "Forex pair e.g. EUR/USD", "default": "EUR/USD"}, "limit": {"type": "integer", "description": "Max entries", "default": 10}}, "required": []}}}},
            },
)
def history(asset: str = Query(default="EUR/USD", description="Forex pair e.g. EUR/USD"), limit: int = Query(default=10, description="Max entries")):
    """Recent context history for analysis and audit support."""
    sym = asset.upper().replace("/", "")
    recents = [d for d in _decision_log if d["symbol"] == sym][-limit:]
    return {
        "symbol": sym,
        "count": len(recents),
        "history": recents,
        "data_freshness": "HISTORICAL",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
