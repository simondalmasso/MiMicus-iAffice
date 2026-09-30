import type { DemoArtifactRef } from "./demoJobs.js";

export type ExecutorJobKind =
  | "DISCOVERY_WEB_AUDIT"
  | "DEMO_WEB_BUILD"
  | "DEMO_BROWSER_3D"
  | "DEMO_HEAVY_3D";

export const EXECUTOR_JOB_KINDS: readonly ExecutorJobKind[] = [
  "DISCOVERY_WEB_AUDIT",
  "DEMO_WEB_BUILD",
  "DEMO_BROWSER_3D",
  "DEMO_HEAVY_3D"
] as const;

export interface ExecutorEnvelopeBody {
  protocolVersion: "iaffice-executor-v1";
  runId: string;
  executorId: string;
  jobKind: ExecutorJobKind;
  jobId: string;
  caseId: string | null;
  payloadDigest: string;
  artifactInputRefs: string[];
  expectedCostUsd: 0;
  issuedAt: string;
  expiresAt: string;
  nonce: string;
}

export interface SignedExecutorEnvelope {
  body: ExecutorEnvelopeBody;
  signature: string;
  algorithm: "HMAC-SHA256";
}

export interface ExecutorResultTelemetry {
  startedAt: string;
  endedAt: string;
  cpuMs: number;
  memoryPeakMb: number;
}

export interface ExecutorResult {
  protocolVersion: "iaffice-executor-v1";
  runId: string;
  executorId: string;
  jobKind: ExecutorJobKind;
  jobId: string;
  caseId: string | null;
  state: "SUCCEEDED" | "FAILED";
  actualCostUsd: number;
  artifacts: DemoArtifactRef[];
  telemetry: ExecutorResultTelemetry;
  resultDigest: string;
  errorCode: string | null;
}

const ARTIFACT_KINDS = new Set(["WEB_PREVIEW","IMAGE","VIDEO","THREE_D","DOCUMENT","CODE"]);

function isExecutorJobKind(value: unknown): value is ExecutorJobKind {
  return typeof value === "string" && (EXECUTOR_JOB_KINDS as readonly string[]).includes(value);
}

function canonical(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  const obj=value as Record<string,unknown>;
  return "{" + Object.keys(obj).sort().map(k=>JSON.stringify(k)+":"+canonical(obj[k])).join(",") + "}";
}

function toHex(bytes: ArrayBuffer): string {
  return [...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,"0")).join("");
}

async function hmacKey(secret:string,usage:KeyUsage[]):Promise<CryptoKey>{
  if(secret.length<8)throw new Error("EXECUTOR_SIGNING_KEY_TOO_SHORT");
  return crypto.subtle.importKey("raw",new TextEncoder().encode(secret),{name:"HMAC",hash:"SHA-256"},false,usage);
}

function validateTimes(issuedAt:string,expiresAt:string):void{
  const issued=Date.parse(issuedAt),expires=Date.parse(expiresAt);
  if(!Number.isFinite(issued)||!Number.isFinite(expires)||expires<=issued)throw new Error("EXECUTOR_ENVELOPE_TIME_INVALID");
  if(expires-issued>15*60*1000)throw new Error("EXECUTOR_ENVELOPE_TTL_TOO_LONG");
}

export async function createExecutorEnvelope(
  input:{
    runId:string;
    executorId:string;
    jobKind:ExecutorJobKind | string;
    jobId:string;
    caseId:string|null;
    payloadDigest:string;
    artifactInputRefs:string[];
    issuedAt:string;
    expiresAt:string;
    nonce:string;
  },
  secret:string
):Promise<SignedExecutorEnvelope>{
  if(!input.runId||!input.executorId||!input.jobId)throw new Error("EXECUTOR_ENVELOPE_IDENTITY_REQUIRED");
  if(!isExecutorJobKind(input.jobKind))throw new Error("EXECUTOR_JOB_KIND_INVALID");
  if(!input.payloadDigest.startsWith("sha256:"))throw new Error("EXECUTOR_PAYLOAD_DIGEST_REQUIRED");
  if(!Array.isArray(input.artifactInputRefs))throw new Error("EXECUTOR_INPUT_REFS_INVALID");
  if(!input.nonce||input.nonce.length<8)throw new Error("EXECUTOR_NONCE_INVALID");
  validateTimes(input.issuedAt,input.expiresAt);
  const body:ExecutorEnvelopeBody={
    protocolVersion:"iaffice-executor-v1",
    runId:input.runId,
    executorId:input.executorId,
    jobKind:input.jobKind,
    jobId:input.jobId,
    caseId:input.caseId,
    payloadDigest:input.payloadDigest,
    artifactInputRefs:[...input.artifactInputRefs],
    expectedCostUsd:0,
    issuedAt:input.issuedAt,
    expiresAt:input.expiresAt,
    nonce:input.nonce
  };
  const key=await hmacKey(secret,["sign"]);
  const signature=toHex(await crypto.subtle.sign("HMAC",key,new TextEncoder().encode(canonical(body))));
  return {body,signature,algorithm:"HMAC-SHA256"};
}

export async function verifyExecutorEnvelope(
  envelope:SignedExecutorEnvelope,
  secret:string,
  nowIso:string
):Promise<boolean>{
  try{
    if(envelope.algorithm!=="HMAC-SHA256")return false;
    if(envelope.body.protocolVersion!=="iaffice-executor-v1")return false;
    if(!isExecutorJobKind(envelope.body.jobKind))return false;
    if(envelope.body.expectedCostUsd!==0)return false;
    validateTimes(envelope.body.issuedAt,envelope.body.expiresAt);
    const now=Date.parse(nowIso);
    const issued=Date.parse(envelope.body.issuedAt),expires=Date.parse(envelope.body.expiresAt);
    if(!Number.isFinite(now)||now<issued-60_000||now>expires)return false;
    if(!/^[0-9a-f]{64}$/i.test(envelope.signature))return false;
    const sig=new Uint8Array(envelope.signature.match(/../g)!.map(x=>parseInt(x,16)));
    const key=await hmacKey(secret,["verify"]);
    return crypto.subtle.verify("HMAC",key,sig,new TextEncoder().encode(canonical(envelope.body)));
  }catch{return false}
}

export function executorRequestPath(kind:ExecutorJobKind):string{
  switch(kind){
    case "DISCOVERY_WEB_AUDIT":return "/v1/jobs/discovery-web-audit";
    case "DEMO_WEB_BUILD":return "/v1/jobs/demo-web-build";
    case "DEMO_BROWSER_3D":return "/v1/jobs/demo-browser-3d";
    case "DEMO_HEAVY_3D":return "/v1/jobs/demo-heavy-3d";
  }
}

export function validateExecutorResult(value:unknown):{ok:boolean;reasons:string[];result:ExecutorResult|null}{
  const reasons:string[]=[];
  if(!value||typeof value!=="object")return {ok:false,reasons:["RESULT_OBJECT_REQUIRED"],result:null};
  const v=value as Record<string,unknown>;
  if(v.protocolVersion!=="iaffice-executor-v1")reasons.push("PROTOCOL_VERSION_INVALID");
  if(!isExecutorJobKind(v.jobKind))reasons.push("JOB_KIND_INVALID");
  if(typeof v.runId!=="string"||!v.runId)reasons.push("RUN_ID_REQUIRED");
  if(typeof v.executorId!=="string"||!v.executorId)reasons.push("EXECUTOR_ID_REQUIRED");
  if(typeof v.jobId!=="string"||!v.jobId)reasons.push("JOB_ID_REQUIRED");
  if(v.caseId!==null&&typeof v.caseId!=="string")reasons.push("CASE_ID_INVALID");
  if(!["SUCCEEDED","FAILED"].includes(String(v.state)))reasons.push("STATE_INVALID");
  if(typeof v.actualCostUsd!=="number"||!Number.isFinite(v.actualCostUsd)||v.actualCostUsd!==0)reasons.push("ZERO_COST_RESULT_REQUIRED");
  if(!Array.isArray(v.artifacts))reasons.push("ARTIFACTS_INVALID");
  else for(const artifact of v.artifacts){
    if(!artifact||typeof artifact!=="object"){reasons.push("ARTIFACT_INVALID");continue}
    const a=artifact as Record<string,unknown>;
    if(!ARTIFACT_KINDS.has(String(a.kind))||typeof a.ref!=="string"||!a.ref||typeof a.digest!=="string"||!a.digest.startsWith("sha256:"))reasons.push("ARTIFACT_INVALID");
  }
  const telemetry=v.telemetry;
  if(!telemetry||typeof telemetry!=="object")reasons.push("TELEMETRY_REQUIRED");
  else{
    const t=telemetry as Record<string,unknown>;
    const start=Date.parse(String(t.startedAt??"")),end=Date.parse(String(t.endedAt??""));
    if(!Number.isFinite(start)||!Number.isFinite(end)||end<start)reasons.push("TELEMETRY_TIME_INVALID");
    if(typeof t.cpuMs!=="number"||!Number.isFinite(t.cpuMs)||t.cpuMs<0)reasons.push("CPU_MS_INVALID");
    if(typeof t.memoryPeakMb!=="number"||!Number.isFinite(t.memoryPeakMb)||t.memoryPeakMb<0)reasons.push("MEMORY_INVALID");
  }
  if(typeof v.resultDigest!=="string"||!v.resultDigest.startsWith("sha256:"))reasons.push("RESULT_DIGEST_REQUIRED");
  if(v.errorCode!==null&&typeof v.errorCode!=="string")reasons.push("ERROR_CODE_INVALID");
  return {
    ok:reasons.length===0,
    reasons:[...new Set(reasons)],
    result:reasons.length===0?v as unknown as ExecutorResult:null
  };
}
