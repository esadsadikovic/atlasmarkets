#!/usr/bin/env node

/**
 * AtlasMarkets MCP Server
 * Wraps all 5 AtlasMarkets APIs (Anubis, Viking, Apollo, Pollux, Dagon)
 * for AI agents via the Model Context Protocol (MCP).
 *
 * Usage: npx atlasmarkets-mcp
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const ATLASMARKETS_URL = process.env.ATLASMARKETS_URL || "http://localhost";

// ─────────────────────────────────────────────────────────────────────────────
// Tool Definitions — 35 tools across 5 APIs
// ─────────────────────────────────────────────────────────────────────────────

const TOOLS = [
  // ── Anubis — Crypto ────────────────────────────────────────────────────────
  { name: "anubis_signals",   description: "Anubis crypto signals — BTC ETH SOL XRP ADA. Returns regime, scores, freshness. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Crypto symbol e.g. BTC" } }, required: [] } },
  { name: "anubis_preflight",  description: "Anubis pre-decision check — cooldowns, warnings, volatility. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Crypto symbol e.g. BTC" } }, required: [] } },
  { name: "anubis_history",    description: "Anubis recent decision history. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Crypto symbol e.g. BTC" } }, required: [] } },
  { name: "anubis_decision",   description: "Anubis BUY/SELL/HOLD decision with confidence and decision_id. $0.15", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Crypto symbol e.g. BTC" } }, required: ["symbol"] } },
  { name: "anubis_audit",      description: "Anubis audit — verify prior decision against real prices. $0.07", inputSchema: { type: "object", properties: { decision_id: { type: "string", description: "UUID from a prior decision call" }, window: { type: "string", description: "Evaluation window e.g. 1h, 4h, 1d" } }, required: ["decision_id"] } },
  { name: "anubis_forecast",   description: "Anubis 80% calibrated price range forecast. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Crypto symbol e.g. BTC" } }, required: [] } },
  { name: "anubis_risk",       description: "Anubis current market risk state. $0.02", inputSchema: { type: "object", properties: {}, required: [] } },

  // ── Viking — Stocks ────────────────────────────────────────────────────────
  { name: "viking_signals",   description: "Viking stock signals — SPY QQQ AAPL MSFT NVDA. Returns regime, scores, freshness. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Stock ticker e.g. SPY" } }, required: [] } },
  { name: "viking_preflight",  description: "Viking pre-decision check. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Stock ticker e.g. SPY" } }, required: [] } },
  { name: "viking_history",    description: "Viking recent decision history. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Stock ticker e.g. SPY" } }, required: [] } },
  { name: "viking_decision",  description: "Viking BUY/SELL/HOLD decision with confidence. $0.15", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Stock ticker e.g. SPY" } }, required: ["symbol"] } },
  { name: "viking_audit",     description: "Viking audit — verify prior decision against real prices. $0.07", inputSchema: { type: "object", properties: { decision_id: { type: "string", description: "UUID from prior decision" }, window: { type: "string", description: "Evaluation window" } }, required: ["decision_id"] } },
  { name: "viking_forecast",  description: "Viking 80% calibrated price range. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Stock ticker e.g. SPY" } }, required: [] } },
  { name: "viking_risk",      description: "Viking current market risk state. $0.02", inputSchema: { type: "object", properties: {}, required: [] } },

  // ── Apollo — Forex ────────────────────────────────────────────────────────
  { name: "apollo_signals",   description: "Apollo forex signals — EURUSD GBPUSD USDJPY. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Forex pair e.g. EURUSD" } }, required: [] } },
  { name: "apollo_preflight", description: "Apollo pre-decision check. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Forex pair e.g. EURUSD" } }, required: [] } },
  { name: "apollo_history",   description: "Apollo recent decision history. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Forex pair e.g. EURUSD" } }, required: [] } },
  { name: "apollo_decision",  description: "Apollo BUY/SELL/HOLD decision for forex. $0.15", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Forex pair e.g. EURUSD" } }, required: ["symbol"] } },
  { name: "apollo_audit",    description: "Apollo audit — verify prior forex decision. $0.07", inputSchema: { type: "object", properties: { decision_id: { type: "string" }, window: { type: "string" } }, required: ["decision_id"] } },
  { name: "apollo_forecast", description: "Apollo 80% calibrated exchange rate range. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Forex pair e.g. EURUSD" } }, required: [] } },
  { name: "apollo_risk",      description: "Apollo current forex market risk state. $0.02", inputSchema: { type: "object", properties: {}, required: [] } },

  // ── Pollux — Commodities ──────────────────────────────────────────────────
  { name: "pollux_signals",   description: "Pollux commodity signals — Gold Silver Oil Gas. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Commodity name e.g. Gold (XAU/USD)" } }, required: [] } },
  { name: "pollux_preflight", description: "Pollux pre-decision check. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Commodity name" } }, required: [] } },
  { name: "pollux_history",   description: "Pollux recent decision history. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Commodity name" } }, required: [] } },
  { name: "pollux_decision",  description: "Pollux BUY/SELL/HOLD decision for commodities. $0.15", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Commodity name" } }, required: ["symbol"] } },
  { name: "pollux_audit",    description: "Pollux audit — verify prior commodity decision. $0.07", inputSchema: { type: "object", properties: { decision_id: { type: "string" }, window: { type: "string" } }, required: ["decision_id"] } },
  { name: "pollux_forecast", description: "Pollux 80% calibrated commodity price range. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "Commodity name" } }, required: [] } },
  { name: "pollux_risk",      description: "Pollux current commodity market risk state. $0.02", inputSchema: { type: "object", properties: {}, required: [] } },

  // ── Dagon — On-Chain ──────────────────────────────────────────────────────
  { name: "dagon_signals",   description: "Dagon on-chain signals — ETH gas BTC fees DeFi TVL whale alerts. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "ETH or BTC" } }, required: [] } },
  { name: "dagon_preflight", description: "Dagon pre-decision check — gas state, cooldowns, warnings. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "ETH or BTC" } }, required: [] } },
  { name: "dagon_history",   description: "Dagon recent on-chain decision history. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "ETH or BTC" } }, required: [] } },
  { name: "dagon_decision",  description: "Dagon decision — GOOD_TIME_TO_SWAP / ACCEPTABLE_GAS / WAIT based on gas price. $0.15", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "ETH" } }, required: ["symbol"] } },
  { name: "dagon_audit",    description: "Dagon audit — verify prior on-chain decision (gwei saved vs wasted). $0.07", inputSchema: { type: "object", properties: { decision_id: { type: "string" }, window: { type: "string" } }, required: ["decision_id"] } },
  { name: "dagon_forecast", description: "Dagon 80% calibrated gas price range. $0.05", inputSchema: { type: "object", properties: { symbol: { type: "string", description: "ETH" } }, required: [] } },
  { name: "dagon_risk",      description: "Dagon current on-chain risk state. $0.02", inputSchema: { type: "object", properties: {}, required: [] } },
];

// ─────────────────────────────────────────────────────────────────────────────
// Route mapping
// ─────────────────────────────────────────────────────────────────────────────

// API → { port, route_prefix }
const API_MAP = {
  anubis:  { port: 8001, prefix: "api/anubis"  },
  viking:  { port: 8002, prefix: "api/viking"   },
  apollo:  { port: 8003, prefix: "api/apollo"  },
  pollux:  { port: 8004, prefix: "api/pollux"  },
  dagon:   { port: 8005, prefix: "api/dagon"   },
};

// toolName e.g. "anubis_decision" → { api: "anubis", endpoint: "decision" }
function parseTool(toolName) {
  const [api, endpoint] = toolName.split("_", 2);
  return { api, endpoint };
}

async function callApi(toolName, args) {
  const { api, endpoint } = parseTool(toolName);
  const cfg = API_MAP[api];
  if (!cfg) throw new Error(`Unknown API: ${api}`);

  const base = `${ATLASMARKETS_URL}:${cfg.port}`;
  let url;
  let method = "GET";

  // Build URL with query params
  const params = new URLSearchParams();
  if (args.symbol !== undefined) params.set("symbol", args.symbol);
  if (args.decision_id !== undefined) params.set("decision_id", args.decision_id);
  if (args.window !== undefined) params.set("window", args.window);
  if (args.limit !== undefined) params.set("limit", String(args.limit));

  const qs = params.toString();
  url = `${base}/${cfg.prefix}/${endpoint}${qs ? "?" + qs : ""}`;

  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`AtlasMarkets ${api} error ${response.status}: ${body}`);
  }

  return response.json();
}

// ─────────────────────────────────────────────────────────────────────────────
// MCP Server
// ─────────────────────────────────────────────────────────────────────────────

const server = new Server(
  { name: "atlasmarkets-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;

  try {
    const result = await callApi(name, args);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  } catch (err) {
    return {
      content: [{ type: "text", text: JSON.stringify({ error: err.message, tool: name }) }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[atlasmarkets-mcp] Connected — AtlasMarkets MCP server listening");
}

main().catch((err) => {
  console.error("[atlasmarkets-mcp] Fatal:", err);
  process.exit(1);
});