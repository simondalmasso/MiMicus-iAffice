import { sha256, stableId } from "../../core/src/hash.js";
import { COMPUTE_BENCHMARK_CORPUS, type BenchmarkCase } from "./benchmarkCorpus.js";
import type { ComputeBenchmarkProfile, InferenceExecution, TaskClass } from "./computeTypes.js";
import type { ComputeGovernor } from "./computeGovernor.js";
import type { ModelGateway } from "./modelRouter.js";
import { ProviderRegistry } from "./providerRegistry.js";
import { billingSafetyGate, estimateTokens } from "./computePolicy.js";
import type { ProviderEvidenceRecord } from "./computeTypes.js";
import { qualifies } from "./providerBenchmarks.js";

function normalized(s:string):string{return s.trim().replace(/^```(?:json)?\s*/i,"").replace(/```$/," ").trim().replace(/\s+/g," ").toLowerCase();}
function caseScore(c:BenchmarkCase,text:string):number{const actual=normalized(text),expected=normalized(c.expected);return actual===expected||actual.includes(expected)?1:0;}
function schemaScore(c:BenchmarkCase,text:string):number{if(c.taskClass!=="STRUCTURED_JSON")return text.trim()?1:0;try{JSON.parse(text.replace(/^```json\s*/i,"").replace(/```$/,""));return 1;}catch{return 0;}}
function percentile(values:number[],p:number):number{if(!values.length)return 0;const s=[...values].sort((a,b)=>a-b);return s[Math.min(s.length-1,Math.floor((s.length-1)*p))]!;}

export class ProviderBenchmarkRunner{
 constructor(private readonly registry:ProviderRegistry,private readonly evidence:ProviderEvidenceRecord[],private readonly governor:ComputeGovernor,private readonly gateway:ModelGateway){}
 async run(providerId:string,modelId:string,taskClass:TaskClass,now:string,cases:BenchmarkCase[]=COMPUTE_BENCHMARK_CORPUS.filter(c=>c.taskClass===taskClass)):Promise<ComputeBenchmarkProfile>{
  const provider=this.registry.getProvider(providerId),model=this.registry.getModel(providerId,modelId);if(!provider||!model)throw new Error("BENCHMARK_TARGET_UNKNOWN");this.registry.refreshStates(now);const current=this.registry.getProvider(providerId)!;if(!current.productionEligible)throw new Error("BENCHMARK_PROVIDER_NOT_POLICY_ELIGIBLE");if(billingSafetyGate(current,this.evidence,now)!=="ALLOW_ZERO_COST")throw new Error("BENCHMARK_BILLING_UNSAFE");if(!cases.length)throw new Error("BENCHMARK_CORPUS_EMPTY");
  let correct=0,schema=0,success=0;const latencies:number[]=[];
  for(const c of cases){const prompt=`Benchmark task class ${taskClass}. ${c.prompt}`,input=estimateTokens(prompt),maxOutput=128,reservation=await this.governor.reserve({routeDecisionId:`benchmark:${providerId}:${modelId}:${taskClass}`,providerId,modelId,quotaPoolId:model.freePoolId,estimatedInput:input,reservedOutput:maxOutput,reservedUsageUnits:input+maxOutput,idempotencyKey:`benchmark:${providerId}:${modelId}:${c.id}:${await sha256(prompt)}`,now});const promptHash=await sha256(prompt),providerConfigHash=await sha256({providerId:current.providerId,baseUrlId:current.baseUrlId,protocol:current.apiProtocol}),base={executionId:await stableId("benchmark-exec",{providerId,modelId,case:c.id}),reservationId:reservation.reservationId,taskId:`benchmark:${c.id}`,role:"AUD" as const,dataClass:"PUBLIC" as const,providerId,modelId,adapterVersion:"aria-model-gateway-v1",providerConfigHash,prompt,promptHash,maxOutputTokens:maxOutput,requiredCapabilities:["text"],policyVersion:"aria-compute-policy-v1",routeDecisionId:reservation.routeDecisionId,requestedAt:now,expiresAt:new Date(new Date(now).getTime()+120000).toISOString()},execution:InferenceExecution={...base,executionDigest:await sha256(base)};
    try{const out=await this.gateway.execute(execution);if(out.receipt.status!=="SUCCESS")throw new Error(out.receipt.errorClass??"BENCHMARK_CALL_FAILED");await this.governor.commit(reservation.reservationId,out.receipt.usageUnits,now);success++;correct+=caseScore(c,out.text);schema+=schemaScore(c,out.text);latencies.push(out.receipt.latencyMs);}catch(error){try{await this.governor.release(reservation.reservationId,now);}catch{}throw error;}}
  const profile:ComputeBenchmarkProfile={profileId:await stableId("benchmark-profile",{providerId,modelId,taskClass,now,corpus:cases.map(c=>c.id)}),providerId,modelId,taskClass,score:correct/cases.length,schemaSuccessRate:schema/cases.length,successRate:success/cases.length,latencyP50Ms:percentile(latencies,.5),latencyP95Ms:percentile(latencies,.95),qualified:false,measuredAt:now,evidenceClass:"LIVE_ACCOUNT_PROBE"};profile.qualified=qualifies(profile);return profile;
 }
}
