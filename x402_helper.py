"""
AtlasMarkets x402 Integration
Wires payment middleware into all 5 god APIs via the official x402 Python SDK.
"""

from x402 import server
from x402.http import HTTPFacilitatorClient
from x402.mechanisms.evm.exact import ExactEvmServerScheme

# Wallet receiving USDC payments (Base mainnet)
PAY_TO = "0x8eB96caA976De43027FEf619c4D24F6679486277"
FACILITATOR_URL = "https://api.cdp.coinbase.com/platform/v2/x402"
NETWORK = "eip155:8453"  # Base mainnet

# ── Server bootstrap ──────────────────────────────────────────────────────────
_facilitator = HTTPFacilitatorClient({"url": FACILITATOR_URL})
_server = server.x402ResourceServer(_facilitator)
_server.register(NETWORK, ExactEvmServerScheme())

# ── Route definitions per god ──────────────────────────────────────────────────
# Pattern: "METHOD /relative/path"  (glob wildcards supported)

ENDPOINTS = {
    "signals":  {"price": "$0.05", "method": "GET"},
    "decision": {"price": "$0.15", "method": "POST"},
    "audit":    {"price": "$0.07", "method": "GET"},
    "forecast": {"price": "$0.05", "method": "GET"},
    "risk":     {"price": "$0.02", "method": "GET"},
    "preflight":{"price": "$0.05", "method": "GET"},
    "history":  {"price": "$0.05", "method": "GET"},
}


def make_routes(api_prefix: str) -> dict:
    """Build routes config dict for one god API."""
    routes = {}
    for ep, meta in ENDPOINTS.items():
        route_key = f"{meta['method']} /api/{api_prefix}/{ep}"
        routes[route_key] = {
            "accepts": {
                "scheme": "exact",
                "payTo": PAY_TO,
                "price": meta["price"],
                "network": NETWORK,
            },
            "description": f"AtlasMarkets {api_prefix} {ep} endpoint",
            "mimeType": "application/json",
        }
    return routes


# ── Per-god server + routes (used by each FastAPI app) ───────────────────────

def make_server_and_routes(god: str):
    """Returns (routes_dict, x402_server) for one god."""
    routes = make_routes(god)
    return routes, _server