import type { DemoExecutorClass } from "./demoJobs.js";
import { validateExecutorEndpoint } from "./executorProtocol.js";

export type ExecutorRole = "CONTROL_PLANE" | "JOB_EXECUTOR";
export type ExecutorCostClass = "FREE_VERIFIED" | "FREE_USER_CONFIRMED" | "UNKNOWN" | "PAID";
export type ExecutorHealth = "HEALTHY" | "UNKNOWN" | "DEGRADED";
export type ExecutorAdmissionState = "ENABLED" | "QUARANTINED" | "REJECTED";
export type ExecutorCapability = "CONTROL" | DemoExecutorClass;

export interface ExecutorCandidate {
  id: "CLOUDFLARE_CONTROL" | "ORACLE_FREE_EXECUTOR";
  label: string;
  role: ExecutorRole;
  capabilities: ExecutorCapability[];
  endpoint: string | null;
  costClass: ExecutorCostClass;
  zeroCostVerified: boolean;
  health: ExecutorHealth;
  canonicalState: boolean;
  notes: string[];
}

export interface ExecutorAdmission {
  state: ExecutorAdmissionState;
  reasons: string[];
}

export const EXECUTOR_CANDIDATES: ExecutorCandidate[] = [
  {
    id:"CLOUDFLARE_CONTROL",
    label:"Cloudflare control plane",
    role:"CONTROL_PLANE",
    capabilities:["CONTROL"],
    endpoint:"internal://agent-os",
    costClass:"FREE_VERIFIED",
    zeroCostVerified:true,
    health:"UNKNOWN",
    canonicalState:true,
    notes:[
      "Owns routing, D1, queues, workflows, policy and dashboard.",
      "Does not provide a general filesystem/browser/GPU build sandbox.",
      "Heavy jobs must leave the request path."
    ]
  },
  {
    id:"ORACLE_FREE_EXECUTOR",
    label:"Oracle Free Tier job executor",
    role:"JOB_EXECUTOR",
    capabilities:["WEB_BUILD","BROWSER_3D","HEAVY_3D"],
    endpoint:null,
    costClass:"FREE_USER_CONFIRMED",
    zeroCostVerified:false,
    health:"UNKNOWN",
    canonicalState:false,
    notes:[
      "User reports an available Oracle Free Tier environment.",
      "Must remain stateless relative to canonical D1 state.",
      "Endpoint, health and zero-cost runtime evidence are required before execution."
    ]
  }
];

export function evaluateExecutorAdmission(candidate: ExecutorCandidate | undefined): ExecutorAdmission {
  if(!candidate) return {state:"REJECTED",reasons:["EXECUTOR_NOT_FOUND"]};
  const rejected:string[]=[];
  const quarantined:string[]=[];

  if(candidate.costClass==="PAID") rejected.push("PAID_RUNTIME_FORBIDDEN");
  if(candidate.canonicalState && candidate.role!=="CONTROL_PLANE") rejected.push("CANONICAL_STATE_BOUNDARY_INVALID");

  if(rejected.length) return {state:"REJECTED",reasons:rejected};

  if(candidate.role==="JOB_EXECUTOR"){
    const endpoint=validateExecutorEndpoint(candidate.endpoint);
    if(!endpoint.ok)quarantined.push(...endpoint.reasons);
  }
  if(!candidate.zeroCostVerified) quarantined.push("ZERO_COST_NOT_VERIFIED");
  if(candidate.costClass==="UNKNOWN") quarantined.push("COST_UNKNOWN");
  if(candidate.health!=="HEALTHY") quarantined.push("HEALTH_NOT_VERIFIED");

  return quarantined.length
    ? {state:"QUARANTINED",reasons:quarantined}
    : {state:"ENABLED",reasons:["COST_ENDPOINT_HEALTH_VERIFIED"]};
}

export function selectExecutor(candidates: ExecutorCandidate[], capability: DemoExecutorClass): ExecutorCandidate | null {
  const eligible=candidates
    .filter(x=>x.role==="JOB_EXECUTOR")
    .filter(x=>x.capabilities.includes(capability))
    .filter(x=>evaluateExecutorAdmission(x).state==="ENABLED")
    .sort((a,b)=>a.id.localeCompare(b.id));
  return eligible[0]??null;
}