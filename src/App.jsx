import { useEffect, useState } from "react";

const TYPES = { incoming: "Incoming", memo: "Internal memos", outgoing: "Outgoing" };
const pretty = (s) => (s || "").replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const fmt = (d) => (d ? new Date(d).toLocaleString() : "");

async function call(path, body) {
  const token = localStorage.getItem("token");
  const r = await fetch("/api" + path, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (r.status === 401 && token) { localStorage.clear(); location.reload(); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Please check the form and try again");
  return data;
}

export default function App() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("user") || "null"));
  if (!user) return <Login onDone={setUser} />;
  return <Shell user={user} out={() => { localStorage.clear(); setUser(null); }} />;
}

function Login({ onDone }) {
  const [f, setF] = useState({ email: "", password: "" });
  const [err, setErr] = useState("");
  const go = async (e) => {
    e.preventDefault();
    try {
      const r = await call("/login", f);
      localStorage.setItem("token", r.token);
      localStorage.setItem("user", JSON.stringify(r.user));
      onDone(r.user);
    } catch (x) { setErr(x.message); }
  };
  return (
    <form className="login" onSubmit={go}>
      <h1>Correspondence management</h1>
      <label>Email<input value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} autoFocus /></label>
      <label>Password<input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></label>
      {err && <p className="err">{err}</p>}
      <button className="primary">Sign in</button>
    </form>
  );
}

function Shell({ user, out }) {
  const [tab, setTab] = useState("tasks");
  const [items, setItems] = useState([]);
  const [users, setUsers] = useState([]);
  const [open, setOpen] = useState(null);
  const [creating, setCreating] = useState(false);
  const load = () => call("/correspondence").then(setItems).catch(() => {});
  useEffect(() => { load(); call("/users").then(setUsers).catch(() => {}); }, []);
  const mine = items.filter((i) => i.actions.length);
  const shown = tab === "tasks" ? mine : items.filter((i) => i.type === tab);
  const home = () => { setOpen(null); setCreating(false); load(); };

  return (
    <div className="shell">
      <header>
        <h1>Correspondence</h1>
        <span>{user.name}, {pretty(user.role)}</span>
        <button onClick={out}>Sign out</button>
      </header>
      <nav>
        <button className={tab === "tasks" ? "on" : ""} onClick={() => { setTab("tasks"); home(); }}>
          Waiting for me {mine.length > 0 && <b className="count">{mine.length}</b>}
        </button>
        {Object.entries(TYPES).map(([k, v]) => (
          <button key={k} className={tab === k ? "on" : ""} onClick={() => { setTab(k); home(); }}>{v}</button>
        ))}
        {user.creates.length > 0 && <button className="primary" onClick={() => { setCreating(true); setOpen(null); }}>New</button>}
      </nav>
      <main>
        {creating ? <NewForm user={user} done={(id) => { setCreating(false); setOpen(id); load(); }} cancel={home} />
          : open ? <Detail id={open} users={users} back={home} refresh={load} />
          : shown.length === 0 ? <p className="empty">{tab === "tasks" ? "Nothing is waiting for you." : "No items yet."}</p>
          : (
            <table>
              <thead><tr><th>Reference</th><th>Subject</th><th>Type</th><th>Status</th><th>Updated</th></tr></thead>
              <tbody>
                {shown.map((i) => (
                  <tr key={i.id} className={i.actions.length ? "mine" : ""} onClick={() => setOpen(i.id)}>
                    <td>{i.ref_no || "Draft"}</td><td>{i.subject}</td><td>{TYPES[i.type]}</td>
                    <td><span className={"badge " + i.status}>{pretty(i.status)}</span></td><td>{fmt(i.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </main>
    </div>
  );
}

function NewForm({ user, done, cancel }) {
  const [f, setF] = useState({ type: user.creates[0], subject: "", sender: "", body: "" });
  const [file, setFile] = useState(null);
  const [err, setErr] = useState("");
  const who = { incoming: "Received from", memo: "Memo to", outgoing: "Addressed to" }[f.type];
  const pick = (e) => {
    const x = e.target.files[0];
    if (!x) return setFile(null);
    if (x.size > 3 * 1024 * 1024) { setErr("File is larger than 3 MB"); e.target.value = ""; return; }
    const r = new FileReader();
    r.onload = () => setFile({ file_name: x.name, file_mime: x.type, file_b64: r.result.split(",")[1] });
    r.readAsDataURL(x);
  };
  const save = async () => {
    try { const r = await call("/correspondence", { ...f, ...file }); done(r.id); } catch (x) { setErr(x.message); }
  };
  return (
    <div className="panel">
      <h2>New correspondence</h2>
      <label>Type<select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}>
        {user.creates.map((t) => <option key={t} value={t}>{TYPES[t]}</option>)}</select></label>
      <label>Subject<input value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} /></label>
      <label>{who}<input value={f.sender} onChange={(e) => setF({ ...f, sender: e.target.value })} /></label>
      <label>{f.type === "incoming" ? "Summary" : "Content"}<textarea rows="6" value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} /></label>
      <label>{f.type === "incoming" ? "Scanned document" : "Attachment"}<input type="file" onChange={pick} /></label>
      {err && <p className="err">{err}</p>}
      <div className="row"><button className="primary" onClick={save}>{f.type === "incoming" ? "Register" : "Save draft"}</button><button onClick={cancel}>Cancel</button></div>
    </div>
  );
}

function Detail({ id, users, back, refresh }) {
  const [d, setD] = useState(null);
  const [act, setAct] = useState(null);
  const [fields, setFields] = useState({});
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const load = () => call("/correspondence/" + id).then(setD).catch((x) => setErr(x.message));
  useEffect(() => { load(); }, [id]);
  if (!d) return <p>{err || "Loading…"}</p>;
  const i = d.item;
  const name = (uid) => users.find((u) => u.id === uid)?.name;
  const submit = async () => {
    try {
      await call(`/correspondence/${id}/act`, { action: act.key, note, fields });
      setAct(null); setFields({}); setNote(""); setErr(""); await load(); refresh();
    } catch (x) { setErr(x.message); }
  };
  const download = async (a) => {
    const r = await fetch("/api/attachments/" + a.id, { headers: { Authorization: "Bearer " + localStorage.getItem("token") } });
    const url = URL.createObjectURL(await r.blob());
    const l = document.createElement("a"); l.href = url; l.download = a.filename; l.click(); URL.revokeObjectURL(url);
  };
  const facts = [
    ["Reference", i.ref_no], ["Type", TYPES[i.type]], ["Counterparty", i.sender], ["Created by", name(i.created_by)],
    ["Assigned to", name(i.assignee_id)], ["Approver", name(i.approver_id)], ["Category", i.category],
    ["Official stamp", i.stamped ? "Applied" : ""], ["Signed by", i.signed_by], ["CC", i.cc], ["Registered", fmt(i.registered_at)],
  ].filter((x) => x[1]);
  return (
    <div className="panel">
      <button onClick={back}>Back to list</button>
      <h2>{i.subject} <span className={"badge " + i.status}>{pretty(i.status)}</span></h2>
      <dl>{facts.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
      {i.body && <p className="body">{i.body}</p>}
      {d.attachments.map((a) => <button key={a.id} onClick={() => download(a)}>Download {a.filename}</button>)}

      {d.actions.length > 0 && (
        <section className="actions">
          <h3>Your next step</h3>
          <div className="row">{d.actions.map((a) => (
            <button key={a.key} className={act?.key === a.key ? "on" : "primary"} onClick={() => { setAct(a); setErr(""); }}>{a.label}</button>))}</div>
          {act && (
            <div className="form">
              {(act.fields || []).map((f) => f.kind === "user" ? (
                <label key={f.name}>{f.label}<select value={fields[f.name] || ""} onChange={(e) => setFields({ ...fields, [f.name]: e.target.value })}>
                  <option value="">Choose…</option>
                  {users.filter((u) => !f.roles || f.roles.includes(u.role)).map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
                </select></label>
              ) : (
                <label key={f.name}>{f.label}<input value={fields[f.name] || ""} onChange={(e) => setFields({ ...fields, [f.name]: e.target.value })} /></label>
              ))}
              <label>Note{act.note ? "" : " (optional)"}<textarea rows="3" value={note} onChange={(e) => setNote(e.target.value)} /></label>
              <button className="primary" onClick={submit}>Confirm: {act.label}</button>
            </div>
          )}
          {err && <p className="err">{err}</p>}
        </section>
      )}

      <section>
        <h3>History</h3>
        <ol className="timeline">{d.events.map((e) => (
          <li key={e.id}><b>{pretty(e.action)}</b> by {e.actor}<small>{fmt(e.at)}</small>
            {e.to_status && <small>Status: {pretty(e.to_status)}</small>}{e.note && <p>{e.note}</p>}</li>))}</ol>
      </section>
    </div>
  );
}
