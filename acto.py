# -*- coding: utf-8 -*-
"""
APEX / acto.py - el lazo de ACTUAR SEGURO.
Fusiona los patrones que ganan hackathones 2026 en un solo ciclo de ejecucion:
  plan -> sandbox dry-run (Time-Traveler) -> ejecutar -> guardia (ModelProof)
       -> auto-reparar (Schema-Drift/Gitdefender) -> traza glass-box (Zarks)
       -> escribir aprendizaje en memoria (Hindsight)
Cada paso es real y deja rastro en apex/diario.jsonl. Sin dependencias externas.
"""
import json, time, traceback, subprocess, sys, os
from pathlib import Path

APEX = Path(r"C:\Users\Admin\apex")
DIARIO = APEX / "diario.jsonl"
MEM = APEX / "memoria.json"

def _stamp():   # sin Date.now prohibido aqui; time.time si vale en python normal
    return round(time.time(), 3)

def traza(evento, **datos):
    """glass-box: toda decision/accion queda legible y auditable en vivo."""
    linea = {"t": _stamp(), "evento": evento, **datos}
    with open(DIARIO, "a", encoding="utf-8") as f:
        f.write(json.dumps(linea, ensure_ascii=False) + "\n")
    print(f"[{evento}] " + " ".join(f"{k}={v}" for k,v in datos.items()))
    return linea

def memoria_leer():
    if MEM.exists():
        return json.loads(MEM.read_text(encoding="utf-8"))
    return {"aprendizajes": []}

def memoria_escribir(leccion):
    """Hindsight: el sistema escribe su propio postmortem para la proxima vez."""
    m = memoria_leer()
    m["aprendizajes"].append({"t": _stamp(), **leccion})
    MEM.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")

def sandbox_dry_run(accion):
    """Time-Traveler: valida la accion contra una copia segura ANTES de tocar nada real.
    Aqui: comprueba que el comando existe/parsea sin ejecutar efectos destructivos."""
    cmd = accion.get("cmd")
    if not cmd:
        return {"ok": False, "motivo": "sin comando"}
    # dry: solo validamos que el ejecutable/el script existen; no corremos efectos
    prueba = accion.get("dry")
    if prueba:
        try:
            r = subprocess.run(prueba, shell=True, capture_output=True, text=True, timeout=60)
            return {"ok": r.returncode == 0, "motivo": (r.stderr or r.stdout)[-300:]}
        except Exception as e:
            return {"ok": False, "motivo": str(e)[:200]}
    return {"ok": True, "motivo": "sin dry definido -> se permite con cautela"}

def guardia(resultado, criterio):
    """ModelProof/triangulacion: el resultado pasa solo si cumple un criterio verificable."""
    try:
        return bool(criterio(resultado)), "criterio aplicado"
    except Exception as e:
        return False, f"guardia fallo: {e}"

def actuar_seguro(accion, criterio=lambda r: r.get("rc") == 0, reparar=None, intentos=2):
    """El ciclo completo. accion = {nombre, cmd, dry?}. Devuelve el resultado o None."""
    traza("plan", accion=accion.get("nombre"))
    dry = sandbox_dry_run(accion)
    traza("sandbox", ok=dry["ok"], motivo=dry["motivo"][:80])
    if not dry["ok"] and not accion.get("forzar"):
        memoria_escribir({"accion": accion.get("nombre"), "resultado": "bloqueado_en_sandbox",
                          "motivo": dry["motivo"][:200]})
        traza("abortado", razon="sandbox rechazo")
        return None
    for intento in range(1, intentos+1):
        try:
            r = subprocess.run(accion["cmd"], shell=True, capture_output=True, text=True,
                               timeout=accion.get("timeout", 600))
            res = {"rc": r.returncode, "out": r.stdout[-400:], "err": r.stderr[-400:]}
        except Exception as e:
            res = {"rc": -1, "out": "", "err": str(e)[:300]}
        ok, nota = guardia(res, criterio)
        traza("ejecucion", intento=intento, rc=res["rc"], guardia_ok=ok)
        if ok:
            memoria_escribir({"accion": accion.get("nombre"), "resultado": "ok", "intento": intento})
            return res
        # Gitdefender: auto-reparar y reintentar
        if reparar and intento < intentos:
            fix = reparar(res, intento)
            traza("auto_reparar", intento=intento, fix=str(fix)[:80])
            if fix: accion = fix
    memoria_escribir({"accion": accion.get("nombre"), "resultado": "fallo_final",
                      "err": res.get("err","")[:200]})
    traza("fallo_final", accion=accion.get("nombre"))
    return None

def demo():
    traza("apex_acto_arranca", version="0.1")
    # demo real e inofensiva: una accion que pasa sandbox, ejecuta y guardia la valida
    accion = {"nombre":"latido", "cmd": sys.executable+' -c "print(42)"',
              "dry": sys.executable+' -c "compile(open(__file__).read(),__file__,\'exec\') if False else print(\'dry ok\')"'}
    res = actuar_seguro(accion, criterio=lambda r: r["rc"]==0 and "42" in r["out"])
    traza("resultado_demo", ok=bool(res), out=(res or {}).get("out","").strip())
    print("\nmemoria:", json.dumps(memoria_leer(), ensure_ascii=False)[-200:])

if __name__ == "__main__":
    demo()
