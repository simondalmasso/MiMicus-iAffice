const stream = document.getElementById("activityStream");
const pauseButton = document.getElementById("pauseStream");
const autopilot = document.getElementById("autopilot");
let paused = false;
let cursor = 0;

const lines = [
  ["SISTEMA","QA pass 78s. Staging lista. Infata ST probe aprobar on clic."],
  ["LAYA","Token burn 111 t/h — rote-only intacta."],
  ["ESPÍA","Envío bloqueado hasta human-gate."],
  ["CAZADOR","12 nuevos leads agendados — Industria: Real Estate."],
  ["CAZADOR","12 nuevos leads agendados — Industria: Real Estate (AR)."],
  ["EXTRACCIÓN","Prepara agendado con Estudio Contable Purenal — Cliente 18:00."],
  ["LAYA","Asigna asincronía unidad data — Rendimiento Puerto SF."],
  ["LOGÍSTICO","Queue consolidada; 0 duplicados; 3 handoffs confirmados."],
  ["SETTER","Secuencia de seguimiento preparada; salida externa deshabilitada."],
  ["SISTEMA","MiMicus immune core archivado y trazable en source 565407e."]
];

function stamp(){
  return new Intl.DateTimeFormat("es-AR",{hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false}).format(new Date());
}
function appendLine(){
  if(paused) return;
  const [agent,msg] = lines[cursor++ % lines.length];
  const row = document.createElement("div");
  row.className = "logline";
  row.innerHTML = `<time>${stamp()}</time><b>${agent}</b><span>${msg}</span>`;
  stream.append(row);
  while(stream.children.length > 11) stream.firstElementChild?.remove();
  stream.scrollTop = stream.scrollHeight;
}
for(let i=0;i<7;i++) appendLine();
setInterval(appendLine, 5200);

pauseButton.addEventListener("click",()=>{
  paused=!paused;
  pauseButton.textContent = paused ? "RESUME" : "PAUSE";
});
autopilot.addEventListener("change",()=>{
  const row = document.createElement("div");
  row.className="logline";
  row.innerHTML=`<time>${stamp()}</time><b>LAYA</b><span>Autopilot SIM ${autopilot.checked?"ON":"OFF"} — no external side effects.</span>`;
  stream.append(row); stream.scrollTop=stream.scrollHeight;
});

document.querySelectorAll(".agent").forEach(node=>{
  node.addEventListener("click",()=>{
    const agent=node.dataset.agent;
    const row=document.createElement("div");
    row.className="logline";
    row.innerHTML=`<time>${stamp()}</time><b>${agent}</b><span>Inspector local: nodo activo, policy intacta, authority sin expansión.</span>`;
    stream.append(row); stream.scrollTop=stream.scrollHeight;
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
    document.getElementById("runtimeStatus").textContent=health.ok ? "EDGE READY" : "DEGRADED";
    if(runtime?.sourceHead){
      const row=document.createElement("div");row.className="logline";
      row.innerHTML=`<time>${stamp()}</time><b>SISTEMA</b><span>Core absorbido: ${runtime.sourceHead.slice(0,7)} · ${runtime.morphologies.length} morphologies.</span>`;
      stream.append(row);
    }
  }catch{
    document.getElementById("runtimeStatus").textContent="LOCAL PREVIEW";
  }
}
boot();
