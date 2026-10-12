// MiMicus cockpit: public view is observation-only. No synthetic agents, data or external effects.
"use strict";
const get = (id) => document.getElementById(id);
const state = { snapshot: null, liveMode: false, paused: false, cursor: 0, eventCount: 0, pending: false, checking: false, filter: "", lastPolicy: "—" };
const eventsPanel = get("activityStream");

function stamp(value) {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.valueOf())) return "—";
  return new Intl.DateTimeFormat("es-AR", {hour:"2-digit", minute:"2-digit", second:"2-digit", hour12:false}).format(date);
}
function limit(value, max = 150) { return String(value ?? "—").slice(0, max); }
function show(id, content) { get(id).textContent = limit(content, 800); }
function mark(id, dot, content, live = false) {
  show(id, content);
  get(dot).classList.toggle("healthy", live);
  get(dot).classList.toggle("unavailable", !live);
}
function filteredRows() {
  const query = state.filter.toLocaleLowerCase("es-AR");
  let visible = 0;
  for (const row of eventsPanel.children) {
    const showRow = !query || (row.dataset.search || "").includes(query);
    row.hidden = !showRow;
    if (showRow) visible++;
  }
  show("filterState", state.filter ? `${visible} COINCIDENCIAS · SOLO LECTURA` : "CONSULTA LOCAL · SIN EFECTOS");
}
function appendEvent(source, message, observedAt, kind = "activity") {
  const row = document.createElement("div");
  row.className = "logline";
  row.dataset.kind = kind;
  const time = document.createElement("time");
  time.textContent = stamp(observedAt);
  const by = document.createElement("b");
  by.textContent = limit(source, 28);
  const content = document.createElement("span");
  content.textContent = limit(message, 1000);
  row.append(time, by, content);
  row.dataset.search = `${by.textContent} ${content.textContent}`.toLocaleLowerCase("es-AR");
  eventsPanel.append(row);
  while (eventsPanel.children.length > 300) eventsPanel.firstElementChild?.remove();
  get("emptyLog").hidden = true;
  state.eventCount += 1;
  filteredRows();
  eventsPanel.scrollTop = eventsPanel.scrollHeight;
  mark("activityStatus", "activityDot", `${state.eventCount} eventos`, true);
}
function renderLiveEvent(record) {
  if (!record || typeof record !== "object" || Array.isArray(record)) return;
  const when = record.as_of ?? record.observed_at;
  if (record.event === "lead_ingested") {
    appendEvent("INGESTA", `${limit(record.lane, 40)} / ${limit(record.prospect_id, 120)} · etapa ${limit(record.outreach_status, 50)} · score setter ${limit(record.setter_score, 12)}`, when);
  } else if (record.event === "laya_reading") {
    state.lastPolicy = limit(record.policy_version, 80);
    appendEvent("LAYA / READ", `${limit(record.prospect_id, 120)} · etapa ${limit(record.commercial_stage, 40)} · evidencias ${limit(record.commercial_evidence_count, 12)} · sustentada ${limit(record.commercial_stage_evidenced, 20)} · política ${state.lastPolicy}`, when);
  } else if (record.event === "decision_emitted") {
    const reasons = Array.isArray(record.reasons) ? record.reasons.map(x => limit(x, 120)).join(" · ") : "";
    appendEvent("LAYA / DECIDE", `${limit(record.prospect_id, 120)} → ${limit(record.disposition, 40)} · ${limit(record.stage, 55)} · ${reasons}`, when, "decision");
    show("decisionDisposition", record.disposition ?? "SIN CLASIFICAR");
    show("decisionProspect", record.prospect_id ?? "Prospecto no identificado");
    show("decisionStage", record.stage);
    show("decisionPolicy", state.lastPolicy);
    show("decisionReasons", reasons || "No detallados");
  } else if (record.event === "batch_complete") {
    const selected = Object.values(record.selected_by_lane ?? {}).reduce((sum, entries) => sum + (Array.isArray(entries) ? entries.length : 0), 0);
    appendEvent("LOTE", `${limit(record.batch_hash, 12)} · seleccionados ${selected} · en espera ${Array.isArray(record.held_ids) ? record.held_ids.length : 0} · rechazados ${Array.isArray(record.rejected_ids) ? record.rejected_ids.length : 0}`, when);
  } else if (record.event === "observer_error") {
    appendEvent("ERROR", `Observador: ${limit(record.error_type, 80)}`, when);
  }
}
async function fetchJson(path) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(path, { cache:"no-store", signal:controller.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status} ${path}`);
    return await response.json();
  } finally { clearTimeout(timeout); }
}
async function pollLiveActivity() {
  if (!state.liveMode || state.paused || state.pending || document.hidden) return;
  state.pending = true;
  try {
    const data = await fetchJson("/api/activity?since=" + state.cursor);
    if (!Array.isArray(data.events) || !Number.isSafeInteger(data.cursor) || data.cursor < state.cursor) {
      throw new Error("Contrato de observador inválido");
    }
    for (const event of data.events) renderLiveEvent(event);
    state.cursor = data.cursor;
    show("cursorLabel", state.cursor);
    show("activityDetail", `Cursor verificado: ${state.cursor}`);
    mark("activityStatus", "activityDot", state.eventCount ? `${state.eventCount} eventos` : "Sin eventos", true);
  } catch(error) {
    mark("activityStatus", "activityDot", "Sin respuesta", false);
    show("activityDetail", String(error.message).slice(0, 100));
  } finally { state.pending = false; }
}
function sourceStatus(local, seconds) {
  mark("edgeStatus", "edgeDot", local ? "Observador HTTP activo" : "Cloudflare operativo", true);
  show("edgeDetail", local ? "Proceso Python / loopback" : "Respuesta verificada de /api/health y /api/runtime");
  mark("coreStatus", "coreDot", local ? "Decisión LAYA disponible" : "Sin conexión pública", local);
  show("coreDetail", local ? "MiMicusEngine vía observador de sólo lectura" : "El Worker público no ejecuta el núcleo Python");
  mark("effectStatus", "effectsDot", "DENY BY DEFAULT", false);
  if (!state.liveMode && local) state.cursor = 0;
  state.liveMode = local;
  mark("activityStatus", "activityDot", local ? (state.eventCount ? `${state.eventCount} eventos` : "Esperando eventos") : "Sin conexión", local);
  show("activityDetail", local ? "Flujo de eventos del observador Python" : "No hay eventos del núcleo en el Worker público");
  show("sourceLabel", local ? "ORIGEN / LAYA LOCAL" : "ORIGEN / EDGE");
  show("originStatus", local ? "LAYA local" : "Edge / sin núcleo");
  show("heroSource", local ? "OBSERVADOR LOCAL" : "SIN TELEMETRÍA LAYA");
  show("modeLabel", local ? "LAYA / OBSERVADOR LOCAL" : "EDGE / OBSERVACIÓN");
  show("sidebarStatus", local ? "OBSERVADOR ACTIVO" : "LAYA NO CONECTADA");
  show("connectionDetail", local
    ? "El observador Python local está conectado. Muestra decisiones producidas por MiMicusEngine; no puede enviar instrucciones ni ejecutar acciones."
    : "El Worker público está operativo, pero no ejecuta MiMicusEngine ni publica actividad artificial. Iniciá el observador local sobre una fuente de prospectos real para ver ingesta, lectura y decisión.");
  show("lastCheck", stamp(new Date().toISOString()));
  show("edgeLatency", seconds + " ms");
  get("globalState").textContent = local ? "LAYA LOCAL" : "EDGE ONLINE";
  get("globalState").className = "state-pill" + (local ? " live" : "");
  get("pauseStream").disabled = !local;
  if (local) void pollLiveActivity();
  else if (!state.eventCount) get("emptyLog").hidden = false;
}
async function checkNow() {
  if (state.checking) return;
  state.checking = true;
  get("refreshBtn").disabled = true;
  try {
    const start = performance.now();
    const [health, runtime] = await Promise.all([fetchJson("/api/health"), fetchJson("/api/runtime")]);
    if (health?.ok !== true || !runtime || typeof runtime !== "object") throw new Error("Respuesta de servicio inválida");
    const millis = Math.round(performance.now() - start);
    const local = runtime.mode === "local-live-observer" && runtime.decisionAuthority === "MiMicusEngine" && runtime.sideEffects === false;
    state.snapshot = { checkedAt: new Date().toISOString(), responseMs: millis, health, runtime };
    sourceStatus(local, millis);
  } catch (error) {
    state.liveMode = false;
    state.snapshot = {checkedAt:new Date().toISOString(), error:String(error.message)};
    mark("edgeStatus", "edgeDot", "Sin respuesta", false);
    show("edgeDetail", String(error.message).slice(0, 100));
    mark("coreStatus", "coreDot", "No verificable", false);
    mark("activityStatus", "activityDot", "No verificable", false);
    mark("effectStatus", "effectsDot", "No verificable", false);
    show("heroSource", "FUENTE NO DISPONIBLE");
    show("originStatus", "No verificable");
    show("sidebarStatus", "ERROR DE CONEXIÓN");
    show("sourceLabel", "ORIGEN / ERROR");
    show("lastCheck", stamp(new Date().toISOString()));
    show("edgeLatency", "—");
    get("globalState").textContent = "NO VERIFICADO";
    get("globalState").className = "state-pill offline";
    get("pauseStream").disabled = true;
  } finally { get("refreshBtn").disabled = false; state.checking = false; }
}
get("refreshBtn").addEventListener("click", () => void checkNow());
get("pauseStream").addEventListener("click", () => {
  if (!state.liveMode) return;
  state.paused = !state.paused;
  show("pauseStream", state.paused ? "REANUDAR FEED" : "PAUSAR FEED");
  if (!state.paused) void pollLiveActivity();
});
get("filterForm").addEventListener("submit", event => {
  event.preventDefault();
  state.filter = get("leadFilter").value.trim().slice(0, 120);
  filteredRows();
});
get("clearFilter").addEventListener("click", () => {
  state.filter = "";
  get("leadFilter").value = "";
  filteredRows();
});
get("copyDiagnostics").addEventListener("click", async () => {
  if (!state.snapshot) return;
  try {
    await navigator.clipboard.writeText(JSON.stringify(state.snapshot, null, 2));
    show("copyDiagnostics", "DIAGNÓSTICO COPIADO ↗");
  } catch { show("copyDiagnostics", "NO SE PUDO COPIAR"); }
  setTimeout(() => show("copyDiagnostics", "COPIAR DIAGNÓSTICO ↗"), 1800);
});
function utcClock() {
  const time = new Date().toISOString().slice(11, 19) + " UTC";
  show("utcClock", time);
  show("footerTime", time);
}
utcClock();
setInterval(utcClock, 1000);
void checkNow();
setInterval(() => {
  if (document.hidden) return;
  if (state.liveMode) void pollLiveActivity();
  else void checkNow();
}, 5000);

// Self-contained visual, conceptual topology. Never construed as live telemetry.
const canvas = get("topologyCanvas");
const context = canvas.getContext("2d", {alpha:true});
if (context) {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  const geom = {w:0,h:0, px:0, py:0, targetX:0, targetY:0, phase:0, active:!reduced.matches, dragging:false, last:0};
  function resize() {
    const rect = canvas.getBoundingClientRect();
    geom.w = Math.max(1, rect.width); geom.h = Math.max(1, rect.height);
    const ratio = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(geom.w * ratio);
    canvas.height = Math.round(geom.h * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
  }
  resize();
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(resize).observe(canvas);
  else window.addEventListener("resize", resize);
  canvas.addEventListener("pointermove", e => {
    const rect = canvas.getBoundingClientRect();
    geom.targetX = Math.max(-1, Math.min(1, 2 * (e.clientX - rect.left) / rect.width - 1));
    geom.targetY = Math.max(-1, Math.min(1, 2 * (e.clientY - rect.top) / rect.height - 1));
  });
  canvas.addEventListener("pointerleave", () => {geom.targetX=0;geom.targetY=0;});
  canvas.addEventListener("pointerdown", e => {geom.dragging=true;canvas.setPointerCapture?.(e.pointerId);});
  canvas.addEventListener("pointerup", () => {geom.dragging=false;});
  function draw() {
    const {w,h} = geom;
    context.clearRect(0,0,w,h);
    geom.px += (geom.targetX-geom.px)*.035;
    geom.py += (geom.targetY-geom.py)*.035;
    const cx = w*.51 + geom.px*15, cy = h*.54 + geom.py*13;
    const r = Math.min(w*.24,h*.38,170);
    const phase = geom.phase;
    context.save();
    context.lineWidth = .75;
    // Eight deforming radial ribbons describe topology, not active-agent counts.
    for(let arm=0; arm<8; arm++){
      const angle = Math.PI*2*arm/8 + phase*.052;
      const outer = r * 1.64;
      const endX = cx + Math.cos(angle)*outer;
      const endY = cy + Math.sin(angle)*outer*.8;
      const bend = Math.sin(phase*.36+arm*.93)*r*.19;
      for(let fiber=0;fiber<5;fiber++){
        const offset=(fiber-2)*5.1;
        const x1=cx+Math.cos(angle+1.55)*offset;
        const y1=cy+Math.sin(angle+1.55)*offset;
        const x2=endX+Math.cos(angle+1.55)*offset*.65;
        const y2=endY+Math.sin(angle+1.55)*offset*.65;
        const controlX=cx+Math.cos(angle)*r*.95 + Math.cos(angle+1.5)*bend;
        const controlY=cy+Math.sin(angle)*r*.78 + Math.sin(angle+1.5)*bend;
        context.beginPath();context.moveTo(x1,y1);
        context.quadraticCurveTo(controlX,controlY,x2,y2);
        context.strokeStyle=`rgba(209,207,209,${.105+(2-Math.abs(fiber-2))*.047})`;context.stroke();
      }
      context.beginPath();context.arc(endX,endY,2,0,Math.PI*2);context.fillStyle="rgba(233,230,226,.45)";context.fill();
    }
    const pointCount = 90;
    for(let i=0;i<pointCount;i++){
      const a=i*2.39996322973+phase*.009;
      const radius=Math.sqrt((i+.5)/pointCount)*r*1.45;
      const px=cx+Math.cos(a)*radius*1.23,py=cy+Math.sin(a)*radius*.78;
      const t=.16+.20*Math.sin(i*9+phase*.19);
      context.fillStyle=`rgba(244,239,232,${Math.max(.07,t)})`;
      context.fillRect(px,py,i%9===0?2:1,i%9===0?2:1);
    }
    // Core geodesic-like orbital cage with projections, no third-party renderer.
    const rings=11, points=42;
    for(let ring=1;ring<=rings;ring++){
      context.beginPath();
      const lat=-Math.PI/2 + ring*Math.PI/(rings+1);
      const scale=Math.cos(lat), depth=Math.sin(lat);
      for(let i=0;i<=points;i++){
        const longitude=(i%points)/points*Math.PI*2+phase*.10;
        const x=cx+Math.cos(longitude)*scale*r*.71 + Math.sin(depth+phase*.07)*7;
        const y=cy+Math.sin(longitude)*scale*r*.28 + depth*r*.58;
        i===0?context.moveTo(x,y):context.lineTo(x,y);
      }
      context.strokeStyle=`rgba(236,233,226,${.105+(ring===6?.2:.04)})`;context.stroke();
    }
    for(let meridian=0;meridian<13;meridian++){
      context.beginPath();
      const longitude=meridian/13*Math.PI*2+phase*.10;
      for(let i=0;i<=32;i++){
        const lat=-Math.PI/2+i*Math.PI/32;
        const x=cx+Math.cos(longitude)*Math.cos(lat)*r*.71 + Math.sin(Math.sin(lat)+phase*.07)*7;
        const y=cy+Math.sin(longitude)*Math.cos(lat)*r*.28 + Math.sin(lat)*r*.58;
        i===0?context.moveTo(x,y):context.lineTo(x,y);
      }
      context.strokeStyle="rgba(234,231,222,.21)";context.stroke();
    }
    context.beginPath();context.ellipse(cx,cy,r*.73,r*.29,0,0,Math.PI*2);
    context.strokeStyle="rgba(239,235,227,.34)";context.stroke();
    context.beginPath();context.arc(cx,cy,r*.32,0,Math.PI*2);
    context.fillStyle="rgba(9,9,12,.84)";context.fill();
    context.strokeStyle="rgba(228,226,221,.45)";context.stroke();
    context.restore();
    show("heroCoordinates", `X ${geom.px>=0?"+":""}${geom.px.toFixed(2)} / Y ${geom.py>=0?"+":""}${geom.py.toFixed(2)}`);
  }
  function frame(now) {
    if (!geom.last) geom.last=now;
    const delta = Math.min(80,now-geom.last);
    geom.last=now;
    if(geom.active && !document.hidden)geom.phase+=delta/1000;
    draw();
    requestAnimationFrame(frame);
  }
  const toggle=get("topologyToggle");
  if(reduced.matches){geom.active=false;show("topologyToggle","MOVIMIENTO REDUCIDO");}
  toggle.addEventListener("click",()=>{geom.active=!geom.active;show("topologyToggle",geom.active?"PAUSAR MOVIMIENTO":"REANUDAR MOVIMIENTO");});
  requestAnimationFrame(frame);
}
