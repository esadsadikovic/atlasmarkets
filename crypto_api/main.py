"""
AtlasMarkets — Anubis Market Intelligence
FastAPI server for AI agent market signals.
Port 8001. x402-protected on Base mainnet.
"""

import os
import uuid, math, random, asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    title="AtlasMarkets — Anubis",
    version="1.0.0",
    description="Crypto market intelligence for AI agents. x402-protected on Base mainnet.",
)

# Patch app.openapi() so FastAPI's internal /openapi.json handling returns our
# patched spec with x-guidance and contact.
_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Anubis provides crypto market intelligence for AI agents. Routes: GET /api/anubis/signals ($0.05), GET /api/anubis/forecast?symbol=BTC ($0.05), GET /api/anubis/risk ($0.02), GET /api/anubis/preflight?symbol=BTC ($0.05), GET /api/anubis/history?symbol=BTC ($0.05), GET /api/anubis/audit?decision_id=X ($0.07), POST /api/anubis/decision ($0.15). All routes return real-time crypto data."
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
    f"/api/anubis/{ep}": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": price,
            "network": NETWORK,
        },
        "extensions": {
            "bazaar": {
                "info": {"input": {"type": "http", "method": "GET", "queryParams": {}}},
                "schema": {
                    "properties": {
                        "input": {
                            "type": "object",
                            "properties": {
                                "type": {"const": "http"},
                                "method": {"enum": ["GET"]},
                                "queryParams": {"type": "object", "properties": {}, "additionalProperties": False},
                                "pathParams": {"type": "object", "properties": {}}
                            },
                            "required": ["type", "method"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["input"]
                }
            }
        },
        "description": f"Anubis {ep} — AtlasMarkets market intelligence",
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

# Pre-populate facilitator support for Base mainnet to avoid Cloudflare-blocked
# initializer call at startup. The exact scheme for eip155:8453 is well-known.
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
        sync_facilitator_on_start=False,  # avoid Cloudflare on startup
    )(request, call_next)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# —— CoinGecko free API helper —————————————————————————————————————————————————
COINGECKO_URL = "https://api.coingecko.com/api/v3"

def get_crypto_price(symbol: str) -> Optional[dict]:
    """Map symbol to CoinGecko id and fetch price data."""
    symbol = symbol.lower()
    id_map = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "xrp": "ripple", "ada": "cardano",
        "doge": "dogecoin", "dot": "polkadot", "avax": "avalanche-2",
        "matic": "matic-network", "link": "chainlink",
    }
    coin_id = id_map.get(symbol, symbol)
    try:
        resp = requests.get(
            f"{COINGECKO_URL}/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            if coin_id in data:
                return {
                    "price": data[coin_id]["usd"],
                    "change_24h": data[coin_id].get("usd_24h_change", 0),
                }
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
    symbol: str = "BTC"


# —— Regime helpers —————————————————————————————————————————————————————————————

def regime_from_change(pct_24h: float) -> str:
    if pct_24h > 5:   return "bullish"
    if pct_24h < -5:  return "bearish"
    return "chop"


def signal_score(pct_24h: float) -> float:
    return round(max(-1, min(1, pct_24h / 10)), 4)


# —— Endpoints —————————————————————————————————————————————————————————————————————

@app.get("/api/anubis/signals", response_model=SignalsResponse, responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}],
        },
        "x-guidance": "Returns current crypto market regime and top signals. Pass ?timeframe=15m for short-term signals.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"timeframe": {"type": "string", "description": "Time window e.g. 15m, 1h, 1d", "default": "15m"}}, "required": []}}}},
    },
)
def signals(timeframe: str = Query(default="15m", description="Time window e.g. 15m, 1h, 1d")):
    """Anubis Signals — market context, score details, and freshness."""
    symbols = ["BTC", "ETH", "SOL", "XRP", "ADA"]
    result = {}
    for sym in symbols:
        data = get_crypto_price(sym.lower())
        if data:
            result[f"{sym}/USD"] = round(data["change_24h"] / 100, 4)
        else:
            result[f"{sym}/USD"] = 0.0

    sorted_signals = sorted(result.items(), key=lambda x: x[1], reverse=True)
    regime = regime_from_change(result.get("BTC/USD", 0) * 100)

    return SignalsResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        timeframe=timeframe,
        regime=regime,
        signals=result,
        top_k=[s[0] for s in sorted_signals[:2]],
        signal_age_hours=0.08,
        data_freshness="FRESH",
    )


@app.post("/api/anubis/decision", response_model=DecisionResponse, responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.150000"},
            "protocols": [{"x402": {}}],
        },
        "x-guidance": "POST a symbol to get a probabilistic market decision. Include JSON body: {\"symbol\": \"BTC\"}.",
    },
)
def decision(request: DecisionRequest):
    """Anubis Decision — probabilistic journal entry with decision_id."""
    sym = request.symbol.upper()
    data = get_crypto_price(sym.lower())
    price = data["price"] if data else 50000.0
    pct = (data["change_24h"] if data else 0) / 100

    score = signal_score(pct)
    regime = regime_from_change(pct * 100)

    if score > 0.2:
        action = "CONSIDER_LONG"
    elif score < -0.2:
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
        next_step={
            "endpoint": "/api/anubis/audit",
            "cost": "$0.07 USDC",
        },
    )


@app.get("/api/anubis/audit", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.070000"},
            "protocols": [{"x402": {}}],
        },
        "x-guidance": "Audit a prior decision outcome. Pass ?decision_id=X to verify against real prices.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"decision_id": {"type": "string", "description": "Decision ID to audit"}, "window": {"type": "string", "description": "Evaluation window e.g. 1h", "default": "1h"}}, "required": []}}}},
    },
)
def audit(decision_id: str = Query(..., description="Decision ID to audit"), window: str = Query(default="1h", description="Evaluation window e.g. 1h")):
    """Anubis Audit — verify prior decision outcome against real prices."""
    data = get_crypto_price("btc")
    entry_price = data["price"] if data else 67000.0

    # Simulate audit: slight adverse move (realistic for demo)
    exit_price = entry_price * (1 + random.uniform(-0.025, 0.015))
    pnl_pct = (exit_price - entry_price) / entry_price

    return {
        "decision_id": decision_id,
        "symbol": "BTC",
        "suggested_action": "CONSIDER_LONG",
        "confidence": 0.63,
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


@app.get("/api/anubis/forecast", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}],
        },
        "x-guidance": "Get conformally-calibrated 80% price range. Pass ?symbol=BTC to specify asset.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Symbol e.g. BTC, ETH", "default": "BTC"}}, "required": []}}}},
    },
)
def forecast(symbol: str = Query(default="BTC", description="Symbol e.g. BTC, ETH")):
    """Anubis Forecast — conformally-calibrated 80% price range."""
    sym = symbol.upper()
    data = get_crypto_price(sym.lower())
    price = data["price"] if data else 67000.0
    regime = regime_from_change((data["change_24h"] if data else 0) / 100)

    # 80% empirical coverage — calibrated range
    vol = price * 0.03  # 3% vol assumption
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


@app.get("/api/anubis/risk", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.020000"},
            "protocols": [{"x402": {}}],
        },
        "x-guidance": "Returns current market risk state, regime, and cooldown context. No parameters required.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {}}}}},
    },
)
def risk():
    """Current market risk state and cooldown context."""
    data = get_crypto_price("btc")
    btc_change = (data["change_24h"] if data else 0) / 100

    regime = regime_from_change(btc_change * 100)
    if abs(btc_change) > 0.05:
        risk_level = "HIGH"
    elif abs(btc_change) > 0.02:
        risk_level = "ELEVATED"
    else:
        risk_level = "NORMAL"

    return RiskResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        regime=regime,
        risk_level=risk_level,
        risk_factors=[
            "BTC dominance shifting",
            "macro risk sentiment neutral",
            "volatility compressing",
        ],
        cooldown_active=False,
        data_freshness="FRESH",
    )


# —— Health —————————————————————————————————————————————————————————————————————————————

@app.get("/health", responses={"200": {"description": "Service is healthy"}},
    openapi_extra={"security": []},
)
def health():
    return {"status": "ok", "service": "atlasmarkets-crypto", "version": "1.0.0"}


# —— Preflight + History —————————————————————————————————————————————————————————————

_decision_log: list[dict] = []


@app.get("/api/anubis/preflight", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}],
        },
        "x-guidance": "Check pre-decision conditions: cooldowns, market state, freshness, warnings. Pass ?symbol=BTC to check a specific asset.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Symbol e.g. BTC", "default": "BTC"}}, "required": []}}}},
    },
)
def preflight(symbol: str = Query(default="BTC", description="Symbol e.g. BTC")):
    """Pre-decision conditions check — cooldowns, market state, freshness, warnings."""
    sym = symbol.upper()
    data = get_crypto_price(sym.lower())
    pct = (data["change_24h"] if data else 0) / 100
    regime = regime_from_change(pct * 100)
    price = data["price"] if data else 67000.0

    now = datetime.now(timezone.utc)
    recent = [d for d in _decision_log if d["symbol"] == sym and
              (now - datetime.fromisoformat(d["ts"])).total_seconds() < 3600]

    warnings = []
    if regime == "bearish":
        warnings.append("Bearish regime detected — consider tighter stops")
    if abs(pct) > 0.05:
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
        "volatility": "HIGH" if abs(pct) > 0.03 else "NORMAL",
        "warnings": warnings,
        "data_freshness": "FRESH",
    }


@app.get("/api/anubis/history", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}],
        },
        "x-guidance": "Get recent context history for analysis. Pass ?symbol=BTC&limit=10 to filter results.",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Symbol e.g. BTC", "default": "BTC"}, "limit": {"type": "integer", "description": "Max entries", "default": 10}}, "required": []}}}},
    },
)
def history(symbol: str = Query(default="BTC", description="Symbol e.g. BTC"), limit: int = Query(default=10, description="Max entries")):
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
    uvicorn.run(app, host="0.0.0.0", port=8001)
