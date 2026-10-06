const stream = document.getElementById("activityStream");
const pauseButton = document.getElementById("pauseStream");
const autopilot = document.getElementById("autopilot");
const modePill = document.getElementById("modePill");
const truthBanner = document.getElementById("truthBanner");

let paused = false;
let simulationCursor = 0;
let simulationTimer = null;
let liveTimer = null;
let liveCursor = 0;
let liveMode = false;

const simulationLines = [
  ["SISTEMA","QA pass 78s. Staging lista. Infata ST probe aprobar on clic."],
  ["LAYA","Token burn 111 t/h — rote-only intacta."],
  ["ESPÍA","Envío bloqueado hasta human-gate."],
  ["CAZADOR","12 nuevos leads agendados — Industria: Real Estate."],
  ["CAZADOR","12 nuevos leads agendados — Industria: Real Estate (AR)."],
  ["EXTRACCIÓN","Prepara agendado con Cliente Demo — ventana 18:00."],
  ["LAYA","Asigna asincronía unidad data — Dataset Demo."],
  ["LOGÍSTICO","Queue consolidada; 0 duplicados; 3 handoffs confirmados."],
  ["SETTER","Secuencia de seguimiento preparada; salida externa deshabilitada."],
  ["SISTEMA","Checkpoint histórico del core: 565407e · no implica HEAD actual."]
];

function stamp(value = new Date()){
  const date = value instanceof Date ? value : new Date(value);
  const safeDate = Number.isNaN(date.getTime()) ? new Date() : date;
  return new Intl.DateTimeFormat("es-AR",{
    hour:"2-digit",
    minute:"2-digit",
    second:"2-digit",
    hour12:false
  }).format(safeDate);
}

function appendLog(agent,msg,when){
  const row = document.createElement("div");
  row.className = "logline";

  const time = document.createElement("time");
  time.textContent = stamp(when);

  const label = document.createElement("b");
  label.textContent = String(agent ?? "SISTEMA");

  const body = document.createElement("span");
  body.textContent = String(msg ?? "");

  row.append(time,label,body);
  stream.append(row);
  while(stream.children.length > 16) stream.firstElementChild?.remove();
  stream.scrollTop = stream.scrollHeight;
}

function appendSimulationLine(){
  if(paused || liveMode) return;
  const [agent,msg] = simulationLines[simulationCursor++ % simulationLines.length];
  appendLog(`SIM/${agent}`,msg);
}

function startSimulation(){
  if(liveMode || simulationTimer) return;
  modePill.textContent="SIMULACIÓN";
  truthBanner.innerHTML="<b>SIMULATED_FIXTURE</b> · datos sintéticos de demostración; no representan actividad, ingresos ni conversiones reales.";
  document.getElementById("runtimeStatus").textContent="SIMULATED_FIXTURE";
  for(let i=0;i<7;i++) appendSimulationLine();
  simulationTimer = setInterval(appendSimulationLine,5200);
}

function setLiveMetricMode(){
  document.getElementById("mAgents").textContent="LAYA";
  document.getElementById("mLeads").textContent="0";
  document.getElementById("mConv").textContent="—";
  document.getElementById("mCpu").textContent="—";
  document.getElementById("mPipeline").textContent="—";
  document.getElementById("mPipeline2").textContent="—";
  document.getElementById("mCollected").textContent="—";
}

function selectedCount(selectedByLane){
  return Object.values(selectedByLane ?? {}).reduce(
    (total, ids)=>total + (Array.isArray(ids) ? ids.length : 0),
    0
  );
}

function renderLiveEvent(row){
  const when = row.as_of ?? row.observed_at;

  if(row.event === "lead_ingested"){
    const score = row.setter_score ?? "—";
    appendLog(
      "SETTER",
      `${String(row.lane ?? "").toUpperCase()} · ${row.prospect_id} · ${row.outreach_status} · score ${score}`,
      when
    );
    return;
  }

  if(row.event === "laya_reading"){
    const stage = row.commercial_stage ?? "unknown";
    const evidenceCount = row.commercial_evidence_count ?? 0;
    const evidenceMatch = row.commercial_stage_evidenced === true
      ? "yes"
      : row.commercial_stage_evidenced === false
        ? "no"
        : "—";
    appendLog(
      "LAYA",
      `Leyendo ${row.prospect_id} · stage ${stage} · evidence ${evidenceCount} · matched ${evidenceMatch} · policy ${row.policy_version ?? "—"} · risk ${row.scam_risk ?? "—"} · active ${row.active ?? "—"}`,
      when
    );
    return;
  }

  if(row.event === "decision_emitted"){
    const reasons = Array.isArray(row.reasons) && row.reasons.length
      ? ` · ${row.reasons.join(" · ")}`
      : "";
    appendLog(
      "LAYA",
      `${row.prospect_id} → ${row.disposition} · ${row.stage}${reasons}`,
      when
    );
    return;
  }

  if(row.event === "batch_complete"){
    const selected = selectedCount(row.selected_by_lane);
    const held = Array.isArray(row.held_ids) ? row.held_ids.length : 0;
    const rejected = Array.isArray(row.rejected_ids) ? row.rejected_ids.length : 0;
    const repair = Array.isArray(row.repair_data_ids) ? row.repair_data_ids.length : 0;
    const total = selected + held + rejected + repair;
    document.getElementById("mLeads").textContent=String(total);
    appendLog(
      "SISTEMA",
      `Batch ${String(row.batch_hash ?? "").slice(0,8)} · work ${selected} · hold ${held} · repair ${repair} · reject ${rejected}`,
      when
    );
    return;
  }

  if(row.event === "observer_error"){
    appendLog(
      "SISTEMA",
      `Observer degradado · ${row.error_type ?? "unknown"}`,
      when
    );
  }
}

async function pollLiveActivity(){
  if(paused || !liveMode) return;
  try{
    const response = await fetch(`/api/activity?since=${liveCursor}`,{cache:"no-store"});
    if(!response.ok) throw new Error(`activity HTTP ${response.status}`);
    const payload = await response.json();
    const events = Array.isArray(payload.events) ? payload.events : [];
    for(const row of events) renderLiveEvent(row);
    if(Number.isInteger(payload.cursor)) liveCursor = payload.cursor;
    document.getElementById("runtimeStatus").textContent="LIVE LAYA";
  }catch{
    document.getElementById("runtimeStatus").textContent="OBSERVER DEGRADED";
  }
}

function startLiveActivity(){
  if(liveMode) return;
  liveMode = true;
  if(simulationTimer){
    clearInterval(simulationTimer);
    simulationTimer = null;
  }
  stream.replaceChildren();
  setLiveMetricMode();
  document.getElementById("runtimeStatus").textContent="LIVE LAYA";
  modePill.textContent="LIVE OBSERVER";
  truthBanner.innerHTML="<b>LIVE_OBSERVED</b> · observer local read-only conectado; las decisiones externas permanecen deshabilitadas.";
  appendLog("SISTEMA","Observer local conectado · decisiones externas deshabilitadas.");
  void pollLiveActivity();
  liveTimer = setInterval(()=>{ void pollLiveActivity(); },1000);
}

pauseButton.addEventListener("click",()=>{
  paused=!paused;
  pauseButton.textContent = paused ? "RESUME" : "PAUSE";
  if(!paused && liveMode) void pollLiveActivity();
});

autopilot.addEventListener("change",()=>{
  appendLog(
    "LAYA",
    `Autopilot SIM ${autopilot.checked?"ON":"OFF"} — no external side effects.`
  );
});

document.querySelectorAll(".agent").forEach(node=>{
  node.addEventListener("click",()=>{
    appendLog(
      node.dataset.agent,
      "Inspector local: nodo activo, policy intacta, authority sin expansión."
    );
  });
});

async function boot(){
  const started=performance.now();
  try{
    const [health,runtime]=await Promise.all([
      fetch("/api/health",{cache:"no-store"}).then(r=>r.json()),
      fetch("/api/runtime",{cache:"no-store"}).then(r=>r.json())
    ]);
    document.getElementById("apiLatency").textContent=`${Math.max(1,Math.round(performance.now()-started))}ms`;

    if(runtime?.mode === "local-live-observer"){
      startLiveActivity();
      return;
    }

    document.getElementById("runtimeStatus").textContent=health.ok ? (runtime?.evidenceClass ?? "SIMULATED_FIXTURE") : "DEGRADED";
    if(runtime?.historicalCoreCheckpoint){
      appendLog(
        "SISTEMA",
        `Checkpoint histórico: ${runtime.historicalCoreCheckpoint.slice(0,7)} · ${runtime.morphologies.length} morphologies.`
      );
    }
    startSimulation();
  }catch{
    document.getElementById("runtimeStatus").textContent="LOCAL PREVIEW · SIMULATED_FIXTURE";
    startSimulation();
  }
}

boot();
