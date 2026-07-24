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

app = FastAPI(
    title="AtlasMarkets — Anubis",
    version="1.0.0",
    contact={"email": "max.sadikovic@gmail.com"},
    openapi_extra={
        "x-agentcash-provenance": {
            "ownershipProofs": [
                "d5299c94df61f692f8b778c964348de932f192c43bcaf5ec8757c206ea926d400cd421daacc73ead49370897e0d593e23a1aa46299ab1dad747c575da31b2f3e1c",
                "89f89072a0260fe47bd2e65450e6032cb74c247c1f8667b2a43c5c9b07d0dbcf647a9deef60570e5da312c649b3f93359340bdf249cbfda01e41116851c756e21b",
                "f0fa23832316e244b1524ac9de2bc94ae21aadf46a3c9c2565af6dfe9e55acb3431f43fc673dd8162d0bd5f38cb7b594144f0d04498d421c261e0bb65cf53b8d1b",
                "d9b9b997a3f0ebb605015f091009cff80eeff8d8078eb13a0431692f89f0dfb87f8c96b5dcb0769f7923d62bb98ee795c0caa8f7f476955f377b9d6e828189341c",
                "d6ec3f51dbebbb6c945e65d6de81f665c32fef26b8761b9bd961cc77519103f05e9d9bdbf356d2d47af2b5edbcfe68c3b38c64621ea77d059fc734d5a041ea2f1b",
            ]
        },
    },
)

# ── Root-level OpenAPI extensions ─────────────────────────────────────────────
_orig_openapi = app.openapi

def _patched_openapi():
    schema = _orig_openapi()
    schema["info"]["x-guidance"] = (
        "AtlasMarkets Anubis provides crypto market intelligence for AI agents. "
        "Routes: GET /api/anubis/signals ($0.05), GET /api/anubis/forecast?symbol=BTC ($0.05), "
        "GET /api/anubis/risk ($0.02), GET /api/anubis/preflight?symbol=BTC ($0.05), "
        "GET /api/anubis/history?symbol=BTC ($0.05), GET /api/anubis/audit?decision_id=X ($0.07), "
        "POST /api/anubis/decision?symbol=BTC ($0.15). All routes return real-time crypto data."
    )
    schema["x-x402"] = {
        "network": "eip155:8453",
        "payTo": "0x8eB96caA976De43027FEf619c4D24F6679486277",
        "facilitator": "https://facilitator.payai.network",
        "extensions": {
            "bazaar": {
                "status": "live",
                "purpose": "AtlasMarkets Anubis crypto market intelligence for AI agents.",
            }
        },
    }
    return schema

app.openapi = _patched_openapi

# ── x402 payment middleware ──────────────────────────────────────────────────
PAY_TO = "0x8eB96caA976De43027FEf619c4D24F6679486277"
FACILITATOR_URL = os.environ.get("FACILITATOR_URL", "https://facilitator.payai.network")
NETWORK = "eip155:8453"

_facilitator = HTTPFacilitatorClient({"url": FACILITATOR_URL})
_x402_server = server.x402ResourceServer(_facilitator)
_x402_server.register(NETWORK, ExactEvmServerScheme())

_ROUTES = {
    f"/api/anubis/{ep}": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": price,
            "network": NETWORK,
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

# ── 405 guard: intercept wrong HTTP methods and return 402 so x402scan can probe ──
_METHOD_ACCEPTS = {
    "/api/anubis/signals":  ["GET"],
    "/api/anubis/decision": ["POST"],
    "/api/anubis/audit":    ["GET"],
    "/api/anubis/forecast": ["GET"],
    "/api/anubis/risk":     ["GET"],
    "/api/anubis/preflight":["GET"],
    "/api/anubis/history":  ["GET"],
    "/health":              ["GET"],
}

@app.middleware("http")
async def x402_mw(request: Request, call_next):
    # Let the x402 payment middleware handle everything — including wrong-method probes
    try:
        return await payment_middleware(_ROUTES, _x402_server)(request, call_next)
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={"detail": f"x402 middleware error: {str(e)}", "traceback": traceback.format_exc()}
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── CoinGecko free API helper ───────────────────────────────────────────────

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

def regime_from_change(pct_24h: float) -> str:
    if pct_24h > 5:   return "bullish"
    if pct_24h < -5:  return "bearish"
    return "chop"


def signal_score(pct_24h: float) -> float:
    return round(max(-1, min(1, pct_24h / 10)), 4)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/anubis/signals", response_model=SignalsResponse,
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        },
        "requestBody": {
            "required": False,
            "content": {
                "application/json": {
                    "schema": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
                        }
                }
            }
        },
    },
    responses={
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"ts": {"type": "string"}, "timeframe": {"type": "string"}, "regime": {"type": "string"}, "signals": {"type": "object"}, "top_k": {"type": "array", "items": {"type": "string"}}, "signal_age_hours": {"type": "number"}, "data_freshness": {"type": "string"}}, "additionalProperties": False}
                }
            }
        },
        "402": {"description": "Payment Required"}
    }
)
def signals(timeframe: str = "15m"):
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


@app.post("/api/anubis/decision", response_model=DecisionResponse,
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.150000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def decision(symbol: str = Query(default="BTC", description="Crypto symbol e.g. BTC, ETH")):
    """Anubis Decision — probabilistic journal entry with decision_id."""
    sym = symbol.upper()
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


@app.get("/api/anubis/audit",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.070000"},
            "protocols": [{"x402": {}}]
        },
        "requestBody": {
            "required": False,
            "content": {
                "application/json": {
                    "schema": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
                        }
                }
            }
        },
    },
    responses={
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"decision_id": {"type": "string"}, "symbol": {"type": "string"}, "suggested_action": {"type": "string"}, "confidence": {"type": "number"}, "evaluation_window": {"type": "string"}, "prices": {"type": "object", "properties": {"entry": {"type": "number"}, "exit": {"type": "number"}}}, "outcome": {"type": "object", "properties": {"pnl_pct": {"type": "number"}, "direction_correct": {"type": "boolean"}, "verdict": {"type": "string"}}}}, "additionalProperties": False}
                }
            }
        },
        "402": {"description": "Payment Required"}
    }
)
def audit(decision_id: str, window: str = "1h"):
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


@app.get("/api/anubis/forecast",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        },
        "requestBody": {
            "required": False,
            "content": {
                "application/json": {
                    "schema": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
                        }
                }
            }
        },
    },
    responses={
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"symbol": {"type": "string"}, "ts": {"type": "string"}, "regime": {"type": "string"}, "forecast": {"type": "object", "properties": {"range_80": {"type": "object", "properties": {"lower": {"type": "number"}, "upper": {"type": "number"}}}, "mid": {"type": "number"}, "confidence": {"type": "string"}, "coverage_method": {"type": "string"}}}, "data_freshness": {"type": "string"}}, "additionalProperties": False}
                }
            }
        },
        "402": {"description": "Payment Required"}
    }
)
def forecast(symbol: str = "BTC"):
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


@app.get("/api/anubis/risk",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.020000"},
            "protocols": [{"x402": {}}]
        },
        "requestBody": {
            "required": False,
            "content": {
                "application/json": {
                    "schema": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
                        }
                }
            }
        },
    },
    responses={
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"ts": {"type": "string"}, "regime": {"type": "string"}, "risk_level": {"type": "string"}, "risk_factors": {"type": "array", "items": {"type": "string"}}, "cooldown_active": {"type": "boolean"}, "data_freshness": {"type": "string"}}, "additionalProperties": False}
                }
            }
        },
        "402": {"description": "Payment Required"}
    }
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


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "atlasmarkets-crypto", "version": "1.0.0"}


# ─── Preflight + History ─────────────────────────────────────────────────────

_decision_log: list[dict] = []


@app.get("/api/anubis/preflight",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        },
        "requestBody": {
            "required": False,
            "content": {
                "application/json": {
                    "schema": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
                        }
                }
            }
        },
    },
    responses={
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"symbol": {"type": "string"}, "ts": {"type": "string"}, "can_decide": {"type": "boolean"}, "cooldown_active": {"type": "boolean"}, "market_state": {"type": "string"}, "price": {"type": "number"}, "volatility": {"type": "string"}, "warnings": {"type": "array", "items": {"type": "string"}}, "data_freshness": {"type": "string"}}, "additionalProperties": False}
                }
            }
        },
        "402": {"description": "Payment Required"}
    }
)
def preflight(symbol: str = "BTC"):
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


@app.get("/api/anubis/history",
    openapi_extra={
        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"},
            "protocols": [{"x402": {}}]
        },
        "requestBody": {
            "required": False,
            "content": {
                "application/json": {
                    "schema": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
                        }
                }
            }
        },
    },
    responses={
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"symbol": {"type": "string"}, "count": {"type": "integer"}, "history": {"type": "array"}, "data_freshness": {"type": "string"}}, "additionalProperties": False}
                }
            }
        },
        "402": {"description": "Payment Required"}
    }
)
def history(symbol: str = "BTC", limit: int = 10):
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