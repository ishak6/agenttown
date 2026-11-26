"""AgentTown local autonomous workflow engine. Run: python app.py"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from datetime import datetime, timezone
import json, sqlite3, threading

DB_PATH="agenttown.db"
LOCK=threading.RLock()
AGENTS=[
("mayor","Mayor","Coordinator","Coordinates goals and dependencies."),
("researcher","Researcher","Research","Structures questions and evidence plans."),
("developer","Developer","Engineering","Creates technical implementation plans."),
("designer","Designer","Design","Creates user journeys and interface plans."),
("auditor","Auditor","Governance","Checks quality, risks, and completion criteria.")]
def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def db():
 c=sqlite3.connect(DB_PATH,timeout=10); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c
def event(msg,c):
 c.execute("INSERT INTO events(message,created_at) VALUES (?,?)",(msg,now()))
def initialize():
 with LOCK,db() as c:
  c.execute("CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,name TEXT NOT NULL,role TEXT NOT NULL,description TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'idle')")
  c.execute("""CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',agent_id TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',created_at TEXT NOT NULL,FOREIGN KEY(agent_id) REFERENCES agents(id))""")
  c.execute("CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,message TEXT NOT NULL,created_at TEXT NOT NULL)")
  c.execute("CREATE TABLE IF NOT EXISTS world_state(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
  ac={r["name"] for r in c.execute("PRAGMA table_info(agents)")}
  if "status" not in ac: c.execute("ALTER TABLE agents ADD COLUMN status TEXT NOT NULL DEFAULT 'idle'")
  tc={r["name"] for r in c.execute("PRAGMA table_info(tasks)")}
  if "result" not in tc: c.execute("ALTER TABLE tasks ADD COLUMN result TEXT NOT NULL DEFAULT ''")
  if "completed_at" not in tc: c.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
  c.executemany("INSERT OR IGNORE INTO agents(id,name,role,description) VALUES (?,?,?,?)",AGENTS)
  c.execute("INSERT OR IGNORE INTO world_state VALUES('paused','false')")
  if not c.execute("SELECT 1 FROM events LIMIT 1").fetchone(): event("AgentTown local engine initialized; five worker agents registered.",c)
def paused():
 with LOCK,db() as c:
  r=c.execute("SELECT value FROM world_state WHERE key='paused'").fetchone(); return bool(r and r["value"]=="true")
def set_paused(v):
 with LOCK,db() as c:
  c.execute("UPDATE world_state SET value=? WHERE key='paused'",("true" if v else "false",))
  event("Creator paused the civilization." if v else "Creator resumed the civilization.",c)
def work(a,title,desc):
 goal=title+(": "+desc if desc else "")
 templates={
 "mayor":"COORDINATION RESULT\nGoal: "+goal+"\n1. Scope the objective.\n2. Break it into actionable steps.\n3. Identify dependencies and owners.\n4. Record measurable completion checks.",
 "researcher":"RESEARCH WORK PRODUCT\nGoal: "+goal+"\n1. Define the core question.\n2. Gather primary sources and compare independent evidence.\n3. Separate verified facts, assumptions, and open questions.\nLIMITATION: This first local worker does not browse the live web; it creates a research plan, not verified findings.",
 "developer":"ENGINEERING WORK PRODUCT\nGoal: "+goal+"\n1. Define inputs, outputs, and acceptance criteria.\n2. Implement the smallest testable change.\n3. Test normal, invalid, and edge cases.\n4. Record technical risks and remaining work.\nDELIVERABLE: implementation plan.",
 "designer":"DESIGN WORK PRODUCT\nGoal: "+goal+"\n1. Identify the primary user and task.\n2. Map entry, action, feedback, and recovery.\n3. Prioritize accessibility and responsive layout.\n4. Define a review checklist.",
 "auditor":"GOVERNANCE AUDIT\nGoal: "+goal+"\n1. Check clarity and measurability.\n2. Identify safety, privacy, and reliability risks.\n3. Define evidence required for completion.\n4. Flag unsupported claims and assumptions."}
 return templates[a]
def execute(tid):
 if paused(): return False
 with LOCK,db() as c:
  t=c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
  if not t or t["status"] not in ("queued","failed"): return False
  c.execute("UPDATE tasks SET status='running' WHERE id=?",(tid,))
  c.execute("UPDATE agents SET status='working' WHERE id=?",(t["agent_id"],))
  event(t["agent_id"].title()+" started: "+t["title"],c)
 try:
  result=work(t["agent_id"],t["title"],t["description"])
  with LOCK,db() as c:
   c.execute("UPDATE tasks SET status='completed',result=?,completed_at=? WHERE id=? AND status='running'",(result,now(),tid))
   c.execute("UPDATE agents SET status='idle' WHERE id=?",(t["agent_id"],))
   event(t["agent_id"].title()+" completed: "+t["title"],c)
  return True
 except Exception as e:
  with LOCK,db() as c:
   c.execute("UPDATE tasks SET status='failed',result=? WHERE id=?",("Worker error: "+str(e),tid))
   c.execute("UPDATE agents SET status='idle' WHERE id=?",(t["agent_id"],))
   event("Task failed: "+t["title"],c)
  return False
def create_task(title,desc,aid):
 title=title.strip()
 if not title: raise ValueError("Task title is required.")
 if aid not in {a[0] for a in AGENTS}: raise ValueError("Unknown agent.")
 with LOCK,db() as c:
  cur=c.execute("INSERT INTO tasks(title,description,agent_id,status,created_at) VALUES (?,?,?,'queued',?)",(title[:120],desc.strip()[:1000],aid,now()))
  tid=cur.lastrowid; event(aid.title()+" received task: "+title[:120],c)
 if not paused(): execute(tid)
 return tid
def council():
 if paused(): raise RuntimeError("Civilization is paused by Creator.")
 jobs=[
 ("Prepare a civilization status report","Summarize current work and blockers.","mayor"),
 ("Create a knowledge-gathering plan","Define evidence and source checks for the next research cycle.","researcher"),
 ("Improve task execution workflow","Identify the next engineering improvement and tests.","developer"),
 ("Design Creator monitoring experience","Define a clear view of agent status and outcomes.","designer"),
 ("Audit civilization operations","Review execution, data handling, and reliability.","auditor")]
 ids=[create_task(*j) for j in jobs]
 event("Council cycle finished; five workers processed their assignments.",db())
 return ids
def snapshot():
 with LOCK,db() as c:
  agents=[dict(x) for x in c.execute("SELECT agents.*,(SELECT COUNT(*) FROM tasks WHERE tasks.agent_id=agents.id AND status='completed') AS completed_tasks FROM agents ORDER BY rowid")]
  tasks=[dict(x) for x in c.execute("SELECT tasks.*,agents.name AS agent_name FROM tasks JOIN agents ON agents.id=tasks.agent_id ORDER BY tasks.id DESC LIMIT 100")]
  events=[dict(x) for x in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50")]
  counts={x["status"]:x["n"] for x in c.execute("SELECT status,COUNT(*) n FROM tasks GROUP BY status")}
 return {"agents":agents,"tasks":tasks,"events":events,"counts":counts,"paused":paused(),"engine":"local-role-workers"}
PAGE=r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AgentTown Creator Command</title><style>
:root{color-scheme:dark;font:15px system-ui;color:#edf2ff;background:#0b1220}*{box-sizing:border-box}body{margin:0}.shell{max-width:1160px;margin:auto;padding:28px 20px}header,.head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}h1{margin:0}h2{font-size:17px;margin:0 0 14px}.muted{color:#9eabc2;font-size:12px}.stats,.agents{display:grid;gap:12px}.stats{grid-template-columns:repeat(4,1fr);margin:20px 0}.agents{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}.stat,.panel,.agent{background:#151f31;border:1px solid #29364d;border-radius:14px;padding:16px}.stat strong{display:block;font-size:26px}.agent{background:#101a2b;padding:12px}.agent b{display:block}button{border:0;border-radius:8px;padding:9px 12px;background:#9ab7ff;color:#10182a;font-weight:700;cursor:pointer}button.alt{background:#293750;color:#fff}.actions{display:flex;gap:8px;flex-wrap:wrap}.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:14px;margin-top:14px}input,textarea,select{width:100%;background:#0e1727;color:#fff;border:1px solid #34435e;border-radius:8px;padding:10px;margin:6px 0 12px}textarea{min-height:65px}.task,.event{border-top:1px solid #29364d;padding:11px 0}.task h3{font-size:13px;margin:0 0 5px}.task p{white-space:pre-wrap;color:#c0ccdc;font-size:12px}.tag{border:1px solid #486078;border-radius:20px;padding:4px 8px;font-size:11px}.task summary{cursor:pointer;color:#9ab7ff}.pill{color:#9ce4c5;border:1px solid #285b4c;border-radius:20px;padding:7px 10px;font-size:12px}@media(max-width:740px){.grid{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}}</style></head><body><main class="shell">
<header><div><h1>🏙️ AgentTown</h1><div class="muted">Creator Command · Local autonomous workflow engine</div></div><div class="actions"><span class="pill" id="world">Connecting…</span><button class="alt" id="pause">Pause</button></div></header>
<div class="stats"><div class="stat"><strong id="ac">5</strong><span class="muted">Agents</span></div><div class="stat"><strong id="active">0</strong><span class="muted">Active tasks</span></div><div class="stat"><strong id="done">0</strong><span class="muted">Completed</span></div><div class="stat"><strong id="ec">0</strong><span class="muted">Events</span></div></div>
<section class="panel"><div class="head"><h2>👁 Creator / God View — live agent monitor</h2><button id="council">Run autonomous council</button></div><div class="agents" id="agents"></div><p class="muted">Work is executed locally and persisted in SQLite. This first version uses deterministic role workers, not an LLM.</p></section>
<div class="grid"><section class="panel"><h2>Agent work & results</h2><div id="tasks">Loading…</div></section><section class="panel"><h2>Creator decree</h2><label class="muted">Goal</label><input id="title" maxlength="120" placeholder="Build a shared knowledge archive"><label class="muted">Details / expected result</label><textarea id="desc" maxlength="1000"></textarea><label class="muted">First worker</label><select id="agent"><option value="mayor">Mayor</option><option value="researcher">Researcher</option><option value="developer">Developer</option><option value="designer">Designer</option><option value="auditor">Auditor</option></select><button id="issue">Issue decree & execute</button><h2 style="margin-top:22px">Civilization history</h2><div id="events"></div></section></div><p class="muted" style="text-align:center">Local SQLite · No paid API · Not yet an LLM agent society</p></main>
<script>
const $=x=>document.getElementById(x);async function api(p,m="GET",b){let r=await fetch(p,{method:m,headers:{"Content-Type":"application/json"},body:b?JSON.stringify(b):undefined}),d=await r.json();if(!r.ok)throw Error(d.error||"Request failed");return d}function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
async function refresh(){let d=await api("/api/state");$("ac").textContent=d.agents.length;$("active").textContent=(d.counts.queued||0)+(d.counts.running||0);$("done").textContent=d.counts.completed||0;$("ec").textContent=d.events.length;$("world").textContent=d.paused?"PAUSED BY CREATOR":"CIVILIZATION RUNNING";$("pause").textContent=d.paused?"Resume civilization":"Pause civilization";$("agents").innerHTML=d.agents.map(a=>'<article class="agent"><b>🤖 '+esc(a.name)+' · '+esc(a.status)+'</b><div class="muted">'+esc(a.role)+' · '+a.completed_tasks+' completed</div><div class="muted">'+esc(a.description)+'</div></article>').join("");$("tasks").innerHTML=d.tasks.length?d.tasks.map(t=>'<article class="task"><h3>'+esc(t.title)+' <span class="tag">'+esc(t.status)+'</span></h3><div class="muted">'+esc(t.agent_name)+' · '+esc(t.created_at)+'</div><div class="muted">'+esc(t.description)+'</div>'+(t.result?'<details><summary>View work result</summary><p>'+esc(t.result)+'</p></details>':"")+'</article>').join(""):"No tasks yet."; $("events").innerHTML=d.events.map(e=>'<div class="event">'+esc(e.message)+'<div class="muted">'+esc(e.created_at)+'</div></div>').join("")}
$("pause").onclick=async()=>{try{await api("/api/control/pause","POST",{});await refresh()}catch(e){alert(e.message)}};$("council").onclick=async()=>{try{await api("/api/run","POST",{});await refresh()}catch(e){alert(e.message)}};$("issue").onclick=async()=>{if(!$("title").value.trim())return alert("Enter a goal.");try{await api("/api/decree","POST",{title:$("title").value,description:$("desc").value,agent_id:$("agent").value});$("title").value="";$("desc").value="";await refresh()}catch(e){alert(e.message)}};refresh().catch(e=>alert("Backend connection failed: "+e.message));setInterval(()=>refresh().catch(()=>{}),5000);
</script></body></html>"""
class Handler(BaseHTTPRequestHandler):
 def send_json(self,data,status=200):
  b=json.dumps(data).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def read_body(self):
  n=int(self.headers.get("Content-Length","0"))
  if n>16384: raise ValueError("Request body too large.")
  d=json.loads(self.rfile.read(n) if n else b"{}")
  if not isinstance(d,dict): raise ValueError("JSON body must be an object.")
  return d
 def do_GET(self):
  p=urlparse(self.path).path
  if p=="/":
   b=PAGE.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
  elif p=="/api/state": self.send_json(snapshot())
  else:self.send_json({"error":"Not found"},404)
 def do_POST(self):
  try:
   d=self.read_body();p=urlparse(self.path).path
   if p=="/api/control/pause":
    v=not paused();set_paused(v);return self.send_json({"ok":True,"paused":v})
   if p=="/api/run": return self.send_json({"ok":True,"task_ids":council()})
   if p=="/api/decree":
    if paused():return self.send_json({"error":"Civilization is paused. Resume it first."},409)
    tid=create_task(str(d.get("title","")),str(d.get("description","")),str(d.get("agent_id","mayor")))
    event("Creator decree executed as task #"+str(tid),None);return self.send_json({"ok":True,"task_id":tid})
   self.send_json({"error":"Not found"},404)
  except (ValueError,json.JSONDecodeError) as e:self.send_json({"error":str(e)},400)
  except RuntimeError as e:self.send_json({"error":str(e)},409)
 def log_message(self,fmt,*args):print("%s - %s"%(self.address_string(),fmt%args))
if __name__=="__main__":
 initialize();print("AgentTown is running at http://127.0.0.1:8000");print("Press Ctrl+C to stop.");ThreadingHTTPServer(("127.0.0.1",8000),Handler).serve_forever()
