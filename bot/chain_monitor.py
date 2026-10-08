# -*- coding: utf-8 -*-
"""
APEX chain_monitor - infraestructura VIVA conectada a la blockchain.
Se suscribe por WebSocket a Alchemy (Arbitrum) a los eventos Swap de TODA la cadena
en tiempo real, los decodifica, mide el flujo, y detecta dislocaciones mecanicamente.
Sirve un panel que se MUEVE (no una foto) + un endpoint JSON en vivo.
  python chain_monitor.py   ->   http://localhost:8711
"""
import json, threading, time, os, collections
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import websocket  # websocket-client

KEY = os.environ.get("ALCHEMY_KEY", "XZ-qNgdCcEZP5gBNxCb_V")
WS  = f"wss://arb-mainnet.g.alchemy.com/v2/{KEY}"

# topics de eventos
SWAP_V3 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"  # UniV3 Swap
SWAP_V2 = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"  # UniV2 Swap

STATE = {
    "block": 0, "swaps_total": 0, "swaps_window": collections.deque(maxlen=2000),
    "recent": collections.deque(maxlen=40), "pools": collections.Counter(),
    "started": None, "big": collections.deque(maxlen=12),
}
LOCK = threading.Lock()

def h2int(x):
    try: return int(x, 16)
    except: return 0

def s256(h):  # hex -> int con signo (256 bits)
    v = int(h, 16)
    return v - (1 << 256) if v >= (1 << 255) else v

def on_open(ws):
    for i, topic in enumerate([SWAP_V3, SWAP_V2]):
        ws.send(json.dumps({"jsonrpc":"2.0","id":10+i,"method":"eth_subscribe",
                            "params":["logs", {"topics":[topic]}]}))
    ws.send(json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_subscribe","params":["newHeads"]}))

def on_msg(ws, m):
    try: d = json.loads(m)
    except: return
    if d.get("method") != "eth_subscription": return
    r = d["params"]["result"]
    now = time.time()
    with LOCK:
        if isinstance(r, dict) and "number" in r and "parentHash" in r:
            STATE["block"] = h2int(r["number"]); return
        if isinstance(r, dict) and "topics" in r:
            pool = r.get("address","")[:42]
            data = r.get("data","0x")[2:]
            # tamano aproximado del swap (magnitud de los campos de data)
            mag = 0
            try:
                for i in range(0, min(len(data), 256), 64):
                    mag = max(mag, abs(s256("0x"+data[i:i+64])))
            except: pass
            STATE["swaps_total"] += 1
            STATE["swaps_window"].append(now)
            STATE["pools"][pool] += 1
            ver = "V3" if r["topics"][0].lower()==SWAP_V3 else "V2"
            ev = {"pool":pool, "ver":ver, "mag":mag, "blk":STATE["block"], "t":round(now,1)}
            STATE["recent"].appendleft(ev)
            if mag > 10**22:  # flujo grande (heuristico)
                STATE["big"].appendleft(ev)

def listen():
    while True:
        try:
            ws = websocket.WebSocketApp(WS, on_open=on_open, on_message=on_msg)
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except Exception as e:
            print("ws reconnect:", str(e)[:80])
        time.sleep(2)

def live_json():
    with LOCK:
        now = time.time()
        w = [t for t in STATE["swaps_window"] if now - t <= 10]
        sps = round(len(w)/10.0, 1)
        top = STATE["pools"].most_common(6)
        return {
            "block": STATE["block"], "swaps_total": STATE["swaps_total"],
            "swaps_per_sec": sps, "uptime": int(now-(STATE["started"] or now)),
            "recent": list(STATE["recent"])[:24],
            "top_pools": [{"pool":p,"n":n} for p,n in top],
            "big": list(STATE["big"])[:10],
        }

PAGE = """<!doctype html><html><head><meta charset=utf-8>
<title>APEX · Live Chain Monitor</title><meta name=viewport content="width=device-width,initial-scale=1">
<style>
:root{--ink:#070A0F;--pan:#0E141C;--ln:#1E2A38;--fg:#E8EEF4;--mut:#7E8CA0;--sig:#34E5C6;--val:#F6B452;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--ink);color:var(--fg);font-family:var(--mono);font-size:13px}
.wrap{max-width:1000px;margin:0 auto;padding:18px}
.hd{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--ln);padding-bottom:12px}
.hd b{letter-spacing:.14em}.dot{color:var(--sig);animation:b 1.2s infinite}@keyframes b{50%{opacity:.3}}
.k{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:16px 0}
@media(max-width:620px){.k{grid-template-columns:repeat(2,1fr)}}
.c{background:var(--pan);border:1px solid var(--ln);border-radius:10px;padding:14px}
.c .l{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.1em}
.c .v{font-size:26px;margin-top:6px}.c .v.s{color:var(--sig)}.c .v.g{color:var(--val)}
h3{color:var(--mut);font-size:11px;letter-spacing:.14em;text-transform:uppercase;margin:22px 0 8px}
.feed{background:var(--pan);border:1px solid var(--ln);border-radius:10px;max-height:340px;overflow:auto}
.rowh,.row{display:grid;grid-template-columns:70px 44px 1fr 110px;gap:8px;padding:8px 12px;border-bottom:1px solid var(--ln)}
.rowh{color:var(--mut);font-size:10px;text-transform:uppercase;position:sticky;top:0;background:var(--pan)}
.row:last-child{border-bottom:0}.row .p{color:var(--mut);overflow:hidden;text-overflow:ellipsis}
.new{animation:f 1s}@keyframes f{from{background:rgba(52,229,198,.14)}to{background:transparent}}
.v3{color:var(--sig)}.v2{color:var(--val)}.big{color:var(--val);font-weight:700}
</style></head><body><div class=wrap>
<div class=hd><b>◆ APEX · LIVE CHAIN MONITOR</b><span><span class=dot>●</span> arbitrum · alchemy ws</span></div>
<div class=k>
 <div class=c><div class=l>Block</div><div class="v s" id=block>—</div></div>
 <div class=c><div class=l>Swaps / sec</div><div class="v" id=sps>—</div></div>
 <div class=c><div class=l>Swaps seen</div><div class="v g" id=tot>—</div></div>
 <div class=c><div class=l>Uptime</div><div class=v id=up>—</div></div>
</div>
<h3>Live swap feed (every DEX swap on-chain, as it lands)</h3>
<div class=feed><div class=rowh><span>block</span><span>dex</span><span>pool</span><span>magnitude</span></div>
<div id=feed></div></div>
<h3>Hottest pools (last window)</h3><div class=feed id=pools style="max-height:160px"></div>
<p style="color:var(--mut);font-size:11px">Infraestructura viva. Lee el flujo confirmado de la cadena en tiempo real.
Las dislocaciones grandes se marcan en <span class=big>ámbar</span>. Esto es la capa base real — no una foto.</p>
</div>
<script>
let seen=new Set();
function mag(x){x=Number(x);if(!x)return"·";const u=["","K","M","B","T","Qa","Qi"];let i=0;x/=1e18;while(x>=1000&&i<6){x/=1000;i++}return x.toFixed(1)+u[i]}
async function tick(){
 try{const d=await (await fetch("/live")).json();
 block.textContent=d.block.toLocaleString();sps.textContent=d.swaps_per_sec;
 tot.textContent=d.swaps_total.toLocaleString();up.textContent=d.uptime+"s";
 feed.innerHTML=d.recent.map(e=>{const id=e.pool+e.t+e.mag;const nw=!seen.has(id);seen.add(id);
   return `<div class="row ${nw?'new':''}"><span>${e.blk}</span><span class="${e.ver=='V3'?'v3':'v2'}">${e.ver}</span>`+
   `<span class=p>${e.pool}</span><span class="${e.mag>1e22?'big':''}">${mag(e.mag)}</span></div>`}).join("");
 pools.innerHTML=d.top_pools.map(p=>`<div class=row style="grid-template-columns:1fr 60px"><span class=p>${p.pool}</span><span>${p.n}</span></div>`).join("");
 }catch(e){}
}
setInterval(tick,1000);tick();
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        if self.path.startswith("/live"):
            b=json.dumps(live_json()).encode()
            self.send_response(200);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(b)
        else:
            b=PAGE.encode("utf-8")
            self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.end_headers();self.wfile.write(b)

if __name__=="__main__":
    STATE["started"]=time.time()
    threading.Thread(target=listen,daemon=True).start()
    print("APEX chain monitor VIVO -> http://localhost:8711  (Ctrl+C para parar)")
    ThreadingHTTPServer(("0.0.0.0",8711), H).serve_forever()
