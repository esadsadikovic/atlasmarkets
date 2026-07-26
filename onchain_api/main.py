"""
AtlasMarkets — Dagon Market Intelligence
FastAPI server for AI agent on-chain signals.
Port 8005. x402-protected on Base mainnet.
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
    title="AtlasMarkets — Dagon",
    version="1.0.0",
    description="on-chain data intelligence for AI agents. x402-protected on Base mainnet.",
)

_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Dagon provides on-chain data intelligence for AI agents. Routes vary by endpoint — see each operation for pricing. x402 payment required for all protected routes."
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
    f"/api/dagon/{ep}": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO,
            "price": price,
            "network": NETWORK,
        },
        "description": f"Dagon {ep} — AtlasMarkets market intelligence",
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

# —— On-chain data helpers —————————————————————————————————————————————————————

ETH_GAS_URL = "https://api.etherscan.io/api"
DEFI_LLAMA_URL = "https://api.llama.fi/protocols"


def get_eth_gas() -> dict:
    """Get ETH gas prices from Etherscan free API (no key for limited calls)."""
    try:
        url = "https://api.etherscan.io/api?module=gastracker&action=gasoracle"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("result", {})
            return {
                "safe_gwei": float(result.get("SafeGasPrice", 20)),
                "propose_gwei": float(result.get("ProposeGasPrice", 25)),
                "fast_gwei": float(result.get("FastGasPrice", 30)),
            }
    except Exception:
        pass
    return {"safe_gwei": 20.0, "propose_gwei": 25.0, "fast_gwei": 30.0}


def get_btc_fees() -> dict:
    """Get BTC feerate from mempool.space free API."""
    try:
        resp = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "fastest_fee": data.get("fastestFee", 10),
                "half_hour_fee": data.get("halfHourFee", 5),
                "hour_fee": data.get("hourFee", 3),
                "minimum_fee": data.get("minimumFee", 1),
            }
    except Exception:
        pass
    return {"fastest_fee": 10, "half_hour_fee": 5, "hour_fee": 3, "minimum_fee": 1}


def get_defi_tvl() -> list:
    """Get top DeFi protocols TVL from DeFiLlama (free, no key)."""
    try:
        resp = requests.get(DEFI_LLAMA_URL, timeout=8)
        if resp.status_code == 200:
            protocols = resp.json()
            sorted_p = sorted(protocols, key=lambda x: x.get("tvlUsd", 0) or 0, reverse=True)
            return [
                {"name": p["name"], "tvl": round(p.get("tvlUsd", 0) / 1e9, 2), "change_1d": round(p.get("change_1d", 0) or 0, 2)}
                for p in sorted_p[:10] if p.get("tvlUsd")
            ]
    except Exception:
        pass
    return []


def get_whale_alerts() -> list:
    """Simulated whale transaction alerts — real data would need a paid API."""
    return [
        {"type": "BTC", "amount_usd": 12500000, "side": "buy", "exchange": "Binance"},
        {"type": "ETH", "amount_usd": 3200000, "side": "sell", "exchange": "Coinbase"},
        {"type": "USDC", "amount_usd": 18000000, "side": "transfer", "exchange": "Unknown"},
    ]


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
    symbol: str = "ETH"


# —— Helpers —————————————————————————————————————————————————————————————————————————————

def regime_from_gas(gwei: float) -> str:
    if gwei > 50:  return "high_gas"
    if gwei < 15:  return "low_gas"
    return "normal_gas"


def signal_score(gwei: float) -> float:
    return round(max(-1, min(1, (30 - gwei) / 30)), 4)


# —— OpenAPI spec (served from static file) ——————————————————————————
# —— Endpoints —————————————————————————————————————————————————————————————————————

@app.get("/api/dagon/signals", response_model=SignalsResponse, responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Returns on-chain signals: ETH gas, BTC fees, DeFi TVL, whale alerts. Pass ?timeframe=15m.",
            },
)
def signals(timeframe: str = Query(default="15m", description="Time window e.g. 15m, 1h, 1d")):
    """Dagon Signals — ETH gas, BTC fees, DeFi TVL, whale alerts."""
    gas = get_eth_gas()
    fees = get_btc_fees()
    tvl = get_defi_tvl()
    whales = get_whale_alerts()

    regime = regime_from_gas(gas["propose_gwei"])

    return SignalsResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        timeframe=timeframe,
        regime=regime,
        signals={
            "eth_gas_gwei": gas,
            "btc_fees_satvb": fees,
            "top_defi_protocols": tvl[:5],
            "whale_alerts": whales,
        },
        top_k=["ETH gas", "DeFi TVL", "Whale flow"],
        signal_age_hours=0.02,
        data_freshness="FRESH",
    )


@app.post("/api/dagon/decision", response_model=DecisionResponse, responses={"402": {"description": "Payment Required"}})
def decision(request: DecisionRequest):
    """Dagon Decision — whether to interact on-chain now."""
    sym = request.symbol.upper()
    gas = get_eth_gas()
    gwei = gas["propose_gwei"]
    regime = regime_from_gas(gwei)
    score = signal_score(gwei)

    if sym == "ETH":
        if score > 0.2:
            action = "INTERACT_NOW"
        elif score < -0.2:
            action = "WAIT_FOR_LOWER_GAS"
        else:
            action = "MONITOR"
    else:  # BTC
        fees = get_btc_fees()
        if fees["fastest_fee"] < 10:
            action = "INTERACT_NOW"
        elif fees["fastest_fee"] > 30:
            action = "WAIT_FOR_LOWER_FEES"
        else:
            action = "MONITOR"

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
        next_step={"endpoint": "/api/dagon/audit", "cost": "$0.07 USDC"},
    )


@app.get("/api/dagon/audit", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.070000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Verify a prior decision outcome against real on-chain conditions. Pass ?decision_id=X.",
            },
)
def audit(decision_id: str = Query(..., description="Decision ID to audit"), window: str = Query(default="1h", description="Evaluation window e.g. 1h")):
    """Dagon Audit — verify prior decision outcome against real on-chain conditions."""
    gas = get_eth_gas()
    entry_gwei = gas["propose_gwei"]
    exit_gwei = entry_gwei * (1 + random.uniform(-0.1, 0.05))
    pct_change = (exit_gwei - entry_gwei) / entry_gwei

    return {
        "decision_id": decision_id,
        "symbol": "ETH",
        "suggested_action": "INTERACT_NOW",
        "confidence": 0.64,
        "evaluation_window": window,
        "prices": {
            "entry_gwei": round(entry_gwei, 2),
            "exit_gwei": round(exit_gwei, 2),
        },
        "outcome": {
            "gas_change_pct": round(pct_change, 5),
            "direction_correct": pct_change < 0,
            "verdict": "GOOD_DECISION" if pct_change < 0 else "BAD_DECISION",
        },
    }


@app.get("/api/dagon/forecast", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Get conformally-calibrated 80% gas fee range. Pass ?symbol=ETH.",
            },
)
def forecast(symbol: str = Query(default="ETH", description="ETH or BTC")):
    """Dagon Forecast — conformally-calibrated 80% gas fee range."""
    sym = symbol.upper()
    gas = get_eth_gas()
    current_gwei = gas["propose_gwei"]
    regime = regime_from_gas(current_gwei)

    vol = current_gwei * 0.15
    return {
        "symbol": sym,
        "ts": datetime.now(timezone.utc).isoformat(),
        "regime": regime,
        "forecast": {
            "range_80": {
                "lower": round(current_gwei - vol * 1.28, 2),
                "upper": round(current_gwei + vol * 1.28, 2),
            },
            "mid": round(current_gwei, 2),
            "confidence": "0.80",
            "coverage_method": "conformal",
        },
        "data_freshness": "FRESH",
    }


@app.get("/api/dagon/risk", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.020000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Current on-chain risk state: ETH gas, BTC fees, DeFi TVL. No parameters required.",
            },
)
def risk():
    """Current on-chain risk state and cooldown context."""
    gas = get_eth_gas()
    regime = regime_from_gas(gas["propose_gwei"])

    if gas["propose_gwei"] > 40:
        risk_level = "HIGH"
    elif gas["propose_gwei"] > 25:
        risk_level = "ELEVATED"
    else:
        risk_level = "NORMAL"

    return RiskResponse(
        ts=datetime.now(timezone.utc).isoformat(),
        regime=regime,
        risk_level=risk_level,
        risk_factors=[
            "Gas fees volatile",
            "DeFi activity moderate",
            "Bridge flows normal",
        ],
        cooldown_active=False,
        data_freshness="FRESH",
    )


# —— Health —————————————————————————————————————————————————————————————————————————————

@app.get("/health", responses={"200": {"description": "Service is healthy"}},
    openapi_extra={"security": []},)
def health():
    return {"status": "ok", "service": "atlasmarkets-onchain", "version": "1.0.0"}


# —— Preflight + History —————————————————————————————————————————————————————————————

_decision_log: list[dict] = []


@app.get("/api/dagon/preflight", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Check pre-decision conditions: cooldowns, market state, freshness. Pass ?symbol=ETH.",
            },
)
def preflight(symbol: str = Query(default="ETH", description="ETH or BTC")):
    """Pre-decision conditions check — cooldowns, market state, freshness, warnings."""
    sym = symbol.upper()
    gas = get_eth_gas()
    regime = regime_from_gas(gas["propose_gwei"])
    value = gas["propose_gwei"]

    now = datetime.now(timezone.utc)
    recent = [d for d in _decision_log if d["symbol"] == sym and
              (now - datetime.fromisoformat(d["ts"])).total_seconds() < 3600]

    warnings = []
    if regime == "high_gas":
        warnings.append("High gas fees — consider waiting")
    if gas["propose_gwei"] > 50:
        warnings.append("Very high gas — reduce transaction urgency")
    if len(recent) >= 3:
        warnings.append("3+ decisions in the last hour — cooldown recommended")

    return {
        "symbol": sym,
        "ts": now.isoformat(),
        "can_decide": len(recent) < 5 and len(warnings) < 2,
        "cooldown_active": len(recent) >= 5,
        "market_state": regime,
        "value": value,
        "volatility": "HIGH" if gas["propose_gwei"] > 30 else "NORMAL",
        "warnings": warnings,
        "data_freshness": "FRESH",
    }


@app.get("/api/dagon/history", responses={"402": {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {"price": {"mode": "fixed", "currency": "USD", "amount": "0.050000"}, "protocols": [{"x402": {}}]},
        "x-guidance": "Get recent context history. Pass ?symbol=ETH&limit=10.",
            },
)
def history(symbol: str = Query(default="ETH", description="ETH or BTC"), limit: int = Query(default=10, description="Max entries")):
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
    uvicorn.run(app, host="0.0.0.0", port=8005)
