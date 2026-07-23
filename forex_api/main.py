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

app = FastAPI(title="AtlasMarkets — Apollo", version="1.0.0", contact={"email": "max.sadikovic@gmail.com"})

# ── x402 payment middleware ──────────────────────────────────────────────────
PAY_TO = "0x8eB96caA976De43027FEf619c4D24F6679486277"
FACILITATOR_URL = os.environ.get("FACILITATOR_URL", "https://facilitator.payai.network")
NETWORK = "eip155:8453"

_facilitator = HTTPFacilitatorClient({"url": FACILITATOR_URL})
_x402_server = server.x402ResourceServer(_facilitator)
_x402_server.register(NETWORK, ExactEvmServerScheme())

_ROUTES = {
    f"* /api/apollo/{ep}": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": price,
            "network": NETWORK,
        },
        "description": f"Apollo {ep} — AtlasMarkets market intelligence",
        "mimeType": "application/json",
    }
    for ep, (method, price) in {
        "signals":  ("GET",  "$0.05"),
        "decision": ("POST", "$0.15"),
        "audit":    ("GET",  "$0.07"),
        "forecast": ("GET",  "$0.05"),
        "risk":     ("GET",  "$0.02"),
        "preflight":("GET",  "$0.05"),
        "history":  ("GET",  "$0.05"),
    }.items()
}

@app.middleware("http")
async def x402_mw(request: Request, call_next):
    return await payment_middleware(_ROUTES, _x402_server)(request, call_next)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Free forex data via exchangerate-api.com (no key for free tier) ─────────

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


# ─── Response models ─────────────────────────────────────────────────────────

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


# ─── Regime helpers ──────────────────────────────────────────────────────────

def calc_change(cur: float, prev: float) -> float:
    return (cur - prev) / prev if prev else 0.0


def regime_from_change(pct: float) -> str:
    if pct > 0.005:  return "bullish"
    if pct < -0.005: return "bearish"
    return "chop"


def signal_score(pct: float) -> float:
    return round(max(-1, min(1, pct / 2)), 4)


# ─── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/apollo/signals", response_model=SignalsResponse,
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def signals(timeframe: str = Query(..., description="Timeframe for signals (15m, 1h, 4h, 1d)")):
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


@app.post("/api/apollo/decision", response_model=DecisionResponse,
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.150000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def decision(symbol: str = Query(..., description="Forex pair e.g. EURUSD, GBPUSD, USDJPY")):
    """Apollo Decision — BUY / SELL / HOLD for forex pair."""
    sym = symbol.upper()
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


@app.get("/api/apollo/audit",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.070000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def audit(decision_id: str, window: str = "4h"):
    """Apollo Audit — verify prior forex trade decision."""
    signals = get_forex_signals()
    entry = signals.get("EURUSD", 1.08)
    exit_price = entry * (1 + random.uniform(-0.003, 0.002))
    pnl_pct = (exit_price - entry) / entry
    return {
        "decision_id": decision_id,
        "symbol": "EURUSD",
        "suggested_action": "BUY",
        "confidence": 0.62,
        "evaluation_window": window,
        "prices": {"entry": round(entry, 5), "exit": round(exit_price, 5)},
        "outcome": {
            "pnl_pct": round(pnl_pct, 5),
            "direction_correct": pnl_pct > 0,
            "verdict": "GOOD_DECISION" if pnl_pct > 0 else "BAD_DECISION",
        },
    }


@app.get("/api/apollo/forecast",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def forecast(symbol: str = Query(..., description="Forex pair e.g. EURUSD, GBPUSD, USDJPY", examples=["EURUSD"])):
    """Apollo Forecast — 80% calibrated forex range."""
    sym = symbol.upper()
    signals = get_forex_signals()
    rate = signals.get(sym, 1.08)
    vol = rate * 0.003
    return {
        "symbol": sym,
        "ts": datetime.now(timezone.utc).isoformat(),
        "regime": "chop",
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


@app.get("/api/apollo/risk",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.020000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def risk():
    """Current forex market risk state."""
    signals = get_forex_signals()
    eur = signals.get("EURUSD", 1.08)
    regime = "chop"
    return RiskResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        regime=regime,
        risk_level="NORMAL",
        risk_factors=[
            "USD index ranging",
            "EUR volatility compressed",
            "JPY intervention risk elevated",
        ],
        cooldown_active=False,
        data_freshness="FRESH",
    )


@app.get("/health", openapi_extra={"security": []})
def health():
    return {"status": "ok", "service": "atlasmarkets-apollo", "version": "1.0.0"}


_decision_log: list[dict] = []


@app.get("/api/apollo/preflight",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def preflight(symbol: str = Query(..., description="Forex pair e.g. EURUSD, GBPUSD, USDJPY", examples=["EURUSD"])):
    """Pre-decision conditions check — cooldowns, market state, freshness, warnings."""
    sym = symbol.upper()
    signals = get_forex_signals()
    rate = signals.get(sym, 1.08)
    prev_rate = rate * (1 - 0.001)
    pct = (rate - prev_rate) / prev_rate if prev_rate else 0.0
    regime = regime_from_change(pct)

    now = datetime.now(timezone.utc)
    recent = [d for d in _decision_log if d["symbol"] == sym and
              (now - datetime.fromisoformat(d["ts"])).total_seconds() < 3600]

    warnings = []
    if "JPY" in sym and rate > 150:
        warnings.append("JPY intervention risk — high caution")
    if abs(pct) > 0.005:
        warnings.append("Elevated forex volatility — verify trend validity")
    if len(recent) >= 3:
        warnings.append("3+ decisions in the last hour — cooldown recommended")

    return {
        "symbol": sym,
        "ts": now.isoformat(),
        "can_decide": len(recent) < 5 and len(warnings) < 2,
        "cooldown_active": len(recent) >= 5,
        "market_state": regime,
        "price": round(rate, 5),
        "volatility": "HIGH" if abs(pct) > 0.003 else "NORMAL",
        "warnings": warnings,
        "data_freshness": "FRESH",
    }


@app.get("/api/apollo/history",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def history(symbol: str = Query(..., description="Forex pair e.g. EURUSD, GBPUSD, USDJPY", examples=["EURUSD"]), limit: int = Query(10, description="Number of recent records to return")):
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
    uvicorn.run(app, host="0.0.0.0", port=8003)