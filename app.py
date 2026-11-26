"""AgentTown: zero-dependency Agent Civilization prototype.
Run: python app.py | Open: http://localhost:8000
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from datetime import datetime, timezone
import json
import sqlite3

DB_PATH = "agenttown.db"
AGENTS = [
    ("mayor", "Mayor", "Coordinator", "Keeps the civilization organized."),
    ("researcher", "Researcher", "Research", "Collects and summarizes knowledge."),
    ("developer", "Developer", "Engineering", "Builds and improves tools."),
    ("designer", "Designer", "Design", "Improves the citizen experience."),
    ("auditor", "Auditor", "Governance", "Reviews work for clarity and safety."),
]

def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL,
            description TEXT NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '', agent_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'proposed', created_at TEXT NOT NULL,
            FOREIGN KEY(agent_id) REFERENCES agents(id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT NOT NULL,
            created_at TEXT NOT NULL)""")
        conn.executemany(
            "INSERT OR IGNORE INTO agents(id,name,role,description) VALUES (?,?,?,?)",
            AGENTS)
        if conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
            conn.execute("INSERT INTO events(message,created_at) VALUES (?,?)",
                         ("AgentTown founded. Five founding agents joined the council.", timestamp()))

def record_event(message):
    with db() as conn:
        conn.execute("INSERT INTO events(message,created_at) VALUES (?,?)",
                     (message, timestamp()))

def snapshot():
    with db() as conn:
        agents = [dict(r) for r in conn.execute("SELECT * FROM agents ORDER BY rowid")]
        tasks = [dict(r) for r in conn.execute(
            "SELECT tasks.*, agents.name AS agent_name FROM tasks "
            "JOIN agents ON agents.id=tasks.agent_id ORDER BY tasks.id DESC")]
        events = [dict(r) for r in conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT 25")]
    return {"agents": agents, "tasks": tasks, "events": events}

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgentTown — Agent Civilization</title>
<style>
:root{color-scheme:dark;font-family:Inter,system-ui,Arial;color:#edf2ff;background:#0d1422}
*{box-sizing:border-box}body{margin:0}.shell{max-width:1120px;margin:auto;padding:30px 20px}
header{display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap}
h1{font-size:30px;margin:0}h2{font-size:18px;margin:0 0 16px}.muted{color:#9eabc2;font-size:13px}
.sub{margin-top:6px;color:#9eabc2}.live{border:1px solid #285b4c;color:#9ce4c5;padding:7px 12px;border-radius:30px;font-size:12px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:24px 0}
.panel,.stat{background:#151f31;border:1px solid #29364d;border-radius:15px;padding:18px}
.stat strong{display:block;font-size:28px;margin-bottom:4px}.agents{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:10px}
.agent{background:#101a2b;border:1px solid #29364d;border-radius:11px;padding:13px}
.agent b{display:block;margin-bottom:5px}.role{font-size:12px;color:#9abaff}
button{border:0;border-radius:9px;padding:10px 14px;background:#9ab7ff;color:#10182a;font-weight:700;cursor:pointer}
button.alt{background:#293750;color:#edf2ff}button.small{padding:7px 10px;font-size:12px;margin:5px 0 0 5px}
.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:16px}.grid{display:grid;grid-template-columns:1.35fr 1fr;gap:14px;margin-top:14px}
input,textarea,select{width:100%;background:#0e1727;color:#edf2ff;border:1px solid #34435e;border-radius:8px;padding:10px;margin:6px 0 13px}
textarea{min-height:75px;resize:vertical}.task{display:flex;justify-content:space-between;gap:12px;padding:13px 0;border-top:1px solid #29364d}
.task:first-child{border-top:0}.task h3{font-size:14px;margin:0 0 5px}.task p{font-size:13px;color:#aab6ca;margin:0 0 7px}
.tag{font-size:11px;border-radius:20px;padding:4px 8px;background:#293750;white-space:nowrap}
.proposed{color:#ffd58b}.approved{color:#9ce4c5}.completed{color:#b8c7ff}
.event{padding:9px 0;border-top:1px solid #29364d;font-size:13px}.event:first-child{border-top:0}
@media(max-width:720px){.grid{grid-template-columns:1fr}.stats{grid-template-columns:repeat(3,1fr)}.stat{padding:12px}.stat strong{font-size:22px}.task{display:block}}
</style></head><body><main class="shell">
<header><div><h1>🏙️ AgentTown</h1><div class="sub">Agent Civilization · First local prototype</div></div><span class="live">● LOCAL PROTOTYPE</span></header>
<section class="stats"><div class="stat"><strong id="agent-count">5</strong><span class="muted">Founding agents</span></div>
<div class="stat"><strong id="task-count">0</strong><span class="muted">Total tasks</span></div>
<div class="stat"><strong id="done-count">0</strong><span class="muted">Completed</span></div></section>
<section class="panel"><h2>Founding Council</h2><div class="agents" id="agents"></div>
<div class="actions"><button onclick="runCouncil()">Run council</button><button class="alt" onclick="refresh()">Refresh</button></div>
<p class="muted">Demo agents create proposals. Human approval is required before completion.</p></section>
<div class="grid"><section class="panel"><h2>Task Market</h2><div id="tasks" class="muted">Loading…</div></section>
<section class="panel"><h2>Create a task proposal</h2><label class="muted" for="title">Title</label>
<input id="title" maxlength="120" placeholder="e.g. Research renewable energy">
<label class="muted" for="description">Description</label><textarea id="description" maxlength="500" placeholder="Describe the work…"></textarea>
<label class="muted" for="agent">Assign to agent</label><select id="agent"></select><button onclick="createTask()">Create proposal</button>
<h2 style="margin-top:25px">Civilization history</h2><div id="events"></div></section></div>
<p class="muted" style="text-align:center;margin-top:24px">AgentTown · Data is stored locally in agenttown.db</p></main>
<script>
async function api(path,method,body){const r=await fetch(path,{method:method||"GET",headers:{"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.error||"Request failed");return d}
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
async function refresh(){
 const d=await api("/api/state");
 document.getElementById("agent-count").textContent=d.agents.length;
 document.getElementById("task-count").textContent=d.tasks.length;
 document.getElementById("done-count").textContent=d.tasks.filter(t=>t.status==="completed").length;
 document.getElementById("agents").innerHTML=d.agents.map(a=>'<article class="agent"><b>🤖 '+esc(a.name)+'</b><div class="role">'+esc(a.role)+'</div><div class="muted">'+esc(a.description)+'</div></article>').join("");
 const sel=document.getElementById("agent"),old=sel.value;
 sel.innerHTML=d.agents.map(a=>'<option value="'+esc(a.id)+'">'+esc(a.name)+'</option>').join("");if(old)sel.value=old;
 document.getElementById("tasks").innerHTML=d.tasks.length?d.tasks.map(t=>'<article class="task"><div><h3>'+esc(t.title)+'</h3><p>'+esc(t.description)+'</p><span class="muted">Assigned: '+esc(t.agent_name)+'</span></div><div><span class="tag '+esc(t.status)+'">'+esc(t.status)+'</span><div>'+(t.status==="proposed"?'<button class="small" onclick="changeTask('+t.id+',\\'approve\\')">Approve</button>':"")+(t.status==="approved"?'<button class="small" onclick="changeTask('+t.id+',\\'complete\\')">Complete</button>':"")+'</div></div></article>').join(""):"No tasks yet. Run the council or create a proposal.";
 document.getElementById("events").innerHTML=d.events.map(e=>'<div class="event">'+esc(e.message)+'<div class="muted">'+esc(e.created_at)+'</div></div>').join("");
}
async function runCouncil(){try{await api("/api/run","POST",{});await refresh()}catch(e){alert(e.message)}}
async function createTask(){const title=document.getElementById("title").value.trim(),description=document.getElementById("description").value.trim(),agent_id=document.getElementById("agent").value;if(!title){alert("Please enter a title.");return}try{await api("/api/tasks","POST",{title,description,agent_id});document.getElementById("title").value="";document.getElementById("description").value="";await refresh()}catch(e){alert(e.message)}}
async function changeTask(id,action){try{await api("/api/tasks/"+id+"/"+action,"POST",{});await refresh()}catch(e){alert(e.message)}}
refresh().catch(e=>alert(e.message));
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/state":
            self.send_json(snapshot())
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self.read_body()
            if path == "/api/run":
                proposals = [
                    ("Prepare a civilization status report", "Summarize current work and identify blockers.", "mayor"),
                    ("Research a useful open-source technology", "Find one technology that could help AgentTown.", "researcher"),
                    ("Suggest one workflow improvement", "Identify a small improvement to task handling.", "developer"),
                    ("Propose a dashboard improvement", "Suggest a clearer way to present civilization activity.", "designer"),
                    ("Review the task governance rules", "Check whether approval and completion rules are clear.", "auditor"),
                ]
                with db() as conn:
                    for title, description, agent_id in proposals:
                        conn.execute("INSERT INTO tasks(title,description,agent_id,status,created_at) VALUES (?,?,?,'proposed',?)",
                                     (title, description, agent_id, timestamp()))
                record_event("The founding council created five proposals. Human approval is required.")
                return self.send_json({"ok": True})
            if path == "/api/tasks":
                title = str(data.get("title", "")).strip()[:120]
                description = str(data.get("description", "")).strip()[:500]
                agent_id = str(data.get("agent_id", ""))
                if not title:
                    return self.send_json({"error": "Task title is required."}, 400)
                if agent_id not in {a[0] for a in AGENTS}:
                    return self.send_json({"error": "Unknown agent."}, 400)
                with db() as conn:
                    conn.execute("INSERT INTO tasks(title,description,agent_id,status,created_at) VALUES (?,?,?,'proposed',?)",
                                 (title, description, agent_id, timestamp()))
                record_event('New proposal created: "' + title + '".')
                return self.send_json({"ok": True})
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "tasks":
                task_id = int(parts[2])
                action = parts[3]
                if action == "approve":
                    expected, new_status = "proposed", "approved"
                elif action == "complete":
                    expected, new_status = "approved", "completed"
                else:
                    return self.send_json({"error": "Unknown action."}, 404)
                with db() as conn:
                    task = conn.execute("SELECT title,status FROM tasks WHERE id=?", (task_id,)).fetchone()
                    if not task:
                        return self.send_json({"error": "Task not found."}, 404)
                    if task["status"] != expected:
                        return self.send_json({"error": "Task must be " + expected + " first."}, 400)
                    conn.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
                record_event('Task "' + task["title"] + '" marked ' + new_status + '.')
                return self.send_json({"ok": True})
            self.send_json({"error": "Not found"}, 404)
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    initialize()
    print("AgentTown is running at http://localhost:8000")
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
