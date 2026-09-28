import type { ServiceDeliverable, ServicePackId } from "./servicePacks.js";

export type DemoExecutorClass = "WEB_BUILD" | "BROWSER_3D" | "HEAVY_3D";

export interface DemoJobRequest {
  jobId: string;
  caseId: string;
  servicePackId: ServicePackId;
  evidenceRefs: string[];
  requestedDeliverables: ServiceDeliverable[];
  privatePreview: boolean;
  productionDeploy: boolean;
  executorId: string;
  executorCostVerifiedZero: boolean;
  createdAt: string;
}

export interface DemoJobDecision {
  allowed: boolean;
  reasons: string[];
  executorClass: DemoExecutorClass;
}

export interface DemoArtifactRef {
  kind: "WEB_PREVIEW" | "IMAGE" | "VIDEO" | "THREE_D" | "DOCUMENT" | "CODE";
  ref: string;
  digest: string;
}

export interface DemoArtifactManifest {
  jobId: string;
  caseId: string;
  servicePackId: ServicePackId;
  visibility: "PRIVATE";
  production: false;
  executorId: string;
  executorClass: DemoExecutorClass;
  requestedDeliverables: ServiceDeliverable[];
  evidenceRefs: string[];
  artifacts: DemoArtifactRef[];
  auditRequired: true;
  createdAt: string;
}

export function chooseDemoExecutorClass(deliverables: ServiceDeliverable[]): DemoExecutorClass {
  if (deliverables.includes("EMBEDDABLE_3D_TOUR")) return "HEAVY_3D";
  if (deliverables.includes("VISUAL_CONFIGURATOR")) return "BROWSER_3D";
  return "WEB_BUILD";
}

export function evaluateDemoJob(request: DemoJobRequest): DemoJobDecision {
  const reasons:string[]=[];
  if(!request.jobId) reasons.push("DEMO_JOB_ID_REQUIRED");
  if(!request.caseId) reasons.push("CASE_ID_REQUIRED");
  if(!request.servicePackId) reasons.push("SERVICE_PACK_REQUIRED");
  if(request.evidenceRefs.length===0) reasons.push("EVIDENCE_REQUIRED");
  if(request.requestedDeliverables.length===0) reasons.push("DELIVERABLE_REQUIRED");
  if(!request.privatePreview) reasons.push("PRIVATE_PREVIEW_REQUIRED");
  if(request.productionDeploy) reasons.push("DEMO_PRODUCTION_DEPLOY_FORBIDDEN");
  if(!request.executorId) reasons.push("EXECUTOR_REQUIRED");
  if(!request.executorCostVerifiedZero) reasons.push("ZERO_COST_EXECUTOR_REQUIRED");
  return {
    allowed:reasons.length===0,
    reasons,
    executorClass:chooseDemoExecutorClass(request.requestedDeliverables)
  };
}

export function buildDemoArtifactManifest(request: DemoJobRequest, artifacts: DemoArtifactRef[]): DemoArtifactManifest {
  const decision=evaluateDemoJob(request);
  if(!decision.allowed) throw new Error("DEMO_JOB_NOT_ALLOWED:"+decision.reasons.join(","));
  if(artifacts.length===0) throw new Error("DEMO_ARTIFACT_REQUIRED");
  for(const artifact of artifacts){
    if(!artifact.ref||!artifact.digest) throw new Error("DEMO_ARTIFACT_INVALID");
  }
  return {
    jobId:request.jobId,
    caseId:request.caseId,
    servicePackId:request.servicePackId,
    visibility:"PRIVATE",
    production:false,
    executorId:request.executorId,
    executorClass:decision.executorClass,
    requestedDeliverables:[...request.requestedDeliverables],
    evidenceRefs:[...request.evidenceRefs],
    artifacts:artifacts.map(x=>structuredClone(x)),
    auditRequired:true,
    createdAt:request.createdAt
  };
}
