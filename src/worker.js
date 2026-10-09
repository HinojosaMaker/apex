/**
 * APEX x402 gate — Cloudflare Worker (always-on).
 * Cobra USDC real en SOLANA mainnet via facilitator keyless (twzrd, feePayer patrocinado).
 * Sin secretos, sin API key, sin gas: solo la wallet receptora (publica) + el facilitator.
 * Capacidades reales (datos en vivo de Dexscreener): exit-check, token-safety,
 * multichain-quote, screen (modelo biomimetico evolucionado, AUC 0.69 OOS).
 */
const PAYTO    = "GmoCdZy25Z6DoDVj14Lh6twthfL6RCnxPjL8oVoSKTZP";
const USDC     = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"; // USDC mint Solana
const FACIL    = "https://intel.twzrd.xyz";
const FEEPAYER = "GWRLgRB6diC2zG9BaoGJsan9T8JvJCk7usFruiefnfMP";
const NETWORK  = "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"; // Solana mainnet CAIP-2
const GENOME   = [1.0355841279, -0.0121140570, 1.4152982046, 0.7254057529, -1.1825634873, -0.2270064257];

const CAPS = {
  "exit-check":       { usd: 0.05, desc: "Real liquidity / can you sell this token?" },
  "token-safety":     { usd: 0.05, desc: "Risk score: liquidity, volume, age, momentum" },
  "multichain-quote": { usd: 0.05, desc: "Where it trades and with how much liquidity" },
  "screen":           { usd: 0.05, desc: "Evolved tradeability score (genetic, AUC~0.69 OOS)" },
  "oracle":           { usd: 0.05, desc: "Live on-chain intelligence: spot, real funding, Polymarket odds, gas, latency" },
};

const UA = { "User-Agent": "APEX-x402-worker" };
const j = (code, obj, extra = {}) =>
  new Response(JSON.stringify(obj), { status: code,
    headers: { "Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*", ...extra } });

function requirements(resource, usd) {
  const atomic = String(Math.max(50000, Math.round(usd * 1e6)));
  return { scheme: "exact", network: NETWORK, amount: atomic, maxAmountRequired: atomic,
    asset: USDC, payTo: PAYTO, resource, description: "APEX capability", mimeType: "application/json",
    maxTimeoutSeconds: 120, extra: { feePayer: FEEPAYER } };
}
function manifest(origin) {
  return {
    x402Version: 2, name: "APEX Capability Gate", serviceName: "APEX",
    description: "Pay-per-call crypto intelligence for AI agents. Measured signals (liquidity, exit, safety, evolved tradeability) with on-chain verifiable track record. USDC on Solana, gasless.",
    facilitator: FACIL, network: NETWORK, asset: USDC, payTo: PAYTO,
    tags: ["crypto", "defi", "trading", "token-safety", "liquidity", "ai-agents", "oracle", "solana", "signals"],
    type: "http", icon: origin + "/icon.svg",
    resources: Object.entries(CAPS).map(([k, v]) => ({
      path: "/" + k, resource: origin + "/" + k, serviceName: "APEX " + k,
      price: "$" + v.usd, network: NETWORK, asset: USDC, payTo: PAYTO,
      description: v.desc, tags: ["crypto", k],
      accepts: [requirements("/" + k, v.usd)],
      extensions: { bazaar: { info: {
        input: { method: "GET", queryParams: { token: "token mint/contract address (required)" } },
        output: { body: "JSON verdict with measured on-chain metrics" } } } },
      example: origin + "/" + k + "?token=So11111111111111111111111111111111111111112",
    })),
  };
}
const LLMS_TXT = `# APEX — Pay-per-call crypto intelligence for AI agents

APEX sells measured crypto signals per call in USDC on Solana (x402), gasless for buyer and seller.
Every answer is real on-chain data, not vibes. Pay \$0.05 USDC per call via the x402 protocol.

## Endpoints (GET, pass ?token=<mint/address>)
- /exit-check       Can you actually sell this token? Real liquidity. \$0.05
- /token-safety     Risk score from liquidity, volume, age, momentum. \$0.05
- /multichain-quote Where it trades and with how much liquidity per chain. \$0.05
- /screen           Evolved tradeability score (genetic model, AUC~0.69 out-of-sample). \$0.05

## How to pay
1. GET the endpoint -> receive HTTP 402 with accepts[] (Solana USDC, feePayer sponsored).
2. Sign the x402 payment, send header X-PAYMENT.
3. Receive the data. Settlement via facilitator ${FACIL}.

payTo: ${PAYTO} (Solana mainnet). Manifest: /.well-known/x402.json
`;
function agentCard(origin) {
  return {
    name: "APEX", description: "Pay-per-call crypto intelligence oracle for AI agents (x402, USDC on Solana).",
    url: origin, version: "1.0.0", protocol: "x402",
    capabilities: Object.keys(CAPS), payment: { protocol: "x402", network: "solana", asset: USDC, payTo: PAYTO },
    manifest: origin + "/.well-known/x402.json", docs: origin + "/llms.txt",
  };
}
function openapiDoc(origin) {
  const paths = {};
  for (const [k, v] of Object.entries(CAPS)) {
    paths["/" + k] = { get: {
      summary: v.desc, operationId: k,
      parameters: [{ name: "token", in: "query", required: true, schema: { type: "string" },
        description: "token mint/contract address" }],
      responses: {
        "200": { description: "paid result (JSON verdict with measured on-chain metrics)" },
        "402": { description: "Payment Required — x402 challenge, $" + v.usd + " USDC on Solana" },
      },
      "x-402": { price: "$" + v.usd, network: NETWORK, asset: USDC, payTo: PAYTO },
    } };
  }
  return { openapi: "3.0.0",
    info: { title: "APEX Capability Gate", version: "1.0.0",
      description: "Pay-per-call crypto intelligence for AI agents (x402, USDC on Solana)." },
    servers: [{ url: origin }], paths };
}

async function dex(addr) {
  const r = await fetch(`https://api.dexscreener.com/latest/dex/tokens/${addr}`, { headers: UA });
  return await r.json();
}

// Live on-chain intelligence: all REAL public sources, with measured latency. No shell, no fake PnL.
async function oracle() {
  const t = (p) => { const s = Date.now(); return p.then((v) => [v, Date.now() - s]).catch(() => [null, Date.now() - s]); };
  const jget = (u, o) => fetch(u, { headers: UA, ...(o || {}) }).then((r) => r.json());
  const rpc = (u, m) => jget(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: m, params: [] }) });
  const [cb, cbL] = await t(Promise.all(["BTC", "ETH", "SOL"].map((s) =>
    jget(`https://api.coinbase.com/v2/prices/${s}-USD/spot`).then((d) => [s, parseFloat(d.data.amount)]))));
  const [hl, hlL] = await t(jget("https://api.hyperliquid.xyz/info", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type: "metaAndAssetCtxs" }) }));
  const [pm, pmL] = await t(jget("https://gamma-api.polymarket.com/markets?limit=5&active=true&closed=false&order=volume24hr&ascending=false"));
  const [pg, pgL] = await t(rpc("https://polygon-bor-rpc.publicnode.com", "eth_gasPrice"));
  const prices = {}; (cb || []).forEach(([s, p]) => (prices[s] = p));
  let funding = {};
  if (hl && hl[0] && hl[1]) {
    const univ = hl[0].universe, ctx = hl[1];
    for (const name of ["BTC", "ETH", "SOL"]) {
      const i = univ.findIndex((u) => u.name === name);
      if (i >= 0) funding[name] = { apr_pct: Math.round(parseFloat(ctx[i].funding || 0) * 24 * 365 * 1e4) / 100, mark: parseFloat(ctx[i].markPx || 0) };
    }
  }
  const rows = Array.isArray(pm) ? pm : (pm && pm.data) || [];
  const markets = rows.slice(0, 5).map((m) => {
    try {
      const outs = JSON.parse(m.outcomes || "[]"), pr = JSON.parse(m.outcomePrices || "[]").map(Number);
      const top = pr.indexOf(Math.max(...pr));
      return { q: (m.question || "").slice(0, 80), lead: outs[top], p: Math.round(pr[top] * 1000) / 10, vol24h: Math.round(+m.volume24hr || 0) };
    } catch { return null; }
  }).filter(Boolean);
  const gas = pg && pg.result ? Math.round(parseInt(pg.result, 16) / 1e7) / 100 : null;
  const btcChg = null; // (24h change omitted to keep the paid call fast; spot+funding+odds are the alpha)
  const carry = funding.BTC ? (funding.BTC.apr_pct > 3 ? "LONG-SPOT/SHORT-PERP pays" : funding.BTC.apr_pct < -3 ? "SHORT-SPOT/LONG-PERP pays" : "carry flat") : null;
  return {
    product: "APEX oracle — live on-chain intelligence (real sources, measured)",
    ts: Date.now(), prices, funding, polymarket: markets,
    chain: { polygon_gas_gwei: gas },
    latency_ms: { coinbase: cbL, hyperliquid: hlL, polymarket: pmL, polygon: pgL },
    read: { funding_carry: carry, note: "measured from public sources; not financial advice; no shell, no fake PnL" },
  };
}

async function runCap(cap, q) {
  if (cap === "oracle") return await oracle();
  const token = (q.get("token") || "").trim();
  if (!token) return { error: "missing ?token=<address>" };
  const d = await dex(token);
  const pairs = (d.pairs || []).filter(p => p.priceUsd);
  if (cap === "multichain-quote") {
    const byChain = {};
    for (const p of pairs) { const c = p.chainId || "?"; byChain[c] = (byChain[c] || 0) + ((p.liquidity || {}).usd || 0); }
    const rank = Object.entries(byChain).sort((a, b) => b[1] - a[1]);
    return { token, chains: rank.length, liquidity_by_chain: rank.map(([c, l]) => ({ chain: c, liquidity_usd: Math.round(l) })), best_chain: rank[0]?.[0] || null };
  }
  if (!pairs.length) return { token, verdict: "NO POOL", tradeable: false, liquidity_usd: 0 };
  const best = pairs.reduce((a, b) => (((b.liquidity || {}).usd || 0) > ((a.liquidity || {}).usd || 0) ? b : a));
  const liq = (best.liquidity || {}).usd || 0, vol = (best.volume || {}).h24 || 0;
  const chg = (best.priceChange || {}).h24 || 0;
  const txns = ((best.txns || {}).h24 || {}); const nt = (txns.buys || 0) + (txns.sells || 0);
  const ageH = best.pairCreatedAt ? Math.max(0, (Date.now() - best.pairCreatedAt) / 3.6e6) : 0;
  if (cap === "exit-check")
    return { token, tradeable: liq >= 5000, liquidity_usd: Math.round(liq), volume_24h_usd: Math.round(vol),
      dex: best.dexId, verdict: liq >= 5000 ? "LIQUID" : (liq > 0 ? "THIN" : "NO EXIT") };
  if (cap === "token-safety") {
    let s = 0; s += liq >= 50000 ? 35 : (liq >= 5000 ? 20 : 0); s += vol >= 20000 ? 25 : (vol >= 2000 ? 12 : 0);
    s += ageH >= 168 ? 20 : (ageH >= 24 ? 10 : 0); s += Math.abs(chg) <= 50 ? 20 : (Math.abs(chg) <= 200 ? 8 : 0);
    return { token, score: s, risk: s >= 70 ? "LOW" : (s >= 40 ? "MEDIUM" : "HIGH"), liquidity_usd: Math.round(liq), volume_24h_usd: Math.round(vol), age_hours: Math.round(ageH), change_24h_pct: chg };
  }
  if (cap === "screen") {
    const x = [Math.log1p(ageH), Math.log1p(nt), Math.tanh(chg / 100), nt > 50 ? 1 : 0, ageH > 24 ? 1 : 0];
    let z = GENOME[5]; for (let i = 0; i < 5; i++) z += GENOME[i] * x[i];
    const prob = 1 / (1 + Math.exp(-z));
    return { token, score_tradeable: Math.round(prob * 1000) / 1000, verdict: prob >= 0.5 ? "TRADEABLE" : "AVOID", model: "genetic evolved AUC~0.69 OOS" };
  }
  return { error: "unknown cap" };
}

async function facil(path, body) {
  const r = await fetch(FACIL + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  try { return await r.json(); } catch { return {}; }
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const origin = url.origin;
    const path = url.pathname;
    if (path === "/" || path === "/.well-known/x402.json") return j(200, manifest(origin));
    if (path === "/llms.txt") return new Response(LLMS_TXT, { headers: { "Content-Type": "text/plain; charset=utf-8", "Access-Control-Allow-Origin": "*" } });
    if (path === "/.well-known/agent.json" || path === "/.well-known/agent-card.json" || path === "/agent.json") return j(200, agentCard(origin));
    if (path === "/openapi.json") return j(200, openapiDoc(origin));
    if (path === "/icon.svg") return new Response('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#070A0F"/><circle cx="32" cy="32" r="9" fill="none" stroke="#34E5C6" stroke-width="4"/><circle cx="32" cy="32" r="3" fill="#F6B452"/></svg>', { headers: { "Content-Type": "image/svg+xml", "Access-Control-Allow-Origin": "*" } });
    const cap = path.replace(/^\//, "");
    if (!CAPS[cap]) return j(404, { error: "unknown capability", catalog: Object.keys(CAPS) });
    const reqs = requirements("/" + cap, CAPS[cap].usd);
    const xpay = request.headers.get("X-PAYMENT");
    if (!xpay) return j(402, { x402Version: 2, error: "Payment Required", accepts: [reqs] }, { "X-PAYMENT-REQUIRED": JSON.stringify(reqs) });
    let payload;
    try { payload = JSON.parse(atob(xpay)); } catch (e) { return j(402, { error: "X-PAYMENT unreadable", accepts: [reqs] }); }
    const vr = await facil("/verify", { x402Version: 2, paymentPayload: payload, paymentRequirements: reqs });
    if (!vr.isValid) return j(402, { error: "invalid payment", detail: vr, accepts: [reqs] });
    const sr = await facil("/settle", { x402Version: 2, paymentPayload: payload, paymentRequirements: reqs });
    const res = await runCap(cap, url.searchParams);
    res._paid = true; res._settle = sr; res._payTo = PAYTO;
    return j(200, res);
  },
};
