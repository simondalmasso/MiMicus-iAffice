#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import html
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import resource
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROTOCOL = "iaffice-executor-v1"
EXECUTOR_ID = os.environ.get("IAFFICE_EXECUTOR_ID", "ORACLE_FREE_EXECUTOR")
ROOT = Path(os.environ.get("IAFFICE_EXECUTOR_ROOT", "/var/lib/iaffice-executor"))
CALLBACK_URL = os.environ.get("IAFFICE_CORE_CALLBACK_URL", "")
SIGNING_KEY = os.environ.get("IAFFICE_EXECUTOR_SIGNING_KEY", "")
BIND = os.environ.get("IAFFICE_EXECUTOR_BIND", "127.0.0.1")
PORT = int(os.environ.get("IAFFICE_EXECUTOR_PORT", "8788"))
MAX_BODY = 512 * 1024
MAX_TTL_SECONDS = 15 * 60

JOB_PATHS = {
    "DISCOVERY_WEB_AUDIT": "/v1/jobs/discovery-web-audit",
    "DEMO_WEB_BUILD": "/v1/jobs/demo-web-build",
    "DEMO_BROWSER_3D": "/v1/jobs/demo-browser-3d",
    "DEMO_HEAVY_3D": "/v1/jobs/demo-heavy-3d",
}
ARTIFACT_KIND = {"html": "WEB_PREVIEW", "json": "DOCUMENT", "glb": "THREE_D", "py": "CODE"}


def canonical(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not value == value or value in (float("inf"), float("-inf")):
            raise ValueError("NON_FINITE_NUMBER")
        if value.is_integer():
            return str(int(value))
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(canonical(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            json.dumps(str(k), ensure_ascii=False) + ":" + canonical(value[k])
            for k in sorted(value.keys())
        ) + "}"
    raise TypeError("UNSUPPORTED_CANONICAL_TYPE")


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sign(value: Any) -> str:
    if len(SIGNING_KEY) < 8:
        raise RuntimeError("EXECUTOR_SIGNING_KEY_REQUIRED")
    return hmac.new(SIGNING_KEY.encode("utf-8"), canonical(value).encode("utf-8"), hashlib.sha256).hexdigest()


def parse_iso(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("TIME_INVALID")
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return dt.astimezone(timezone.utc)


def exact_keys(value: Any, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value.keys()) == keys


def validate_demo_payload(payload: Any) -> bool:
    keys = {
        "businessName", "category", "locality", "servicePackId",
        "requestedDeliverables", "evidenceRefs", "observedFacts", "demoBrief"
    }
    if not exact_keys(payload, keys):
        return False
    for key in ("businessName", "category", "locality", "servicePackId", "demoBrief"):
        if not isinstance(payload[key], str) or not payload[key].strip():
            return False
    for key in ("requestedDeliverables", "evidenceRefs", "observedFacts"):
        if not isinstance(payload[key], list) or not payload[key]:
            return False
        if not all(isinstance(x, str) and x.strip() for x in payload[key]):
            return False
    return True


def validate_discovery_payload(payload: Any) -> bool:
    return (
        exact_keys(payload, {"targetUrl", "auditProfile"})
        and payload.get("auditProfile") == "PUBLIC_BUSINESS_WEB"
        and isinstance(payload.get("targetUrl"), str)
        and payload["targetUrl"].startswith(("https://", "http://"))
    )


def verify_artifact_request(path: str, timestamp_raw: str | None, signature: str | None) -> bool:
    try:
        if not timestamp_raw or not signature or not re.fullmatch(r"[0-9a-fA-F]{64}", signature):
            return False
        timestamp = int(timestamp_raw)
        if abs(int(time.time()) - timestamp) > 300:
            return False
        message = f"GET\n{path}\n{timestamp}"
        expected = hmac.new(SIGNING_KEY.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature.lower(), expected.lower())
    except Exception:
        return False


def validate_envelope(envelope: Any, request_path: str) -> tuple[bool, str]:
    if not exact_keys(envelope, {"body", "signature", "algorithm"}):
        return False, "ENVELOPE_SHAPE_INVALID"
    if envelope.get("algorithm") != "HMAC-SHA256":
        return False, "ALGORITHM_INVALID"
    body = envelope.get("body")
    body_keys = {
        "protocolVersion", "runId", "executorId", "jobKind", "jobId", "caseId",
        "payload", "payloadDigest", "artifactInputRefs", "expectedCostUsd",
        "issuedAt", "expiresAt", "nonce"
    }
    if not exact_keys(body, body_keys):
        return False, "BODY_SHAPE_INVALID"
    if body["protocolVersion"] != PROTOCOL or body["executorId"] != EXECUTOR_ID:
        return False, "IDENTITY_INVALID"
    kind = body["jobKind"]
    if kind not in JOB_PATHS or JOB_PATHS[kind] != request_path:
        return False, "JOB_KIND_PATH_INVALID"
    if body["expectedCostUsd"] != 0:
        return False, "NONZERO_EXPECTED_COST_FORBIDDEN"
    if not isinstance(body["runId"], str) or not body["runId"]:
        return False, "RUN_ID_REQUIRED"
    if not isinstance(body["jobId"], str) or not body["jobId"]:
        return False, "JOB_ID_REQUIRED"
    if body["caseId"] is not None and not isinstance(body["caseId"], str):
        return False, "CASE_ID_INVALID"
    if not isinstance(body["nonce"], str) or len(body["nonce"]) < 8:
        return False, "NONCE_INVALID"
    if not isinstance(body["artifactInputRefs"], list) or not all(isinstance(x, str) and x for x in body["artifactInputRefs"]):
        return False, "ARTIFACT_INPUT_REFS_INVALID"
    payload_ok = validate_discovery_payload(body["payload"]) if kind == "DISCOVERY_WEB_AUDIT" else validate_demo_payload(body["payload"])
    if not payload_ok:
        return False, "PAYLOAD_INVALID"
    if body["payloadDigest"] != sha256_text(canonical(body["payload"])):
        return False, "PAYLOAD_DIGEST_INVALID"
    try:
        issued = parse_iso(body["issuedAt"])
        expires = parse_iso(body["expiresAt"])
        now = datetime.now(timezone.utc)
        ttl = (expires - issued).total_seconds()
        if ttl <= 0 or ttl > MAX_TTL_SECONDS:
            return False, "TTL_INVALID"
        if now.timestamp() < issued.timestamp() - 60:
            return False, "ISSUED_IN_FUTURE"
        if now > expires:
            return False, "ENVELOPE_EXPIRED"
    except Exception:
        return False, "TIME_INVALID"
    signature = envelope.get("signature")
    if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", signature):
        return False, "SIGNATURE_INVALID"
    if not hmac.compare_digest(signature.lower(), sign(body).lower()):
        return False, "SIGNATURE_INVALID"
    return True, "OK"


def db() -> sqlite3.Connection:
    ROOT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(ROOT / "executor.sqlite3", timeout=30)
    conn.execute("""
      CREATE TABLE IF NOT EXISTS runs(
        run_id TEXT PRIMARY KEY,
        nonce TEXT NOT NULL UNIQUE,
        request_digest TEXT NOT NULL,
        state TEXT NOT NULL,
        result_json TEXT,
        callback_state TEXT NOT NULL DEFAULT 'NONE',
        callback_attempts INTEGER NOT NULL DEFAULT 0,
        callback_error TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )
    """)
    columns={row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
    if "callback_state" not in columns:
        conn.execute("ALTER TABLE runs ADD COLUMN callback_state TEXT NOT NULL DEFAULT 'NONE'")
    if "callback_attempts" not in columns:
        conn.execute("ALTER TABLE runs ADD COLUMN callback_attempts INTEGER NOT NULL DEFAULT 0")
    if "callback_error" not in columns:
        conn.execute("ALTER TABLE runs ADD COLUMN callback_error TEXT")
    conn.commit()
    return conn


def artifact_dir(run_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", run_id)
    out = ROOT / "artifacts" / safe
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_artifact(run_id: str, name: str, content: bytes) -> dict[str, str]:
    out = artifact_dir(run_id)
    path = out / name
    path.write_bytes(content)
    digest = "sha256:" + hashlib.sha256(content).hexdigest()
    ext = path.suffix.lower().lstrip(".")
    return {
        "kind": ARTIFACT_KIND.get(ext, "DOCUMENT"),
        "ref": f"executor://{EXECUTOR_ID}/{run_id}/{name}",
        "digest": digest,
    }


def base_css() -> str:
    return """
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#151515;background:#f3f1eb}
*{box-sizing:border-box}body{margin:0}.shell{max-width:1180px;margin:auto;padding:28px}.private{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#6d6962}
h1{font-size:clamp(34px,6vw,72px);letter-spacing:-.06em;line-height:.95;margin:16px 0}.lead{max-width:760px;font-size:18px;color:#625f59}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:26px}.card{background:#fff;border:1px solid #dad6cc;border-radius:16px;padding:18px}
.facts{display:grid;gap:8px}.fact{padding:12px;border-radius:12px;background:#ece9e1}.cta{display:inline-flex;margin-top:22px;background:#171717;color:#fff;padding:12px 16px;border-radius:999px;text-decoration:none}
.note{margin-top:30px;color:#777167;font-size:12px;border-top:1px solid #d7d2c8;padding-top:14px}@media(max-width:720px){.grid{grid-template-columns:1fr}.shell{padding:18px}}
"""


def build_web_demo(body: dict[str, Any]) -> list[dict[str, str]]:
    p = body["payload"]
    facts = "".join(f'<div class="fact">{html.escape(x)}</div>' for x in p["observedFacts"])
    deliverables = "".join(
        f'<div class="card"><strong>{html.escape(x.replace("_"," ").title())}</strong>'
        '<p>Private proof surface only. No invented prices, stock, specs or performance claims.</p></div>'
        for x in p["requestedDeliverables"]
    )
    doc = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(p["businessName"])} · private demo</title><style>{base_css()}</style></head>
<body><main class="shell"><div class="private">iAffice · private evidence-backed demo · not production</div><h1>{html.escape(p["businessName"])}</h1>
<p class="lead">{html.escape(p["demoBrief"])}</p><section class="grid">{deliverables}</section>
<section style="margin-top:26px"><div class="private">Observed evidence</div><div class="facts">{facts}</div></section>
<a class="cta" href="#" onclick="return false">Preview conversion path</a>
<div class="note">Category: {html.escape(p["category"])} · Area: {html.escape(p["locality"])} · Evidence refs: {len(p["evidenceRefs"])} · This prototype does not publish, send, charge or claim measured uplift.</div></main></body></html>"""
    manifest = {
        "servicePackId": p["servicePackId"],
        "requestedDeliverables": p["requestedDeliverables"],
        "observedFacts": p["observedFacts"],
        "evidenceRefs": p["evidenceRefs"],
        "private": True,
        "production": False,
    }
    return [
        write_artifact(body["runId"], "index.html", doc.encode("utf-8")),
        write_artifact(body["runId"], "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")),
    ]


def webgl_script() -> str:
    return """
const c=document.querySelector('canvas'),gl=c.getContext('webgl',{antialias:true});
if(!gl){document.querySelector('#status').textContent='WebGL unavailable';throw new Error('WEBGL_UNAVAILABLE')}
const vs='attribute vec3 p;uniform mat4 m;void main(){gl_Position=m*vec4(p,1.0);}';
const fs='precision mediump float;uniform vec3 col;void main(){gl_FragColor=vec4(col,1.0);}';
function sh(t,s){const x=gl.createShader(t);gl.shaderSource(x,s);gl.compileShader(x);return x}
const pr=gl.createProgram();gl.attachShader(pr,sh(gl.VERTEX_SHADER,vs));gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(pr);gl.useProgram(pr);
const v=new Float32Array([-1,-1,-1,1,-1,-1,1,1,-1,-1,-1,-1,1,1,-1,-1,1,-1,-1,-1,1,1,-1,1,1,1,1,-1,-1,1,1,1,1,-1,1,1,-1,-1,-1,-1,1,-1,-1,1,1,-1,-1,-1,-1,1,1,-1,-1,1,1,-1,-1,1,1,-1,1,1,1,1,-1,-1,1,1,1,1,-1,1,-1,-1,-1,-1,-1,1,1,-1,1,-1,-1,-1,1,-1,1,1,-1,-1,-1,1,-1,-1,1,1,1,1,1,-1,1,-1,1,1,1,1,1,1,-1]);
const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,v,gl.STATIC_DRAW);const loc=gl.getAttribLocation(pr,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,0,0);
const ml=gl.getUniformLocation(pr,'m'),cl=gl.getUniformLocation(pr,'col');let ax=.45,ay=.65,drag=false,lx=0,ly=0,col=[.22,.28,.34];
function mul(a,b){let o=new Float32Array(16);for(let r=0;r<4;r++)for(let c=0;c<4;c++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o}
function rx(a){let c=Math.cos(a),s=Math.sin(a);return new Float32Array([1,0,0,0,0,c,s,0,0,-s,c,0,0,0,0,1])}
function ry(a){let c=Math.cos(a),s=Math.sin(a);return new Float32Array([c,0,-s,0,0,1,0,0,s,0,c,0,0,0,0,1])}
function sc(s){return new Float32Array([s,0,0,0,0,s,0,0,0,0,s,0,0,0,0,1])}
function draw(){const d=devicePixelRatio||1;c.width=c.clientWidth*d;c.height=c.clientHeight*d;gl.viewport(0,0,c.width,c.height);gl.clearColor(.94,.93,.90,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.uniformMatrix4fv(ml,false,mul(sc(.58),mul(rx(ax),ry(ay))));gl.uniform3fv(cl,col);gl.drawArrays(gl.TRIANGLES,0,36)}
c.onpointerdown=e=>{drag=true;lx=e.clientX;ly=e.clientY;c.setPointerCapture(e.pointerId)};c.onpointermove=e=>{if(!drag)return;ay+=(e.clientX-lx)*.01;ax+=(e.clientY-ly)*.01;lx=e.clientX;ly=e.clientY;draw()};c.onpointerup=()=>drag=false;
document.querySelectorAll('[data-col]').forEach(x=>x.onclick=()=>{col=x.dataset.col.split(',').map(Number);draw()});addEventListener('resize',draw);draw();
"""


def build_browser_3d_demo(body: dict[str, Any]) -> list[dict[str, str]]:
    p = body["payload"]
    facts = "".join(f"<li>{html.escape(x)}</li>" for x in p["observedFacts"])
    doc = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(p["businessName"])} · 3D proof</title>
<style>{base_css()}canvas{{width:100%;height:58vh;min-height:360px;border-radius:18px;background:#eeece6;touch-action:none}}.tools{{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}}.tools button{{border:1px solid #cbc6bc;background:#fff;border-radius:999px;padding:9px 12px;cursor:pointer}}ul{{padding-left:20px}}</style></head>
<body><main class="shell"><div class="private">iAffice · private browser 3D proof · not production</div><h1>{html.escape(p["businessName"])}</h1><p class="lead">{html.escape(p["demoBrief"])}</p>
<canvas aria-label="Interactive 3D proof"></canvas><div class="tools"><button data-col=".22,.28,.34">Graphite</button><button data-col=".65,.48,.30">Warm</button><button data-col=".72,.74,.71">Light</button></div>
<div id="status" class="private">Drag to orbit · material controls are illustrative only</div><section class="card"><strong>Observed evidence only</strong><ul>{facts}</ul></section>
<div class="note">No dimensions, prices, materials, stock or uplift are asserted unless supported by CASE evidence. Evidence refs: {len(p["evidenceRefs"])}.</div></main><script>{webgl_script()}</script></body></html>"""
    return [
        write_artifact(body["runId"], "index.html", doc.encode("utf-8")),
        write_artifact(body["runId"], "manifest.json", json.dumps({"mode":"BROWSER_3D","private":True,"evidenceRefs":p["evidenceRefs"]}, indent=2).encode("utf-8")),
    ]


def build_blender_demo(body: dict[str, Any]) -> list[dict[str, str]]:
    blender = shutil.which("blender")
    if not blender:
        raise RuntimeError("HEAVY_3D_TOOLCHAIN_NOT_CONFIGURED")
    out = artifact_dir(body["runId"])
    script = out / "scene.py"
    glb = out / "scene.glb"
    script.write_text(
        "import bpy\\n"
        "bpy.ops.object.select_all(action='SELECT')\\n"
        "bpy.ops.object.delete(use_global=False)\\n"
        "bpy.ops.mesh.primitive_cube_add(location=(0,0,0))\\n"
        "bpy.context.active_object.scale=(2.4,0.15,1.6)\\n"
        "bpy.ops.mesh.primitive_cube_add(location=(0,0,1.9))\\n"
        "bpy.context.active_object.scale=(2.8,0.2,0.2)\\n"
        "bpy.ops.mesh.primitive_cube_add(location=(0,0,-1.9))\\n"
        "bpy.context.active_object.scale=(2.8,0.2,0.2)\\n"
        + "bpy.ops.export_scene.gltf(filepath=" + json.dumps(str(glb)) + ",export_format='GLB')\\n",
        encoding="utf-8",
    )
    subprocess.run(
        [blender, "--background", "--factory-startup", "--python", str(script)],
        cwd=str(out), check=True, timeout=120,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={"PATH": os.environ.get("PATH",""), "HOME": str(out)}
    )
    if not glb.exists() or glb.stat().st_size == 0:
        raise RuntimeError("HEAVY_3D_EXPORT_FAILED")
    return [
        write_artifact(body["runId"], "scene.glb", glb.read_bytes()),
        write_artifact(body["runId"], "scene.py", script.read_bytes()),
    ]


def execute(body: dict[str, Any]) -> list[dict[str, str]]:
    kind = body["jobKind"]
    if kind == "DEMO_WEB_BUILD":
        return build_web_demo(body)
    if kind == "DEMO_BROWSER_3D":
        return build_browser_3d_demo(body)
    if kind == "DEMO_HEAVY_3D":
        return build_blender_demo(body)
    if kind == "DISCOVERY_WEB_AUDIT":
        raise RuntimeError("DISCOVERY_EXECUTOR_ADAPTER_NOT_ENABLED")
    raise RuntimeError("JOB_KIND_INVALID")


def result_for(body: dict[str, Any], state: str, artifacts: list[dict[str, str]], started_wall: float, started_cpu: float, error: str | None) -> dict[str, Any]:
    ended = time.time()
    digest_basis = {"runId": body["runId"], "jobId": body["jobId"], "state": state, "artifacts": artifacts, "errorCode": error}
    return {
        "protocolVersion": PROTOCOL,
        "runId": body["runId"],
        "executorId": EXECUTOR_ID,
        "jobKind": body["jobKind"],
        "jobId": body["jobId"],
        "caseId": body["caseId"],
        "state": state,
        "actualCostUsd": 0,
        "artifacts": artifacts,
        "telemetry": {
            "startedAt": datetime.fromtimestamp(started_wall, timezone.utc).isoformat().replace("+00:00","Z"),
            "endedAt": datetime.fromtimestamp(ended, timezone.utc).isoformat().replace("+00:00","Z"),
            "cpuMs": max(0, int((time.process_time() - started_cpu) * 1000)),
            "memoryPeakMb": max(0, int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)),
        },
        "resultDigest": sha256_text(canonical(digest_basis)),
        "errorCode": error,
    }


def signed_result(result: dict[str, Any]) -> dict[str, Any]:
    return {"result": result, "signature": sign(result), "algorithm": "HMAC-SHA256"}


def callback_once(payload: dict[str, Any]) -> None:
    if not CALLBACK_URL.startswith("https://"):
        raise RuntimeError("CORE_CALLBACK_HTTPS_REQUIRED")
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        CALLBACK_URL, data=data, method="POST",
        headers={"content-type": "application/json", "user-agent": "iaffice-oracle-executor/1.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        if res.status not in (200, 201, 202):
            raise RuntimeError(f"CALLBACK_HTTP_{res.status}")


def callback_status(run_id: str, state: str, error: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    with db() as conn:
        conn.execute(
            "UPDATE runs SET callback_state=?,callback_attempts=callback_attempts+1,callback_error=?,updated_at=? WHERE run_id=?",
            (state, error, now, run_id),
        )
        conn.commit()


def deliver_callback(run_id: str, signed: dict[str, Any]) -> None:
    last_error = None
    for delay in (0, 1, 3, 10, 30, 60, 120, 300):
        if delay:
            time.sleep(delay)
        try:
            callback_once(signed)
            callback_status(run_id, "DELIVERED", None)
            log("callback_delivered", runId=run_id)
            return
        except Exception as exc:
            last_error = f"{type(exc).__name__}:{str(exc)[:180]}"
            callback_status(run_id, "PENDING", last_error)
    log("callback_pending", runId=run_id, error=last_error or "UNKNOWN")


def persist_new(body: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str, bool]:
    request_digest = sha256_text(canonical(body))
    now = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    with db() as conn:
        row = conn.execute(
            "SELECT request_digest,state,result_json,callback_state FROM runs WHERE run_id=?",
            (body["runId"],)
        ).fetchone()
        if row:
            if row[0] != request_digest:
                raise RuntimeError("RUN_REPLAY_CONFLICT")
            return row[1], json.loads(row[2]) if row[2] else None, row[3], False
        try:
            conn.execute(
                "INSERT INTO runs(run_id,nonce,request_digest,state,result_json,callback_state,created_at,updated_at) VALUES(?,?,?,'RUNNING',NULL,'NONE',?,?)",
                (body["runId"], body["nonce"], request_digest, now, now),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise RuntimeError("NONCE_REPLAY_REJECTED") from exc
    return "RUNNING", None, "NONE", True


def persist_result(run_id: str, signed: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    with db() as conn:
        conn.execute(
            "UPDATE runs SET state=?,result_json=?,callback_state='PENDING',callback_error=NULL,updated_at=? WHERE run_id=?",
            (signed["result"]["state"], json.dumps(signed, ensure_ascii=False, separators=(",", ":")), now, run_id),
        )
        conn.commit()


def process_job(body: dict[str, Any]) -> None:
    started_wall, started_cpu = time.time(), time.process_time()
    try:
        artifacts = execute(body)
        result = result_for(body, "SUCCEEDED", artifacts, started_wall, started_cpu, None)
    except Exception as exc:
        code = str(exc).split(":", 1)[0][:96] or "EXECUTOR_JOB_FAILED"
        result = result_for(body, "FAILED", [], started_wall, started_cpu, code)
    signed = signed_result(result)
    persist_result(body["runId"], signed)
    log("job_complete", runId=body["runId"], jobKind=body["jobKind"], state=result["state"], artifactCount=len(result["artifacts"]))
    deliver_callback(body["runId"], signed)


def recover_pending_callbacks() -> None:
    while True:
        try:
            with db() as conn:
                rows = conn.execute(
                    "SELECT run_id,result_json FROM runs WHERE result_json IS NOT NULL AND callback_state!='DELIVERED' ORDER BY updated_at LIMIT 20"
                ).fetchall()
            for run_id, raw in rows:
                try:
                    deliver_callback(run_id, json.loads(raw))
                except Exception as exc:
                    log("callback_recovery_error", runId=run_id, error=type(exc).__name__)
        except Exception as exc:
            log("callback_recovery_scan_error", error=type(exc).__name__)
        time.sleep(300)


def log(event: str, **detail: Any) -> None:
    print(json.dumps({"event": event, **detail}, ensure_ascii=False, separators=(",", ":")), flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "iAfficeOracleExecutor/1.0"

    def _json(self, status: int, value: Any) -> None:
        data = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("x-content-type-options", "nosniff")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {
                "ok": bool(SIGNING_KEY and CALLBACK_URL.startswith("https://")),
                "service": "iaffice-oracle-executor",
                "executorId": EXECUTOR_ID,
                "protocolVersion": PROTOCOL,
                "canonicalState": False,
                "arbitraryShell": False,
                "callbackConfigured": CALLBACK_URL.startswith("https://"),
                "signingKeyConfigured": len(SIGNING_KEY) >= 8,
                "heavy3dToolchain": bool(shutil.which("blender")),
                "discoveryAdapter": "DISABLED_FAIL_CLOSED",
                "artifactAccess": "HMAC_TIME_BOUND",
            })
            return
        match = re.fullmatch(r"/v1/artifacts/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", self.path)
        if match:
            if not verify_artifact_request(
                self.path,
                self.headers.get("x-iaffice-artifact-ts"),
                self.headers.get("x-iaffice-artifact-signature"),
            ):
                self._json(401, {"error": "ARTIFACT_AUTH_REQUIRED"})
                return
            run_id, name = match.groups()
            target = ROOT / "artifacts" / run_id / name
            if not target.is_file():
                self._json(404, {"error": "ARTIFACT_NOT_FOUND"})
                return
            data = target.read_bytes()
            content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(data)))
            self.send_header("cache-control", "no-store")
            self.send_header("x-content-type-options", "nosniff")
            self.send_header("content-security-policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; frame-ancestors 'self'")
            self.end_headers()
            self.wfile.write(data)
            return
        self._json(404, {"error": "NOT_FOUND"})

    def do_POST(self) -> None:
        if self.path not in JOB_PATHS.values():
            self._json(404, {"error": "NOT_FOUND"})
            return
        if not SIGNING_KEY or not CALLBACK_URL:
            self._json(503, {"error": "EXECUTOR_NOT_CONFIGURED"})
            return
        try:
            size = int(self.headers.get("content-length", "0"))
            if size <= 0 or size > MAX_BODY:
                self._json(413, {"error": "BODY_SIZE_INVALID"})
                return
            envelope = json.loads(self.rfile.read(size))
            ok, reason = validate_envelope(envelope, self.path)
            if not ok:
                self._json(401, {"error": reason})
                return
            body = envelope["body"]
            state, previous, callback_state, created = persist_new(body)
            if previous is not None:
                if callback_state != "DELIVERED":
                    threading.Thread(target=deliver_callback, args=(body["runId"], previous), daemon=True).start()
                self._json(200, {"accepted": True, "runId": body["runId"], "replayed": True, "state": state, "callbackState": callback_state})
                return
            if not created:
                self._json(202, {"accepted": True, "runId": body["runId"], "replayed": True, "state": state})
                return

            threading.Thread(target=process_job, args=(body,), daemon=True).start()
            self._json(202, {"accepted": True, "runId": body["runId"], "state": "RUNNING"})
        except Exception as exc:
            log("request_error", error=type(exc).__name__, detail=str(exc)[:256])
            self._json(409, {"error": str(exc).split(":", 1)[0][:128]})

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def self_test() -> int:
    global SIGNING_KEY
    if not SIGNING_KEY:
        SIGNING_KEY = "self-test-secret"
    demo_payload = {
        "businessName": "Demo Comercio",
        "category": "retail",
        "locality": "Santa Fe",
        "servicePackId": "LOCAL_COMMERCE_DIGITAL",
        "requestedDeliverables": ["HIGH_CONVERSION_WEBSITE"],
        "evidenceRefs": ["evidence:test:1"],
        "observedFacts": ["mobile CTA is difficult to find"],
        "demoBrief": "Show a private mobile conversion proof.",
    }
    now = datetime.now(timezone.utc)
    body = {
        "protocolVersion": PROTOCOL,
        "runId": "self-test-run",
        "executorId": EXECUTOR_ID,
        "jobKind": "DEMO_WEB_BUILD",
        "jobId": "self-test-job",
        "caseId": "self-test-case",
        "payload": demo_payload,
        "payloadDigest": sha256_text(canonical(demo_payload)),
        "artifactInputRefs": ["evidence:test:1"],
        "expectedCostUsd": 0,
        "issuedAt": now.isoformat().replace("+00:00","Z"),
        "expiresAt": datetime.fromtimestamp(now.timestamp()+600, timezone.utc).isoformat().replace("+00:00","Z"),
        "nonce": "self-test-nonce-123",
    }
    envelope = {"body": body, "signature": sign(body), "algorithm": "HMAC-SHA256"}
    ok, reason = validate_envelope(envelope, "/v1/jobs/demo-web-build")
    if not ok:
        print(reason)
        return 2
    artifacts = build_web_demo(body)
    if not artifacts:
        return 3
    result = result_for(body, "SUCCEEDED", artifacts, time.time(), time.process_time(), None)
    signed = signed_result(result)
    if not hmac.compare_digest(signed["signature"], sign(result)):
        return 4
    artifact_path = "/v1/artifacts/self-test-run/index.html"
    ts = int(time.time())
    artifact_sig = hmac.new(SIGNING_KEY.encode("utf-8"), f"GET\\n{artifact_path}\\n{ts}".encode("utf-8"), hashlib.sha256).hexdigest()
    if not verify_artifact_request(artifact_path, str(ts), artifact_sig):
        return 5
    if verify_artifact_request("/v1/artifacts/self-test-run/other.html", str(ts), artifact_sig):
        return 6
    print(json.dumps({"ok": True, "artifacts": artifacts, "arbitraryShell": False, "artifactAuth": "HMAC_TIME_BOUND"}, indent=2))
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if len(SIGNING_KEY) < 8:
        raise SystemExit("IAFFICE_EXECUTOR_SIGNING_KEY is required")
    if not CALLBACK_URL.startswith("https://"):
        raise SystemExit("IAFFICE_CORE_CALLBACK_URL must be https")
    ROOT.mkdir(parents=True, exist_ok=True)
    with db():
        pass
    threading.Thread(target=recover_pending_callbacks, daemon=True).start()
    server = ThreadingHTTPServer((BIND, PORT), Handler)
    log("executor_start", bind=BIND, port=PORT, executorId=EXECUTOR_ID, root=str(ROOT), arbitraryShell=False, asyncJobs=True, durableCallbackRetry=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())