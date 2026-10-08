# -*- coding: utf-8 -*-
"""
APEX / vender.py - el ORGANO DE MONETIZACION.
Puerta x402 LOCAL (sin hosting, sin capital): convierte cualquier capacidad de la
maquina en algo que un AGENTE paga por USDC (Base), y el dinero entra a TU wallet.
Fusiona: x402 per-call (MCPay) + correr local (docX) + federacion (una puerta, N
capacidades) + manifiesto para discovery (Bazaar).

- Recibir USDC NO cuesta gas y NO requiere capital. Solo tu direccion receptora.
- Config por entorno (NO hardcodeo tu wallet):  APEX_WALLET=0x....  (red Base)
- Arranca sin dependencias externas (http.server de la stdlib).
- /.well-known/x402.json  -> manifiesto para que agentes/Bazaar descubran precios.
- GET /<capacidad>  sin pago -> 402 Payment Required + precio + payTo.
         con cabecera  X-PAYMENT: <prueba>  -> ejecuta y devuelve el resultado.
"""
import os, json, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
try:
    import pago
except Exception:
    import apex.pago as pago

def _wallet_default():
    try:
        import json as _j
        return _j.load(open(os.path.join(os.path.dirname(__file__),"wallet.json")))["x402_primary"]["payTo"]
    except Exception:
        return ""
WALLET = os.environ.get("APEX_WALLET", "").strip() or _wallet_default()   # wallet receptora (Base)
RED    = os.environ.get("APEX_RED", "base")             # base mainnet
USDC   = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"   # USDC en Base
PUERTO = int(os.environ.get("APEX_PUERTO", "8402"))

# ---- CATALOGO: capacidades reales vendibles (federacion) -------------------
def cap_exit_check(q):
    """¿Se puede salir de este token? Liquidez real via Dexscreener (sin API key)."""
    addr = (q.get("token") or "").strip()
    if not addr: return {"error": "falta ?token=<mint/address>"}
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (APEX x402 gate)"})
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.load(r)
        pares = d.get("pairs") or []
        if not pares:
            return {"token": addr, "vendible": False, "motivo": "sin pool: no hay donde vender", "liquidez_usd": 0}
        mejor = max(pares, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)
        liq = (mejor.get("liquidity") or {}).get("usd") or 0
        vol = (mejor.get("volume") or {}).get("h24") or 0
        return {"token": addr, "vendible": liq >= 5000,
                "liquidez_usd": round(liq,2), "volumen_24h_usd": round(vol,2),
                "dex": mejor.get("dexId"), "par": mejor.get("pairAddress"),
                "veredicto": "LIQUIDO" if liq>=5000 else ("FINO" if liq>0 else "SIN SALIDA")}
    except Exception as e:
        return {"token": addr, "error": str(e)[:160]}


def _dex(addr):
    import urllib.request, json
    url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (APEX x402 gate)"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r)

def cap_token_safety(q):
    """Riesgo real de un token por liquidez/volumen/edad/variacion (sin API key)."""
    addr = (q.get("token") or "").strip()
    if not addr: return {"error": "falta ?token=<address>"}
    try:
        d = _dex(addr); pares = d.get("pairs") or []
        if not pares: return {"token": addr, "riesgo": "MAXIMO", "motivo": "sin pool: no hay salida", "score": 0}
        p = max(pares, key=lambda x:(x.get("liquidity") or {}).get("usd") or 0)
        liq=(p.get("liquidity") or {}).get("usd") or 0
        vol=(p.get("volume") or {}).get("h24") or 0
        chg=(p.get("priceChange") or {}).get("h24") or 0
        import time as _t
        edad_h = max(0,(_t.time()*1000 - (p.get("pairCreatedAt") or 0))/3.6e6) if p.get("pairCreatedAt") else None
        score=0
        score += 35 if liq>=50000 else (20 if liq>=5000 else 0)
        score += 25 if vol>=20000 else (12 if vol>=2000 else 0)
        score += 20 if (edad_h or 0)>=168 else (10 if (edad_h or 0)>=24 else 0)
        score += 20 if abs(chg)<=50 else (8 if abs(chg)<=200 else 0)
        nivel = "BAJO" if score>=70 else ("MEDIO" if score>=40 else "ALTO")
        return {"token":addr,"score":score,"riesgo":nivel,"liquidez_usd":round(liq,2),
                "volumen_24h_usd":round(vol,2),"edad_horas":round(edad_h,1) if edad_h else None,
                "cambio_24h_pct":chg,"dex":p.get("dexId")}
    except Exception as e:
        return {"token": addr, "error": str(e)[:160]}

def cap_multichain_quote(q):
    """Donde cotiza y con cuanta liquidez un token en TODAS las cadenas (sin API key)."""
    addr = (q.get("token") or "").strip()
    if not addr: return {"error":"falta ?token=<address>"}
    try:
        d=_dex(addr); pares=d.get("pairs") or []
        porcadena={}
        for p in pares:
            ch=p.get("chainId","?"); liq=(p.get("liquidity") or {}).get("usd") or 0
            porcadena[ch]=porcadena.get(ch,0)+liq
        ranking=sorted(porcadena.items(), key=lambda x:-x[1])
        return {"token":addr,"cadenas":len(ranking),
                "liquidez_por_cadena":[{"cadena":c,"liquidez_usd":round(l,2)} for c,l in ranking],
                "mejor_cadena":ranking[0][0] if ranking else None}
    except Exception as e:
        return {"token":addr,"error":str(e)[:160]}


def cap_screen_evolucionado(q):
    """Score de tradeabilidad con la REGLA EVOLUCIONADA (genetico, AUC~0.69 OOS)."""
    addr=(q.get("token") or "").strip()
    if not addr: return {"error":"falta ?token=<address>"}
    import json as _j, math as _m, os as _o
    try:
        g=_j.load(open(_o.path.join(_o.path.dirname(__file__),"cazador_evolucionado.json")))["genoma"]
    except Exception: return {"error":"cazador no entrenado; corre biomimetica.py"}
    try:
        import urllib.request
        req=urllib.request.Request(f"https://api.dexscreener.com/latest/dex/tokens/{addr}",
                                   headers={"User-Agent":"Mozilla/5.0 (APEX)"})
        import json as J
        with urllib.request.urlopen(req,timeout=12) as r: d=J.load(r)
        pares=d.get("pairs") or []
        if not pares: return {"token":addr,"score_tradeable":0.0,"veredicto":"SIN POOL"}
        p=max(pares,key=lambda x:(x.get("liquidity") or {}).get("usd") or 0)
        import time as _t
        edad=max(0,(_t.time()*1000-(p.get("pairCreatedAt") or 0))/3.6e6) if p.get("pairCreatedAt") else 0
        txh=(p.get("txns") or {}).get("h24") or {}; txns=(txh.get("buys") or 0)+(txh.get("sells") or 0)
        chg=(p.get("priceChange") or {}).get("h24") or 0
        x=[_m.log1p(edad),_m.log1p(txns),_m.tanh(chg/100.0),1.0 if txns>50 else 0.0,1.0 if edad>24 else 0.0]
        sc=g[-1]+sum(w*xi for w,xi in zip(g[:5],x)); prob=1.0/(1.0+_m.exp(-sc))
        return {"token":addr,"score_tradeable":round(prob,3),
                "veredicto":"OPERABLE" if prob>=0.5 else "EVITAR",
                "modelo":"genetico evolucionado AUC~0.69 OOS"}
    except Exception as e: return {"token":addr,"error":str(e)[:140]}

CATALOGO = {
    "exit-check":       {"precio_usdc": 0.01, "fn": cap_exit_check,
                         "desc": "Salida/liquidez real de un token antes de comprar"},
    "token-safety":     {"precio_usdc": 0.02, "fn": cap_token_safety,
                         "desc": "Score de riesgo (liquidez, volumen, edad, variacion)"},
    "multichain-quote": {"precio_usdc": 0.01, "fn": cap_multichain_quote,
                         "desc": "Donde cotiza y con cuanta liquidez en todas las cadenas"},
    "screen":           {"precio_usdc": 0.03, "fn": cap_screen_evolucionado,
                         "desc": "Score de tradeabilidad por regla EVOLUCIONADA (genetico, AUC~0.69 OOS)"},
}

def manifiesto():
    return {
        "x402Version": 1,
        "name": "APEX Capability Gate",
        "description": "Capacidades medidas de la maquina APEX, pago por uso en USDC (Base).",
        "network": RED, "asset": USDC, "payTo": WALLET or "SIN_CONFIGURAR",
        "resources": [
            {"path": f"/{k}", "price": f"${v['precio_usdc']}", "asset": USDC,
             "network": RED, "description": v["desc"]}
            for k,v in CATALOGO.items()
        ],
    }

class H(BaseHTTPRequestHandler):
    def _j(self, code, obj, extra=None):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k,v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path); ruta = u.path.strip("/"); q = {k:v[0] for k,v in parse_qs(u.query).items()}
        if u.path == "/.well-known/x402.json" or ruta == "":
            return self._j(200, manifiesto())
        if ruta not in CATALOGO:
            return self._j(404, {"error": "capacidad desconocida", "catalogo": list(CATALOGO)})
        cap = CATALOGO[ruta]
        xpay = self.headers.get("X-PAYMENT")
        if not xpay:
            # 402: el agente debe pagar y reintentar (esto es lo que hace entrar el dinero)
            reto = {"error":"Payment Required","accepts":[{
                "scheme":"exact","network":pago.NET,"asset":pago.usdc_asset(),
                "maxAmountRequired":str(cap["precio_usdc"]),"payTo":WALLET or "SIN_CONFIGURAR",
                "resource":"/"+ruta}]}
            return self._j(402, reto, {"X-PAYMENT-REQUIRED": json.dumps(reto["accepts"][0])})
        # verificacion REAL contra el facilitator on-chain (ya no es stub)
        ok, info = pago.verificar(xpay, "/"+ruta, cap["precio_usdc"], WALLET)
        if not ok:
            return self._j(402, {"error":"Payment Required","detalle":info,
                                 "accepts":[{"scheme":"exact","network":pago.NET,
                                 "asset":pago.usdc_asset(),"maxAmountRequired":str(cap["precio_usdc"]),
                                 "payTo":WALLET or "SIN_CONFIGURAR","resource":"/"+ruta}]})
        res = cap["fn"](q)
        res["_pagado"] = True; res["_liquidacion"] = info
        return self._j(200, res)

def autotest():
    print("="*60); print(" APEX / vender  ·  autotest (sin red, sin wallet real)")
    print("="*60)
    print(" Manifiesto:", json.dumps(manifiesto(), ensure_ascii=False)[:300], "...")
    print(" wallet receptora:", WALLET or "(SIN CONFIGURAR -> export APEX_WALLET=0x...)")
    print(" 402 para /exit-check:", json.dumps({"accepts":[{"network":RED,"asset":"USDC","price":0.01,"payTo":WALLET or "SIN_CONFIGURAR"}]}))
    print(" prueba de capacidad real (USDC de Base como token de prueba):")
    print("   ", json.dumps(cap_exit_check({"token":USDC}), ensure_ascii=False)[:260])

if __name__ == "__main__":
    import sys
    if "--serve" in sys.argv:
        print(f"APEX vender escuchando en http://0.0.0.0:{PUERTO}  (wallet={WALLET or 'SIN_CONFIGURAR'})")
        print(f"expone por tunel:  ngrok http {PUERTO}")
        ThreadingHTTPServer(("0.0.0.0", PUERTO), H).serve_forever()
    else:
        autotest()
