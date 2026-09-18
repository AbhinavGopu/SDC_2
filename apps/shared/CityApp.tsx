"use client";
import { useEffect, useState } from "react";
import TrafficPlayback from "./TrafficPlayback";

type Role = "citizen" | "planner";
type Row = Record<string, any>;
async function request(path: string, token: string, body?: unknown, method = "GET") {
  const response = await fetch("/api" + path, { method, headers: { ...(token ? { Authorization: "Bearer " + token } : {}), ...(body && !(body instanceof FormData) ? { "Content-Type": "application/json" } : {}) }, body: body ? body instanceof FormData ? body : JSON.stringify(body) : undefined });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || "Request failed"));
  return data;
}
export default function CityApp({ role }: { role: Role }) {
  const [token, setToken] = useState(""), [user, setUser] = useState<Row | null>(null);
  const [email, setEmail] = useState(""), [password, setPassword] = useState("");
  const [error, setError] = useState(""), [notice, setNotice] = useState(""), [busy, setBusy] = useState(false);
  const [wards, setWards] = useState<Row[]>([]), [ward, setWard] = useState(1), [search, setSearch] = useState("");
  const [complaints, setComplaints] = useState<Row[]>([]), [overview, setOverview] = useState<Row | null>(null);
  const [description, setDescription] = useState(""), [lat, setLat] = useState(17.435), [lon, setLon] = useState(78.445);
  const [file, setFile] = useState<File | null>(null), [domain, setDomain] = useState("traffic");
  const [prompt, setPrompt] = useState("");
  const [budget, setBudget] = useState(50), [days, setDays] = useState(30), [row, setRow] = useState(0);
  const [noConstruction, setNoConstruction] = useState(true), [noClosures, setNoClosures] = useState(true), [preserveBus, setPreserveBus] = useState(true);
  const [plan, setPlan] = useState<Row | null>(null), [plans, setPlans] = useState<Row[]>([]), [audit, setAudit] = useState<Row[]>([]);
  const [job, setJob] = useState<Row | null>(null), [green, setGreen] = useState(25);

  async function run(action: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function refresh(t = token) {
    setComplaints(await request("/complaints", t));
    if (role === "planner") {
      setPlans(await request("/plans", t)); setAudit(await request("/audit", t));
    }
  }
  async function login(register = false) {
    const data = await request(register ? "/auth/register" : "/auth/login", "", { email, password }, "POST");
    if (data.user.role !== role) throw new Error("This account belongs in the " + data.user.role + " portal.");
    setToken(data.token); setUser(data.user); setWard(data.user.ward_id || 1);
    setWards((await request("/wards", data.token)).features); await refresh(data.token);
  }
  useEffect(() => {
    if (!token || role !== "planner") return;
    let current = true;
    request("/wards/" + ward + "/overview", token).then(data => { if (current) setOverview(data); }).catch(e => { if (current) setError(e.message); });
    return () => { current = false; };
  }, [ward, token, role]);
  useEffect(() => {
    if (!token) return;
    const id = setInterval(() => { refresh().catch(e => setError(e.message)); }, 10000);
    return () => clearInterval(id);
  }, [token]);
  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const id = setInterval(() => { request("/jobs/" + job.id, token).then(setJob).catch(e => setError(e.message)); }, 1500);
    return () => clearInterval(id);
  }, [job?.id, job?.status, token]);
  const readOnly = role === "planner" && user?.ward_id !== ward;
  const visibleComplaints = role === "planner" ? complaints.filter(c => c.status !== "resolved").slice(0, 5) : complaints.filter(c => c.owner_id === user?.id);
  const priorityTarget = complaints.find(c => c.status !== "resolved" && c.ward_id === ward);
  const selected = wards.find(w => w.properties.id === ward);
  async function submitComplaint() {
    const c = await request("/complaints", token, { description, latitude: lat, longitude: lon }, "POST");
    setNotice("Report received. Tracking ID: " + c.id);
    if (file) {
      const body = new FormData(); body.append("file", file);
      try { await request("/complaints/" + c.id + "/media", token, body, "POST"); }
      catch (e) { setError("Report saved as " + c.id + ", but attachment failed: " + (e as Error).message); }
    }
    setDescription(""); await refresh();
  }
  async function exportCsv() {
    const response = await fetch("/api/wards/" + ward + "/export", { headers: { Authorization: "Bearer " + token } });
    if (!response.ok) throw new Error("Export failed");
    const url = URL.createObjectURL(await response.blob()); const a = document.createElement("a");
    a.href = url; a.download = "ward-" + ward + "-observations.csv"; a.click(); URL.revokeObjectURL(url);
  }
  function signOut() {
    setToken(""); setUser(null); setEmail(""); setPassword("");
    setError(""); setNotice(""); setPlan(null); setJob(null);
    setComplaints([]); setPlans([]); setAudit([]); setOverview(null);
    window.scrollTo(0, 0);
  }
  if (!user) return <main className="auth-page">
    <div className="auth-brand"><span className="brand-icon">H</span><span>HYDERABAD CITY LAB</span></div>
    <section className="card login" aria-labelledby="login-title"><div className="eyebrow">WELCOME TO CITY LAB</div><h1 id="login-title">{role === "planner" ? "Planner sign in" : "Citizen sign in"}</h1><p className="muted">Sign in to access your workspace.</p>{error && <div role="alert" className="error">{error}</div>}<form onSubmit={e => {e.preventDefault(); run(() => login());}}>
        <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="username"/></label>
        <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} minLength={10} required autoComplete="current-password"/></label>
        <button disabled={busy} type="submit">{busy ? "Signing in…" : "Enter workspace →"}</button>
        {role === "citizen" && <button className="secondary" disabled={busy} type="button" onClick={() => run(() => login(true))}>Create citizen account</button>}
      </form></section>
  </main>;
  return <div className={`shell ${role}-workspace`}>
    <header className="topbar">
      <div className="topbar-heading">
        <a className="brand" href="#workspace"><span className="brand-icon">H</span> HYDERABAD CITY LAB</a>
        <div className="account"><span>{user.email}</span><button className="quiet" onClick={signOut}>Sign out</button></div>
      </div>
      <nav aria-label="Workspace navigation">
        <a href="#workspace">{role === "planner" ? "Ward overview" : "Report an issue"}</a>
        <a href="#reports">{role === "planner" ? "Ward reports" : "My reports"}</a>
        {role === "planner" && <><a href="#advisor">Planning advisor</a><a href="#simulation">Simulation lab</a></>}
        <a className="portal-link" href={role === "citizen" ? "http://localhost:3001" : "http://localhost:3000"}>Open {role === "citizen" ? "planner" : "citizen"} portal</a>
      </nav>
    </header>
    <main id="workspace">
      <div className="eyebrow">A BETTER CITY STARTS WITH BETTER EVIDENCE</div>
      <h1>{role === "planner" ? "See the city. Plan with context." : "Your street. Your voice."}</h1>
      <p className="subtitle">{role === "planner" ? "Explore local indicators, review citizen reports, and test planning ideas." : "Tell us what needs attention. Follow your report from receipt to resolution."}</p>
      <div className="disclosure"><strong>DEMONSTRATION DATA</strong> Bundled indicators and ward shapes are simulated. Historical records are labeled separately. Nothing here is official live telemetry.</div>
      {error && <div role="alert" className="error">{error}</div>}{notice && <div role="status" className="success">{notice}</div>}

      {role === "citizen" ? <div className="grid two"><section className="card"><span className="eyebrow">01 / REPORT</span><h2>What’s happening nearby?</h2><form onSubmit={e => {e.preventDefault(); run(submitComplaint);}}>
        <label>Describe the issue<textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="A blocked drain is causing waterlogging near the junction…" minLength={10} maxLength={4000} required /></label>
        <div className="grid two"><label>Latitude<input type="number" step="any" min="17.2" max="17.6" value={lat} onChange={e => setLat(Number(e.target.value))} required/></label><label>Longitude<input type="number" step="any" min="78.25" max="78.65" value={lon} onChange={e => setLon(Number(e.target.value))} required/></label></div>
        <label>Photo or video (optional, up to 10 MB)<input type="file" accept="image/jpeg,image/png,video/mp4" onChange={e => setFile(e.target.files?.[0] || null)}/></label><p className="muted">Offline mode stores evidence for human review. An explicitly configured OpenAI key enables visual analysis in the worker.</p>
        <button disabled={busy}>Submit report →</button></form></section><section className="card"><span className="eyebrow">02 / LOCATE</span><h2>Confirm the report location</h2><p>Click inside a study area. These shapes are illustrative and are not official wards.</p><StudyMap wards={wards} lat={lat} lon={lon} onPick={(a,b) => {setLat(a);setLon(b);}}/><label>Jump to study area<select value={ward} onChange={e => {const id=Number(e.target.value);setWard(id);const p=wards.find(w => w.properties.id===id)?.geometry.coordinates[0]; if(p){setLon((p[0][0]+p[2][0])/2);setLat((p[0][1]+p[2][1])/2);}}}>{wards.map(w=><option key={w.properties.id} value={w.properties.id}>{w.properties.name}</option>)}</select></label></section></div> : <>
      <div className="toolbar"><label>Find a locality<input placeholder="Search loaded study areas" value={search} onChange={e => setSearch(e.target.value)}/></label><label>Study area<select value={ward} onChange={e => setWard(Number(e.target.value))}>{wards.filter(w => w.properties.name.toLowerCase().includes(search.toLowerCase())).map(w => <option key={w.properties.id} value={w.properties.id}>{w.properties.name}</option>)}</select></label><button className="secondary" onClick={() => run(exportCsv)}>Export source data ↓</button></div>
      {readOnly && <div className="disclosure">Read-only locality view. Your account can change only its assigned demonstration ward.</div>}
      <div className="grid overview"><section className="card map-card"><div className="section-head"><h2>{selected?.properties.name}</h2><span className="tag">SIMULATED BOUNDARY</span></div><StudyMap wards={wards} selected={ward}/><p className="muted">Coordinates shown in WGS84 · no external map service required</p></section><section className="card"><span className="eyebrow">WARD SNAPSHOT</span><div className="big-number">{overview?.open_complaints ?? "—"}</div><p>Open citizen reports</p><hr/><h3>Data you can trace</h3><p>Every indicator includes a timestamp, origin, and provenance label.</p><p className="muted">Air, waste and energy indicators support the traffic review. They do not establish causation.</p></section></div>
      <section id="simulation" className="card"><span className="eyebrow">SUMO / TRACI</span><h2>Traffic congestion playback</h2><p>Compare identical synthetic demand on a generated four-arm junction. This is not a calibrated Hyderabad road model. Better results are not guaranteed.</p><label>Trial green phase (seconds)<input type="number" min="10" max="90" value={green} onChange={e=>setGreen(Number(e.target.value))}/></label><button disabled={busy || readOnly || (!!job && ["queued","running"].includes(job.status))} onClick={()=>run(async()=>setJob(await request("/simulations",token,{ward_id:ward,seconds:300,seed:42,green_seconds:green},"POST")))}>Run comparison →</button>
        <TrafficPlayback key={job?.id || "empty"} result={job?.result}/>
        {job && <div role="status"><p>Run {job.id.slice(0,8)} · {job.status}</p>{job.error && <p className="error">{job.error}</p>}{job.result && <><span className="tag">{job.result.engine} · SIMULATED</span><table><thead><tr><th>Metric</th><th>Baseline</th><th>Trial</th></tr></thead><tbody>{["mean_speed_kmh","mean_halting_vehicles","arrived_vehicles","co2_grams","remaining_vehicles"].map(k=><tr key={k}><td>{k.replaceAll("_"," ")}</td><td>{job.result.baseline[k]}</td><td>{job.result.intervention[k]}</td></tr>)}</tbody></table><p>{job.result.scenario}</p></>}</div>}
      </section>
      <section className="card"><div className="section-head"><h2>Indicators to review</h2><div className="tabs">{["traffic","pollution","energy"].map(d => <button key={d} className={domain===d?"selected":""} onClick={() => setDomain(d)}>{d}</button>)}</div></div><div className="grid three">{overview?.problems?.[domain]?.map((p: Row) => <article className="metric" key={p.title}><span className="tag">{p.provenance}</span><h3>{p.title}</h3><div className="metric-value">{p.value}<small> {p.unit}</small></div><p className="muted">{p.observed_at.slice(0,10)} · {p.source}</p></article>)}</div><details><summary>Inspect history and source records</summary><div className="table-scroll"><table><thead><tr><th>Date</th><th>Metric</th><th>Value</th><th>Provenance / source</th></tr></thead><tbody>{overview?.history?.map((o:Row)=><tr key={o.id}><td>{o.observed_at.slice(0,10)}</td><td>{o.metric}</td><td>{o.value} {o.unit}</td><td>{o.provenance} · {o.source}</td></tr>)}</tbody></table></div></details></section>
      <section id="advisor" className="card"><h2 className="advisor-title">Planning Advisor</h2><p className="advisor-subtitle">Address the highest-priority issue.</p>{priorityTarget ? <div className="priority-explanation advisor-target"><span className={"priority-badge priority-" + priorityTarget.priority?.level}>{priorityTarget.priority?.level} priority</span><p>{priorityTarget.description}</p><small>Tracking ID: {priorityTarget.id}. The server checks the queue again when you request advice.</small></div> : <p className="muted">No unresolved reports are loaded for this area. Enter a brief to review another planning issue.</p>}<form onSubmit={e=>{e.preventDefault();run(async()=>{setPlan(await request("/plans",token,{ward_id:ward,prompt,constraints:{budget_lakhs:budget,timeline_days:days,available_row_m:row,no_construction:noConstruction,no_road_closures:noClosures,preserve_bus:preserveBus}},"POST"));await refresh();});}}>
        <label>Planning brief<textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="For example: Suggest the next steps for the highest-priority complaint." maxLength={2000}/></label><div className="grid three"><label>Budget ceiling (₹ lakh)<input type="number" min="0" value={budget} onChange={e=>setBudget(Number(e.target.value))}/></label><label>Timeline (days)<input type="number" min="0" value={days} onChange={e=>setDays(Number(e.target.value))}/></label><label>Extra road space available (m)<input type="number" min="0" value={row} onChange={e=>setRow(Number(e.target.value))}/></label></div>
        <div className="checks"><label><input type="checkbox" checked={noConstruction} onChange={e=>setNoConstruction(e.target.checked)}/>No construction</label><label><input type="checkbox" checked={noClosures} onChange={e=>setNoClosures(e.target.checked)}/>No road closures</label><label><input type="checkbox" checked={preserveBus} onChange={e=>setPreserveBus(e.target.checked)}/>Preserve bus corridor</label></div><p className="muted">Costs and scores are simulated assumptions. Only the displayed structured constraints are automatically enforced.</p><button disabled={busy || readOnly}>Review eligible options →</button></form>
        {plan && <div className="plan">{plan.result.target_complaint && <div className="priority-explanation"><strong>{plan.result.review_action}</strong><p>Focused report: {plan.result.target_complaint.description}</p><small>Tracking ID: {plan.result.target_complaint.id}</small></div>}<span className="tag">{plan.result.rag.mode} · {plan.result.rag.retrieval}</span><h3>Suggested next steps</h3><p>{plan.result.rag.explanation}</p>{plan.result.rag.fallback_reason && <p className="muted">{plan.result.rag.fallback_reason}</p>}{plan.result.candidates.length ? plan.result.candidates.map((c:Row)=><article className="candidate" key={c.id}><strong>{c.name}</strong><span>₹{c.cost_lakhs} lakh · {c.days} days</span><p>{c.authority}</p><small>{c.estimate_provenance}</small></article>) : <div className="empty">No suggestion fits the current limits. Increase the budget or timeline, allow construction or road closures, or add more extra road space.</div>}<h3>Enforced constraints</h3><pre>{JSON.stringify(plan.result.constraints,null,2)}</pre><details open={!plan.result.candidates.length}><summary>Excluded options ({plan.result.rejected.length})</summary>{plan.result.rejected.map((c:Row)=><p key={c.id}>{c.name}: {c.reasons.join(", ")}</p>)}</details><details><summary>Retrieved references</summary>{plan.result.rag.citations.map((c:Row)=><p key={c.id}><strong>[{c.id}] {c.title}</strong><br/>{c.excerpt}<br/><small>{c.source} · {c.provenance}</small></p>)}</details><button className="secondary" disabled={busy || readOnly || plan.status!=="proposed" || !plan.result.candidates.length} onClick={()=>run(async()=>{setPlan(await request("/plans/"+plan.id+"/approve",token,{},"POST"));await refresh();})}>Approve for human review</button><p className="muted">Status: {plan.status}. Verify the work and update the complaint status separately. Approval records a local decision; it does not dispatch work to an authority.</p></div>}
      </section>

      </>}
      <section id="reports" className="card"><div className="section-head"><h2>{role==="planner"?"Assigned ward reports":"Your reports"}</h2><button className="quiet" onClick={()=>run(()=>refresh())}>Refresh ↻</button></div><p className="muted">Updates every 10 seconds. {role === "planner" ? "Showing the top 5 unresolved issues, highest priority first and oldest first for ties. Resolving an issue brings the next waiting issue into view. " : "Only reports submitted from this account are shown, including pending, in-progress, and resolved reports. "}Submitted reports are citizen statements, not verified sensor readings.</p>{!visibleComplaints.length && <div className="empty">{role === "planner" ? "No unresolved reports in your ward." : "No reports submitted from this account yet."}</div>}{visibleComplaints.map(c=><article className="report" key={c.id}><div className="section-head"><div className="report-labels"><span className={"priority-badge priority-" + (c.priority?.level || "normal")}>{c.priority?.level || "normal"} priority</span><span className="tag">{c.category}</span></div><strong>{c.status.replaceAll("_"," ")}</strong></div><p>{c.description}</p>{c.priority && <div className="priority-explanation"><strong>{c.priority.review}</strong><p>{c.priority.reason}</p><small>Automatically triaged from the report text; requires planner confirmation.</small></div>}<small>Tracking ID: {c.id}<br/>{c.authority}<br/>{c.created_at}</small><p className="muted">{c.analysis?.suggested_fix}</p>{c.media?.map((m:Row)=><p key={m.id} className="muted">Evidence: {m.mime} · {typeof m.analysis==="string"?m.analysis:m.analysis.description}</p>)}{role==="planner" && c.status!=="resolved" && <button className="secondary" disabled={busy} onClick={()=>run(async()=>{await request("/complaints/"+c.id,token,{status:({received:"acknowledged",acknowledged:"in_progress",in_progress:"resolved"} as Row)[c.status]},"PATCH");await refresh();})}>Move to {({received:"acknowledged",acknowledged:"in progress",in_progress:"resolved"} as Row)[c.status]}</button>}</article>)}</section>
      {role==="planner" && <section className="card"><h2>Decision history</h2>{plans.map(p=><p key={p.id}>{p.created_at.slice(0,10)} · {p.result.prompt} · <strong>{p.status}</strong></p>)}<details><summary>Audit trail ({audit.length})</summary>{audit.map(a=><p key={a.id}>{a.created_at} · {a.action} · {a.target_id}</p>)}</details></section>}
      <footer>Hyderabad City Lab · Local prototype · Historical and simulated data are explicitly distinguished.</footer>
    </main></div>;
}
function StudyMap({ wards, lat, lon, selected, onPick }: { wards: Row[]; lat?: number; lon?: number; selected?: number; onPick?: (lat:number,lon:number)=>void }) {
  const x=(v:number)=>(v-78.30)/0.18*600, y=(v:number)=>300-(v-17.40)/0.09*300;
  return <svg className="map" viewBox="0 0 600 300" role="img" aria-label="Illustrative study area map. Use latitude and longitude fields for keyboard location entry." onClick={e=>{if(onPick){const r=e.currentTarget.getBoundingClientRect();onPick(Number((17.49-(e.clientY-r.top)/r.height*.09).toFixed(5)),Number((78.30+(e.clientX-r.left)/r.width*.18).toFixed(5)));}}}>
    <defs><pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M 30 0 L 0 0 0 30" fill="none" stroke="#cbdfea" strokeWidth=".7"/></pattern></defs><rect width="600" height="300" fill="#e9f4fc"/><rect width="600" height="300" fill="url(#grid)"/><path d="M0 235 Q180 200 250 150 T600 70 M80 0 Q170 120 340 200 T600 250" stroke="#fff" strokeWidth="12" fill="none"/><path d="M0 235 Q180 200 250 150 T600 70" stroke="#bad3e5" strokeWidth="2" fill="none"/>
    {wards.map(w=>{const p=w.geometry.coordinates[0];return <g key={w.properties.id}><polygon points={p.map((c:number[])=>x(c[0])+","+y(c[1])).join(" ")} fill={selected===w.properties.id?"#a7d4f4":"#cee7f8"} fillOpacity=".8" stroke="#5a95bf" strokeDasharray="5 3"/><text x={x(p[0][0])+5} y={y(p[2][1])+20} fontSize="11" fill="#245777">{w.properties.name.split(" ")[0]}</text></g>;})}
    {lat!==undefined && lon!==undefined && <circle cx={x(lon)} cy={y(lat)} r="7" fill="#e38d4d" stroke="white" strokeWidth="3"/>}<text x="14" y="282" fill="#4b6d86" fontSize="10">SCHEMATIC · SIMULATED BOUNDARIES</text><text x="568" y="24" fontSize="13" fill="#4b6d86">N ↑</text>
  </svg>;
}
