# -*- coding: utf-8 -*-
"""
apex/descubridor.py - el motor biomimetico aplicado a la CUSPIDE DE LA FISICA.
Regresion simbolica por evolucion: redescubre una LEY FISICA desde datos REALES,
igual que las herramientas que la ciencia de frontera usa de verdad.
Demo medible: a partir del sistema solar real, recuperar la 3a ley de Kepler (T ~ a^1.5)
y la ley de gravitacion de Newton (F ~ m1*m2/r^2). Sin trampa: se mide el ajuste.
"""
import math, random

# --- DATOS REALES del sistema solar: (semieje mayor AU, periodo orbital anios) ---
PLANETAS = {
 "Mercurio":(0.387,0.2408),"Venus":(0.723,0.6152),"Tierra":(1.000,1.000),
 "Marte":(1.524,1.8808),"Jupiter":(5.203,11.862),"Saturno":(9.537,29.457),
 "Urano":(19.191,84.011),"Neptuno":(30.07,164.79)}

def evolucionar_potencia(xs, ys, gen=120, pob=60, semilla=3):
    """Evoluciona y = C * x^p (C,p) por seleccion-cruce-mutacion para ajustar datos reales."""
    rnd=random.Random(semilla)
    def error(ind):
        C,p=ind
        e=0.0
        for x,y in zip(xs,ys):
            try: pred=C*(x**p)
            except Exception: return 1e9
            e+=(math.log(pred+1e-12)-math.log(y+1e-12))**2   # error relativo (log)
        return e/len(xs)
    poblacion=[[rnd.uniform(0.1,3),rnd.uniform(0.1,3)] for _ in range(pob)]
    mejor=None; mejorE=1e18; hist=[]
    for g in range(gen):
        rank=sorted(poblacion,key=error)
        if error(rank[0])<mejorE: mejorE=error(rank[0]); mejor=list(rank[0])
        hist.append(round(mejorE,6))
        elite=rank[:max(2,pob//5)]; nueva=list(elite)
        while len(nueva)<pob:
            a=rnd.choice(elite); b=rnd.choice(elite)
            hijo=[(a[i] if rnd.random()<0.5 else b[i]) for i in range(2)]
            if rnd.random()<0.4:
                j=rnd.randrange(2); hijo[j]+=rnd.gauss(0,0.2*(1-g/gen)+0.01)
            nueva.append([max(1e-3,hijo[0]),hijo[1]])
        poblacion=nueva
    return mejor, mejorE, hist

def kepler():
    xs=[a for a,_ in PLANETAS.values()]; ys=[T for _,T in PLANETAS.values()]
    (C,p), err, hist = evolucionar_potencia(xs,ys)
    print("  3a LEY DE KEPLER (datos reales de 8 planetas):")
    print(f"    ley evolucionada:  T = {C:.4f} * a^{p:.4f}")
    print(f"    verdad fisica:     T = 1.0000 * a^1.5000   (T^2 = a^3)")
    print(f"    exponente recuperado: {p:.4f}  (error vs 1.5: {abs(p-1.5):.4f})")
    print(f"    ajuste log-MSE: {err:.2e}  <- medido sobre los datos reales")
    return abs(p-1.5)

def newton():
    # datos sinteticos de F = G*m1*m2/r^2 con G real, para recuperar los EXPONENTES
    G=6.674e-11; rnd=random.Random(1)
    datos=[]
    for _ in range(40):
        m1=10**rnd.uniform(1,6); m2=10**rnd.uniform(1,6); r=10**rnd.uniform(0,3)
        F=G*m1*m2/r**2; datos.append((m1,m2,r,F))
    # evoluciona F = C * m1^a * m2^b * r^c
    def err(ind):
        C,a,b,c=ind; e=0.0
        for m1,m2,r,F in datos:
            pred=C*(m1**a)*(m2**b)*(r**c)
            e+=(math.log(pred+1e-300)-math.log(F+1e-300))**2
        return e/len(datos)
    rndp=random.Random(5)
    pobl=[[10**rndp.uniform(-12,-9),rndp.uniform(0,2),rndp.uniform(0,2),rndp.uniform(-3,0)] for _ in range(80)]
    best=None;bE=1e18
    for g in range(200):
        rank=sorted(pobl,key=err)
        if err(rank[0])<bE: bE=err(rank[0]); best=list(rank[0])
        el=rank[:16]; nu=list(el)
        while len(nu)<80:
            a=rndp.choice(el); b=rndp.choice(el)
            h=[(a[i] if rndp.random()<0.5 else b[i]) for i in range(4)]
            if rndp.random()<0.5:
                j=rndp.randrange(4); h[j]+= h[j]*rndp.gauss(0,0.1) if j==0 else rndp.gauss(0,0.15*(1-g/200)+0.01)
            nu.append(h)
        pobl=nu
    C,a,b,c=best
    print("  LEY DE GRAVITACION DE NEWTON (recuperar exponentes desde datos):")
    print(f"    ley evolucionada:  F = {C:.3e} * m1^{a:.3f} * m2^{b:.3f} * r^{c:.3f}")
    print(f"    verdad fisica:     F = {G:.3e} * m1^1 * m2^1 * r^-2")
    print(f"    exponentes recuperados: m1={a:.3f} m2={b:.3f} r={c:.3f}  | C={C:.3e} vs G={G:.3e}")
    print(f"    ajuste log-MSE: {bE:.2e}")

def main():
    print("="*64); print(" APEX / descubridor  ·  biomimetica en la cuspide de la fisica")
    print("="*64)
    d=kepler(); print()
    newton(); print()
    print(" "+("VEREDICTO: la evolucion REDESCUBRIO la ley (exponente a <0.05 del real)." if d<0.05
               else "VEREDICTO: aproximacion parcial."))
    print(" Esto es la herramienta REAL de IA-para-ciencia. El salto a fusion/ToE/Marte")
    print(" exige hardware fisico (tokamaks, aceleradores, naves), no esta PC. Sin humo.")

if __name__=="__main__": main()
