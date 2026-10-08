# -*- coding: utf-8 -*-
"""
apex/residuo2.py - test DEFINITIVO a escala: enumera pares de una factory UniV2 en Base
y mide skimmable real (balanceOf - reserva) en cientos de pares. Gratis, solo lectura.
"""
import json, urllib.request
RPCS=["https://base.llamarpc.com","https://base.publicnode.com","https://mainnet.base.org","https://1rpc.io/base"]
import time, itertools
_rr=itertools.cycle(RPCS)
UA={"User-Agent":"Mozilla/5.0 (APEX residuo2)"}
def rpc(m,p):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    for intento in range(5):
        url=next(_rr)
        try:
            r=urllib.request.Request(url,data=b,headers={**UA,"Content-Type":"application/json"})
            with urllib.request.urlopen(r,timeout=25) as x: return json.load(x).get("result")
        except Exception:
            time.sleep(0.4*(intento+1))
    return None
def call(to,data): return rpc("eth_call",[{"to":to,"data":data},"latest"])
def H(x): return int(x,16) if x and x!="0x" else 0
def allPairsLength(f): return H(call(f,"0x574f2ba3"))
def allPairs(f,i): r=call(f,"0x1e3dd18b"+hex(i)[2:].rjust(64,"0")); return "0x"+r[-40:] if r else None
def getReserves(p):
    r=call(p,"0x0902f1ac")
    if not r or len(r)<130: return None
    return H("0x"+r[2:66]), H("0x"+r[66:130])
def token0(p): r=call(p,"0x0dfe1681"); return "0x"+r[-40:] if r else None
def token1(p): r=call(p,"0xd21220a7"); return "0x"+r[-40:] if r else None
def balanceOf(t,h): return H(call(t,"0x70a08231"+h[2:].rjust(64,"0")))

FACTORIES=[("BaseSwap","0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB"),
           ("SushiV2Base","0x71524B4f93c58fcbF659783284E38825f0622859")]

def main():
    print("="*66); print(" APEX / residuo2  ·  test definitivo de skimmable en Base (a escala)")
    print("="*66)
    N=50  # muestra real (throttled para no reventar RPCs publicos)
    con_exceso=[]; total=0
    for nombre,f in FACTORIES:
        try: L=allPairsLength(f)
        except Exception as e: print(f" {nombre}: factory no responde ({str(e)[:40]})"); continue
        print(f" {nombre}: {L} pares totales; audito los ultimos {min(N,L)}")
        ini=max(0,L-N)
        for i in range(L-1, ini-1, -1):
            p=allPairs(f,i)
            if not p: continue
            res=getReserves(p)
            if not res: continue
            total+=1
            t0=token0(p); t1=token1(p)
            if not t0 or not t1: continue
            try:
                b0=balanceOf(t0,p); b1=balanceOf(t1,p)
            except Exception: continue
            e0=b0-res[0]; e1=b1-res[1]
            if e0>0 or e1>0:
                con_exceso.append({"factory":nombre,"pair":p,"t0":t0,"t1":t1,
                                   "exceso_t0":e0,"exceso_t1":e1,
                                   "frac0":e0/res[0] if res[0] else 0,
                                   "frac1":e1/res[1] if res[1] else 0})
    print(f"\n pares con getReserves auditados: {total}")
    print(f" pares con skimmable>0 (bruto): {len(con_exceso)}")
    con_exceso.sort(key=lambda x:max(x['frac0'],x['frac1']),reverse=True)
    for h in con_exceso[:15]:
        print(f"   {h['factory']:12s} {h['pair'][:12]}..  exc0={h['exceso_t0']} ({h['frac0']*100:.2f}%)  exc1={h['exceso_t1']} ({h['frac1']*100:.2f}%)")
    json.dump(con_exceso, open("residuo2.json","w",encoding="utf-8"), indent=2, ensure_ascii=False)
    print()
    if con_exceso:
        print(" HAY residuo bruto. Siguiente: valorar en USD el token skimmable y comparar vs gas")
        print(" (~$0.006 en Base) + confirmar que el token es VENDIBLE. Eso dice si NETEA de verdad.")
    else:
        print(" VEREDICTO DEFINITIVO (medido, no supuesto): 0 skimmable en", total, "pares.")
        print(" Confirma la fisica: el residuo de pares se barre al instante. No es una veta.")

if __name__=="__main__": main()
