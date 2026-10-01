import base64, os, time
from datetime import datetime
from typing import Optional
import jwt, psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from lib.security import check_pw
from lib.workflow import CREATORS, PREFIX, WORKFLOWS, actions_for, visible

SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
FIELDS = ("assignee_id", "approver_id", "category", "cc")
app = FastAPI()
api = APIRouter(prefix="/api")

def db():
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn:
        yield conn

def me(authorization: str = Header("")):
    try:
        return jwt.decode(authorization.removeprefix("Bearer "), SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Please sign in again")

def next_ref(c, typ):
    n = c.execute("select nextval('ref_seq') n").fetchone()["n"]
    return f"{PREFIX[typ]}/{datetime.now().year}/{n:04d}"

def load(c, cid, u):
    item = c.execute("select * from correspondence where id=%s", (cid,)).fetchone()
    if not item or not visible(item, u):
        raise HTTPException(404, "Not found")
    return item

def log(c, cid, u, action, old, new, note=""):
    c.execute("insert into events(corr_id,actor,action,from_status,to_status,note) values(%s,%s,%s,%s,%s,%s)",
              (cid, u["name"], action, old, new, note))

class Login(BaseModel):
    email: str
    password: str

@api.post("/login")
def login(b: Login, c=Depends(db)):
    r = c.execute("select * from users where email=%s", (b.email.strip().lower(),)).fetchone()
    if not r or not check_pw(b.password, r["password_hash"]):
        raise HTTPException(401, "Wrong email or password")
    user = {"id": r["id"], "name": r["name"], "role": r["role"]}
    token = jwt.encode({**user, "exp": int(time.time()) + 8 * 3600}, SECRET, algorithm="HS256")
    return {"token": token, "user": {**user, "creates": [k for k, v in CREATORS.items() if r["role"] in v]}}

@api.get("/users")
def users(u=Depends(me), c=Depends(db)):
    return c.execute("select id,name,role from users order by name").fetchall()

@api.get("/correspondence")
def list_items(u=Depends(me), c=Depends(db)):
    rows = [r for r in c.execute("select * from correspondence order by updated_at desc").fetchall() if visible(r, u)]
    for r in rows:
        r["actions"] = [a["key"] for a in actions_for(r, u)]
    return rows

class New(BaseModel):
    type: str
    subject: str
    body: str = ""
    sender: str = ""
    file_name: Optional[str] = None
    file_mime: Optional[str] = None
    file_b64: Optional[str] = None

@api.post("/correspondence")
def create(n: New, u=Depends(me), c=Depends(db)):
    if n.type not in WORKFLOWS or u["role"] not in CREATORS[n.type]:
        raise HTTPException(403, "Your role cannot create this type")
    status = WORKFLOWS[n.type]["start"]
    ref = next_ref(c, n.type) if n.type == "incoming" else None
    cid = c.execute(
        "insert into correspondence(type,subject,body,sender,status,ref_no,created_by) "
        "values(%s,%s,%s,%s,%s,%s,%s) returning id",
        (n.type, n.subject, n.body, n.sender, status, ref, u["id"])).fetchone()["id"]
    if n.file_b64:
        c.execute("insert into attachments(corr_id,filename,mime,data) values(%s,%s,%s,%s)",
                  (cid, n.file_name, n.file_mime, base64.b64decode(n.file_b64)))
    log(c, cid, u, "created", None, status)
    return {"id": cid}

@api.get("/correspondence/{cid}")
def detail(cid: int, u=Depends(me), c=Depends(db)):
    item = load(c, cid, u)
    return {
        "item": item,
        "actions": actions_for(item, u),
        "events": c.execute("select * from events where corr_id=%s order by at", (cid,)).fetchall(),
        "attachments": c.execute("select id,filename from attachments where corr_id=%s", (cid,)).fetchall(),
    }

class Act(BaseModel):
    action: str
    note: str = ""
    fields: dict = {}

@api.post("/correspondence/{cid}/act")
def act(cid: int, a: Act, u=Depends(me), c=Depends(db)):
    item = load(c, cid, u)
    t = next((x for x in actions_for(item, u) if x["key"] == a.action), None)
    if not t:
        raise HTTPException(403, "That action isn't available to you right now")
    if t.get("note") and not a.note.strip():
        raise HTTPException(400, "Please add a note")
    cols = {}
    for f in t.get("fields", []):
        v = a.fields.get(f["name"])
        if not v and not f.get("optional"):
            raise HTTPException(400, f"{f['label']} is required")
        if v and f["name"] in FIELDS:
            cols[f["name"]] = int(v) if f["name"].endswith("_id") else v
    new = t["to"] or item["status"]
    cols["status"] = new
    if t.get("stamp"): cols["stamped"] = True
    if t.get("sign"): cols["signed_by"] = u["name"]
    if t.get("ref"): cols["ref_no"] = next_ref(c, item["type"])
    sets = ", ".join(f"{k}=%s" for k in cols) + ", updated_at=now()"
    if t.get("ref") and item["type"] == "outgoing":
        sets += ", registered_at=now()"
    c.execute(f"update correspondence set {sets} where id=%s", [*cols.values(), cid])
    log(c, cid, u, t["label"], item["status"], new, a.note)
    return {"ok": True}

@api.get("/attachments/{aid}")
def attachment(aid: int, u=Depends(me), c=Depends(db)):
    r = c.execute("select * from attachments where id=%s", (aid,)).fetchone()
    if not r:
        raise HTTPException(404, "Not found")
    load(c, r["corr_id"], u)
    return Response(bytes(r["data"]), media_type=r["mime"] or "application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{r["filename"]}"'})

app.include_router(api)
