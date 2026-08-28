"""Dashboard with human tasks. Binds 0.0.0.0:8787."""
from __future__ import annotations

import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from get_me_money.dashboard import get_dashboard_data
from get_me_money.ledger import load_attempts, load_opportunities
from get_me_money.human_tasks import get_pending, get_all, create_task, complete_task, reject_task, batch_summary


def _attempt_json(a):
    return {"id": a.id, "platform": a.platform.value, "title": a.title, "outcome": a.outcome.value, "reward": a.reward, "cost": a.cost, "fees": a.fees, "net": a.net, "error": a.error, "started_at": a.started_at, "updated_at": a.updated_at}


HTML = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>moltwork</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#0a0e14;color:#e1e7ef;min-height:100vh;padding:1.5rem}
h1{font-size:1.8rem;margin-bottom:.2rem}
h2{font-size:1.1rem;margin:1.5rem 0 .8rem;color:#9ca3af}
.sub{color:#6b7a8d;font-size:.85rem;margin-bottom:1.5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:1.5rem}
.card{background:#151b25;padding:16px;border-radius:10px}
.card .label{color:#6b7a8d;font-size:.75rem;text-transform:uppercase;letter-spacing:.5px}
.card .val{font-size:1.6rem;font-weight:700;margin-top:2px}
.good{color:#34d399}.bad{color:#f87171}.muted{color:#6b7a8d}
table{width:100%;border-collapse:collapse}
td,th{text-align:left;padding:8px;border-bottom:1px solid #2b3441;font-size:.85rem}
th{color:#6b7a8d;font-size:.75rem;text-transform:uppercase}
.task{background:#151b25;border-radius:10px;padding:16px;margin-bottom:10px;border-left:4px solid #fbbf24}
.task.done{border-left-color:#34d399;opacity:.6}
.task.rejected{border-left-color:#f87171;opacity:.4}
.task-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.task-title{font-weight:600}
.badge{padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600;text-transform:uppercase}
.badge.pending{background:#78350f;color:#fbbf24}
.badge.done{background:#064e3b;color:#34d399}
.badge.auth{background:#1e3a5f;color:#60a5fa}
.badge.payment{background:#064e3b;color:#34d399}
.badge.approval{background:#3b0764;color:#c084fc}
.btn{padding:6px 14px;border:none;border-radius:6px;font-size:.8rem;font-weight:600;cursor:pointer}
.btn-done{background:#059669;color:#fff}.btn-done:hover{background:#047857}
.btn-reject{background:#374151;color:#9ca3af}.btn-reject:hover{background:#4b5563}
.progress{height:6px;background:#1f2937;border-radius:3px;margin-top:8px;overflow:hidden}
.progress-bar{height:100%;background:linear-gradient(90deg,#3b82f6,#8b5cf6);border-radius:3px;transition:width .3s}
.tab-bar{display:flex;gap:4px;margin-bottom:1.5rem}
.tab{padding:8px 16px;border-radius:8px;cursor:pointer;font-size:.85rem;color:#6b7a8d;background:#151b25;border:none}
.tab.active{background:#1f2937;color:#e1e7ef}
</style>
</head>
<body>
<h1>moltwork</h1>
<div class="sub">from agent to paid worker</div>

<div class="tab-bar">
<button class="tab active" onclick="showTab('home')">Home</button>
<button class="tab" onclick="showTab('tasks')">Needs You <span id="task-count"></span></button>
<button class="tab" onclick="showTab('jobs')">Jobs</button>
</div>

<div id="tab-home">
<div class="grid" id="cards"></div>
<h2>Recent attempts</h2>
<table><thead><tr><th>status</th><th>platform</th><th>task</th><th>cost</th><th>earned</th><th>net</th></tr></thead><tbody id="rows"></tbody></table>
</div>

<div id="tab-tasks" style="display:none">
<h2 style="margin-top:0">Needs You</h2>
<div id="human-tasks"></div>
</div>

<div id="tab-jobs" style="display:none">
<h2 style="margin-top:0">Opportunities</h2>
<table><thead><tr><th>platform</th><th>task</th><th>reward</th><th>ev</th><th>p(win)</th><th>status</th></tr></thead><tbody id="job-rows"></tbody></table>
</div>

<script>
let currentTab='home';
function showTab(t){currentTab=t;document.querySelectorAll('.tab').forEach((el,i)=>{el.classList.toggle('active',['home','tasks','jobs'][i]===t)});document.getElementById('tab-home').style.display=t==='home'?'':'none';document.getElementById('tab-tasks').style.display=t==='tasks'?'':'none';document.getElementById('tab-jobs').style.display=t==='jobs'?'':'none';if(t==='tasks')loadTasks();if(t==='jobs')loadJobs()}
function esc(s){let d=document.createElement('div');d.textContent=s||'';return d.innerHTML}
async function load(){
try{
let s=await fetch('/api/status').then(r=>r.json());
let a=await fetch('/api/attempts').then(r=>r.json());
let vals=[['Net','$'+s.net_earned.toFixed(2)],['Gross','$'+s.gross_earned.toFixed(2)],['Cost','$'+s.total_cost.toFixed(2)],['Wins',s.successes],['Pending',s.pending],['Scanned',s.opportunities_seen]];
document.getElementById('cards').innerHTML=vals.map(x=>'<div class="card"><div class="label">'+x[0]+'</div><div class="val">'+x[1]+'</div></div>').join('');
document.getElementById('rows').innerHTML=a.slice(-20).reverse().map(x=>'<tr><td><span class="badge '+(x.outcome==='succeeded'?'done':'pending')+'">'+x.outcome+'</span></td><td>'+x.platform+'</td><td>'+esc(x.title)+'</td><td>$'+Number(x.cost).toFixed(4)+'</td><td>$'+Number(x.reward).toFixed(4)+'</td><td class="'+(x.net>=0?'good':'bad')+'">$'+Number(x.net).toFixed(4)+'</td></tr>').join('');
}catch(e){}}
async function loadTasks(){
try{
let t=await fetch('/api/human-tasks').then(r=>r.json());
document.getElementById('task-count').textContent=t.length?' ('+t.length+')':'';
document.getElementById('human-tasks').innerHTML=t.length?t.map(x=>'<div class="task '+(x.status==='done'?'done':'')+'"><div class="task-header"><div class="task-title">'+esc(x.title)+'</div><div><span class="badge '+x.status+'">'+x.status+'</span> <span class="badge '+x.type+'">'+x.type+'</span></div></div>'+(x.description?'<div class="muted" style="margin:6px 0;font-size:.85rem">'+esc(x.description)+'</div>':'')+(x.agent_progress&&x.agent_progress.length?'<div class="muted" style="font-size:.8rem">agent did: '+x.agent_progress.join(' → ')+'</div>':'')+(x.status==='pending'?'<div style="margin-top:8px"><button class="btn btn-done" onclick="resolveTask(\\''+x.id+'\\',\\''+x.resume_event+'\\')">Done</button> <button class="btn btn-reject" onclick="rejectT(\\''+x.id+'\\')">Reject</button></div>':'')+'</div>').join(''):'<div class="muted" style="padding:2rem;text-align:center">No pending tasks</div>';
}catch(e){}}
async function loadJobs(){
try{
let q=await fetch('/api/queue').then(r=>r.json());
document.getElementById('job-rows').innerHTML=(q.jobs||[]).slice(0,20).map(j=>'<tr><td>'+j.platform+'</td><td>'+esc(j.title)+'</td><td>$'+j.reward.toFixed(2)+'</td><td class="'+(j.ev_cash>0?'good':'bad')+'">$'+j.ev_cash.toFixed(4)+'</td><td>'+(j.p_success*100).toFixed(0)+'%</td><td>'+(j.should_attempt?'<span class="badge done">GO</span>':'<span class="badge pending">SKIP</span>')+'</td></tr>').join('');
}catch(e){}}
async function resolveTask(id,evt){
await fetch('/api/human-tasks/'+id+'/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({resume_event:evt})});
loadTasks();}
async function rejectT(id){
let r=prompt('Reason:');if(r===null)return;
await fetch('/api/human-tasks/'+id+'/reject',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:r})});
loadTasks();}
load();setInterval(load,10000);
</script>
</body></html>'''


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())

    def _json(self, data, code=200):
        self._send(code, json.dumps(data, default=str))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/healthz": return self._send(200, b"ok\n", "text/plain")
        if path == "/": return self._send(200, HTML.encode(), "text/html; charset=utf-8")
        if path == "/api/status": return self._json(get_dashboard_data())
        if path == "/api/attempts": return self._json([_attempt_json(a) for a in load_attempts()])
        if path == "/api/human-tasks": return self._json(get_pending())
        if path == "/api/queue":
            qpath = Path(os.getenv("GMM_DATA_DIR", "data")) / "oracle-queue.json"
            if qpath.exists():
                return self._json(json.loads(qpath.read_text()))
            return self._json({"jobs": []})
        if path == "/api/opportunities":
            return self._json([{"id":o.id,"platform":o.platform.value,"title":o.title,"reward":o.reward} for o in load_opportunities()])
        self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        path = urlparse(self.path).path
        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len)) if content_len > 0 else {}

        # Complete task
        m = __import__("re").match(r"^/api/human-tasks/([^/]+)/complete$", path)
        if m:
            task = complete_task(m.group(1), body)
            if task:
                return self._json(task)
            return self._json({"error": "not found"}, 404)

        # Reject task
        m = __import__("re").match(r"^/api/human-tasks/([^/]+)/reject$", path)
        if m:
            task = reject_task(m.group(1), body.get("reason", ""))
            if task:
                return self._json(task)
            return self._json({"error": "not found"}, 404)

        # Create task
        if path == "/api/human-tasks":
            task = create_task(
                body.get("title", ""),
                body.get("description", ""),
                task_type=body.get("type", "approval"),
                priority=body.get("priority", "normal"),
                estimated_value=body.get("estimated_value", 0),
            )
            return self._json(task, 201)

        self._send(404, b'{"error":"not found"}')

    def log_message(self, fmt, *args):
        return


def main():
    from pathlib import Path
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8787)
    a = p.parse_args()
    print(f"moltwork dashboard live on http://{a.host}:{a.port}")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()

if __name__ == "__main__":
    main()
