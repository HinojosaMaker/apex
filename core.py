# -*- coding: utf-8 -*-
"""
APEX - el cerebro por encima de todo.
No es otro proyecto: DESCUBRE el arsenal entero de la maquina y lo convierte en
un solo sistema autonomo, fusionando los patrones que ganan hackathones 2026:
  - Router de agentes especializados (patron LORE)
  - Prueba en sandbox antes de actuar (patron Time-Traveler)
  - Auto-reparacion sin intervencion (patron Gitdefender)
  - Corre local/gratis (patron docX)
  - Organos que producen y monetizan (fabricas de video + x402)
Este nucleo hace lo primero: descubrir, clasificar y enrutar. Arranca hoy.
"""
import os, json, re, sys
from pathlib import Path

HOME = Path(r"C:\Users\Admin")

# firmas de capacidad: que hace cada organo, por senales en disco
SENALES = {
    "video":        ["remotion", "ffmpeg", "wan", "ltx", "shorts", "video", "clip", "kokoro", "capcut", "veo"],
    "trading":      ["edge", "scalper", "arbitra", "backtest", "fomo", "predator", "signal", "trade", "pump"],
    "agentes":      ["agent", "swarm", "flexcorp", "aleph", "orchestr", "hive", "crew"],
    "mcp":          ["mcp", "server.py", "tools", "fastmcp"],
    "monetizacion": ["x402", "vexa", "escudo", "usdc", "payment", "exitguard", "survival"],
    "cripto_onchain":["wallet", "solana", "bsc", "eth", "sweep", "onchain", "web3", "sniper"],
    "ia_local":     ["ollama", "llama", "dolphin", "qwen", "jarvis", "mi-ia", "local-model"],
}

def firmar(d: Path):
    """clasifica un proyecto por nombre + archivos clave (barato, sin LLM)."""
    nombre = d.name.lower()
    blob = nombre + " "
    try:
        for f in list(d.iterdir())[:60]:
            blob += f.name.lower() + " "
    except Exception:
        pass
    caps = set()
    for cap, kws in SENALES.items():
        if any(k in blob for k in kws):
            caps.add(cap)
    # entrypoints ejecutables
    entradas = []
    for cand in ["main.py","run.py","app.py","core.py","server.py","cli.py","index.js","package.json"]:
        if (d / cand).exists():
            entradas.append(cand)
    return caps, entradas

def descubrir():
    organos = []
    for d in sorted(HOME.iterdir()):
        if not d.is_dir(): continue
        if d.name.startswith((".", "AppData", "OneDrive")): continue
        if d.name in {"Documents","Pictures","Music","Videos","Downloads","Desktop",
                      "Contacts","Favorites","Links","node_modules","venv","vendor","bin",
                      "Saved Games","Searches","Templates","Start Menu"}: continue
        caps, entradas = firmar(d)
        if not caps and not entradas: continue
        organos.append({"nombre": d.name, "caps": sorted(caps), "entradas": entradas,
                        "ruta": str(d)})
    return organos

# router: un objetivo en lenguaje natural -> organos relevantes (patron LORE)
def enrutar(objetivo: str, organos):
    o = objetivo.lower()
    quiere = set()
    mapa = {
        "video":["video","short","youtube","clip","pelicula","anima"],
        "trading":["trade","senal","edge","arbitr","mercado","cripto precio","predict"],
        "agentes":["agente","enjambre","equipo","autonom","orquesta"],
        "monetizacion":["cobrar","vender","dinero","monetiz","usdc","pago","x402"],
        "cripto_onchain":["wallet","onchain","solana","token","sniper","blockchain"],
        "ia_local":["local","sin api","offline","privado","jarvis"],
        "mcp":["mcp","herramienta","tool","conectar"],
    }
    for cap, kws in mapa.items():
        if any(k in o for k in kws): quiere.add(cap)
    if not quiere: quiere = {"agentes"}
    rank = []
    for org in organos:
        score = len(quiere & set(org["caps"]))
        if score: rank.append((score, org))
    rank.sort(key=lambda x: (-x[0], x[1]["nombre"]))
    return quiere, [r[1] for r in rank[:8]]

def main():
    organos = descubrir()
    cap_count = {}
    for org in organos:
        for c in org["caps"]:
            cap_count[c] = cap_count.get(c,0)+1
    Path(HOME/"apex"/"registro.json").write_text(
        json.dumps({"organos":organos,"resumen":cap_count}, indent=2, ensure_ascii=False), encoding="utf-8")

    print("="*64)
    print(" APEX  ·  el cerebro por encima de todo")
    print("="*64)
    print(f" Organos vivos descubiertos: {len(organos)}")
    print(" Capacidades de la maquina:")
    for c,n in sorted(cap_count.items(), key=lambda x:-x[1]):
        print(f"   {c:16s} x{n}")
    print("-"*64)
    objetivo = " ".join(sys.argv[1:]) or "haz un video corto y monetizalo"
    quiere, elegidos = enrutar(objetivo, organos)
    print(f" Objetivo: {objetivo}")
    print(f" El router activa: {', '.join(sorted(quiere))}")
    print(" Organos enrutados:")
    for org in elegidos:
        ep = org["entradas"][0] if org["entradas"] else "(sin entrypoint)"
        print(f"   -> {org['nombre']:22s} [{','.join(org['caps'])}]  {ep}")
    print("="*64)
    print(" registro.json escrito. Nucleo APEX operativo.")

if __name__ == "__main__":
    main()
