# -*- coding: utf-8 -*-
"""
apex/biomimetica.py - ORGANO BIOMIMETICO de APEX (computacion evolutiva real).
Algoritmo genetico: evoluciona por seleccion-cruce-mutacion una REGLA que separa
tokens 'operables' de 'muertos', con APTITUD MEDIDA sobre datos on-chain REALES
(Dexscreener). Sin fitness inventado: se entrena en un split y se mide en otro.
El mejor genoma queda como regla-cazador reutilizable por la puerta x402.
"""
import os, json, urllib.request, random, math

UA = {"User-Agent":"Mozilla/5.0 (APEX biomimetica)"}
def _get(url):
    req=urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r: return json.load(r)

# ---- 1) DATASET REAL: tokens frescos + sus stats reales --------------------
def dataset(maximo=60):
    fuentes=["https://api.dexscreener.com/token-profiles/latest/v1",
             "https://api.dexscreener.com/token-boosts/latest/v1",
             "https://api.dexscreener.com/token-boosts/top/v1"]
    perfiles=[]
    for u in fuentes:
        try: perfiles += _get(u)
        except Exception: pass
    if not perfiles:
        print("no pude bajar perfiles"); return []
    filas=[]
    vistos=set()
    for p in perfiles[:maximo*4]:
        ch=p.get("chainId"); addr=p.get("tokenAddress")
        if not addr or addr in vistos: continue
        vistos.add(addr)
        try:
            d=_get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}")
            pares=d.get("pairs") or []
            if not pares: 
                filas.append({"liq":0,"vol":0,"edad":0,"txns":0,"chg":0,"ok":0}); continue
            pr=max(pares,key=lambda x:(x.get("liquidity") or {}).get("usd") or 0)
            liq=(pr.get("liquidity") or {}).get("usd") or 0
            vol=(pr.get("volume") or {}).get("h24") or 0
            txh=(pr.get("txns") or {}).get("h24") or {}
            txns=(txh.get("buys") or 0)+(txh.get("sells") or 0)
            chg=(pr.get("priceChange") or {}).get("h24") or 0
            import time as _t
            edad=max(0,(_t.time()*1000-(pr.get("pairCreatedAt") or 0))/3.6e6) if pr.get("pairCreatedAt") else 0
            # ETIQUETA REAL (lo que queremos predecir): operable = liquido Y con flujo
            ok=1 if (liq>=10000 and vol>=1000) else 0
            filas.append({"liq":liq,"vol":vol,"edad":edad,"txns":txns,"chg":chg,"ok":ok})
        except Exception:
            continue
        if len(filas)>=maximo: break
    return filas

# features que el genoma PUEDE usar (excluye liq y vol directos: eso seria trampa)
def feats(f):
    return [
        math.log1p(f["edad"]),            # edad (horas)
        math.log1p(f["txns"]),            # actividad
        math.tanh(f["chg"]/100.0),        # momentum acotado
        1.0 if f["txns"]>50 else 0.0,     # flag actividad alta
        1.0 if f["edad"]>24 else 0.0,     # flag sobrevivio 1 dia
    ]
NF=5

# ---- 2) GENOMA = pesos + sesgo; predice 'operable' --------------------------
def predice(gen, f):
    x=feats(f); s=gen[-1]
    for w,xi in zip(gen[:NF], x): s+=w*xi
    return 1.0/(1.0+math.exp(-s))

def aptitud(gen, filas):
    # AUC medida: prob. de rankear un positivo por encima de un negativo
    pos=[predice(gen,f) for f in filas if f["ok"]==1]
    neg=[predice(gen,f) for f in filas if f["ok"]==0]
    if not pos or not neg: return 0.5
    g=sum(1 for p in pos for n in neg if p>n)+0.5*sum(1 for p in pos for n in neg if p==n)
    return g/(len(pos)*len(neg))

# ---- 3) EVOLUCION: seleccion + cruce + mutacion -----------------------------
def evolucionar(train, generaciones=40, pob=40, semilla=7):
    rnd=random.Random(semilla)
    poblacion=[[rnd.uniform(-2,2) for _ in range(NF+1)] for _ in range(pob)]
    mejor=None; mejor_apt=-1; historia=[]
    for g in range(generaciones):
        punt=sorted(((aptitud(ind,train),ind) for ind in poblacion), key=lambda x:-x[0])
        if punt[0][0]>mejor_apt: mejor_apt, mejor = punt[0][0], list(punt[0][1])
        historia.append(round(punt[0][0],3))
        elite=[ind for _,ind in punt[:max(2,pob//5)]]      # supervivencia del mas apto
        nueva=list(elite)
        while len(nueva)<pob:
            a=rnd.choice(elite); b=rnd.choice(elite)
            hijo=[(a[i] if rnd.random()<0.5 else b[i]) for i in range(NF+1)]  # cruce
            if rnd.random()<0.3:                                             # mutacion
                j=rnd.randrange(NF+1); hijo[j]+=rnd.gauss(0,0.5)
            nueva.append(hijo)
        poblacion=nueva
    return mejor, mejor_apt, historia

def main():
    print("="*60); print(" APEX / biomimetica  ·  algoritmo genetico sobre datos reales")
    print("="*60)
    print(" bajando dataset real de tokens (Dexscreener)...")
    filas=dataset(60)
    npos=sum(f["ok"] for f in filas); n=len(filas)
    print(f" dataset: {n} tokens reales, {npos} operables / {n-npos} muertos")
    if n<12 or npos<3 or (n-npos)<3:
        print(" dataset insuficiente para medir honesto; reintenta mas tarde."); return
    random.Random(1).shuffle(filas)
    K=5; folds=[filas[i::K] for i in range(K)]
    aucs=[]
    for i in range(K):
        test=folds[i]; train=[x for j in range(K) if j!=i for x in folds[j]]
        if sum(f["ok"] for f in test)<1 or (len(test)-sum(f["ok"] for f in test))<1: continue
        gen,_,_=evolucionar(train, generaciones=50, pob=50, semilla=i+1)
        aucs.append(aptitud(gen,test))
    apt_te = sum(aucs)/len(aucs) if aucs else 0.5
    gen, apt_tr, hist = evolucionar(filas, generaciones=50, pob=50)  # genoma final con todo
    print(f" aptitud (AUC) TRAIN(full): {apt_tr:.3f}   <- evolucion: {hist[0]} -> {hist[-1]}")
    print(f" aptitud (AUC) CV {len(aucs)}-fold OUT-OF-SAMPLE: {apt_te:.3f}   (0.5=azar)  <- la que cuenta")
    pesos={"edad":round(gen[0],3),"txns":round(gen[1],3),"momentum":round(gen[2],3),
           "flag_activo":round(gen[3],3),"flag_sobrevive":round(gen[4],3),"sesgo":round(gen[5],3)}
    print(" regla-cazador evolucionada:", json.dumps(pesos))
    out={"genoma":gen,"pesos":pesos,"auc_train":apt_tr,"auc_test":apt_te,"n":n,"npos":npos,"historia":hist}
    open(os.path.join(os.path.dirname(__file__),"cazador_evolucionado.json"),"w",encoding="utf-8").write(json.dumps(out,indent=2,ensure_ascii=False))
    veredicto = "PREDICE (mejor que azar)" if apt_te>0.6 else ("marginal" if apt_te>0.52 else "NO predice (honesto: no sirve)")
    print(" veredicto medido:", veredicto)
    print(" guardado -> cazador_evolucionado.json")

if __name__=="__main__": main()
