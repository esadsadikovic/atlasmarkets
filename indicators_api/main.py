"""
AtlasMarkets — Technical Indicators API
RSI, MACD, Bollinger Bands, EMA for crypto and stocks.
Port 8006. x402-protected on Base mainnet.
"""

import os, math
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests

from x402.http.middleware.fastapi import payment_middleware
from x402 import server
from x402.http import HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.extensions.bazaar import bazaar_resource_server_extension

app = FastAPI(
    title="AtlasMarkets — Technical Indicators",
    version="1.0.0",
    description="Technical indicators for AI agents. RSI, MACD, Bollinger Bands, EMA. x402-protected on Base mainnet.",
)

_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Technical Indicators: RSI, MACD, Bollinger Bands, EMA. Use ?symbol=BTC&interval=1h. Returns computed values for AI agent decision making."
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
                                "queryParams": {"type": "object", "properties": {}, "additionalProperties": False}
                            },
                            "required": ["type", "method"]
                        }
                    },
                    "required": ["input"]
                }
            }
        }
    }

for ep in ["rsi", "macd", "bollinger", "ema"]:
    _add_route(f"/api/indicators/{ep}", 0.05)
_add_route("/api/indicators/all", 0.10)

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

COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin",
    "DOT": "polkadot", "AVAX": "avalanche-2", "LINK": "chainlink",
    "MATIC": "matic-network"
}

def get_ohlcv(symbol: str, days: int = 30):
    coin = COINGECKO_IDS.get(symbol.upper(), symbol.lower())
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/ohlc"
    try:
        r = requests.get(url, params={"vs_currency": "usd", "days": days}, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def compute_rsi(closes, period=14):
    if len(closes) < period + 2:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    if len(deltas) < period:
        return None
    avg_gain = sum(max(d, 0) for d in deltas[:period]) / period
    avg_loss = sum(max(-d, 0) for d in deltas[:period]) / period
    for d in deltas[period:]:
        avg_gain = (avg_gain * (period - 1) + max(d, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0)) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def _ema(closes, period):
    if len(closes) < period:
        return closes[-1] if closes else 0
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return ema

def compute_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + 1:
        return None
    ef = _ema(closes, fast)
    es = _ema(closes, slow)
    macd = ef - es
    signal_line = _ema([ef - es] * max(signal, 1), signal) if len(closes) >= slow + signal else macd
    return {"macd": round(macd, 4), "signal": round(signal_line, 4), "histogram": round(macd - signal_line, 4)}

def compute_bollinger(closes, period=20, std_mult=2):
    if len(closes) < period:
        return None
    window = closes[-period:]
    sma = sum(window) / period
    variance = sum((x - sma) ** 2 for x in window) / period
    std = math.sqrt(variance)
    return {
        "upper": round(sma + std_mult * std, 4),
        "middle": round(sma, 4),
        "lower": round(sma - std_mult * std, 4),
        "bandwidth": round(std_mult * std * 2 / sma * 100, 4)
    }

def compute_ema_values(closes, periods=[5, 10, 20, 50, 200]):
    return {f"ema_{p}": round(_ema(closes, p), 4) for p in periods if len(closes) >= p}

@app.get("/api/indicators/rsi")
async def rsi(symbol: str = Query(..., description="Symbol like BTC"), interval: str = Query("1d")):
    ohlcv = get_ohlcv(symbol, days=60 if interval == "1d" else 30)
    if not ohlcv:
        return JSONResponse(status_code=502, content={"error": "Could not fetch data from CoinGecko"})
    closes = [d[4] for d in ohlcv]
    rsi_val = compute_rsi(closes)
    interpretation = "oversold" if rsi_val and rsi_val < 30 else "overbought" if rsi_val and rsi_val > 70 else "neutral"
    return {
        "symbol": symbol.upper(), "indicator": "RSI", "period": 14, "value": rsi_val,
        "interpretation": interpretation, "unit": "index (0-100)",
        "data_source": "CoinGecko", "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/indicators/macd")
async def macd(symbol: str = Query(..., description="Symbol like BTC"), interval: str = Query("1d")):
    ohlcv = get_ohlcv(symbol, days=60 if interval == "1d" else 30)
    if not ohlcv:
        return JSONResponse(status_code=502, content={"error": "Could not fetch data from CoinGecko"})
    closes = [d[4] for d in ohlcv]
    m = compute_macd(closes)
    return {
        "symbol": symbol.upper(), "indicator": "MACD",
        "macd": m["macd"], "signal": m["signal"], "histogram": m["histogram"],
        "interpretation": "bullish" if m["histogram"] > 0 else "bearish",
        "fast": 12, "slow": 26, "signal": 9,
        "data_source": "CoinGecko",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/indicators/bollinger")
async def bollinger(symbol: str = Query(..., description="Symbol like BTC"), interval: str = Query("1d")):
    ohlcv = get_ohlcv(symbol, days=60 if interval == "1d" else 30)
    if not ohlcv:
        return JSONResponse(status_code=502, content={"error": "Could not fetch data from CoinGecko"})
    closes = [d[4] for d in ohlcv]
    bb = compute_bollinger(closes)
    current_price = closes[-1]
    if bb:
        pos = round((current_price - bb["lower"]) / (bb["upper"] - bb["lower"]) * 100, 1)
    else:
        pos = None
    return {
        "symbol": symbol.upper(), "indicator": "Bollinger Bands", "period": 20, "std_mult": 2,
        "upper": bb["upper"], "middle": bb["middle"], "lower": bb["lower"],
        "bandwidth": bb["bandwidth"], "current_price": current_price,
        "position_in_band": pos,
        "interpretation": "near_upper_band" if pos and pos > 80 else "near_lower_band" if pos and pos < 20 else "mid_band",
        "unit": "usd", "data_source": "CoinGecko",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/indicators/ema")
async def ema(symbol: str = Query(..., description="Symbol like BTC"), interval: str = Query("1d")):
    ohlcv = get_ohlcv(symbol, days=365 if interval == "1d" else 60)
    if not ohlcv:
        return JSONResponse(status_code=502, content={"error": "Could not fetch data from CoinGecko"})
    closes = [d[4] for d in ohlcv]
    ema_v = compute_ema_values(closes)
    current_price = closes[-1]
    return {
        "symbol": symbol.upper(), "indicator": "EMA",
        "values": ema_v, "current_price": current_price,
        "data_source": "CoinGecko",
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/indicators/all")
async def all_indicators(symbol: str = Query(..., description="Symbol like BTC"), interval: str = Query("1d")):
    ohlcv = get_ohlcv(symbol, days=365 if interval == "1d" else 60)
    if not ohlcv:
        return JSONResponse(status_code=502, content={"error": "Could not fetch data from CoinGecko"})
    closes = [d[4] for d in ohlcv]
    current = closes[-1]
    rsi_v = compute_rsi(closes)
    macd_v = compute_macd(closes)
    bb = compute_bollinger(closes)
    ema_v = compute_ema_values(closes)
    return {
        "symbol": symbol.upper(), "interval": interval, "current_price": current,
        "rsi": {"value": rsi_v, "interpretation": "oversold" if rsi_v and rsi_v < 30 else "overbought" if rsi_v and rsi_v > 70 else "neutral"},
        "macd": macd_v,
        "bollinger": bb,
        "ema": ema_v,
        "ts": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "indicators", "version": "1.0.0"}

@app.get("/favicon.ico")
async def favicon():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/static/favicon.ico", status_code=302)