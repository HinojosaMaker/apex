# -*- coding: utf-8 -*-
"""
apex/cuantico.py - optimizacion CUANTICA (modelo QUBO / annealing) sobre edges reales.
QUBO = el problema nativo de los computadores cuanticos (D-Wave). Aqui se resuelve con
RECOCIDO SIMULADO (la simulacion clasica del annealing cuantico): elige el mejor
subconjunto de carries de funding que maximiza retorno y castiga concentracion/riesgo.
HONESTO: optimiza la ASIGNACION; NO crea edge. El techo es el ~10% APR ya medido.
"""
import json, math, random

def cargar():
    try: return json.load(open("borde_lento.json",encoding="utf-8"))
    except Exception: return []

def construir_qubo(edges, lam=0.6):
    """QUBO: maximizar sum(apr_i x_i) - lam * penalizacion. x_i in {0,1} = incluir el carry i.
    Penaliza: (a) elegir demasiados (riesgo operativo), (b) concentracion en un mismo venue."""
    n=len(edges)
    apr=[e["apr"] for e in edges]
    mx=max(apr) if apr else 1
    # Q[i][j]: diagonal = -beneficio normalizado; fuera-diagonal = penalizacion por co-seleccion
    Q=[[0.0]*n for _ in range(n)]
    for i in range(n):
        Q[i][i]= -apr[i]/mx                      # recompensa (minimizamos energia -> maximiza apr)
        for j in range(i+1,n):
            pen=0.0
            if edges[i].get("long")==edges[j].get("long") or edges[i].get("short")==edges[j].get("short"):
                pen+=0.5                          # mismo venue = riesgo correlado
            pen+=0.15                              # coste marginal por cada posicion extra
            Q[i][j]=lam*pen; Q[j][i]=lam*pen
    return Q

def energia(Q,x):
    n=len(x); e=0.0
    for i in range(n):
        if not x[i]: continue
        e+=Q[i][i]
        for j in range(i+1,n):
            if x[j]: e+=Q[i][j]
    return e

def recocido(Q, pasos=20000, T0=2.0, semilla=42):
    """Recocido simulado = annealing cuantico simulado: baja la 'temperatura' y acepta
    peores soluciones con prob. decreciente (tunelado termico, analogo al cuantico)."""
    rnd=random.Random(semilla); n=len(Q)
    x=[rnd.randint(0,1) for _ in range(n)]; E=energia(Q,x)
    best=list(x); bestE=E
    for t in range(pasos):
        T=T0*(1-t/pasos)+1e-3
        i=rnd.randrange(n); x[i]^=1; E2=energia(Q,x)
        if E2<E or rnd.random()<math.exp(-(E2-E)/T): E=E2
        else: x[i]^=1
        if E<bestE: bestE=E; best=list(x)
    return best,bestE

def main():
    print("="*66); print(" APEX / cuantico  ·  QUBO + annealing sobre edges de funding REALES")
    print("="*66)
    edges=cargar()
    if not edges:
        print(" no hay borde_lento.json; corre borde_lento.py primero."); return
    print(f" universo: {len(edges)} carries medidos")
    Q=construir_qubo(edges)
    sel,E=recocido(Q)
    elegidos=[edges[i] for i in range(len(edges)) if sel[i]]
    elegidos.sort(key=lambda e:-e["apr"])
    print(f" annealing -> energia {E:.3f}")
    print(f" CESTA OPTIMA (delta-neutral, diversificada por venue): {len(elegidos)} carries")
    carry_prom=sum(e["apr"] for e in elegidos)/len(elegidos) if elegidos else 0
    for e in elegidos:
        print(f"   {e['coin']:10s} {e['apr']:6.1f}% APR   long {e['long']:12s} short {e['short']}")
    print(f"\n carry promedio de la cesta: {carry_prom:.1f}% APR (delta-neutral)")
    print(" ---------------------------------------------------------------")
    print(" LO QUE LO CUANTICO HIZO: elegir el mejor subconjunto diversificado (QUBO).")
    print(" LO QUE NO HIZO: crear edge. El techo sigue siendo el funding medido.")
    print(" Un QPU real (D-Wave) resolveria el MISMO QUBO; a esta escala no da ventaja.")
    print(" Y sin capital para sostener la cesta, esto es un plano, no un ingreso.")
    json.dump(elegidos, open("cesta_optima.json","w",encoding="utf-8"), indent=2, ensure_ascii=False)

if __name__=="__main__": main()
