// Never synthesize commercial metrics, agent conversations or activity events.
const get = (id) => document.getElementById(id);
const activityStream = get("activityStream");
const pauseButton = get("pauseStream");
const refreshButton = get("refreshBtn");
let snapshot = null;
let liveMode = false;
let paused = false;
let liveCursor = 0;
let verifiedEvents = 0;
let inFlight = false;

function markStatus(id, dotId, text, good = false) {
  get(id).textContent = text;
  const dot = get(dotId);
  dot.classList.toggle("healthy", good);
  dot.classList.toggle("unavailable", !good);
}

function localTime(date = new Date()) {
  return new Intl.DateTimeFormat("es-AR", {
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false
  }).format(date);
}

function appendVerifiedEvent(agent, message, when) {
  const row = document.createElement("div");
  row.className = "logline";
  const time = document.createElement("time");
  time.textContent = localTime(when && !Number.isNaN(new Date(when).getTime()) ? new Date(when) : new Date());
  const label = document.createElement("b");
  label.textContent = String(agent ?? "SISTEMA").slice(0, 40);
  const body = document.createElement("span");
  body.textContent = String(message ?? "").slice(0, 1200);
  row.append(time, label, body);
  activityStream.append(row);
  while (activityStream.children.length > 200) activityStream.firstElementChild?.remove();
  get("emptyLog").hidden = true;
  activityStream.scrollTop = activityStream.scrollHeight;
  verifiedEvents += 1;
  get("activityStatus").textContent = verifiedEvents + " eventos";
}

function renderLiveEvent(row) {
  if (!row || typeof row !== "object") return;
  const when = row.as_of ?? row.observed_at;
  if (row.event === "lead_ingested") {
    appendVerifiedEvent("SETTER", `${row.lane ?? "—"} · ${row.prospect_id ?? "—"} · ${row.outreach_status ?? "—"} · score ${row.setter_score ?? "—"}`, when);
  } else if (row.event === "laya_reading") {
    appendVerifiedEvent("LAYA", `Lectura ${row.prospect_id ?? "—"} · etapa ${row.commercial_stage ?? "—"} · evidencias ${row.commercial_evidence_count ?? "—"} · coincide ${row.commercial_stage_evidenced ?? "—"} · política ${row.policy_version ?? "—"}`, when);
  } else if (row.event === "decision_emitted") {
    appendVerifiedEvent("LAYA", `${row.prospect_id ?? "—"} → ${row.disposition ?? "—"} · ${row.stage ?? "—"} · ${Array.isArray(row.reasons) ? row.reasons.join(", ") : ""}`, when);
  } else if (row.event === "batch_complete") {
    const selected = Object.values(row.selected_by_lane ?? {}).reduce((total, entries) => total + (Array.isArray(entries) ? entries.length : 0), 0);
    appendVerifiedEvent("SISTEMA", `Lote ${String(row.batch_hash ?? "—").slice(0, 12)} · tickets ${selected} · retenidos ${Array.isArray(row.held_ids) ? row.held_ids.length : 0}`, when);
  } else if (row.event === "observer_error") {
    appendVerifiedEvent("OBSERVADOR", `Error observado: ${row.error_type ?? "desconocido"}`, when);
  }
}

async function fetchJson(path) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(path, { cache: "no-store", signal: controller.signal });
    if (!response.ok) throw new Error("HTTP " + response.status + " " + path);
    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
}

async function pollLiveActivity() {
  if (!liveMode || paused || inFlight) return;
  inFlight = true;
  try {
    const result = await fetchJson("/api/activity?since=" + liveCursor);
    if (!Array.isArray(result.events) || !Number.isSafeInteger(result.cursor) || result.cursor < liveCursor) {
      throw new Error("Contrato del observador inválido");
    }
    for (const event of result.events) renderLiveEvent(event);
    liveCursor = result.cursor;
    markStatus("activityStatus", "activityDot", verifiedEvents ? verifiedEvents + " eventos" : "Sin eventos", true);
    get("activityDetail").textContent = "Último cursor confirmado: " + liveCursor;
  } catch (error) {
    markStatus("activityStatus", "activityDot", "Sin respuesta", false);
    get("activityDetail").textContent = String(error.message).slice(0, 100);
  } finally {
    inFlight = false;
  }
}

async function checkNow() {
  refreshButton.disabled = true;
  get("lastCheck").textContent = "Comprobando…";
  const start = performance.now();
  try {
    const [health, runtime] = await Promise.all([fetchJson("/api/health"), fetchJson("/api/runtime")]);
    if (health?.ok !== true || !runtime || typeof runtime !== "object") throw new Error("Respuesta inválida");
    const seconds = Math.round(performance.now() - start);
    const local = runtime.mode === "local-live-observer";
    liveMode = local;
    snapshot = {
      observedAt: new Date().toISOString(),
      edgeLatencyMs: seconds,
      health,
      runtime
    };
    markStatus("edgeStatus", "edgeDot", local ? "HTTP local activo" : "HTTP activo", true);
    get("edgeDetail").textContent = local ? "Servidor observador en localhost" : "Worker respondió a dos comprobaciones reales";
    markStatus("coreStatus", "coreDot", local ? "Observador conectado" : "No conectado", local);
    get("coreDetail").textContent = local
      ? "Observador Python local de decisiones LAYA, solo lectura"
      : "El Worker público no ejecuta MiMicusEngine";
    markStatus("effectStatus", "effectsDot", "Deshabilitadas", false);
    markStatus("activityStatus", "activityDot", local ? "Esperando eventos" : "Sin conexión", local);
    get("activityDetail").textContent = local ? "Origen: observador Python" : "No hay canal de eventos real en esta superficie";
    get("sourceLabel").textContent = local ? "ORIGEN: LAYA LOCAL" : "ORIGEN: NO CONECTADO";
    get("originStatus").textContent = local ? "Observador local" : "Worker real / núcleo ausente";
    get("sidebarStatus").textContent = local ? "LAYA: observador conectado" : "Edge online · LAYA no conectada";
    get("connectionDetail").textContent = local
      ? "Observador Python operativo. Registro de decisiones verificadas, sin canal de instrucciones ni acciones externas."
      : "La web pública funciona, pero el núcleo Python no está enlazado. No hay chat grupal activo ni agentes ejecutándose desde esta web. Para ver eventos reales, iniciá el observador local sobre una fuente real.";
    get("lastCheck").textContent = localTime();
    get("edgeLatency").textContent = seconds + " ms";
    pauseButton.disabled = !local;
    if (local) {
      await pollLiveActivity();
    } else {
      get("emptyLog").hidden = false;
      if (!verifiedEvents) activityStream.replaceChildren();
    }
  } catch (error) {
    liveMode = false;
    snapshot = { observedAt: new Date().toISOString(), error: String(error.message) };
    markStatus("edgeStatus", "edgeDot", "Sin respuesta", false);
    get("edgeDetail").textContent = String(error.message).slice(0, 120);
    markStatus("coreStatus", "coreDot", "No verificable", false);
    markStatus("activityStatus", "activityDot", "No verificable", false);
    markStatus("effectStatus", "effectsDot", "No verificable", false);
    get("originStatus").textContent = "Sin conexión";
    get("sidebarStatus").textContent = "Error de comprobación";
    get("lastCheck").textContent = localTime();
    get("edgeLatency").textContent = "—";
    get("sourceLabel").textContent = "ORIGEN: ERROR";
    pauseButton.disabled = true;
  } finally {
    refreshButton.disabled = false;
  }
}

pauseButton.addEventListener("click", () => {
  if (!liveMode) return;
  paused = !paused;
  pauseButton.textContent = paused ? "Reanudar" : "Pausar";
  if (!paused) void pollLiveActivity();
});
refreshButton.addEventListener("click", () => { void checkNow(); });
get("copyDiagnostics").addEventListener("click", async () => {
  if (!snapshot) return;
  try {
    await navigator.clipboard.writeText(JSON.stringify(snapshot, null, 2));
    get("copyDiagnostics").textContent = "Copiado";
  } catch {
    get("copyDiagnostics").textContent = "No se pudo copiar";
  }
  setTimeout(() => { get("copyDiagnostics").textContent = "Copiar diagnóstico"; }, 1800);
});
void checkNow();
setInterval(() => {
  if (!document.hidden) {
    if (liveMode) { void pollLiveActivity(); }
    else { void checkNow(); }
  }
}, 5000);
