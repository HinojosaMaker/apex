# -*- coding: utf-8 -*-
"""
apex/ruta_fija.py - mide si existe RUTA FIJA de arbitraje capturable AHORA.
Por cada token, compara su precio entre TODOS sus pools/DEXs. Si el mismo token
cotiza distinto en dos pools mas alla de las comisiones, esa diferencia es el
spread que el movimiento de otros creo -> la ruta: comprar barato, vender caro.
Solo LEE datos reales (Dexscreener). Honesto: descuenta comisiones (~0.3% x2) y
senala slippage/gas/competencia como los que se comen el spread.
"""
import json, urllib.request
UA={"User-Agent":"Mozilla/5.0 (APEX ruta)"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=15) as x: return json.load(x)

def tokens_universo(maximo=70):
    out=[]; vistos=set()
    for u in ["https://api.dexscreener.com/token-boosts/top/v1",
              "https://api.dexscreener.com/token-boosts/latest/v1",
              "https://api.dexscreener.com/token-profiles/latest/v1"]:
        try:
            for t in get(u):
                a=t.get("tokenAddress"); c=t.get("chainId")
                if a and a not in vistos: vistos.add(a); out.append((c,a))
        except Exception: pass
    return out[:maximo]

def main():
    print("="*66); print(" APEX / ruta_fija  ·  ¿existe spread de arbitraje AHORA? (medido)")
    print("="*66)
    COM=0.003  # comision tipica por lado en un AMM
    universo=tokens_universo(70)
    print(f" tokens a auditar: {len(universo)}")
    rutas=[]
    for ch,addr in universo:
        try:
            d=get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}")
            pares=[p for p in (d.get("pairs") or []) if p.get("priceUsd")]
            # agrupar por el MISMO par de tokens (misma cotizacion) para comparar manzanas con manzanas
            porquote={}
            for p in pares:
                q=(p.get("quoteToken") or {}).get("symbol","?")
                liq=(p.get("liquidity") or {}).get("usd") or 0
                if liq<2000: continue      # sin liquidez no hay salida real
                try: pr=float(p["priceUsd"])
                except: continue
                porquote.setdefault(q,[]).append((pr,p.get("dexId"),liq,p.get("chainId")))
            for q,lst in porquote.items():
                if len(lst)<2: continue
                lo=min(lst); hi=max(lst)
                if lo[0]<=0: continue
                spread=(hi[0]-lo[0])/lo[0]
                neto=spread-2*COM         # descontar comision de comprar y vender
                if neto>0:
                    rutas.append({"token":addr[:10],"sym_quote":q,"spread_pct":round(spread*100,3),
                                  "neto_pct":round(neto*100,3),
                                  "compra":f"{lo[1]}({lo[3]})","vende":f"{hi[1]}({hi[3]})",
                                  "liq_min":round(min(lo[2],hi[2]))})
        except Exception: continue
    rutas.sort(key=lambda r:-r["neto_pct"])
    print(f"\n rutas con spread NETO de comision > 0: {len(rutas)}")
    for r in rutas[:15]:
        print(f"   {r['token']}.. /{r['sym_quote']:6s} spread {r['spread_pct']:.2f}% -> neto {r['neto_pct']:.2f}%  "
              f"compra {r['compra']} vende {r['vende']} | liq ${r['liq_min']}")
    json.dump(rutas, open("ruta_fija.json","w",encoding="utf-8"), indent=2, ensure_ascii=False)
    print()
    if rutas:
        realistas=[r for r in rutas if r["neto_pct"]>0.3 and r["liq_min"]>5000]
        print(f" rutas 'realistas' (neto>0.3% y liq>$5k): {len(realistas)}")
        print(" HONESTO: esto es spread BRUTO entre pools. Aun falta: slippage al ejecutar,")
        print(" gas, y que un bot mas rapido no lo tome antes. Lo SIGUIENTE es medir si")
        print(" ESTAS rutas SOBREVIVEN varios minutos (tu mordisco: borde en 13-55min).")
    else:
        print(" 0 rutas netas de comision. Confirma que los pools estan alineados (eficientes).")

if __name__=="__main__": main()
