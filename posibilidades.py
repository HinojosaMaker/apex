# -*- coding: utf-8 -*-
"""
apex/posibilidades.py - EL MEZCLADOR: crea posibilidades nuevas recombinando
evolutivamente TODO lo que la maquina ya tiene.
  - organos reales (registro.json, 53)       <- lo que produce valor
  - mecanismos ganadores de hackathon         <- como se conecta/monetiza
  - motor biomimetico + rail x402             <- inteligencia + cobro
Algoritmo genetico: el genoma es una COMBINACION (organos + mecanismo + monetizacion);
la APTITUD mide FACTIBILIDAD REAL (que las piezas existan y sean complementarias) y
NOVEDAD (diversidad de capacidades). Sale un ranking de posibilidades concretas.
"""
import json, os, random

APEX=os.path.dirname(__file__)
reg=json.load(open(os.path.join(APEX,"registro.json"),encoding="utf-8"))
ORG=[o for o in reg["organos"] if o["caps"]]

# mecanismos extraidos de la investigacion de hackathones (reutilizables)
MECANISMOS=[
 ("x402 per-call","cobrar USDC por request, sin gas ni capital (MCPay/coinbase)"),
 ("federacion","exponer varias capacidades tras una sola puerta (MIMIC-IV)"),
 ("bazaar-discovery","listar para que agentes que pagan te encuentren (Infinite Bazaar)"),
 ("genetico-evolutivo","evolucionar la mejor regla/estrategia por seleccion (AUC medido)"),
 ("regresion-simbolica","descubrir la ley/relacion oculta desde datos (Kepler)"),
 ("mundo-modelo-critico","un modelo juez que regenera solo lo malo (fix-it-in-post)"),
 ("auto-reparacion","detectar fallo->arreglar->reintentar solo (Gitdefender/BobOps)"),
 ("doble-modelo","dos modelos que se auditan: divergencia=riesgo (ModelProof)"),
 ("enjambre-roles","sub-agentes por rol que votan un veredicto (SOC/NeMo)"),
 ("flashloan","capital prestado y devuelto en 1 tx: cero capital propio"),
 ("edge-local","correr el modelo en hardware minimo, offline (docX)"),
 ("voz-canal","voz como interfaz y como bus de datos agente-agente (Gibberlink)"),
]
# categoria "productora" de valor por capacidad
PRODUCTORAS={"video","trading","cripto_onchain","mcp","ia_local"}

def organos_por_cap(cap): return [o for o in ORG if cap in o["caps"]]

def genoma_aleatorio(rnd):
    k=rnd.choice([2,2,3])
    orgs=rnd.sample(ORG, k)
    mec=rnd.choice(MECANISMOS)
    return {"orgs":orgs,"mec":mec}

def caps_de(g):
    c=set()
    for o in g["orgs"]: c|=set(o["caps"])
    return c

def aptitud(g):
    caps=caps_de(g)
    score=0.0
    # FACTIBILIDAD: tiene al menos una productora + una via de monetizacion
    tiene_prod = len(caps & PRODUCTORAS)>0
    tiene_money = ("monetizacion" in caps) or (g["mec"][0] in ("x402 per-call","flashloan"))
    if tiene_prod: score+=3
    if tiene_money: score+=3
    # NOVEDAD/COMPLEMENTO: diversidad de categorias (mezcla real, no mas de lo mismo)
    score += len(caps)*1.0
    # SINERGIA: inteligencia (agentes/biomimetica) sobre una productora
    if ("agentes" in caps or g["mec"][0] in ("genetico-evolutivo","regresion-simbolica","mundo-modelo-critico")) and tiene_prod:
        score+=2
    # penaliza redundancia (dos organos identicos en caps)
    if len(g["orgs"])>=2 and all(set(g["orgs"][0]["caps"])==set(o["caps"]) for o in g["orgs"]):
        score-=2
    return score

def evolucionar(gen=60, pob=80, semilla=11):
    rnd=random.Random(semilla)
    pobl=[genoma_aleatorio(rnd) for _ in range(pob)]
    for _ in range(gen):
        rank=sorted(pobl,key=aptitud,reverse=True)
        elite=rank[:pob//5]; nueva=list(elite)
        while len(nueva)<pob:
            if rnd.random()<0.5:
                a=rnd.choice(elite); b=rnd.choice(elite)
                orgs=list({id(o):o for o in (a["orgs"]+b["orgs"])}.values())
                rnd.shuffle(orgs); orgs=orgs[:rnd.choice([2,3])]
                hijo={"orgs":orgs,"mec":rnd.choice([a["mec"],b["mec"]])}
            else:
                hijo=genoma_aleatorio(rnd)
            if rnd.random()<0.3: hijo["mec"]=rnd.choice(MECANISMOS)   # mutacion
            nueva.append(hijo)
        pobl=nueva
    # dedupe por firma
    vistos=set(); unicos=[]
    for g in sorted(pobl,key=aptitud,reverse=True):
        firma=tuple(sorted(o["nombre"] for o in g["orgs"]))
        if firma in vistos: continue
        vistos.add(firma); unicos.append(g)
    return unicos


def idea_concreta(g):
    caps=caps_de(g); mec=g["mec"][0]
    n=[o["nombre"] for o in g["orgs"]]
    piezas=" + ".join(n)
    tiene=lambda c: c in caps
    # producto segun que capacidades se mezclan
    if tiene("video") and tiene("trading"):
        base=f"Fabrica Shorts/clips sobre senales de mercado REALES de ({piezas})"
    elif tiene("video") and (tiene("cripto_onchain") or tiene("monetizacion")):
        base=f"Fabrica de video autonoma ({piezas}) que se vende a agentes"
    elif tiene("trading") and tiene("cripto_onchain"):
        base=f"Cazador de oportunidades on-chain ({piezas})"
    elif tiene("mcp"):
        base=f"Servicio MCP compuesto ({piezas})"
    else:
        base=f"Servicio autonomo ({piezas})"
    # que le aporta el mecanismo
    extra={
     "x402 per-call":"cobrado por request en USDC a tu wallet, sin gas ni capital",
     "federacion":"todo tras UNA puerta x402 que un agente consume de golpe",
     "bazaar-discovery":"listado para que agentes que pagan lo descubran (demanda)",
     "genetico-evolutivo":"que EVOLUCIONA su mejor estrategia por seleccion (AUC medido)",
     "regresion-simbolica":"que DESCUBRE la relacion oculta en los datos",
     "mundo-modelo-critico":"con un juez que regenera solo lo que sale mal (ahorra coste)",
     "auto-reparacion":"que se AUTO-REPARA ante fallos sin que toques nada",
     "doble-modelo":"con dos modelos que se auditan: si divergen, descarta (calidad)",
     "enjambre-roles":"como enjambre de sub-agentes por rol que votan el veredicto",
     "flashloan":"con capital PRESTADO y devuelto en 1 tx: cero dinero tuyo",
     "edge-local":"corriendo offline en hardware minimo, privado",
     "voz-canal":"controlado por voz y hablando con otros agentes por audio",
    }.get(mec,"")
    return base+" — "+extra

def render(g,i):
    nombres=" + ".join(o["nombre"] for o in g["orgs"])
    caps=sorted(caps_de(g))
    mec,desc=g["mec"]
    return (f" {i:2d}. [{aptitud(g):.0f}pts] {nombres}\n"
            f"      capacidades: {', '.join(caps)}\n"
            f"      mecanismo: {mec} — {desc}")

def main():
    print("="*70); print(" APEX / posibilidades  ·  el mezclador evolutivo de TODO")
    print("="*70)
    print(f" recombinando {len(ORG)} organos reales x {len(MECANISMOS)} mecanismos de hackathon")
    top=evolucionar()[:10]
    print(" TOP posibilidades factibles (aptitud = piezas reales + complemento + novedad):\n")
    for i,g in enumerate(top,1): print(render(g,i)); print()
    json.dump([{"orgs":[o["nombre"] for o in g["orgs"]],"caps":sorted(caps_de(g)),
                "mecanismo":g["mec"][0],"aptitud":aptitud(g)} for g in top],
              open(os.path.join(APEX,"posibilidades.json"),"w",encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(" guardado -> posibilidades.json  (combinaciones reales, no fantasia)")

if __name__=="__main__": main()
