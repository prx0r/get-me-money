"""Minimal read-only dashboard. Binds localhost by default."""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from get_me_money.dashboard import get_dashboard_data
from get_me_money.ledger import load_attempts, load_opportunities

HTML = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>get-me-money</title><style>body{font-family:system-ui;margin:2rem;max-width:1100px;background:#0e1116;color:#e7edf3}h1{margin-bottom:.2rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.card{background:#171c24;padding:16px;border-radius:10px}.n{font-size:1.7rem;font-weight:700}table{width:100%;border-collapse:collapse;margin-top:1rem}td,th{text-align:left;padding:8px;border-bottom:1px solid #2b3441;font-size:.9rem}.good{color:#65d487}.bad{color:#ff7c7c}.muted{color:#93a1b2}</style></head>
<body><h1>get-me-money</h1><div class="muted">autonomous earning ledger · refreshes every 15s</div><div id="cards" class="grid"></div><h2>Recent attempts</h2><table><thead><tr><th>status</th><th>platform</th><th>task</th><th>cost</th><th>earned</th><th>net</th></tr></thead><tbody id="rows"></tbody></table>
<script>async function load(){let s=await fetch('/api/status').then(r=>r.json());let a=await fetch('/api/attempts').then(r=>r.json());let vals=[['Net','$'+s.net_earned.toFixed(4)],['Gross','$'+s.gross_earned.toFixed(4)],['Cost','$'+s.total_cost.toFixed(4)],['Wins',s.successes],['Pending',s.pending],['Seen',s.opportunities_seen]];cards.innerHTML=vals.map(x=>`<div class=card><div class=muted>${x[0]}</div><div class=n>${x[1]}</div></div>`).join('');rows.innerHTML=a.slice(-30).reverse().map(x=>`<tr><td>${x.outcome}</td><td>${x.platform}</td><td>${esc(x.title)}</td><td>$${Number(x.cost).toFixed(4)}</td><td>$${Number(x.reward).toFixed(4)}</td><td class=${x.net>=0?'good':'bad'}>$${Number(x.net).toFixed(4)}</td></tr>`).join('')} function esc(s){let d=document.createElement('div');d.textContent=s||'';return d.innerHTML}load();setInterval(load,15000)</script></body></html>'''


def _attempt_json(a):
    return {"id": a.id, "platform": a.platform.value, "title": a.title, "outcome": a.outcome.value, "reward": a.reward, "cost": a.cost, "fees": a.fees, "net": a.net, "error": a.error, "started_at": a.started_at, "updated_at": a.updated_at}


class Handler(BaseHTTPRequestHandler):
    def _authorized(self) -> bool:
        token = os.getenv("GMM_DASHBOARD_TOKEN", "")
        return not token or self.headers.get("Authorization") == f"Bearer {token}"

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/healthz": return self._send(200, b"ok\n", "text/plain")
        if not self._authorized(): return self._send(401, b'{"error":"unauthorized"}', "application/json")
        if path == "/": return self._send(200, HTML.encode(), "text/html; charset=utf-8")
        if path == "/api/status": data = get_dashboard_data()
        elif path == "/api/attempts": data = [_attempt_json(a) for a in load_attempts()]
        elif path == "/api/opportunities": data = [{"id":o.id,"platform":o.platform.value,"title":o.title,"reward":o.reward,"currency":o.currency,"url":o.url} for o in load_opportunities()]
        else: return self._send(404, b'{"error":"not found"}', "application/json")
        return self._send(200, json.dumps(data).encode(), "application/json")

    def log_message(self, fmt, *args):
        return


def main():
    p = argparse.ArgumentParser(); p.add_argument("--host", default="127.0.0.1"); p.add_argument("--port", type=int, default=8787); a = p.parse_args()
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()

if __name__ == "__main__": main()
