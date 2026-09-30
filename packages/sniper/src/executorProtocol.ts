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

export interface DiscoveryExecutorPayload {
  targetUrl: string;
  auditProfile: "PUBLIC_BUSINESS_WEB";
}

export interface DemoExecutorPayload {
  businessName: string;
  category: string;
  locality: string;
  servicePackId: string;
  requestedDeliverables: string[];
  evidenceRefs: string[];
  observedFacts: string[];
  demoBrief: string;
}

export type ExecutorJobPayload = DiscoveryExecutorPayload | DemoExecutorPayload;

export interface ExecutorEnvelopeBody {
  protocolVersion: "iaffice-executor-v1";
  runId: string;
  executorId: string;
  jobKind: ExecutorJobKind;
  jobId: string;
  caseId: string | null;
  payload: ExecutorJobPayload;
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

export interface SignedExecutorResult {
  result: ExecutorResult;
  signature: string;
  algorithm: "HMAC-SHA256";
}

const ARTIFACT_KINDS = new Set(["WEB_PREVIEW","IMAGE","VIDEO","THREE_D","DOCUMENT","CODE"]);

function isExecutorJobKind(value: unknown): value is ExecutorJobKind {
  return typeof value === "string" && (EXECUTOR_JOB_KINDS as readonly string[]).includes(value);
}

function canonical(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  const obj=value as Record<string,unknown>;
  return "{" + Object.keys(obj).filter(k=>obj[k]!==undefined).sort().map(k=>JSON.stringify(k)+":"+canonical(obj[k])).join(",") + "}";
}

function toHex(bytes: ArrayBuffer): string {
  return [...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,"0")).join("");
}

async function sha256Canonical(value:unknown):Promise<string>{
  const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(canonical(value)));
  return "sha256:"+toHex(digest);
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

function objectWithExactKeys(value:unknown,allowed:string[]):value is Record<string,unknown>{
  if(!value||typeof value!=="object"||Array.isArray(value))return false;
  const keys=Object.keys(value as Record<string,unknown>).sort();
  return keys.length===allowed.length&&keys.every((k,i)=>k===allowed.slice().sort()[i]);
}

function isPublicWebTarget(raw:string):boolean{
  try{
    const u=new URL(raw);
    if(!["http:","https:"].includes(u.protocol))return false;
    const host=u.hostname.toLowerCase();
    if(host==="localhost"||host.endsWith(".localhost")||host==="[::1]"||host==="::1")return false;
    const ip=ipv4Parts(host);
    if(ip){
      const [a,b]=ip;
      if(a===10||a===127||a===0||(a===169&&b===254)||(a===192&&b===168)||(a===172&&b!==undefined&&b>=16&&b<=31))return false;
    }
    return !u.username&&!u.password;
  }catch{return false}
}

function validatePayload(kind:ExecutorJobKind,payload:unknown):payload is ExecutorJobPayload{
  if(kind==="DISCOVERY_WEB_AUDIT"){
    if(!objectWithExactKeys(payload,["auditProfile","targetUrl"]))return false;
    return payload.auditProfile==="PUBLIC_BUSINESS_WEB"&&typeof payload.targetUrl==="string"&&isPublicWebTarget(payload.targetUrl);
  }
  if(!objectWithExactKeys(payload,["businessName","category","demoBrief","evidenceRefs","locality","observedFacts","requestedDeliverables","servicePackId"]))return false;
  return typeof payload.businessName==="string"&&payload.businessName.length>0
    &&typeof payload.category==="string"&&payload.category.length>0
    &&typeof payload.locality==="string"&&payload.locality.length>0
    &&typeof payload.servicePackId==="string"&&payload.servicePackId.length>0
    &&typeof payload.demoBrief==="string"&&payload.demoBrief.length>0
    &&Array.isArray(payload.observedFacts)&&payload.observedFacts.length>0&&payload.observedFacts.every(x=>typeof x==="string"&&x.length>0)
    &&Array.isArray(payload.requestedDeliverables)&&payload.requestedDeliverables.length>0&&payload.requestedDeliverables.every(x=>typeof x==="string"&&x.length>0)
    &&Array.isArray(payload.evidenceRefs)&&payload.evidenceRefs.length>0&&payload.evidenceRefs.every(x=>typeof x==="string"&&x.length>0);
}

export async function createExecutorEnvelope(
  input:{
    runId:string;
    executorId:string;
    jobKind:ExecutorJobKind | string;
    jobId:string;
    caseId:string|null;
    payload:unknown;
    artifactInputRefs:string[];
    issuedAt:string;
    expiresAt:string;
    nonce:string;
  },
  secret:string
):Promise<SignedExecutorEnvelope>{
  if(!input.runId||!input.executorId||!input.jobId)throw new Error("EXECUTOR_ENVELOPE_IDENTITY_REQUIRED");
  if(!isExecutorJobKind(input.jobKind))throw new Error("EXECUTOR_JOB_KIND_INVALID");
  if(!validatePayload(input.jobKind,input.payload))throw new Error("EXECUTOR_PAYLOAD_INVALID");
  if(!Array.isArray(input.artifactInputRefs)||!input.artifactInputRefs.every(x=>typeof x==="string"&&x.length>0))throw new Error("EXECUTOR_INPUT_REFS_INVALID");
  if(!input.nonce||input.nonce.length<8)throw new Error("EXECUTOR_NONCE_INVALID");
  validateTimes(input.issuedAt,input.expiresAt);
  const payload=structuredClone(input.payload) as ExecutorJobPayload;
  const body:ExecutorEnvelopeBody={
    protocolVersion:"iaffice-executor-v1",
    runId:input.runId,
    executorId:input.executorId,
    jobKind:input.jobKind,
    jobId:input.jobId,
    caseId:input.caseId,
    payload,
    payloadDigest:await sha256Canonical(payload),
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
    if(!validatePayload(envelope.body.jobKind,envelope.body.payload))return false;
    if(envelope.body.payloadDigest!==await sha256Canonical(envelope.body.payload))return false;
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
  else{
    if(v.state==="SUCCEEDED"&&v.artifacts.length===0)reasons.push("SUCCEEDED_ARTIFACT_REQUIRED");
    for(const artifact of v.artifacts){
      if(!artifact||typeof artifact!=="object"){reasons.push("ARTIFACT_INVALID");continue}
      const a=artifact as Record<string,unknown>;
      if(!ARTIFACT_KINDS.has(String(a.kind))||typeof a.ref!=="string"||!a.ref||typeof a.digest!=="string"||!a.digest.startsWith("sha256:"))reasons.push("ARTIFACT_INVALID");
    }
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
  if(v.state==="FAILED"&&(typeof v.errorCode!=="string"||!v.errorCode))reasons.push("FAILED_ERROR_CODE_REQUIRED");
  return {
    ok:reasons.length===0,
    reasons:[...new Set(reasons)],
    result:reasons.length===0?v as unknown as ExecutorResult:null
  };
}

function ipv4Parts(hostname:string):number[]|null{
  const m=hostname.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if(!m)return null;
  const parts=m.slice(1).map(Number);
  return parts.every(x=>x>=0&&x<=255)?parts:null;
}

export function validateExecutorEndpoint(endpoint:string|null):{ok:boolean;reasons:string[]}{
  const reasons:string[]=[];
  if(!endpoint)return {ok:false,reasons:["ENDPOINT_REQUIRED"]};
  try{
    const u=new URL(endpoint);
    if(u.protocol!=="https:")reasons.push("HTTPS_REQUIRED");
    const host=u.hostname.toLowerCase();
    if(host==="localhost"||host.endsWith(".localhost")||host==="[::1]"||host==="::1")reasons.push("LOCAL_ENDPOINT_FORBIDDEN");
    const ip=ipv4Parts(host);
    if(ip){
      const [a,b]=ip;
      if(a===10||a===127||a===0||(a===169&&b===254)||(a===192&&b===168)||(a===172&&b!==undefined&&b>=16&&b<=31))reasons.push("PRIVATE_ENDPOINT_FORBIDDEN");
    }
    if(u.username||u.password)reasons.push("ENDPOINT_CREDENTIALS_FORBIDDEN");
    if(u.search||u.hash)reasons.push("ENDPOINT_QUERY_FRAGMENT_FORBIDDEN");
    if(u.pathname!=="/"&&u.pathname!=="")reasons.push("ENDPOINT_BASE_PATH_FORBIDDEN");
  }catch{
    reasons.push("ENDPOINT_URL_INVALID");
  }
  return {ok:reasons.length===0,reasons:[...new Set(reasons)]};
}

export async function signExecutorResult(result:ExecutorResult,secret:string):Promise<SignedExecutorResult>{
  const validation=validateExecutorResult(result);
  if(!validation.ok||!validation.result)throw new Error("EXECUTOR_RESULT_INVALID:"+validation.reasons.join(","));
  const key=await hmacKey(secret,["sign"]);
  const signature=toHex(await crypto.subtle.sign("HMAC",key,new TextEncoder().encode(canonical(validation.result))));
  return {result:validation.result,signature,algorithm:"HMAC-SHA256"};
}

export async function verifySignedExecutorResult(envelope:SignedExecutorResult,secret:string):Promise<boolean>{
  try{
    if(envelope.algorithm!=="HMAC-SHA256")return false;
    const validation=validateExecutorResult(envelope.result);
    if(!validation.ok||!validation.result)return false;
    if(!/^[0-9a-f]{64}$/i.test(envelope.signature))return false;
    const sig=new Uint8Array(envelope.signature.match(/../g)!.map(x=>parseInt(x,16)));
    const key=await hmacKey(secret,["verify"]);
    return crypto.subtle.verify("HMAC",key,sig,new TextEncoder().encode(canonical(validation.result)));
  }catch{return false}
}

export async function signArtifactRequest(path:string,timestamp:number,secret:string):Promise<string>{
  if(!path.startsWith("/v1/artifacts/"))throw new Error("ARTIFACT_PATH_INVALID");
  if(!Number.isInteger(timestamp)||timestamp<=0)throw new Error("ARTIFACT_TIMESTAMP_INVALID");
  const key=await hmacKey(secret,["sign"]);
  return toHex(await crypto.subtle.sign("HMAC",key,new TextEncoder().encode("GET\n"+path+"\n"+timestamp)));
}

export async function verifyArtifactRequest(
  path:string,
  timestamp:number,
  signature:string,
  secret:string,
  nowEpochSeconds=Math.floor(Date.now()/1000)
):Promise<boolean>{
  try{
    if(!path.startsWith("/v1/artifacts/"))return false;
    if(!Number.isInteger(timestamp)||timestamp<=0)return false;
    if(Math.abs(nowEpochSeconds-timestamp)>300)return false;
    if(!/^[0-9a-f]{64}$/i.test(signature))return false;
    const expected=await signArtifactRequest(path,timestamp,secret);
    const a=new Uint8Array(expected.match(/../g)!.map(x=>parseInt(x,16)));
    const b=new Uint8Array(signature.match(/../g)!.map(x=>parseInt(x,16)));
    if(a.length!==b.length)return false;
    let diff=0;
    for(let i=0;i<a.length;i++)diff|=a[i]!^b[i]!;
    return diff===0;
  }catch{return false}
}
