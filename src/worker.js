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
const GENOME   = [1.0355841279, -0.0121140570, 1.4152982046, 0.7254057529, -1.1825634873, -0.2270064257];

const CAPS = {
  "exit-check":       { usd: 0.05, desc: "Real liquidity / can you sell this token?" },
  "token-safety":     { usd: 0.05, desc: "Risk score: liquidity, volume, age, momentum" },
  "multichain-quote": { usd: 0.05, desc: "Where it trades and with how much liquidity" },
  "screen":           { usd: 0.05, desc: "Evolved tradeability score (genetic, AUC~0.69 OOS)" },
};

const UA = { "User-Agent": "APEX-x402-worker" };
const j = (code, obj, extra = {}) =>
  new Response(JSON.stringify(obj), { status: code,
    headers: { "Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*", ...extra } });

function requirements(resource, usd) {
  const atomic = String(Math.max(50000, Math.round(usd * 1e6)));
  return { scheme: "exact", network: "solana", maxAmountRequired: atomic, asset: USDC,
    payTo: PAYTO, resource, description: "APEX capability", mimeType: "application/json",
    maxTimeoutSeconds: 120, extra: { feePayer: FEEPAYER } };
}
function manifest(origin) {
  return { x402Version: 2, name: "APEX Capability Gate", facilitator: FACIL, network: "solana",
    asset: USDC, payTo: PAYTO,
    resources: Object.entries(CAPS).map(([k, v]) => ({ path: "/" + k, resource: origin + "/" + k,
      price: "$" + v.usd, network: "solana", asset: USDC, payTo: PAYTO, description: v.desc })) };
}

async function dex(addr) {
  const r = await fetch(`https://api.dexscreener.com/latest/dex/tokens/${addr}`, { headers: UA });
  return await r.json();
}
async function runCap(cap, q) {
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
