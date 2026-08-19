import type { ComputeErrorClass, ProviderHealthRecord, ProviderHealthState } from "./computeTypes.js";

export interface HealthObservation { status?:number; error?:string; now:string; retryAfter?:string; modelMissing?:boolean; malformed?:boolean; usageAnomaly?:boolean; }

export function classifyProviderFailure(o:HealthObservation):{state:ProviderHealthState;errorClass:ComputeErrorClass|"MODEL_RESPONSE_INVALID";terminal:boolean}{
  if(o.status===402)return{state:"BILLING_RISK",errorClass:"BILLING_REQUIRED",terminal:true};
  if(o.status===401)return{state:"AUTH_FAILED",errorClass:"AUTH_INVALID",terminal:true};
  if(o.status===403)return{state:"AUTH_FAILED",errorClass:"AUTH_INVALID",terminal:true};
  if(o.status===404||o.modelMissing)return{state:"MODEL_MISSING",errorClass:"MODEL_REMOVED",terminal:true};
  if(o.status===429)return{state:"RATE_LIMITED",errorClass:"RATE_LIMITED",terminal:false};
  if((o.status??0)>=500)return{state:"OUTAGE",errorClass:"PROVIDER_OUTAGE",terminal:false};
  if(o.malformed||o.usageAnomaly)return{state:"DEGRADED",errorClass:"MODEL_RESPONSE_INVALID",terminal:false};
  if(/timeout/i.test(o.error??""))return{state:"OUTAGE",errorClass:"PROVIDER_OUTAGE",terminal:false};
  return{state:"DEGRADED",errorClass:"MODEL_RESPONSE_INVALID",terminal:false};
}

export class ProviderHealthManager {
  private states=new Map<string,ProviderHealthRecord>();
  private key(providerId:string,modelId?:string):string{return`${providerId}:${modelId??"*"}`;}
  get(providerId:string,modelId?:string):ProviderHealthRecord{return structuredClone(this.states.get(this.key(providerId,modelId))??{providerId,...(modelId?{modelId}:{}),state:"UNKNOWN",consecutiveFailures:0,detail:"no observation"});}
  success(providerId:string,modelId:string,now:string):ProviderHealthRecord{const value:ProviderHealthRecord={providerId,modelId,state:"HEALTHY",consecutiveFailures:0,lastSuccessAt:now,detail:"probe/call success"};this.states.set(this.key(providerId,modelId),value);return structuredClone(value);}
  failure(providerId:string,modelId:string,o:HealthObservation):ProviderHealthRecord{const prior=this.get(providerId,modelId),classified=classifyProviderFailure(o),failures=prior.consecutiveFailures+1;let state=classified.state;if(!classified.terminal&&failures<2&&state==="OUTAGE")state="DEGRADED";const value:ProviderHealthRecord={providerId,modelId,state,consecutiveFailures:failures,...(prior.lastSuccessAt?{lastSuccessAt:prior.lastSuccessAt}:{}),lastFailureAt:o.now,...(o.retryAfter?{retryAfter:o.retryAfter}:{}),...(state==="BILLING_RISK"||state==="AUTH_FAILED"||failures>=2?{openedAt:o.now}:{}),detail:`${classified.errorClass};failures=${failures}`};this.states.set(this.key(providerId,modelId),value);return structuredClone(value);}
  disable(providerId:string,modelId:string,now:string,reason:string):void{this.states.set(this.key(providerId,modelId),{providerId,modelId,state:"DISABLED",consecutiveFailures:0,openedAt:now,detail:reason});}
  circuitOpen(providerId:string,modelId:string):boolean{return["AUTH_FAILED","BILLING_RISK","MODEL_MISSING","OUTAGE","DISABLED","POLICY_STALE","QUOTA_EXHAUSTED"].includes(this.get(providerId,modelId).state);}
  list():ProviderHealthRecord[]{return[...this.states.values()].map((x)=>structuredClone(x));}
}
