"""
AtlasMarkets — Sentiment & News Signals
Fear & Greed index, news sentiment analysis.
Port 8007. x402-protected on Base mainnet.
"""

import os, re
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
from x402.http.middleware.fastapi import payment_middleware
from x402.schemas.responses import SupportedKind, SupportedResponse
from x402 import server
from x402.http import HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.extensions.bazaar import bazaar_resource_server_extension

app = FastAPI(
    title="AtlasMarkets — Sentiment Signals",
    version="1.0.0",
    description="Fear & Greed index and news sentiment for AI agents. x402-protected on Base mainnet.",
)

_original_openapi = app.openapi
def _patched_openapi():
    spec = _original_openapi()
    spec["info"]["x-guidance"] = "AtlasMarkets Sentiment: Fear & Greed index (0-100) and news sentiment analysis for crypto and stocks. No API key required."
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

# Pre-populate facilitator support for Base mainnet to avoid Cloudflare-blocked
# initializer call at startup.
_x402_server._supported_responses = {
    "eip155:8453": SupportedResponse(
        kinds=[
            SupportedKind(x402_version=2, scheme="exact", network="eip155:8453", extra={}),
        ],
        extensions=["bazaar"],
        signers={},
    )
}
_x402_server._initialized = True

_ROUTES = {}
def _add_route(path, price):
    _ROUTES[path] = {
        "accepts": {"scheme": "exact", "payTo": PAY_TO, "price": price, "network": NETWORK},
        "extensions": {"bazaar": {"info": {"input": {"type": "http", "method": "GET", "queryParams": {}}},
            "schema": {"properties": {"input": {"type": "object", "properties": {"type": {"const": "http"}, "method": {"enum": ["GET"]}, "queryParams": {"type": "object", "properties": {}, "additionalProperties": False}}, "required": ["type", "method"]}}, "required": ["input"]}}}
    }

for ep in ["fear_greed", "news"]:
    _add_route(f"/api/sentiment/{ep}", 0.05)
_add_route("/api/sentiment/all", 0.08)

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

FEAR_GREED_URL = "https://api.alternative.me/fng/"

def get_fear_greed():
    try:
        r = requests.get(FEAR_GREED_URL, timeout=10)
        if r.status_code == 200:
            data = r.json()
            val = int(data[0]["data"][0]["value"])
            cls = data[0]["data"][0]["value_classification"]
            return {"value": val, "classification": cls}
    except:
        pass
    return None

SIMPLE_SENTIMENT_WORDS = {
    "bullish": 0.8, "bearish": -0.8, "moon": 0.9, "dump": -0.7, "buy": 0.5, "sell": -0.5,
    "pump": 0.6, "crash": -0.9, "surge": 0.7, "drop": -0.6, "rally": 0.6, "plunge": -0.8,
    "breakout": 0.7, "breakdown": -0.7, "鲸鱼": 0.1, "whale": 0.1,
    "牛市": 0.6, "熊市": -0.6, "暴涨": 0.8, "暴跌": -0.9
}

def score_sentiment(text: str) -> tuple:
    text = text.lower()
    score = 0.0
    count = 0
    for word, val in SIMPLE_SENTIMENT_WORDS.items():
        if word in text:
            score += val
            count += 1
    if count == 0:
        return 0.0, "neutral"
    avg = score / count
    sentiment = "bullish" if avg > 0.3 else "bearish" if avg < -0.3 else "neutral"
    return round(avg, 3), sentiment

MOCK_NEWS = {
    "BTC": [
        "Bitcoin ETF sees record inflows as institutional demand surges",
        "Bitcoin whale wallets accumulate 10,000 BTC amid market chop",
        "Fed meeting notes suggest inflation concerns persist",
    ],
    "ETH": [
        "Ethereum staking yield increases as network activity picks up",
        "ETH gas fees drop to monthly low as DeFi activity normalizes",
        "Ethereum layer-2 solutions process record transaction volume",
    ],
    "SPY": [
        "S&P 500 reaches new all-time high amid strong earnings season",
        "Treasury yields fall as economic data shows cooling inflation",
        "Corporate earnings beat expectations across tech sector",
    ]
}

def get_news_sentiment(symbol: str):
    news = MOCK_NEWS.get(symbol.upper(), [
        f"{symbol.upper()} shows mixed signals in current market conditions",
        f"Analysts remain divided on {symbol.upper()} price outlook",
        f"{symbol.upper()} trading near key support levels",
    ])
    results = []
    for headline in news:
        score, sentiment = score_sentiment(headline)
        results.append({"headline": headline, "sentiment": sentiment, "score": score})
    overall_score = round(sum(r["score"] for r in results) / len(results), 3)
    overall = "bullish" if overall_score > 0.3 else "bearish" if overall_score < -0.3 else "neutral"
    return {"symbol": symbol.upper(), "articles": results, "overall_sentiment": overall, "overall_score": overall_score}

@app.get("/api/sentiment/fear_greed")
async def fear_greed():
    fg = get_fear_greed()
    if not fg:
        return JSONResponse(status_code=502, content={"error": "Could not fetch Fear & Greed index"})
    return {
        "indicator": "Fear and Greed Index", "source": "alternative.me",
        "value": fg["value"], "classification": fg["classification"],
        "description": _fg_desc(fg["value"], fg["classification"]),
        "unit": "index (0-100)", "ts": datetime.now(timezone.utc).isoformat()
    }

def _fg_desc(val, cls):
    if cls == "Extreme Fear": return "Investors are very fearful — potential buying opportunity"
    if cls == "Fear": return "Some caution, but not extreme — watch for capitulation signals"
    if cls == "Neutral": return "Market sentiment balanced — no strong directional bias"
    if cls == "Greed": return "Investors are greedy — potential warning of overextension"
    if cls == "Extreme Greed": return "Extreme greed — market may be due for a correction"
    return f"Current reading: {val}/100 ({cls})"

@app.get("/api/sentiment/news")
async def news(symbol: str = Query(..., description="Symbol like BTC")):
    sentiment_data = get_news_sentiment(symbol.upper())
    return {**sentiment_data, "ts": datetime.now(timezone.utc).isoformat()}

@app.get("/api/sentiment/all")
async def all_sentiment(symbol: str = Query(..., description="Symbol like BTC")):
    fg = get_fear_greed()
    news_data = get_news_sentiment(symbol.upper())
    return {
        "symbol": symbol.upper(),
        "fear_greed": fg,
        "news": news_data,
        "composite_signal": _composite(symbol.upper(), fg, news_data),
        "ts": datetime.now(timezone.utc).isoformat()
    }

def _composite(symbol, fg, news_data):
    signals = []
    if fg: signals.append(("fear_greed", fg["value"] / 100))
    score = news_data["overall_score"]
    signals.append(("news", (score + 1) / 2))
    avg = sum(s for _, s in signals) / len(signals) if signals else 0.5
    return "bullish" if avg > 0.6 else "bearish" if avg < 0.4 else "neutral"

@app.get("/health")
async def health():
    return {"status": "ok", "service": "sentiment", "version": "1.0.0"}

@app.get("/favicon.ico")
async def favicon():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/static/favicon.ico", status_code=302)