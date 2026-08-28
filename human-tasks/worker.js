// get-me-money Human Task Queue
// Cloudflare Worker — serves a web UI for the human to view/complete agent-required tasks

const HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>get-me-money — Human Tasks</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#0a0e14;color:#e1e7ef;min-height:100vh;padding:1.5rem}
h1{font-size:1.6rem;margin-bottom:.3rem}
.sub{color:#6b7a8d;font-size:.85rem;margin-bottom:1.5rem}
.stats{display:flex;gap:12px;margin-bottom:1.5rem;flex-wrap:wrap}
.stat{background:#151b25;padding:12px 18px;border-radius:10px;min-width:120px}
.stat .label{color:#6b7a8d;font-size:.75rem;text-transform:uppercase;letter-spacing:.5px}
.stat .val{font-size:1.5rem;font-weight:700;margin-top:2px}
.stat .val.green{color:#34d399}
.stat .val.yellow{color:#fbbf24}
.stat .val.red{color:#f87171}
.task-list{display:flex;flex-direction:column;gap:10px}
.task{background:#151b25;border-radius:10px;padding:16px;border-left:4px solid #3b82f6;transition:opacity .3s}
.task.pending{border-left-color:#fbbf24}
.task.done{border-left-color:#34d399;opacity:.6}
.task.rejected{border-left-color:#f87171;opacity:.4}
.task-header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:8px}
.task-title{font-weight:600;font-size:1rem}
.task-meta{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px;font-size:.8rem;color:#6b7a8d}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600;text-transform:uppercase}
.badge.pending{background:#78350f;color:#fbbf24}
.badge.done{background:#064e3b;color:#34d399}
.badge.rejected{background:#7f1d1d;color:#f87171}
.badge.urgent{background:#7f1d1d;color:#fca5a5}
.task-desc{color:#9ca3af;font-size:.85rem;line-height:1.5;margin-bottom:12px}
.task-actions{display:flex;gap:8px;flex-wrap:wrap}
button{padding:8px 16px;border:none;border-radius:6px;font-size:.85rem;font-weight:600;cursor:pointer;transition:all .15s}
.btn-done{background:#059669;color:#fff}
.btn-done:hover{background:#047857}
.btn-reject{background:#dc2626;color:#fff}
.btn-reject:hover{background:#b91c1c}
.btn-claim{background:#2563eb;color:#fff}
.btn-claim:hover{background:#1d4ed8}
.btn-add{background:#7c3aed;color:#fff;position:fixed;bottom:1.5rem;right:1.5rem;padding:14px 24px;font-size:1rem;border-radius:12px;box-shadow:0 4px 20px rgba(124,58,237,.4)}
.btn-add:hover{background:#6d28d9}
.empty{text-align:center;padding:3rem;color:#4b5563}
.empty .icon{font-size:3rem;margin-bottom:1rem}
.add-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;justify-content:center;align-items:center}
.add-modal.open{display:flex}
.add-form{background:#151b25;border-radius:14px;padding:24px;width:90%;max-width:500px}
.add-form h2{margin-bottom:16px;font-size:1.2rem}
.add-form input,.add-form textarea,.add-form select{width:100%;padding:10px 12px;border:1px solid #2d3748;border-radius:8px;background:#0a0e14;color:#e1e7ef;font-size:.9rem;margin-bottom:12px;font-family:inherit}
.add-form textarea{min-height:80px;resize:vertical}
.add-form .btn-row{display:flex;gap:8px;justify-content:flex-end}
.add-form .btn-cancel{background:#374151;color:#9ca3af}
</style>
</head>
<body>
<h1>get-me-money</h1>
<div class="sub">Human task queue — actions the agent needs you to do</div>
<div class="stats" id="stats"></div>
<div class="task-list" id="tasks"></div>
<div class="empty" id="empty" style="display:none"><div class="icon">&#x2705;</div>No pending tasks</div>
<button class="btn-add" onclick="openModal()">+ Add Task</button>
<div class="add-modal" id="modal">
<div class="add-form">
<h2>Add Human Task</h2>
<input id="f-title" placeholder="Task title" required>
<textarea id="f-desc" placeholder="Description / instructions"></textarea>
<select id="f-priority"><option value="normal">Normal</option><option value="urgent">Urgent</option></select>
<select id="f-type"><option value="action">Action required</option><option value="review">Review needed</option><option value="approval">Approval needed</option></select>
<div class="btn-row">
<button class="btn-cancel" onclick="closeModal()">Cancel</button>
<button class="btn-done" onclick="addTask()">Add</button>
</div>
</div>
</div>
<script>
const API = location.origin;
let tasks = [];

async function load() {
  try {
    const r = await fetch(API + '/api/tasks');
    tasks = await r.json();
  } catch(e) { tasks = []; }
  render();
}

function render() {
  const pending = tasks.filter(t => t.status === 'pending');
  const done = tasks.filter(t => t.status === 'done');
  const el = document.getElementById('tasks');
  const empty = document.getElementById('empty');

  // Stats
  document.getElementById('stats').innerHTML =
    '<div class="stat"><div class="label">Pending</div><div class="val yellow">' + pending.length + '</div></div>' +
    '<div class="stat"><div class="label">Done</div><div class="val green">' + done.length + '</div></div>' +
    '<div class="stat"><div class="label">Total</div><div class="val">' + tasks.length + '</div></div>';

  if (tasks.length === 0) { el.innerHTML = ''; empty.style.display = 'block'; return; }
  empty.style.display = 'none';

  el.innerHTML = [...pending, ...done].map(t => {
    const time = new Date(t.created_at * 1000).toLocaleString();
    return '<div class="task ' + t.status + '">' +
      '<div class="task-header"><div class="task-title">' + esc(t.title) + '</div>' +
      '<span class="badge ' + t.status + '">' + t.status + '</span>' +
      (t.priority === 'urgent' ? '<span class="badge urgent">urgent</span>' : '') +
      '</div>' +
      '<div class="task-meta"><span>' + esc(t.type || 'action') + '</span><span>' + time + '</span>' +
      (t.agent_id ? '<span>agent: ' + esc(t.agent_id) + '</span>' : '') + '</div>' +
      (t.description ? '<div class="task-desc">' + esc(t.description) + '</div>' : '') +
      (t.status === 'pending' ? '<div class="task-actions">' +
        '<button class="btn-done" onclick="completeTask(\\'' + t.id + '\\')">Done</button>' +
        '<button class="btn-reject" onclick="rejectTask(\\'' + t.id + '\\')">Reject</button>' +
        '</div>' : '') +
      '</div>';
  }).join('');
}

function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

async function completeTask(id) {
  await fetch(API + '/api/tasks/' + id + '/complete', { method: 'POST' });
  load();
}

async function rejectTask(id) {
  const reason = prompt('Reason for rejection:');
  if (reason === null) return;
  await fetch(API + '/api/tasks/' + id + '/reject', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason })
  });
  load();
}

function openModal() { document.getElementById('modal').classList.add('open'); }
function closeModal() { document.getElementById('modal').classList.remove('open'); }

async function addTask() {
  const title = document.getElementById('f-title').value.trim();
  if (!title) return;
  await fetch(API + '/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title,
      description: document.getElementById('f-desc').value.trim(),
      priority: document.getElementById('f-priority').value,
      type: document.getElementById('f-type').value,
    })
  });
  document.getElementById('f-title').value = '';
  document.getElementById('f-desc').value = '';
  closeModal();
  load();
}

load();
setInterval(load, 10000);
</script>
</body>
</html>`;

// In-memory task store (for demo; use KV in production)
let taskStore = [];

function generateId() {
  return Math.random().toString(36).substring(2, 10);
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        }
      });
    }

    // API: GET /api/tasks
    if (path === '/api/tasks' && request.method === 'GET') {
      // Try KV first, fall back to in-memory
      let tasks = taskStore;
      try {
        const stored = await env.TASKS.get('tasks', { type: 'json' });
        if (stored) tasks = stored;
      } catch(e) {}
      return jsonResponse(tasks);
    }

    // API: POST /api/tasks
    if (path === '/api/tasks' && request.method === 'POST') {
      const body = await request.json();
      const task = {
        id: generateId(),
        title: body.title || 'Untitled task',
        description: body.description || '',
        type: body.type || 'action',
        priority: body.priority || 'normal',
        status: 'pending',
        agent_id: body.agent_id || '',
        created_at: Date.now() / 1000,
        completed_at: null,
        completed_by: null,
        result: null,
      };
      taskStore.unshift(task);
      try { await env.TASKS.put('tasks', JSON.stringify(taskStore)); } catch(e) {}
      return jsonResponse(task, 201);
    }

    // API: POST /api/tasks/:id/complete
    const completeMatch = path.match(/^\/api\/tasks\/([^/]+)\/complete$/);
    if (completeMatch && request.method === 'POST') {
      const id = completeMatch[1];
      const task = taskStore.find(t => t.id === id);
      if (!task) return jsonResponse({ error: 'not found' }, 404);
      task.status = 'done';
      task.completed_at = Date.now() / 1000;
      task.completed_by = 'human';
      try { await env.TASKS.put('tasks', JSON.stringify(taskStore)); } catch(e) {}
      return jsonResponse(task);
    }

    // API: POST /api/tasks/:id/reject
    const rejectMatch = path.match(/^\/api\/tasks\/([^/]+)\/reject$/);
    if (rejectMatch && request.method === 'POST') {
      const id = rejectMatch[1];
      const task = taskStore.find(t => t.id === id);
      if (!task) return jsonResponse({ error: 'not found' }, 404);
      const body = await request.json().catch(() => ({}));
      task.status = 'rejected';
      task.completed_at = Date.now() / 1000;
      task.completed_by = 'human';
      task.result = { reason: body.reason || 'rejected' };
      try { await env.TASKS.put('tasks', JSON.stringify(taskStore)); } catch(e) {}
      return jsonResponse(task);
    }

    // API: POST /api/tasks/:id/claim (for agent to claim)
    const claimMatch = path.match(/^\/api\/tasks\/([^/]+)\/claim$/);
    if (claimMatch && request.method === 'POST') {
      const id = claimMatch[1];
      const task = taskStore.find(t => t.id === id);
      if (!task) return jsonResponse({ error: 'not found' }, 404);
      const body = await request.json().catch(() => ({}));
      task.agent_id = body.agent_id || 'agent';
      try { await env.TASKS.put('tasks', JSON.stringify(taskStore)); } catch(e) {}
      return jsonResponse(task);
    }

    // HTML UI
    if (path === '/' || path === '') {
      return new Response(HTML, {
        headers: { 'Content-Type': 'text/html; charset=utf-8' }
      });
    }

    // Health check
    if (path === '/healthz') {
      return new Response('ok\n', { status: 200 });
    }

    return jsonResponse({ error: 'not found' }, 404);
  }
};
