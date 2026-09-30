import { AriaOrchestrator, type EffectDispatcher, type EffectDispatchResult } from "../../../packages/core/src/orchestrator.js";
import { sha256, stableId } from "../../../packages/core/src/hash.js";
import type { ActionClass, ActionIntent, ApprovalRequest, SystemState } from "../../../packages/core/src/types.js";
import { Scheduler, type ScheduledJobName } from "../../../packages/core/src/scheduler.js";
import { D1StateStore } from "../../../packages/memory/src/store.js";
import { BudgetGovernor } from "../../../packages/router/src/budgetGovernor.js";
import { PolicyEngine } from "../../../packages/policy/src/policy.js";
import { createActionIntent } from "../../../packages/effects/src/kernel.js";
import { referenceEvents } from "../../../packages/fixtures/src/reference.js";
import { redactSecrets, WebhookIngestConnector } from "../../../packages/connectors/src/index.js";
import { ServiceModelGateway, ServiceModelProvider } from "../../../packages/router/src/serviceModelGateway.js";
import type { ComputeRequest } from "../../../packages/router/src/computeTypes.js";
import { buildComputeRuntime, executeComputeRequest, probeProvider } from "./computeRuntime.js";
import { SniperStore } from "../../../packages/sniper/src/store.js";
import { buildAgentSquad, requiresHumanGate, type BusinessSignal, type LearningObservation } from "../../../packages/sniper/src/engine.js";
import type { CognitiveContext, MemoryEpisode } from "../../../packages/sniper/src/cognition.js";
import type { TelemetrySpanInput } from "../../../packages/sniper/src/telemetry.js";
import { signArtifactRequest, type SignedExecutorResult } from "../../../packages/sniper/src/executorProtocol.js";
import { CommercialGuard, isExternalOperation } from "../../../packages/sniper/src/commercialGuard.js";
import { requiredEffectClass, type ExternalOperation } from "../../../packages/sniper/src/operatingModel.js";
import type { Env, MessageBatch, ServiceBindingLike } from "./runtime-types.js";
export { AriaCoordinator } from "./coordinator.js";
export { ComputeGovernorDO } from "./computeGovernorDO.js";
export { BusinessWorkflow } from "./workflow.js";
function securityHeaders():HeadersInit{return{"content-type":"application/json; charset=utf-8","cache-control":"no-store","content-security-policy":"default-src 'none'; frame-ancestors 'none'","x-content-type-options":"nosniff","referrer-policy":"no-referrer"};}
function json(body:unknown,status=200):Response{return new Response(JSON.stringify(redactSecrets(body)),{status,headers:securityHeaders()});}
async function sha256Bytes(bytes:ArrayBuffer):Promise<string>{
  const digest=await crypto.subtle.digest("SHA-256",bytes);
  return "sha256:"+[...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,"0")).join("");
}
async function tokenHash(token:string):Promise<string>{const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(token));return[...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,"0")).join("");}
async function authorized(request:Request,env:Env):Promise<boolean>{if(!env.ADMIN_TOKEN_HASH)return false;const token=request.headers.get("authorization")?.replace(/^Bearer\s+/i,"")??"";return Boolean(token)&&(await tokenHash(token))===env.ADMIN_TOKEN_HASH;}
async function withinRateLimit(env:Env,bucket:string,limit:number):Promise<boolean>{if(!env.COORDINATOR)return false;const stub=env.COORDINATOR.get(env.COORDINATOR.idFromName("global"));const response=await stub.fetch("https://coordinator.internal/rate",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({bucket,limit,windowMs:60000})});if(!response.ok)return false;return((await response.json()) as{allowed?:boolean}).allowed===true;}
function configured(env:Env):{ready:boolean;missing:string[]}{const missing:string[]=[];if(!env.ADMIN_TOKEN_HASH)missing.push("ADMIN_TOKEN_HASH");if(!env.APPROVAL_SIGNING_KEY)missing.push("APPROVAL_SIGNING_KEY");if(!env.WEBHOOK_SECRET)missing.push("WEBHOOK_SECRET");if(!env.EXECUTOR_SIGNING_KEY)missing.push("EXECUTOR_SIGNING_KEY");if(!env.COORDINATOR)missing.push("COORDINATOR");if(!env.COMPUTE_GOVERNOR)missing.push("COMPUTE_GOVERNOR");if(!env.BUSINESS_WORKFLOW)missing.push("BUSINESS_WORKFLOW");if(!env.EVENTS_QUEUE)missing.push("EVENTS_QUEUE");if(!env.ASSETS)missing.push("ASSETS");if(!env.EFFECTS)missing.push("EFFECTS_SERVICE_BINDING");if(!env.MODELS)missing.push("MODELS_SERVICE_BINDING");return{ready:missing.length===0,missing};}
function modelProvider(env:Env):ServiceModelProvider{if(!env.MODELS)throw new Error("MODELS_SERVICE_BINDING_REQUIRED");return new ServiceModelProvider(new ServiceModelGateway(env.MODELS));}
async function businessPreconditionHash(state:SystemState):Promise<string>{return sha256({events:state.events.map(e=>e.hash),leads:state.leads.map(l=>({id:l.id,status:l.status,intent:l.intentScore,last:l.lastActivityAt})),knowledge:state.knowledge.map(k=>({id:k.id,status:k.status,evidence:k.evidenceHash})),decisions:state.decisions.map(d=>({id:d.id,priority:d.priority,verdict:d.auditVerdict}))});}
class ServiceEffectDispatcher implements EffectDispatcher{constructor(private readonly service:ServiceBindingLike){}async execute(intent:ActionIntent,approval:ApprovalRequest,currentPreconditionHash:string,now:string):Promise<EffectDispatchResult>{const response=await this.service.fetch("https://aria-effects.internal/internal/execute-intent",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({intent,approval,currentPreconditionHash,now})});const body=await response.json() as EffectDispatchResult&{error?:string};if(!response.ok)throw new Error(body.error??`EFFECT_GATEWAY_HTTP_${response.status}`);return body;}}
async function dispatchApprovedIntent(orchestrator:AriaOrchestrator,env:Env,intent:ActionIntent,approval:ApprovalRequest):Promise<EffectDispatchResult>{if(!env.EFFECTS)throw new Error("EFFECTS_SERVICE_BINDING_REQUIRED");const currentPreconditionHash=await businessPreconditionHash(orchestrator.state),result=await new ServiceEffectDispatcher(env.EFFECTS).execute(intent,approval,currentPreconditionHash,new Date().toISOString());if(result.receipt.status==="EXECUTED"){orchestrator.approvals.consume(approval.id,intent.actionDigest);intent.status="EXECUTED";if(!orchestrator.state.effectReceipts.some(r=>r.receiptId===result.receipt.receiptId))orchestrator.state.effectReceipts.push(result.receipt);const action=orchestrator.state.actions.find(a=>a.approvalId===approval.id);if(action)action.status="EXECUTED";}else intent.status="RETRYABLE";await orchestrator.persist();return result;}
async function dispatchDemoJob(env:Env,jobId:string):Promise<void>{
  if(!env.EXECUTOR_SIGNING_KEY)throw new Error("EXECUTOR_SIGNING_KEY_REQUIRED");
  const store=new SniperStore(env.DB);
  const prepared=await store.prepareDemoExecutorRun(jobId,env.EXECUTOR_SIGNING_KEY);
  const target=new URL(prepared.path,prepared.endpoint).toString();
  const response=await fetch(target,{
    method:"POST",
    headers:{"content-type":"application/json","x-iaffice-executor-protocol":"v1"},
    body:JSON.stringify(prepared.envelope)
  });
  if(response.status!==202&&response.status!==200)throw new Error("EXECUTOR_DISPATCH_HTTP_"+response.status);
  await store.markExecutorDispatched(prepared.runId);
}

async function computeGet(url:URL,env:Env):Promise<Response|null>{if(!url.pathname.startsWith("/api/compute/"))return null;try{const runtime=await buildComputeRuntime(env);if(url.pathname==="/api/compute/providers")return json(runtime.registry.listProviders().map(p=>({...p,credentialBindingName:p.credentialBindingName?"[BOUND_IN_ARIA_MODELS]":null})));if(url.pathname==="/api/compute/models")return json(runtime.registry.listModels());if(url.pathname==="/api/compute/routes")return json(await runtime.store.listRoutes());if(url.pathname==="/api/compute/incidents")return json(await runtime.store.listIncidents());if(url.pathname==="/api/compute/budget"){const reservations=await runtime.governor.list();return json({costHardCapUsd:0,cumulativeMonetarySpendUsd:0,billableExecutionAttempts:0,reservations,currentReserved:reservations.filter(r=>r.status==="RESERVED").reduce((s,r)=>s+r.reservedUsageUnits,0)});}const route=url.pathname.match(/^\/api\/compute\/route\/(.+)$/);if(route)return json(await runtime.store.routeForTask(decodeURIComponent(route[1]!)));return null;}catch(error){return json({error:error instanceof Error?error.message:"COMPUTE_RUNTIME_ERROR"},503);}}
function validSignal(value:unknown):value is BusinessSignal{
    if(!value||typeof value!=="object")return false;
    const v=value as Partial<BusinessSignal>;
    return typeof v.businessId==="string"&&typeof v.name==="string"&&typeof v.category==="string"&&typeof v.locality==="string"&&typeof v.observedAt==="string"&&Boolean(v.demand)&&Boolean(v.digital)&&Array.isArray(v.contacts)&&Array.isArray(v.evidenceRefs)&&v.evidenceRefs.length>0;
  }
function commercialEffectRoute(operation:ExternalOperation):{connector:string;operation:string}|null{
  if(["SEND_OUTREACH","SCHEDULE_EXTERNAL_MEETING","SEND_PROPOSAL","SEND_DELIVERY_NOTICE","SEND_RECEIPT"].includes(operation)){
    return {connector:"safe-outbound",operation:"send"};
  }
  return null;
}

async function sniperGet(url:URL,env:Env):Promise<Response|null>{
  if(!url.pathname.startsWith("/api/sniper/"))return null;
  const sniper=new SniperStore(env.DB);
  if(url.pathname==="/api/sniper/dashboard")return json(await sniper.dashboard());
  if(url.pathname==="/api/sniper/opportunities")return json(await sniper.list(Number(url.searchParams.get("limit")??100)));
  if(url.pathname==="/api/sniper/activity")return json(await sniper.activityFeed(Number(url.searchParams.get("limit")??100)));
  if(url.pathname==="/api/sniper/squad")return json(buildAgentSquad());
  if(url.pathname==="/api/sniper/memory")return json(await sniper.memorySummary());
  if(url.pathname==="/api/sniper/global")return json(await sniper.globalOverview());
  if(url.pathname==="/api/sniper/operations")return json(await sniper.operationsOverview());
  if(url.pathname==="/api/sniper/skills")return json(await sniper.skillRegistryOverview());
  if(url.pathname==="/api/sniper/discovery/sources")return json(await sniper.discoverySourcesOverview());
  if(url.pathname==="/api/sniper/discovery/jobs")return json(await sniper.listDiscoveryJobs(Number(url.searchParams.get("limit")??100)));
  if(url.pathname==="/api/sniper/demos")return json(await sniper.listDemoJobs(Number(url.searchParams.get("limit")??100)));
  if(url.pathname==="/api/sniper/executors")return json(await sniper.executorRegistryOverview());
  if(url.pathname==="/api/sniper/telemetry")return json(await sniper.telemetryOverview(Number(url.searchParams.get("limit")??500)));
  const traceMatch=url.pathname.match(/^\/api\/sniper\/telemetry\/traces\/([^/]+)$/);
  if(traceMatch)return json(await sniper.telemetryTrace(decodeURIComponent(traceMatch[1]!)));
  const caseMatch=url.pathname.match(/^\/api\/sniper\/cases\/([^/]+)$/);
  if(caseMatch){const dossier=await sniper.caseView(decodeURIComponent(caseMatch[1]!));return dossier?json(dossier):json({error:"SNIPER_CASE_NOT_FOUND"},404);}
  const match=url.pathname.match(/^\/api\/sniper\/opportunities\/([^/]+)$/);
  if(match)return json(await sniper.get(decodeURIComponent(match[1]!)));
  return null;
}
async function api(request:Request,env:Env):Promise<Response|null>{const url=new URL(request.url);if(!url.pathname.startsWith("/api/"))return null;const store=new D1StateStore(env.DB);
 const artifactMatch=url.pathname.match(/^\/api\/sniper\/executor\/artifact\/([^/]+)\/([^/]+)$/);
 if(request.method==="GET"&&artifactMatch){
   if(!(await withinRateLimit(env,"artifact-proxy",60)))return json({error:"RATE_LIMITED_OR_COORDINATOR_UNAVAILABLE"},429);
   if(!(await authorized(request,env)))return json({error:"ADMIN_AUTH_REQUIRED"},401);
   if(!env.EXECUTOR_SIGNING_KEY)return json({error:"EXECUTOR_ARTIFACT_PROXY_NOT_CONFIGURED"},503);
   try{
     const runId=decodeURIComponent(artifactMatch[1]!),name=decodeURIComponent(artifactMatch[2]!);
     const resolved=await new SniperStore(env.DB).resolvePrivateArtifact(runId,name);
     if(!resolved)return json({error:"ARTIFACT_NOT_FOUND_OR_NOT_AUTHORIZED"},404);
     const timestamp=Math.floor(Date.now()/1000);
     const signature=await signArtifactRequest(resolved.path,timestamp,env.EXECUTOR_SIGNING_KEY);
     const upstream=await fetch(new URL(resolved.path,resolved.endpoint).toString(),{
       method:"GET",
       headers:{
         "x-iaffice-artifact-ts":String(timestamp),
         "x-iaffice-artifact-signature":signature
       }
     });
     if(!upstream.ok)return json({error:"EXECUTOR_ARTIFACT_UPSTREAM_"+upstream.status},502);
     const declared=Number(upstream.headers.get("content-length")??0);
     if(Number.isFinite(declared)&&declared>15_000_000)return json({error:"ARTIFACT_TOO_LARGE_FOR_PRIVATE_PROXY"},413);
     const bytes=await upstream.arrayBuffer();
     if(bytes.byteLength>15_000_000)return json({error:"ARTIFACT_TOO_LARGE_FOR_PRIVATE_PROXY"},413);
     const digest=await sha256Bytes(bytes);
     if(digest!==resolved.digest)return json({error:"ARTIFACT_DIGEST_MISMATCH"},409);
     const headers=new Headers();
     headers.set("content-type",upstream.headers.get("content-type")??"application/octet-stream");
     headers.set("content-length",String(bytes.byteLength));
     headers.set("cache-control","no-store");
     headers.set("x-content-type-options","nosniff");
     headers.set("referrer-policy","no-referrer");
     headers.set("content-security-policy","default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; frame-ancestors 'self'");
     return new Response(bytes,{status:200,headers});
   }catch(error){return json({error:error instanceof Error?error.message:"ARTIFACT_PROXY_FAILED"},400);}
 }
 if(request.method==="POST"&&url.pathname==="/api/sniper/executor/result"){
   if(!env.EXECUTOR_SIGNING_KEY)return json({error:"EXECUTOR_CALLBACK_NOT_CONFIGURED"},503);
   const body=await request.json() as SignedExecutorResult;
   try{return json(await new SniperStore(env.DB).completeExecutorRun(body,env.EXECUTOR_SIGNING_KEY),200);}catch(error){return json({error:error instanceof Error?error.message:"EXECUTOR_RESULT_REJECTED"},401);}
 }if(request.method==="GET"){const compute=await computeGet(url,env);if(compute)return compute;const sniper=await sniperGet(url,env);if(sniper)return sniper;if(url.pathname==="/api/health"){const cfg=configured(env);return json({ok:cfg.ready,service:"iAffice",worker:"agent-os",environment:env.ENVIRONMENT??"unknown",sha:env.ARIA_GIT_SHA??"unknown",canonicalMemory:"D1",effectBoundary:"SERVICE_BINDING_ONLY",modelBoundary:"SERVICE_BINDING_ONLY",agentWriteCredentials:0,modelProviderCredentials:0,costPolicy:"ZERO_SPEND_HARD_LOCK",missingBindings:cfg.missing},cfg.ready?200:503);}if(url.pathname==="/api/system/budget")return json(new BudgetGovernor().snapshot());if(url.pathname==="/api/system/policy")return json(new PolicyEngine().policyMatrix());if(url.pathname==="/api/state")return json(await store.load());}
 if(request.method!=="GET"){if(!(await withinRateLimit(env,`admin:${url.pathname}`,30)))return json({error:"RATE_LIMITED_OR_COORDINATOR_UNAVAILABLE"},429);if(!(await authorized(request,env)))return json({error:"ADMIN_AUTH_REQUIRED"},401);}
 if(request.method==="POST"&&url.pathname==="/api/sniper/opportunities/ingest"){
    const body=await request.json();
    if(!validSignal(body))return json({error:"SNIPER_SIGNAL_SCHEMA_INVALID"},400);
    const sniper=new SniperStore(env.DB),record=await sniper.ingest(body);
    return json(record,201);
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/contact-control"){
    const body=await request.json() as {caseId?:string;doNotContact?:boolean;explicitRefusal?:boolean;reason?:string|null;evidenceRefs?:string[]};
    if(!body.caseId||typeof body.doNotContact!=="boolean"||typeof body.explicitRefusal!=="boolean"||!Array.isArray(body.evidenceRefs))return json({error:"CONTACT_CONTROL_SCHEMA_INVALID"},400);
    try{
      await new CommercialGuard(env.DB).setContactControl({caseId:body.caseId,doNotContact:body.doNotContact,explicitRefusal:body.explicitRefusal,reason:body.reason??null,evidenceRefs:body.evidenceRefs.map(String)});
      return json({ok:true,caseId:body.caseId,doNotContact:body.doNotContact,explicitRefusal:body.explicitRefusal},201);
    }catch(error){return json({error:error instanceof Error?error.message:"CONTACT_CONTROL_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/commercial/audit"){
    const body=await request.json() as {caseId?:string;operation?:string;target?:string;payload?:Record<string,unknown>;verdict?:"PASS"|"FAIL"|"UNCERTAIN";reason?:string;evidenceRefs?:string[]};
    if(!body.caseId||!isExternalOperation(body.operation)||!body.target||!body.payload||typeof body.payload!=="object"||!body.verdict||!body.reason||!Array.isArray(body.evidenceRefs))return json({error:"COMMERCIAL_AUDIT_SCHEMA_INVALID"},400);
    try{
      return json(await new CommercialGuard(env.DB).recordCommercialAudit({caseId:body.caseId,operation:body.operation,target:body.target,payload:body.payload,verdict:body.verdict,reason:body.reason,evidenceRefs:body.evidenceRefs.map(String)}),201);
    }catch(error){return json({error:error instanceof Error?error.message:"COMMERCIAL_AUDIT_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/commercial/action"){
    const body=await request.json() as {
      requestId?:string;caseId?:string;operation?:string;target?:string;payload?:Record<string,unknown>;
      auditId?:string|null;evidenceRefs?:string[];reason?:string;requestedBy?:"CEO"|"RESEARCH"|"CMO"|"SALES"|"DATA"|"DEV"|"AUD"
    };
    if(!body.requestId||!body.caseId||!isExternalOperation(body.operation)||!body.target||!body.payload||typeof body.payload!=="object"||!Array.isArray(body.evidenceRefs)||!body.reason)return json({error:"COMMERCIAL_ACTION_SCHEMA_INVALID"},400);
    const route=commercialEffectRoute(body.operation);
    if(!route)return json({error:"COMMERCIAL_EFFECT_ADAPTER_NOT_AVAILABLE",operation:body.operation},501);
    const guard=new CommercialGuard(env.DB);
    try{
      const evaluation=await guard.evaluate({caseId:body.caseId,operation:body.operation,target:body.target,payload:body.payload,auditId:body.auditId??null});
      if(evaluation.decision==="HUMAN_GATE")return json({error:"HUMAN_GATE_REQUIRED",reasons:evaluation.reasons,snapshot:evaluation.snapshot},409);
      if(evaluation.decision!=="ALLOW")return json({error:"COMMERCIAL_POLICY_DENIED",reasons:evaluation.reasons,snapshot:evaluation.snapshot},403);

      const actionClass=requiredEffectClass(body.operation);
      const policy=new PolicyEngine(),policyDecision=policy.decision(actionClass);
      if(policyDecision==="DENY")return json({error:"ACTION_DENIED_BY_GLOBAL_POLICY",actionClass,operation:body.operation},403);
      if(!env.APPROVAL_SIGNING_KEY||!env.MODELS)return json({error:"CORE_BINDING_REQUIRED"},503);

      const requestedBy=body.requestedBy??"SALES";
      const now=new Date(),orchestrator=new AriaOrchestrator(store,modelProvider(env),env.APPROVAL_SIGNING_KEY);
      await orchestrator.load();
      const preconditionHash=await businessPreconditionHash(orchestrator.state);
      const evidenceRefs=[...new Set([...body.evidenceRefs.map(String),...(evaluation.snapshot.commercialAuditId?[evaluation.snapshot.commercialAuditId]:[])])];
      const canonicalParameters={
        commercialOperation:body.operation,
        caseId:body.caseId,
        commercialAuditId:evaluation.snapshot.commercialAuditId,
        commercialPayloadDigest:evaluation.snapshot.commercialPayloadDigest,
        payload:structuredClone(body.payload)
      };
      const idempotencyKey=await stableId("commercial-idem",{caseId:body.caseId,operation:body.operation,target:body.target,requestId:body.requestId,payloadDigest:evaluation.snapshot.commercialPayloadDigest});
      const intent=await createActionIntent({
        taskId:await stableId("commercial-task",{caseId:body.caseId,requestId:body.requestId}),
        agentId:requestedBy,
        subjectId:body.caseId,
        actionClass,
        connector:route.connector,
        operation:route.operation,
        target:body.target,
        canonicalParameters,
        justification:body.reason.slice(0,512),
        evidenceRefs,
        preconditionHash,
        idempotencyKey,
        requestedAt:now.toISOString(),
        expiresAt:new Date(now.getTime()+15*60_000).toISOString()
      });
      intent.status="APPROVAL_REQUIRED";
      await store.commitStateAndIntent(orchestrator.state,intent);
      orchestrator.state.actionIntents.push(intent);
      const approval=await orchestrator.approvals.request({actionClass,requestedBy,reason:intent.justification,scope:"action-digest",actionDigest:intent.actionDigest,policyVersion:intent.policyVersion,approvalChainVersion:intent.approvalChainVersion});
      intent.approvalId=approval.id;
      const actionId=await stableId("action",{intentId:intent.intentId});
      orchestrator.state.actions.push({id:actionId,actionClass,payload:structuredClone(body.payload),requestedBy,policyDecision,approvalId:approval.id,status:"BLOCKED",createdAt:now.toISOString()});
      await store.commitStateAndIntent(orchestrator.state,intent);
      orchestrator.state.approvals=orchestrator.approvals.list();
      await orchestrator.persist();
      if(env.BUSINESS_WORKFLOW)await env.BUSINESS_WORKFLOW.create({id:approval.id,params:{taskId:actionId,kind:actionClass,approvalId:approval.id}});
      return json({actionId,intentId:intent.intentId,actionDigest:intent.actionDigest,approvalId:approval.id,policyDecision,status:"PENDING_APPROVAL",commercial:evaluation.snapshot},202);
    }catch(error){return json({error:error instanceof Error?error.message:"COMMERCIAL_ACTION_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/executors/verify"){
    const body=await request.json() as {executorId?:string;endpoint?:string|null;costClass?:"FREE_VERIFIED"|"FREE_USER_CONFIRMED"|"UNKNOWN"|"PAID";zeroCostVerified?:boolean;health?:"HEALTHY"|"UNKNOWN"|"DEGRADED";evidenceRefs?:string[];lastHealthAt?:string|null;verifiedAt?:string};
    if(!body.executorId||body.endpoint===undefined||!body.costClass||typeof body.zeroCostVerified!=="boolean"||!body.health||!Array.isArray(body.evidenceRefs))return json({error:"EXECUTOR_VERIFY_SCHEMA_INVALID"},400);
    try{return json(await new SniperStore(env.DB).verifyExecutor({executorId:body.executorId,endpoint:body.endpoint,costClass:body.costClass,zeroCostVerified:body.zeroCostVerified,health:body.health,evidenceRefs:body.evidenceRefs,...(body.lastHealthAt!==undefined?{lastHealthAt:body.lastHealthAt}:{}),...(body.verifiedAt?{verifiedAt:body.verifiedAt}:{})}),201);}catch(error){return json({error:error instanceof Error?error.message:"EXECUTOR_VERIFY_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/demos"){
    const body=await request.json() as import("../../../packages/sniper/src/demoJobs.js").DemoJobRequest;
    if(!body||!body.jobId||!body.caseId||!body.servicePackId||!Array.isArray(body.evidenceRefs)||!Array.isArray(body.requestedDeliverables)||typeof body.privatePreview!=="boolean"||typeof body.productionDeploy!=="boolean"||!body.executorId||typeof body.executorCostVerifiedZero!=="boolean"||!body.createdAt)return json({error:"DEMO_JOB_SCHEMA_INVALID"},400);
    if(!env.EVENTS_QUEUE)return json({error:"EVENT_QUEUE_NOT_CONFIGURED"},503);
    try{
      const created=await new SniperStore(env.DB).createDemoJob(body);
      if(created.state==="QUEUED")await env.EVENTS_QUEUE.send({kind:"demo-dispatch",jobId:body.jobId});
      return json({...created,dispatchQueued:created.state==="QUEUED"},201);
    }catch(error){return json({error:error instanceof Error?error.message:"DEMO_JOB_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/demos/artifacts"){
    const body=await request.json() as {jobId?:string;artifacts?:import("../../../packages/sniper/src/demoJobs.js").DemoArtifactRef[]};
    if(!body.jobId||!Array.isArray(body.artifacts))return json({error:"DEMO_ARTIFACT_SCHEMA_INVALID"},400);
    try{return json(await new SniperStore(env.DB).recordDemoArtifacts({jobId:body.jobId,artifacts:body.artifacts}),201);}catch(error){return json({error:error instanceof Error?error.message:"DEMO_ARTIFACT_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/demos/audit"){
    const body=await request.json() as {jobId?:string;verdict?:"PASS"|"FAIL"|"UNCERTAIN";evidenceRefs?:string[]};
    if(!body.jobId||!body.verdict||!Array.isArray(body.evidenceRefs))return json({error:"DEMO_AUDIT_SCHEMA_INVALID"},400);
    try{return json(await new SniperStore(env.DB).auditDemo({jobId:body.jobId,verdict:body.verdict,evidenceRefs:body.evidenceRefs}),201);}catch(error){return json({error:error instanceof Error?error.message:"DEMO_AUDIT_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/discovery/source/verify"){
    const body=await request.json() as {sourceId?:string;revisionPin?:string;zeroCostVerified?:boolean;targetTermsVerified?:boolean;automationAllowed?:boolean;health?:"HEALTHY"|"UNKNOWN"|"DEGRADED";evidenceRefs?:string[];verifiedAt?:string};
    if(!body.sourceId||!body.revisionPin||typeof body.zeroCostVerified!=="boolean"||typeof body.targetTermsVerified!=="boolean"||typeof body.automationAllowed!=="boolean"||!body.health||!Array.isArray(body.evidenceRefs))return json({error:"DISCOVERY_SOURCE_VERIFY_SCHEMA_INVALID"},400);
    try{return json(await new SniperStore(env.DB).verifyDiscoverySource({sourceId:body.sourceId,revisionPin:body.revisionPin,zeroCostVerified:body.zeroCostVerified,targetTermsVerified:body.targetTermsVerified,automationAllowed:body.automationAllowed,health:body.health,evidenceRefs:body.evidenceRefs,...(body.verifiedAt?{verifiedAt:body.verifiedAt}:{})}),201);}catch(error){return json({error:error instanceof Error?error.message:"DISCOVERY_SOURCE_VERIFY_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/discovery/jobs"){
    const body=await request.json() as {jobId?:string;locality?:string;categories?:string[];maxCandidates?:number;sourceIds?:string[]};
    if(!body.jobId||!body.locality||!Array.isArray(body.categories)||typeof body.maxCandidates!=="number"||!Array.isArray(body.sourceIds))return json({error:"DISCOVERY_JOB_SCHEMA_INVALID"},400);
    try{return json(await new SniperStore(env.DB).createDiscoveryJob({jobId:body.jobId,locality:body.locality,categories:body.categories.map(String),maxCandidates:body.maxCandidates,sourceIds:body.sourceIds.map(String)}),201);}catch(error){return json({error:error instanceof Error?error.message:"DISCOVERY_JOB_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/discovery/finding"){
    const body=await request.json() as {jobId?:string;findingId?:string;finding?:unknown;auditId?:string;audit?:unknown;rawEvidenceDigest?:string|null};
    if(!body.jobId||!body.findingId||!body.finding||typeof body.finding!=="object"||!body.auditId||!body.audit||typeof body.audit!=="object")return json({error:"DISCOVERY_FINDING_SCHEMA_INVALID"},400);
    try{return json(await new SniperStore(env.DB).recordDiscoveryFinding({jobId:body.jobId,findingId:body.findingId,finding:body.finding as import("../../../packages/sniper/src/discovery.js").RawBusinessFinding,auditId:body.auditId,audit:body.audit as import("../../../packages/sniper/src/discovery.js").DigitalAuditEvidence,...(body.rawEvidenceDigest!==undefined?{rawEvidenceDigest:body.rawEvidenceDigest}:{})}),201);}catch(error){return json({error:error instanceof Error?error.message:"DISCOVERY_FINDING_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/skills/verify"){
    const body=await request.json() as {sourceId?:string;revisionPin?:string;benchmarkScore?:number;health?:"HEALTHY"|"UNKNOWN"|"DEGRADED";verifiedAt?:string};
    if(!body.sourceId||!body.revisionPin||typeof body.benchmarkScore!=="number"||!body.health)return json({error:"SKILL_VERIFY_SCHEMA_INVALID"},400);
    try{return json(await new SniperStore(env.DB).verifySkillSource({sourceId:body.sourceId,revisionPin:body.revisionPin,benchmarkScore:body.benchmarkScore,health:body.health,...(body.verifiedAt?{verifiedAt:body.verifiedAt}:{})}),201);}catch(error){return json({error:error instanceof Error?error.message:"SKILL_VERIFY_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/telemetry/span"){
    const body=await request.json() as Partial<TelemetrySpanInput>;
    if(!body.traceId||!body.spanId||!body.kind||!body.operation||!body.status||!body.startedAt||!body.endedAt||typeof body.inputTokens!=="number"||typeof body.outputTokens!=="number"||typeof body.actualCostUsd!=="number"||!body.attributes||typeof body.attributes!=="object")return json({error:"TELEMETRY_SPAN_SCHEMA_INVALID"},400);
    try{return json(await new SniperStore(env.DB).recordTelemetrySpan(body as TelemetrySpanInput),201);}catch(error){return json({error:error instanceof Error?error.message:"TELEMETRY_SPAN_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/global/plan"){
    const body=await request.json() as {preferredTags?:string[];maxConcurrentCases?:number;minEvidenceCount?:number};
    const policy={
      preferredTags:Array.isArray(body.preferredTags)?body.preferredTags.map(String):[],
      maxConcurrentCases:Number(body.maxConcurrentCases??8),
      minEvidenceCount:Number(body.minEvidenceCount??2)
    };
    try{return json(await new SniperStore(env.DB).planGlobal(policy),201);}catch(error){return json({error:error instanceof Error?error.message:"GLOBAL_PLAN_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/decision"){
    const body=await request.json() as Partial<CognitiveContext>;
    if(!body.opportunityId||!body.stage||typeof body.contactsAvailable!=="boolean"||typeof body.demoReady!=="boolean"||!body.replyState||typeof body.attempts!=="number"||typeof body.daysSinceLastTouch!=="number"||!body.humanGate||!Array.isArray(body.tacticStats))return json({error:"SNIPER_DECISION_SCHEMA_INVALID"},400);
    try{return json(await new SniperStore(env.DB).decide(body as CognitiveContext),201);}catch(error){return json({error:error instanceof Error?error.message:"SNIPER_DECISION_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/episode"){
    const body=await request.json() as Partial<MemoryEpisode>;
    if(!body.episodeId||!body.opportunityId||!body.agentRole||!body.tacticId||!body.observation||!body.outcome||typeof body.audited!=="boolean"||!Array.isArray(body.evidenceRefs)||!body.createdAt)return json({error:"SNIPER_EPISODE_SCHEMA_INVALID"},400);
    try{return json(await new SniperStore(env.DB).recordEpisode(body as MemoryEpisode),201);}catch(error){return json({error:error instanceof Error?error.message:"SNIPER_EPISODE_FAILED"},400);}
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/feedback"){
    const body=await request.json() as {tacticId?:string;observation?:LearningObservation;evidenceRefs?:string[]};
    if(!body.tacticId||!body.observation||!Array.isArray(body.evidenceRefs)||body.evidenceRefs.length===0)return json({error:"SNIPER_FEEDBACK_SCHEMA_INVALID"},400);
    if(!["REPLIED","MEETING","WON","LOST","UNKNOWN"].includes(body.observation.outcome)||typeof body.observation.audited!=="boolean")return json({error:"SNIPER_FEEDBACK_SCHEMA_INVALID"},400);
    const result=await new SniperStore(env.DB).learn(body.tacticId,body.observation,body.evidenceRefs);
    return json(result);
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/negotiation"){
    const body=await request.json() as {id?:string;opportunityId?:string;state?:string;currentOfferArs?:number;floorPriceArs?:number;objections?:string[];concessions?:string[];nextAction?:string;meetingRequested?:boolean;nonStandardTerms?:boolean;legalCommitment?:boolean;lastContactAt?:string};
    if(!body.id||!body.opportunityId||!body.state||!body.nextAction)return json({error:"SNIPER_NEGOTIATION_SCHEMA_INVALID"},400);
    const gate=requiresHumanGate({amountArs:Number(body.currentOfferArs??0),meetingRequested:Boolean(body.meetingRequested),nonStandardTerms:Boolean(body.nonStandardTerms),legalCommitment:Boolean(body.legalCommitment)});
    await new SniperStore(env.DB).recordNegotiation({id:body.id,opportunityId:body.opportunityId,state:body.state,...((typeof body.currentOfferArs==="number"&&Number.isFinite(body.currentOfferArs))?{currentOfferArs:body.currentOfferArs}:{}),...((typeof body.floorPriceArs==="number"&&Number.isFinite(body.floorPriceArs))?{floorPriceArs:body.floorPriceArs}:{}),objections:body.objections??[],concessions:body.concessions??[],nextAction:body.nextAction,humanGate:gate.required,humanGateReasons:gate.reasons,...(body.lastContactAt?{lastContactAt:body.lastContactAt}:{})});
    return json({ok:true,humanGate:gate});
  }
 if(request.method==="POST"&&url.pathname==="/api/sniper/payment"){
    const body=await request.json() as {id?:string;opportunityId?:string;state?:string;amountArs?:number;provider?:string;externalReference?:string};
    if(!body.id||!body.opportunityId||!body.state||typeof body.amountArs!=="number"||!Number.isFinite(body.amountArs)||!body.provider)return json({error:"SNIPER_PAYMENT_SCHEMA_INVALID"},400);
    await new SniperStore(env.DB).recordPayment({id:body.id,opportunityId:body.opportunityId,state:body.state,amountArs:Number(body.amountArs),provider:body.provider,...(body.externalReference?{externalReference:body.externalReference}:{})});
    return json({ok:true});
  }
 if(request.method==="POST"&&url.pathname.startsWith("/api/compute/probe/")){const providerId=decodeURIComponent(url.pathname.slice("/api/compute/probe/".length)),body=await request.json() as{modelId?:string};if(!body.modelId)return json({error:"MODEL_ID_REQUIRED"},400);const probe=await probeProvider(env,providerId,body.modelId);if(!probe.ok)return json(probe,409);const runtime=await buildComputeRuntime(env);await runtime.store.addEvidence(probe.evidence!);return json({ok:true,providerId,modelId:body.modelId,evidenceId:probe.evidence!.evidenceId,expiresAt:probe.evidence!.expiresAt,detail:probe.detail},200);}
 if(request.method==="POST"&&url.pathname==="/api/compute/run"){const body=await request.json() as Partial<ComputeRequest>;if(!body.taskId||!body.role||!body.tier||!body.taskClass||!body.dataClass||typeof body.pii!=="boolean"||!body.prompt||!Number.isFinite(body.requestedMaxOutputTokens)||!Array.isArray(body.requiredCapabilities)||!body.reason)return json({error:"COMPUTE_REQUEST_SCHEMA_INVALID"},400);try{const result=await executeComputeRequest(env,body as ComputeRequest);return json({text:result.text,receipt:result.receipt,route:result.route,reservation:result.reservation});}catch(error){const message=error instanceof Error?error.message:"NO_SAFE_MODEL_ROUTE";return json({error:message,deferred:!body.critical,costUsd:0},409);}}
 if(request.method==="POST"&&url.pathname.startsWith("/api/compute/disable/")){const id=decodeURIComponent(url.pathname.slice("/api/compute/disable/".length)),runtime=await buildComputeRuntime(env);if(!runtime.registry.disable(id,"EMERGENCY_OPERATOR_KILL"))return json({error:"PROVIDER_OR_MODEL_NOT_FOUND"},404);for(const p of runtime.registry.listProviders())await runtime.store.upsertProvider(p);for(const m of runtime.registry.listModels())await runtime.store.upsertModel(m);return json({disabled:id,durable:true,costUsd:0});}
 if(request.method==="POST"&&url.pathname==="/api/actions/request"){if(!env.APPROVAL_SIGNING_KEY||!env.MODELS)return json({error:"CORE_BINDING_REQUIRED"},503);const body=await request.json() as{actionClass?:ActionClass;payload?:Record<string,unknown>;reason?:string;requestedBy?:"CEO"|"RESEARCH"|"CMO"|"SALES"|"DATA"|"DEV"|"AUD";connector?:string;operation?:string;target?:string;subjectId?:string;taskId?:string};const classes:ActionClass[]=["READ_PUBLIC","READ_PRIVATE","INTERNAL_WRITE","DRAFT_EXTERNAL","SEND_EXTERNAL","PUBLISH_CONTENT","MONEY_MUTATION","DESTRUCTIVE_MUTATION","CREDENTIAL_MUTATION","CODE_WRITE","CODE_MERGE","DEPLOY"];if(!body.actionClass||!classes.includes(body.actionClass)||!body.payload||typeof body.payload!=="object")return json({error:"ACTION_SCHEMA_INVALID"},400);if(body.subjectId&&["SEND_EXTERNAL","PUBLISH_CONTENT","MONEY_MUTATION","CREDENTIAL_MUTATION","DEPLOY"].includes(body.actionClass)&&await new CommercialGuard(env.DB).caseExists(body.subjectId))return json({error:"CASE_EXTERNAL_ACTION_REQUIRES_COMMERCIAL_GATE"},409);const requestedBy=body.requestedBy??"CEO",policy=new PolicyEngine(),decision=policy.decision(body.actionClass),orchestrator=new AriaOrchestrator(store,modelProvider(env),env.APPROVAL_SIGNING_KEY);await orchestrator.load();if(decision==="DENY")return json({error:"ACTION_DENIED_BY_POLICY",actionClass:body.actionClass},403);if(decision==="ALLOW"){const id=await stableId("action",{actionClass:body.actionClass,payload:body.payload,at:Date.now()});orchestrator.state.actions.push({id,actionClass:body.actionClass,payload:structuredClone(body.payload),requestedBy,policyDecision:decision,status:"DRAFT",createdAt:new Date().toISOString()});await orchestrator.persist();return json({id,policyDecision:decision,status:"DRAFT",externalEffect:false},201);}const now=new Date(),preconditionHash=await businessPreconditionHash(orchestrator.state),intent=await createActionIntent({taskId:body.taskId??await stableId("task",{requestedBy,at:now.toISOString()}),agentId:requestedBy,subjectId:body.subjectId??"business",actionClass:body.actionClass,connector:body.connector??"safe-outbound",operation:body.operation??"send",target:body.target??String(body.payload.to??"unspecified"),canonicalParameters:body.payload,justification:String(body.reason??"protected action").slice(0,512),evidenceRefs:[],preconditionHash,idempotencyKey:await stableId("idem",{requestedBy,body:body.payload,at:now.toISOString()}),requestedAt:now.toISOString(),expiresAt:new Date(now.getTime()+15*60000).toISOString()});intent.status="APPROVAL_REQUIRED";await store.commitStateAndIntent(orchestrator.state,intent);orchestrator.state.actionIntents.push(intent);const approval=await orchestrator.approvals.request({actionClass:body.actionClass,requestedBy,reason:intent.justification,scope:"action-digest",actionDigest:intent.actionDigest,policyVersion:intent.policyVersion,approvalChainVersion:intent.approvalChainVersion});intent.approvalId=approval.id;const actionId=await stableId("action",{intentId:intent.intentId});orchestrator.state.actions.push({id:actionId,actionClass:body.actionClass,payload:structuredClone(body.payload),requestedBy,policyDecision:decision,approvalId:approval.id,status:"BLOCKED",createdAt:now.toISOString()});await store.commitStateAndIntent(orchestrator.state,intent);orchestrator.state.approvals=orchestrator.approvals.list();await orchestrator.persist();if(env.BUSINESS_WORKFLOW)await env.BUSINESS_WORKFLOW.create({id:approval.id,params:{taskId:actionId,kind:body.actionClass,approvalId:approval.id}});return json({actionId,intentId:intent.intentId,actionDigest:intent.actionDigest,approvalId:approval.id,policyDecision:decision,status:"PENDING_APPROVAL"},202);}
 if(request.method==="POST"&&url.pathname==="/api/reference-e2e"){if(!env.APPROVAL_SIGNING_KEY||!env.EFFECTS||!env.MODELS)return json({error:"LIVE_BINDINGS_REQUIRED"},503);const orchestrator=new AriaOrchestrator(store,modelProvider(env),env.APPROVAL_SIGNING_KEY,()=>new Date("2026-08-19T15:00:00.000Z"));await orchestrator.load();const result=await orchestrator.runReferenceE2E(await referenceEvents(),new ServiceEffectDispatcher(env.EFFECTS));return json({...result,state:undefined});}
 const approvalMatch=url.pathname.match(/^\/api\/approvals\/([^/]+)\/(approve|reject)$/);if(request.method==="POST"&&approvalMatch){if(!env.APPROVAL_SIGNING_KEY||!env.MODELS)return json({error:"CORE_BINDING_REQUIRED"},503);const orchestrator=new AriaOrchestrator(store,modelProvider(env),env.APPROVAL_SIGNING_KEY);await orchestrator.load();const id=decodeURIComponent(approvalMatch[1]!),operation=approvalMatch[2]!;try{const body=await request.json() as{actor?:string},actor=String(body.actor??"cockpit-human").slice(0,128),result=operation==="approve"?await orchestrator.approvals.approve(id,actor):orchestrator.approvals.reject(id,actor);orchestrator.state.approvals=orchestrator.approvals.list();await orchestrator.persist();if(env.BUSINESS_WORKFLOW){try{await env.BUSINESS_WORKFLOW.get(id).sendEvent({type:"approval",payload:{approvalId:id,decision:operation==="approve"?"APPROVED":"REJECTED"}});}catch{}}if(operation==="approve"){const intent=orchestrator.state.actionIntents.find(v=>v.approvalId===id);if(!intent)return json({error:"APPROVAL_INTENT_NOT_FOUND"},409);try{const effect=await dispatchApprovedIntent(orchestrator,env,intent,result);return json({approval:orchestrator.approvals.get(id),intent,effect});}catch(error){intent.status="RETRYABLE";await store.commitStateAndIntent(orchestrator.state,intent);return json({approval:result,intent,error:error instanceof Error?error.message:"EFFECT_DISPATCH_FAILED",status:"RETRYABLE"},409);}}return json(result);}catch(error){return json({error:error instanceof Error?error.message:"APPROVAL_ERROR"},400);}}
 if(request.method==="POST"&&url.pathname==="/api/ingest/webhook"){if(!env.WEBHOOK_SECRET)return json({error:"WEBHOOK_NOT_CONFIGURED"},503);const raw=await request.text(),signature=request.headers.get("x-aria-signature")??"";try{const event=await new WebhookIngestConnector(env.WEBHOOK_SECRET).parse(raw,signature);if(env.EVENTS_QUEUE)await env.EVENTS_QUEUE.send({kind:"event",event});else return json({error:"EVENT_QUEUE_NOT_CONFIGURED"},503);return json({accepted:true,id:event.id},202);}catch(error){return json({error:error instanceof Error?error.message:"INGEST_ERROR"},400);}}
 return json({error:"NOT_FOUND"},404);}
const CRON_JOB:Record<string,ScheduledJobName>={"*/15 * * * *":"business_tick","0 14 * * 1-5":"daily_ceo","0 6 * * *":"nightly_memory","0 10 * * 0":"weekly_security"};
function secureAssetResponse(response:Response):Response{
 const headers=new Headers(response.headers);
 headers.set("x-content-type-options","nosniff");
 headers.set("referrer-policy","no-referrer");
 headers.set("x-frame-options","DENY");
 headers.set("permissions-policy","camera=(), microphone=(), geolocation=(), payment=()");
 headers.set("strict-transport-security","max-age=31536000; includeSubDomains");
 if((headers.get("content-type")??"").includes("text/html")){
   headers.set("content-security-policy","default-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");
 }
 return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
}
export default{async fetch(request:Request,env:Env):Promise<Response>{const r=await api(request,env);if(r)return r;if(env.ASSETS)return secureAssetResponse(await env.ASSETS.fetch(request));return new Response("iAffice cockpit assets not bound",{status:503,headers:{"x-content-type-options":"nosniff","referrer-policy":"no-referrer"}});},async scheduled(controller:{cron?:string;scheduledTime?:number},env:Env):Promise<void>{const name=CRON_JOB[controller.cron??""]??"business_tick",slot=new Date(controller.scheduledTime??Date.now()).toISOString(),store=new D1StateStore(env.DB),state=await store.load(),scheduler=new Scheduler(state),queued=await scheduler.enqueue(name,slot);await store.save(state);if(!queued.duplicate&&env.EVENTS_QUEUE)await env.EVENTS_QUEUE.send({kind:"scheduled",taskId:queued.task.id,job:name,slot});if(name==="business_tick"){await new SniperStore(env.DB).planGlobal({preferredTags:[],maxConcurrentCases:8,minEvidenceCount:2},slot);if(env.COMPUTE_GOVERNOR){const runtime=await buildComputeRuntime(env);await runtime.governor.expire(slot);}}},async queue(batch:MessageBatch,env:Env):Promise<void>{const store=new D1StateStore(env.DB);for(const message of batch.messages){try{const body=message.body as{kind?:string;taskId?:string;jobId?:string};if(body.kind==="demo-dispatch"&&body.jobId){await dispatchDemoJob(env,body.jobId);message.ack();continue;}if(body.kind==="scheduled"&&body.taskId){const state=await store.load(),task=state.tasks.find(v=>v.id===body.taskId);if(!task)throw new Error("SCHEDULED_TASK_NOT_FOUND");if(task.status==="DONE"){message.ack();continue;}task.status="RUNNING";await store.save(state);if(env.BUSINESS_WORKFLOW)await env.BUSINESS_WORKFLOW.create({id:task.id,params:{taskId:task.id,kind:task.type}});else throw new Error("BUSINESS_WORKFLOW_NOT_CONFIGURED");task.status="DONE";await store.save(state);message.ack();continue;}if(body.kind==="event"){message.ack();continue;}throw new Error("QUEUE_MESSAGE_SCHEMA_INVALID");}catch{message.retry({delaySeconds:30});}}}};