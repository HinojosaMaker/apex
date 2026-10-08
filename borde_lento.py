# -*- coding: utf-8 -*-
"""
apex/borde_lento.py - caza el edge donde la latencia NO decide.
Mide, SIN capital ni gas, el DIFERENCIAL DE FUNDING entre venues de perps:
un diferencial sostenido = carry delta-neutral (long el perp barato / short el caro),
edge de horas-dias, inmune a la latencia de Anguila. Solo mide; no opera.
Fuentes publicas sin API key; con fallback (Binance da 451 desde aqui).
"""
import json, urllib.request

UA={"User-Agent":"Mozilla/5.0 (APEX borde)"}
def get(url, timeout=15):
    r=urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=timeout) as x: return json.load(x)

def bybit():
    # funding + mark de perps lineales USDT
    d=get("https://api.bybit.com/v5/market/tickers?category=linear")
    out={}
    for t in d.get("result",{}).get("list",[]):
        s=t.get("symbol","")
        if not s.endswith("USDT"): continue
        try: fr=float(t.get("fundingRate") or 0)
        except: continue
        out[s[:-4]]={"funding_8h":fr}
    return out

def okx():
    # OKX swap funding
    out={}
    try:
        inst=get("https://www.okx.com/api/v5/public/instruments?instType=SWAP")
        syms=[i["instId"] for i in inst.get("data",[]) if i["instId"].endswith("-USDT-SWAP")][:120]
    except Exception: return out
    for iid in syms:
        try:
            d=get(f"https://www.okx.com/api/v5/public/funding-rate?instId={iid}")
            row=(d.get("data") or [{}])[0]; fr=float(row.get("fundingRate") or 0)
            out[iid.split("-")[0]]={"funding_8h":fr}
        except Exception: continue
    return out

def hyperliquid():
    out={}
    try:
        req=urllib.request.Request("https://api.hyperliquid.xyz/info",
            data=json.dumps({"type":"metaAndAssetCtxs"}).encode(),
            headers={**UA,"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=15) as x: d=json.load(x)
        meta,ctxs=d[0]["universe"],d[1]
        for m,c in zip(meta,ctxs):
            fr=c.get("funding")
            if fr is not None: out[m["name"]]={"funding_8h":float(fr)}
    except Exception: pass
    return out

def main():
    print("="*66); print(" APEX / borde_lento  ·  diferencial de funding (edge sin latencia)")
    print("="*66)
    venues={}
    for nombre,fn in [("bybit",bybit),("okx",okx),("hyperliquid",hyperliquid)]:
        try:
            v=fn(); venues[nombre]=v; print(f"  {nombre}: {len(v)} perps")
        except Exception as e: print(f"  {nombre}: fallo {str(e)[:60]}")
    # unir por moneda; buscar el mayor diferencial de funding entre 2 venues
    monedas={}
    for ven,d in venues.items():
        for coin,info in d.items():
            monedas.setdefault(coin,{})[ven]=info["funding_8h"]
    cand=[]
    for coin,m in monedas.items():
        if len(m)<2: continue
        hi=max(m.items(),key=lambda x:x[1]); lo=min(m.items(),key=lambda x:x[1])
        dif=hi[1]-lo[1]
        # funding es por 8h -> anualizar (3 veces/dia * 365)
        apr=dif*3*365*100
        cand.append((apr,coin,lo[0],lo[1],hi[0],hi[1]))
    cand.sort(reverse=True)
    print("\n TOP diferenciales de funding (carry delta-neutral, anualizado):")
    print("  (long el perp de funding BAJO, short el de funding ALTO; cobras la diferencia)\n")
    for apr,coin,lov,lof,hiv,hif in cand[:12]:
        print(f"   {coin:10s} {apr:7.1f}% APR   long {lov}({lof*100:+.4f}%)  short {hiv}({hif*100:+.4f}%)")
    if cand:
        realistas=[c for c in cand if c[0]>8 and c[0]<300]  # descarta ruido y outliers de listado
        print(f"\n  edges 8-300% APR (plausibles, no outliers de listing): {len(realistas)}")
        print("  NOTA HONESTA: funding varia cada 8h; esto es foto, no garantia. Hay que")
        print("  MEDIR persistencia (edge-lab) antes de operar, y necesita capital para sostener.")
    json.dump([{"coin":c[1],"apr":round(c[0],1),"long":c[2],"short":c[4]} for c in cand[:20]],
              open("borde_lento.json","w",encoding="utf-8"), indent=2, ensure_ascii=False)

if __name__=="__main__": main()
