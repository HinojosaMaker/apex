# -*- coding: utf-8 -*-
"""
apex/ruta_atomica.py - escaner de ARBITRAJE ATOMICO en vivo (resultado instantaneo).
Para cientos de tokens Solana: cotiza con Jupiter (precio EJECUTABLE real, con fees)
el ida-y-vuelta SOL->token->SOL. Si neto>0, es ganancia en LA MISMA tx = dinero
instantaneo, sin capital (se puede estructurar atomico), gas Solana ~$0.0002.
Va ANCHO y en paralelo. Reporta al instante lo que haya, sin adornos.
"""
import json, urllib.request, concurrent.futures as cf
UA={"User-Agent":"Mozilla/5.0 (APEX atomico)"}
def get(u,data=None):
    r=urllib.request.Request(u,data=data,headers={**UA,**({"Content-Type":"application/json"} if data else {})})
    with urllib.request.urlopen(r,timeout=15) as x: return json.load(x)
SOL="So11111111111111111111111111111111111111112"
JUPS=["https://lite-api.jup.ag/swap/v1/quote","https://api.jup.ag/swap/v1/quote"]
import time, itertools
_jr=itertools.cycle(JUPS)

def universo(maximo=120):
    out=[]; seen=set()
    for u in ["https://api.dexscreener.com/token-boosts/top/v1",
              "https://api.dexscreener.com/token-boosts/latest/v1",
              "https://api.dexscreener.com/token-profiles/latest/v1"]:
        try:
            for t in get(u):
                if t.get("chainId")=="solana" and t.get("tokenAddress") and t["tokenAddress"] not in seen:
                    seen.add(t["tokenAddress"]); out.append(t["tokenAddress"])
        except Exception: pass
    return out[:maximo]

def roundtrip(mint, amt_sol=0.2):
    amt=int(amt_sol*1e9)
    def q(inp,out,a):
        for k in range(4):
            base=next(_jr)
            try:
                return get(f"{base}?inputMint={inp}&outputMint={out}&amount={a}&slippageBps=100&restrictIntermediateTokens=false")
            except Exception:
                time.sleep(0.5*(k+1))
        return None
    q1=q(SOL,mint,amt)
    if not q1 or "outAmount" not in q1: return None
    got=int(q1["outAmount"])
    q2=q(mint,SOL,got)
    if not q2 or "outAmount" not in q2: return None
    back=int(q2["outAmount"]); neto=(back-amt)/amt*100
    return {"mint":mint,"neto_pct":round(neto,4),"back_sol":round(back/1e9,6)}

def main():
    print("="*64); print(" APEX / ruta_atomica  ·  arbitraje atomico EN VIVO (Jupiter real)")
    print("="*64)
    toks=universo(45); print(f" tokens a escanear: {len(toks)}  (round-trip SOL->token->SOL)")
    res=[]
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(lambda m: roundtrip(m), toks):
            if r: res.append(r)
    res.sort(key=lambda x:-x["neto_pct"])
    print(f" rutas cotizadas OK: {len(res)}")
    pos=[r for r in res if r["neto_pct"]>0]
    print(f" rutas con GANANCIA atomica (neto>0): {len(pos)}")
    print("\n TOP 10 por neto (lo que de verdad existe AHORA):")
    for r in res[:10]:
        flag="  <<< GANANCIA" if r["neto_pct"]>0 else ""
        print(f"   {r['mint'][:14]}..  neto {r['neto_pct']:+.3f}%{flag}")
    json.dump(res, open("ruta_atomica.json","w",encoding="utf-8"), indent=2, ensure_ascii=False)
    if pos:
        print(f"\n >>> {len(pos)} ruta(s) atomicas POSITIVAS ahora. Resta descontar fee de red (~0.00001 SOL)")
        print("     y el riesgo de que cambie en el bloque. Esto SI es resultado instantaneo.")
    else:
        mejor=res[0]["neto_pct"] if res else 0
        print(f"\n 0 rutas positivas. El mejor round-trip fue {mejor:+.3f}% (negativo = fees+spread).")
        print(" Medido ANCHO y en vivo: el mercado Solana esta eficiente en este instante.")
if __name__=="__main__": main()
