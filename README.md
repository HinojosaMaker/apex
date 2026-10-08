# APEX — Verifiable Signal Oracle for the Agent Economy

**Pay-per-call crypto intelligence that AI agents buy with USDC (x402) — and every call's
outcome is attested on-chain, building an un-fakeable track record.**

The agent economy is drowning in unverifiable claims. Thousands of bots sell "signals" and
nobody can prove theirs work. APEX fixes that with two layers:

### 1. x402 Capability Gate (sell to machines, no accounts, no gas for the seller)
An HTTP endpoint that returns `402 Payment Required` + price; an agent pays USDC on Base and
gets a real, measured answer. Live capabilities (real data, no API keys):
- `exit-check` — can you actually sell this token? (real liquidity)
- `token-safety` — risk score from liquidity/volume/age/momentum
- `screen` — tradeability score from an **evolved** model (genetic algorithm, **AUC 0.69 out-of-sample**)
- `multichain-quote` — where a token trades and with how much liquidity

### 2. ApexAttestations (Base smart contract) — the moat time can't copy
Every signal is posted on-chain, sealed with a timestamp; when its horizon passes, the real
outcome is recorded. `accuracyBps()` returns a **verifiable, public hit-rate** nobody can forge.
A 6-month honest track record can't be bought, cloned, or back-dated.

## Why it's different
- **Sells to agents, not humans** — breaks the audience wall (x402, ~2s settlement, <$0.01 gas).
- **Reputation is on-chain and earned over time** — the one edge that compounds and can't be faked.
- **Measurement-first** — the signals come from a real evolutionary engine and live market data,
  not vibes. Honest by construction: wrong calls are recorded too.

## Run it
```bash
# the x402 service (testnet facilitator by default)
python vender.py --serve        # -> http://localhost:8402/.well-known/x402.json

# evolve the screening model on live data
python biomimetica.py           # -> cazador_evolucionado.json (measured AUC)

# deploy the attestations contract to Base
python scripts/deploy.py        # needs APEX_PRIVATE_KEY; APEX_NET=base-sepolia (free) | base
```

## Stack
Python (stdlib HTTP, x402 lib) · Solidity 0.8.26 (Base) · USDC payments via x402 · real data via
public RPC + Dexscreener/Jupiter. No API keys required to run.

Built for the agent economy. License: MIT.
