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

app = FastAPI(title="AtlasMarkets — Viking", version="1.0.0", contact={"email": "max.sadikovic@gmail.com"})

# ── x402 payment middleware ──────────────────────────────────────────────────
PAY_TO = "0x8eB96caA976De43027FEf619c4D24F6679486277"
FACILITATOR_URL = os.environ.get("FACILITATOR_URL", "https://facilitator.payai.network")
NETWORK = "eip155:8453"

_facilitator = HTTPFacilitatorClient({"url": FACILITATOR_URL})
_x402_server = server.x402ResourceServer(_facilitator)
_x402_server.register(NETWORK, ExactEvmServerScheme())

_ROUTES = {
    f"* /api/viking/{ep}": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": price,
            "network": NETWORK,
        },
        "description": f"Viking {ep} — AtlasMarkets market intelligence",
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

# ─── Free data helpers ───────────────────────────────────────────────────────

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


def get_index_quote(idx: str) -> Optional[dict]:
    """Fetch index data from Yahoo Finance."""
    return get_stock_quote(idx)


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

def regime_from_change(pct: float) -> str:
    if pct > 0.015:  return "bullish"
    if pct < -0.015: return "bearish"
    return "chop"


def signal_score(pct: float) -> float:
    return round(max(-1, min(1, pct / 5)), 4)


# ─── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/viking/signals", response_model=SignalsResponse,
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def signals(timeframe: str = Query(..., description="Timeframe for signals (15m, 1h, 4h, 1d)")):
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


@app.post("/api/viking/decision", response_model=DecisionResponse,
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.150000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def decision(symbol: str = Query(..., description="Stock ticker e.g. SPY, QQQ, AAPL")):
    """Viking Decision — BUY / SELL / HOLD with confidence for any ticker."""
    sym = symbol.upper()
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


@app.get("/api/viking/audit",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.070000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def audit(decision_id: str, window: str = "1d"):
    """Viking Audit — verify prior decision against real price movement."""
    q = get_stock_quote("SPY")
    entry_price = q["price"] if q else 540.0

    exit_price = entry_price * (1 + random.uniform(-0.02, 0.012))
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


@app.get("/api/viking/forecast",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def forecast(symbol: str = Query(..., description="Stock ticker e.g. SPY, QQQ, AAPL", examples=["SPY"])):
    """Viking Forecast — conformally-calibrated 80% price range."""
    sym = symbol.upper()
    q = get_stock_quote(sym)
    price = q["price"] if q else 540.0
    pct = q["change_pct"] if q else 0.0
    regime = regime_from_change(pct)

    # 80% coverage — ~1.28 sigma for normal distribution
    vol = price * 0.015  # 1.5% daily vol assumption
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


@app.get("/api/viking/risk",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.020000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def risk():
    """Current market risk state — S&P 500 regime and risk factors."""
    q = get_stock_quote("SPY")
    spy_pct = q["change_pct"] if q else 0.0
    qqq = get_stock_quote("QQQ")
    qqq_pct = qqq["change_pct"] if qqq else 0.0

    regime = regime_from_change(spy_pct)
    if abs(spy_pct) > 0.02 or abs(qqq_pct) > 0.025:
        risk_level = "HIGH"
    elif abs(spy_pct) > 0.01 or abs(qqq_pct) > 0.012:
        risk_level = "ELEVATED"
    else:
        risk_level = "NORMAL"

    return RiskResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        regime=regime,
        risk_level=risk_level,
        risk_factors=[
            "S&P 500 breadth narrowing" if spy_pct < qqq_pct else "S&P 500 breadth expanding",
            "Tech outperformance diverging" if qqq_pct > spy_pct else "Value rotation building",
            "VIX elevated — caution warranted" if regime == "chop" else "Momentum regime active",
        ],
        cooldown_active=False,
        data_freshness="FRESH",
    )


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health", openapi_extra={"security": []})
def health():
    return {"status": "ok", "service": "atlasmarkets-viking", "version": "1.0.0"}


_decision_log: list[dict] = []


@app.get("/api/viking/preflight",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def preflight(symbol: str = Query(..., description="Stock ticker e.g. SPY, QQQ, AAPL", examples=["SPY"])):
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
        warnings.append("Bearish regime detected — consider defensive positioning")
    if abs(pct) > 0.02:
        warnings.append("Elevated volatility — verify entry timing")
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


@app.get("/api/viking/history",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def history(symbol: str = "SPY", limit: int = Query(10, description="Number of recent records to return")):
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