# -*- coding: utf-8 -*-
"""
apex/residuo.py - MIDE residuo skimmable real en pares de Base (gratis, solo lectura).
Para cada par estilo UniV2: skimmable_token = balanceOf(par) - reserva. Si hay excedente
en un token con precio, y su valor > gas (~$0.005 en Base), skim() = ganancia neta sin capital.
Solo LEE la cadena (eth_call). No firma, no gasta. Honesto: prueba o descarta el residuo.
"""
import json, urllib.request

RPC="https://mainnet.base.org"
UA={"User-Agent":"Mozilla/5.0 (APEX residuo)"}
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    r=urllib.request.Request(RPC, data=body, headers={**UA,"Content-Type":"application/json"})
    with urllib.request.urlopen(r, timeout=20) as x: return json.load(x).get("result")

def call(to, data):
    return rpc("eth_call",[{"to":to,"data":data},"latest"])

def _hex(x): return int(x,16) if x and x!="0x" else 0
SEL={"getReserves":"0x0902f1ac","token0":"0x0dfe1681","token1":"0xd21220a7"}
def balanceOf(token, holder):
    return _hex(call(token,"0x70a08231"+holder[2:].rjust(64,"0")))
def getReserves(pair):
    r=call(pair,SEL["getReserves"])
    if not r or len(r)<2: return None
    r=r[2:]; return _hex("0x"+r[0:64]), _hex("0x"+r[64:128])
def token_of(pair,sel):
    r=call(pair,SEL[sel]); return "0x"+r[-40:] if r else None

def pares_base(maximo=40):
    """direcciones de pares reales en Base via Dexscreener (boosts+profiles)."""
    fuentes=["https://api.dexscreener.com/token-boosts/top/v1",
             "https://api.dexscreener.com/token-boosts/latest/v1",
             "https://api.dexscreener.com/token-profiles/latest/v1"]
    toks=[]
    for u in fuentes:
        try:
            d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=15))
            toks+=[t for t in d if t.get("chainId")=="base"]
        except Exception: pass
    pares=[]; vistos=set()
    for t in toks:
        a=t.get("tokenAddress")
        if not a: continue
        try:
            dd=json.load(urllib.request.urlopen(urllib.request.Request(
                f"https://api.dexscreener.com/latest/dex/tokens/{a}",headers=UA),timeout=15))
            for p in (dd.get("pairs") or []):
                if p.get("chainId")!="base": continue
                pa=p.get("pairAddress")
                if pa and pa.lower() not in vistos:
                    vistos.add(pa.lower())
                    pares.append({"pair":pa,"priceUsd":p.get("priceUsd"),
                                  "base":(p.get("baseToken") or {}).get("address"),
                                  "quote":(p.get("quoteToken") or {}).get("address")})
        except Exception: continue
        if len(pares)>=maximo: break
    return pares

def main():
    print("="*66); print(" APEX / residuo  ·  skimmable real en Base (solo lectura, gratis)")
    print("="*66)
    try:
        bn=_hex(rpc("eth_blockNumber",[])); print(f" Base RPC vivo, bloque {bn}")
    except Exception as e:
        print(" RPC fallo:", str(e)[:80]); return
    pares=pares_base(40)
    print(f" pares a auditar: {len(pares)}")
    GAS_USD=0.006
    hallazgos=[]
    probados=0
    for p in pares:
        try:
            res=getReserves(p["pair"])
            if not res: continue
            probados+=1
            t0=token_of(p["pair"],"token0"); t1=token_of(p["pair"],"token1")
            if not t0 or not t1: continue
            b0=balanceOf(t0,p["pair"]); b1=balanceOf(t1,p["pair"])
            ex0=max(0,b0-res[0]); ex1=max(0,b1-res[1])
            if ex0>0 or ex1>0:
                hallazgos.append({"pair":p["pair"],"exceso_t0":ex0,"exceso_t1":ex1,
                                  "t0":t0,"t1":t1})
        except Exception: continue
    print(f" pares con getReserves validos: {probados}")
    print(f" pares con ALGUN excedente (skimmable>0 en bruto): {len(hallazgos)}")
    for h in hallazgos[:15]:
        print(f"   {h['pair'][:12]}..  exceso t0={h['exceso_t0']}  t1={h['exceso_t1']}")
    json.dump(hallazgos, open("residuo.json","w",encoding="utf-8"), indent=2, ensure_ascii=False)
    if not hallazgos:
        print("\n VEREDICTO HONESTO: 0 residuo skimmable en esta muestra.")
        print(" (Como Galactus: los pares activos estan barridos. Habria que escanear")
        print("  MILES de pares inactivos para hallar excedente > gas. Medido, no supuesto.)")
    else:
        print("\n Hay excedente bruto; falta valorarlo en USD vs gas ($0.006) para saber si NETEA.")

if __name__=="__main__": main()
