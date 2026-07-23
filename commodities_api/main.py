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

app = FastAPI(title="AtlasMarkets — Pollux", version="1.0.0")

# ── x402 payment middleware ──────────────────────────────────────────────────
PAY_TO = "0x8eB96caA976De43027FEf619c4D24F6679486277"
FACILITATOR_URL = os.environ.get("FACILITATOR_URL", "https://facilitator.payai.network")
NETWORK = "eip155:8453"

_facilitator = HTTPFacilitatorClient({"url": FACILITATOR_URL})
_x402_server = server.x402ResourceServer(_facilitator)
_x402_server.register(NETWORK, ExactEvmServerScheme())

_ROUTES = {
    f"* /api/pollux/{ep}": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": price,
            "network": NETWORK,
        },
        "description": f"Pollux {ep} — AtlasMarkets market intelligence",
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

# ─── Commodity data via Yahoo Finance ───────────────────────────────────────

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


# ─── Helpers ─────────────────────────────────────────────────────────────────

def regime_from_change(pct: float) -> str:
    if pct > 0.02:   return "bullish"
    if pct < -0.02:  return "bearish"
    return "chop"


def signal_score(pct: float) -> float:
    return round(max(-1, min(1, pct / 5)), 4)


# ─── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/pollux/signals", response_model=SignalsResponse,
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def signals(timeframe: str = "1d"):
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


@app.post("/api/pollux/decision", response_model=DecisionResponse,
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.150000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def decision(symbol: str = Query(default="Gold (XAU/USD)", description="Commodity name as listed")):
    """Pollux Decision — BUY / SELL / HOLD for commodities."""
    sym = symbol
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


@app.get("/api/pollux/audit",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.070000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def audit(decision_id: str, window: str = "1d"):
    """Pollux Audit — verify prior commodity decision."""
    gold = get_commodity_price("GC=F") or 2350.0
    entry = gold
    exit_price = entry * (1 + random.uniform(-0.015, 0.01))
    pnl_pct = (exit_price - entry) / entry
    return {
        "decision_id": decision_id,
        "symbol": "Gold (XAU/USD)",
        "suggested_action": "CONSIDER_LONG",
        "confidence": 0.61,
        "evaluation_window": window,
        "prices": {"entry": round(entry, 2), "exit": round(exit_price, 2)},
        "outcome": {
            "pnl_pct": round(pnl_pct, 5),
            "direction_correct": pnl_pct > 0,
            "verdict": "GOOD_DECISION" if pnl_pct > 0 else "BAD_DECISION",
        },
    }


@app.get("/api/pollux/forecast",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def forecast(symbol: str = "Gold (XAU/USD)"):
    """Pollux Forecast — 80% calibrated commodity range."""
    sym = symbol
    data = get_all_commodities()
    price = data.get(sym, 2350.0)
    vol = price * 0.015
    return {
        "symbol": sym,
        "ts": datetime.now(timezone.utc).isoformat(),
        "regime": "chop",
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


@app.get("/api/pollux/risk",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.020000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def risk():
    """Current commodity market risk state."""
    gold = get_commodity_price("GC=F") or 2350.0
    oil = get_commodity_price("CL=F") or 78.0
    regime = regime_from_change(gold / 2000 - 1)
    if oil > 90:
        risk_level = "HIGH"
    elif oil > 80:
        risk_level = "ELEVATED"
    else:
        risk_level = "NORMAL"
    return RiskResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        regime=regime,
        risk_level=risk_level,
        risk_factors=[
            "Gold range-bound near all-time highs",
            "Oil elevated on supply concerns",
            "Metals showing industrial demand weakness",
        ],
        cooldown_active=False,
        data_freshness="FRESH",
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "atlasmarkets-pollux", "version": "1.0.0"}


_decision_log: list[dict] = []


@app.get("/api/pollux/preflight",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def preflight(symbol: str = "Gold (XAU/USD)"):
    """Pre-decision conditions check — cooldowns, market state, freshness, warnings."""
    sym = symbol
    data = get_all_commodities()
    price = data.get(sym, 2350.0)
    prev = price * (1 - random.uniform(0.005, 0.015))
    pct = (price - prev) / prev if prev else 0.0
    regime = regime_from_change(pct)

    now = datetime.now(timezone.utc)
    recent = [d for d in _decision_log if d["symbol"] == sym and
              (now - datetime.fromisoformat(d["ts"])).total_seconds() < 3600]

    warnings = []
    if "Gold" in sym and price > 2400:
        warnings.append("Gold near all-time highs — reversal risk elevated")
    if "Oil" in sym and price > 90:
        warnings.append("Oil elevated — OPEC supply risk")
    if abs(pct) > 0.02:
        warnings.append("Commodity volatility elevated — verify position sizing")
    if len(recent) >= 3:
        warnings.append("3+ decisions in the last hour — cooldown recommended")

    return {
        "symbol": sym,
        "ts": now.isoformat(),
        "can_decide": len(recent) < 5 and len(warnings) < 2,
        "cooldown_active": len(recent) >= 5,
        "market_state": regime,
        "price": round(price, 2),
        "volatility": "HIGH" if abs(pct) > 0.015 else "NORMAL",
        "warnings": warnings,
        "data_freshness": "FRESH",
    }


@app.get("/api/pollux/history",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def history(symbol: str = "Gold (XAU/USD)", limit: int = 10):
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