import asyncio
import json
import os
import queue
import threading

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from crew import investigate, DEFAULT_INCIDENT

app = FastAPI(title="Argus")

# Public SigNoz URL used for the "view trace" link (browser-facing).
SIGNOZ_URL = os.getenv("SIGNOZ_WEB_URL", "http://localhost:8080")


@app.get("/")
async def index():
    return HTMLResponse(INDEX_HTML)


@app.get("/investigate")
async def investigate_stream(incident: str = DEFAULT_INCIDENT):
    """Run the crew in a background thread and stream its progress as SSE events."""
    q: "queue.Queue" = queue.Queue()

    def emit(stage, text):
        q.put({"stage": stage, "text": text})

    def worker():
        try:
            asyncio.run(investigate(incident, emit=emit))
        except Exception as e:
            q.put({"stage": "error", "text": str(e)})
        finally:
            q.put(None)  # sentinel = done

    threading.Thread(target=worker, daemon=True).start()

    async def event_gen():
        while True:
            try:
                item = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.15)
                continue
            if item is None:
                yield "event: done\ndata: {}\n\n"
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Argus — Agent-native SRE crew</title>
<style>
  :root{
    --bg:#080a10; --bg2:#0e1220; --card:#12172180; --line:#222a3a; --line2:#2c3547;
    --txt:#eef1f7; --muted:#8892a6; --accent:#ff6a3d; --accent2:#ffb020;
    --ok:#38d39f; --err:#ff5d6c; --mcp:#5b8cff;
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{
    background:
      radial-gradient(1100px 500px at 50% -10%, #17203a55, transparent 60%),
      radial-gradient(800px 400px at 90% 10%, #2a143355, transparent 60%),
      var(--bg);
    color:var(--txt);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:1000px;margin:0 auto;padding:40px 22px 90px}
  .brand{display:flex;align-items:center;gap:12px;margin-bottom:6px}
  .eye{font-size:34px;filter:drop-shadow(0 0 10px #ff6a3d88)}
  h1{font-size:30px;margin:0;letter-spacing:-.02em}
  .tag{color:var(--muted);margin:2px 0 26px;font-size:15px}
  .tag b{color:var(--accent2);font-weight:600}

  form{display:flex;gap:10px;margin-bottom:10px}
  input{flex:1;padding:14px 16px;background:#0d111c;border:1px solid var(--line2);
        border-radius:12px;color:var(--txt);font-size:14px;outline:none}
  input:focus{border-color:var(--accent)}
  button{padding:14px 22px;background:linear-gradient(180deg,#ff7a4d,#ef5a2c);color:#fff;
         border:none;border-radius:12px;font-size:14px;font-weight:700;cursor:pointer;
         box-shadow:0 6px 20px #ef5a2c44}
  button:disabled{filter:grayscale(.4) brightness(.7);cursor:not-allowed;box-shadow:none}
  .status{color:var(--muted);font-size:13px;margin:10px 2px 26px;min-height:18px;
          display:flex;align-items:center;gap:8px}

  /* ---- pipeline flow ---- */
  .flow{display:flex;align-items:center;justify-content:center;gap:6px;flex-wrap:wrap;
        padding:22px 10px;border:1px solid var(--line);border-radius:16px;
        background:linear-gradient(180deg,#0d1220aa,#0a0e18aa);margin-bottom:10px}
  .node{position:relative;min-width:118px;padding:14px 12px;border-radius:14px;
        border:1px solid var(--line2);background:#0d121e;text-align:center;
        transition:.3s;opacity:.55}
  .node .ico{font-size:22px;line-height:1}
  .node .lbl{font-size:12.5px;margin-top:6px;color:#cdd4e2;font-weight:600}
  .node .sub{font-size:10.5px;color:var(--muted);margin-top:2px}
  .node .dot{position:absolute;top:9px;right:9px;width:8px;height:8px;border-radius:50%;
             background:#39435a}
  .node.active{opacity:1;border-color:var(--accent);box-shadow:0 0 0 1px #ff6a3d55,0 0 26px #ff6a3d22}
  .node.active .dot{background:var(--accent);animation:pulse 1s infinite}
  .node.done{opacity:1;border-color:#25405f}
  .node.done .dot{background:var(--ok)}
  .node.err{opacity:1;border-color:var(--err);box-shadow:0 0 0 1px #ff5d6c55,0 0 26px #ff5d6c22}
  .node.err .dot{background:var(--err)}
  .node.mcp.active{border-color:var(--mcp);box-shadow:0 0 0 1px #5b8cff55,0 0 26px #5b8cff22}
  .node.mcp.active .dot{background:var(--mcp)}
  .edge{width:26px;height:2px;background:linear-gradient(90deg,#2a3348,#39435a);border-radius:2px}
  .edge.on{background:linear-gradient(90deg,var(--accent),var(--accent2))}
  .branch{display:flex;justify-content:center;margin:-2px 0 26px}
  .branch .vwrap{display:flex;flex-direction:column;align-items:center}
  .branch .vline{width:2px;height:20px;background:#2a3348}
  .branch .vline.on{background:var(--mcp)}
  @keyframes pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.5);opacity:.5}}

  /* ---- agent cards ---- */
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;
        padding:16px 18px;margin-bottom:14px;opacity:.5;transition:.3s;
        backdrop-filter:blur(6px)}
  .card.active{opacity:1;border-color:var(--accent)}
  .card.done{opacity:1}
  .card.err{opacity:1;border-color:var(--err)}
  .card h3{margin:0 0 10px;font-size:15px;display:flex;align-items:center;gap:9px}
  .badge{font-size:11px;color:var(--muted);border:1px solid var(--line2);
         padding:2px 9px;border-radius:20px;font-weight:500}
  .body{white-space:pre-wrap;font-size:13.5px;line-height:1.55;color:#d6dbe6}
  .tools{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;margin-bottom:10px}
  .tool-line{padding:3px 0;color:var(--ok)}
  .tool-line.bad{color:var(--err)}
  a.signoz{display:none;margin-top:6px;color:var(--accent);font-size:13.5px;font-weight:600;
           text-decoration:none}
  a.signoz:hover{text-decoration:underline}
  .foot{color:#5b647a;font-size:12px;margin-top:34px;text-align:center}
  .spinner{width:12px;height:12px;border:2px solid var(--line2);border-top-color:var(--accent);
           border-radius:50%;animation:spin .8s linear infinite;display:inline-block}
  @keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="wrap">
  <div class="brand"><span class="eye">👁️</span><h1>Argus</h1></div>
  <p class="tag">An agent-native SRE crew that investigates your system — <b>observed by SigNoz while it works through SigNoz</b>.</p>

  <form id="f">
    <input id="incident"
      value="The checkout experience feels slow. Investigate system health and find any services that are unhealthy or erroring."/>
    <button id="go" type="submit">Investigate</button>
  </form>
  <div class="status" id="status"></div>

  <!-- pipeline -->
  <div class="flow">
    <div class="node" id="n-incident"><div class="ico">📥</div><div class="lbl">Incident</div><div class="dot"></div></div>
    <div class="edge" id="e-1"></div>
    <div class="node" id="n-triage"><div class="ico">🧭</div><div class="lbl">Triage</div><div class="sub">plan</div><div class="dot"></div></div>
    <div class="edge" id="e-2"></div>
    <div class="node" id="n-investigator"><div class="ico">🔍</div><div class="lbl">Investigator</div><div class="sub">gather evidence</div><div class="dot"></div></div>
    <div class="edge" id="e-3"></div>
    <div class="node" id="n-reporter"><div class="ico">📋</div><div class="lbl">Reporter</div><div class="sub">write report</div><div class="dot"></div></div>
    <div class="edge" id="e-4"></div>
    <div class="node" id="n-report"><div class="ico">✅</div><div class="lbl">Report</div><div class="dot"></div></div>
  </div>
  <div class="branch">
    <div class="vwrap">
      <div class="vline" id="vline"></div>
      <div class="node mcp" id="n-mcp"><div class="ico">🗄️</div><div class="lbl">SigNoz MCP</div><div class="sub">traces · logs · metrics</div><div class="dot"></div></div>
    </div>
  </div>

  <!-- detail cards -->
  <div class="card" id="c-triage">
    <h3>🧭 Triage <span class="badge">plans the investigation</span></h3>
    <div class="body" id="b-triage"></div>
  </div>
  <div class="card" id="c-investigator">
    <h3>🔍 Investigator <span class="badge">queries SigNoz via MCP</span></h3>
    <div class="tools" id="tools"></div>
    <div class="body" id="b-investigator"></div>
  </div>
  <div class="card" id="c-reporter">
    <h3>📋 Reporter <span class="badge">writes the incident report</span></h3>
    <div class="body" id="b-reporter"></div>
  </div>

  <a class="signoz" id="signoz" href="__SIGNOZ__/traces-explorer" target="_blank">→ View this run's trace in SigNoz</a>

  <div class="foot">Argus emits open OpenTelemetry spans · SigNoz is the backend, nothing is locked in.</div>
</div>

<script>
const $ = (id)=>document.getElementById(id);
const cards={triage:"c-triage",investigator:"c-investigator",reporter:"c-reporter"};
const order=["triage","investigator","reporter"];
const setNode=(id,cls)=>{ $("n-"+id).className = "node"+(id==="mcp"?" mcp":"")+(cls?" "+cls:""); };

function reset(){
  ["incident","triage","investigator","reporter","report","mcp"].forEach(n=>setNode(n,""));
  ["1","2","3","4"].forEach(i=>$("e-"+i).className="edge");
  $("vline").className="vline";
  setNode("incident","done"); setNode("triage","active"); $("e-1").className="edge on";
  order.forEach(s=>{$("b-"+s).textContent="";$(cards[s]).className="card";});
  $(cards.triage).className="card active";
  $("tools").innerHTML=""; $("signoz").style.display="none";
}

function isEmpty(t){ return !t || !t.trim() || t.includes("(no answer produced)"); }

$("f").addEventListener("submit",(e)=>{
  e.preventDefault();
  $("go").disabled=true;
  $("status").innerHTML='<span class="spinner"></span> Crew running… local model, ~2–4 min';
  reset();
  let toolFailed=false;

  const es=new EventSource("/investigate?incident="+encodeURIComponent($("incident").value));

  es.onmessage=(ev)=>{
    const d=JSON.parse(ev.data);
    if(d.stage==="tool"){
      const t=d.text; // {agent, tool, ok}
      setNode("mcp", t.ok? "active":"err"); $("vline").className="vline on";
      if(!t.ok) toolFailed=true;
      const line=document.createElement("div");
      line.className="tool-line"+(t.ok?"":" bad");
      line.textContent=(t.ok?"⛁ ":"✗ ")+t.tool;
      $("tools").appendChild(line);
    } else if(d.stage==="error"){
      $("status").textContent="⚠ "+d.text;
    } else if(cards[d.stage]){
      const bad=isEmpty(d.text);
      $("b-"+d.stage).textContent = bad ? "(no output — this step produced nothing)" : d.text;
      $(cards[d.stage]).className = "card "+(bad?"err":"done");
      setNode(d.stage, bad?"err":"done");
      const i=order.indexOf(d.stage);
      $("e-"+(i+2)).className="edge on";
      if(d.stage==="investigator"){ setNode("mcp", toolFailed?"err":"done"); }
      const next=order[i+1];
      if(next){ $(cards[next]).className="card active"; setNode(next,"active"); }
      else { setNode("report","done"); }
    }
  };

  es.addEventListener("done",()=>{
    es.close(); $("go").disabled=false;
    $("status").textContent="✓ Investigation complete.";
    $("signoz").style.display="inline-block";
  });
  es.onerror=()=>{ es.close(); $("go").disabled=false; };
});
</script>
</body>
</html>
""".replace("__SIGNOZ__", SIGNOZ_URL)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8500")),
    )
