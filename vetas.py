# -*- coding: utf-8 -*-
"""
apex/vetas.py - minero de VETAS on-chain: lee la FUENTE del creador y encuentra
funciones PUBLICAS SIN PERMISO que mueven valor a quien las llama (residuo/incentivo).
Es el edge que solo yo tengo: leer codigo a escala. Lo que un humano no puede y los
bots keeper no hacen en la cola larga.
HONESTO: encontrar la funcion != ganancia. Hay que MEDIR residuo real vs gas despues.
"""
import json, urllib.request, re

UA={"User-Agent":"Mozilla/5.0 (APEX vetas)"}
def src(chain, addr):
    url=f"https://sourcify.dev/server/v2/contract/{chain}/{addr}?fields=sources"
    r=urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=25) as x: d=json.load(x)
    return {k:v["content"] for k,v in (d.get("sources") or {}).items()}

# patrones: valor que sale HACIA el que llama / incentivo al caller
PAGA_CALLER=[
 r"transfer\(\s*msg\.sender", r"safeTransfer\(\s*msg\.sender",
 r"_mint\(\s*msg\.sender", r"msg\.sender\.call\{value",
 r"transfer\(\s*to\b", r"safeTransfer\(\s*to\b",   # skim(to)/claim(to)
]
INCENTIVO=["reward","incentive","bounty","caller","keeper","harvest","skim",
           "claimfees","poke","sync","settle","liquidat","sweep","collect"]
# marcas de ACCESO RESTRINGIDO (si estan, NO es sin-permiso)
RESTRINGIDO=[r"onlyOwner", r"onlyGov", r"onlyKeeper", r"onlyRole",
             r"require\(\s*msg\.sender\s*==", r"_checkOwner", r"authorized"]

def funciones(code):
    # extrae firmas de funciones public/external y un bloque aproximado
    for m in re.finditer(r"function\s+(\w+)\s*\(([^)]*)\)([^{;]*)\{", code):
        nombre=m.group(1); cab=m.group(0)
        if not re.search(r"\b(public|external)\b", cab): continue
        ini=m.end(); prof=1; i=ini
        while i<len(code) and prof>0:
            if code[i]=="{": prof+=1
            elif code[i]=="}": prof-=1
            i+=1
        cuerpo=code[ini:i]
        yield nombre, cab, cuerpo

def analiza(code):
    hits=[]
    for nombre,cab,cuerpo in funciones(code):
        restringida = any(re.search(p,cab) for p in RESTRINGIDO) or any(re.search(p,cuerpo[:400]) for p in RESTRINGIDO)
        if restringida: continue
        paga = any(re.search(p,cuerpo) for p in PAGA_CALLER)
        incent = nombre.lower() in INCENTIVO or any(k in nombre.lower() for k in INCENTIVO)
        if paga or incent:
            hits.append({"funcion":nombre,"paga_al_caller":bool(paga),
                         "nombre_incentivo":bool(incent),
                         "firma":re.sub(r"\s+"," ",cab).strip()[:100]})
    return hits

def escanear(objetivos):
    print("="*68); print(" APEX / vetas  ·  funciones sin-permiso que mueven valor (lee la fuente)")
    print("="*68)
    total=[]
    for chain,addr,etq in objetivos:
        try:
            archivos=src(chain,addr)
            code="\n".join(archivos.values())
            hits=analiza(code)
            # dedup por nombre
            vistos=set(); u=[]
            for h in hits:
                if h["funcion"] in vistos: continue
                vistos.add(h["funcion"]); u.append(h)
            print(f"\n {etq}  ({addr[:10]}..  chain {chain})  -> {len(u)} vetas")
            for h in u[:12]:
                flags=("PAGA-CALLER " if h["paga_al_caller"] else "")+("[incentivo]" if h["nombre_incentivo"] else "")
                print(f"    - {h['funcion']:16s} {flags}")
            total += [{**h,"addr":addr,"chain":chain,"etq":etq} for h in u]
        except Exception as e:
            print(f"\n {etq}: no se pudo ({str(e)[:70]})")
    json.dump(total, open("vetas.json","w",encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\n total vetas detectadas: {len(total)}  -> vetas.json")
    print(" SIGUIENTE (honesto): medir residuo real vs gas en cada una antes de tocar nada.")

if __name__=="__main__":
    # contratos REALES verificados en Base para probar el detector
    OBJ=[
     (8453,"0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43","Aerodrome Router"),
     (8453,"0x420DD381b31aEf6683db6B902084cB0FFECe40Da","Aerodrome Pool Factory"),
     (1,"0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f","UniswapV2 Factory (ETH)"),
     (1,"0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc","UniV2 USDC/WETH pair (ETH)"),
    ]
    escanear(OBJ)
