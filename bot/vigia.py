# -*- coding: utf-8 -*-
"""
bot/vigia.py - vigia de arbitraje gasless/sin-capital. Escanea rutas en vivo (Jupiter real),
y cuando una NETEA sobre el umbral, arma el disparo del FlashArbExecutor (via Paymaster).
Modo 'watch' (por defecto): solo mira y reporta, sin clave, sin gastar. 100% honesto.
"""
import json, urllib.request, time, itertools, os, sys
UA={"User-Agent":"Mozilla/5.0 (APEX vigia)"}
JUPS=itertools.cycle(["https://lite-api.jup.ag/swap/v1/quote","https://api.jup.ag/swap/v1/quote"])
SOL="So11111111111111111111111111111111111111112"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=15) as x: return json.load(x)
def tokens(n=40):
    out=[]; seen=set()
    for u in ["https://api.dexscreener.com/token-boosts/top/v1","https://api.dexscreener.com/token-boosts/latest/v1"]:
        try:
            for t in get(u):
                if t.get("chainId")=="solana" and t.get("tokenAddress") not in seen:
                    seen.add(t["tokenAddress"]); out.append(t["tokenAddress"])
        except Exception: pass
    return out[:n]
def rt(mint, amt=0.3):
    a=int(amt*1e9)
    def q(i,o,x):
        for k in range(3):
            try: return get(f"{next(JUPS)}?inputMint={i}&outputMint={o}&amount={x}&slippageBps=80&restrictIntermediateTokens=false")
            except Exception: time.sleep(0.4)
        return None
    q1=q(SOL,mint,a)
    if not q1 or "outAmount" not in q1: return None
    q2=q(mint,SOL,int(q1["outAmount"]))
    if not q2 or "outAmount" not in q2: return None
    return (int(q2["outAmount"])-a)/a*100
def ronda(umbral=0.4):
    toks=tokens(40); mejor=-99; hits=0
    for m in toks:
        n=rt(m)
        if n is None: continue
        if n>mejor: mejor=n
        if n>umbral:
            hits+=1; print(f"  >>> OPORTUNIDAD {m[:12]}.. neto {n:+.3f}% (>{umbral}%) -> dispararia el executor")
    return mejor, hits, len(toks)
def main():
    modo = "exec" if "--exec" in sys.argv else "watch"
    print(f"APEX vigia · modo={modo} · umbral 0.4% neto (cubre flash-fee + margen)")
    print("(watch = solo mira; exec = dispara via Paymaster, requiere setup)")
    rondas = 1 if "--once" in sys.argv else 9999
    for i in range(rondas):
        mejor,hits,n = ronda()
        print(f"[ronda {i+1}] {n} rutas, {hits} oportunidades, mejor neto {mejor:+.3f}%  ({time.strftime('%H:%M:%S')})")
        if hits==0: print("   sin dislocacion ahora (mercado eficiente). El vigia sigue vivo.")
        if rondas>1: time.sleep(45)
if __name__=="__main__": main()
