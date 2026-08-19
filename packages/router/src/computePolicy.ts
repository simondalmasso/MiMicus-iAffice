import type { BillingGateOutcome, ComputeModelRecord, ComputeProviderRecord, ComputeRequest, ModelDataClass, ProviderEvidenceRecord, RouteReasonCode } from "./computeTypes.js";
import { activatingEvidence } from "./providerEvidence.js";

const SECRET_PATTERNS: RegExp[] = [
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/i,
  /\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|session[_ -]?cookie|private[_ -]?key)\s*[:=]\s*[^\s,;]{6,}/i,
  /\bgh[pousr]_[A-Za-z0-9]{20,}\b/,
  /\bsk-[A-Za-z0-9_-]{16,}\b/,
  /\bBearer\s+[A-Za-z0-9._~+\/-]{16,}/i
];
export function containsSecret(prompt:string):boolean{return SECRET_PATTERNS.some((p)=>p.test(prompt));}
export function redactModelSecrets(prompt:string):string{let value=prompt;for(const p of SECRET_PATTERNS)value=value.replace(p,"[SECRET_REDACTED]");return value;}
export function estimateTokens(text:string):number{return Math.max(1,Math.ceil(text.length/4));}

export function deterministicDataClass(input:{declared:ModelDataClass;pii:boolean;prompt:string}):{dataClass:ModelDataClass;pii:boolean;secretDetected:boolean}{
  const secretDetected=containsSecret(input.prompt);return{dataClass:secretDetected?"SECRET":input.declared,pii:input.pii,secretDetected};
}

export function billingSafetyGate(provider:ComputeProviderRecord,evidence:ProviderEvidenceRecord[],now:string):BillingGateOutcome{
  if(provider.verificationExpiresAt<=now||!activatingEvidence(provider,evidence,now).ok)return"DENY_EVIDENCE_STALE";
  if(provider.freeType==="PAID"||provider.billingSafety==="BILLABLE")return"DENY_PRICE_NONZERO";
  if(provider.billingSafety==="UNKNOWN")return"DENY_BILLING_UNKNOWN";
  if(provider.overagePossible===true)return"DENY_OVERAGE_POSSIBLE";
  if(provider.freeType==="SIGNUP_GRANT"&&(provider.grantRemainingUnits??0)<=0)return"DENY_GRANT_EXHAUSTED";
  if(provider.freeType==="UNKNOWN")return"DENY_PRICE_UNKNOWN";
  return"ALLOW_ZERO_COST";
}

export function privacyReasons(request:ComputeRequest,provider:ComputeProviderRecord,model:ComputeModelRecord):RouteReasonCode[]{
  if(request.dataClass==="SECRET"||containsSecret(request.prompt))return["SECRET_DATA_MODEL_DENIED"];
  const reasons:RouteReasonCode[]=[];
  if(request.dataClass==="PUBLIC"&&!request.pii)return reasons;
  if(request.pii&&provider.publicOnly)reasons.push("PRIVACY_DENIED");
  if(request.dataClass==="INTERNAL_BUSINESS"||request.dataClass==="CONFIDENTIAL"){
    if(!["FIRST_PARTY_DIRECT","AUTHORIZED_AGGREGATOR"].includes(provider.trustClass))reasons.push("TRUST_CLASS_DENIED");
    if(!["NO_TRAINING","OPT_OUT_VERIFIED"].includes(provider.trainingUseClass))reasons.push("TRAINING_POLICY_DENIED");
    if(provider.retentionClass==="UNKNOWN")reasons.push("RETENTION_POLICY_DENIED");
    if(provider.publicOnly||provider.privacyClass==="PUBLIC_ONLY")reasons.push("PRIVACY_DENIED");
    if(model.identityAssurance!=="FIRST_PARTY_DECLARED"&&request.dataClass==="CONFIDENTIAL")reasons.push("IDENTITY_ASSURANCE_DENIED");
  }
  if(request.dataClass==="CONFIDENTIAL"&&provider.retentionClass!=="ZERO_RETENTION"&&provider.privacyClass!=="CONFIDENTIAL_ALLOWED")reasons.push("RETENTION_POLICY_DENIED");
  return[...new Set(reasons)];
}

export function capabilityReasons(request:ComputeRequest,model:ComputeModelRecord):RouteReasonCode[]{
  const reasons:RouteReasonCode[]=[];const input=estimateTokens(request.prompt);const required=input+request.requestedMaxOutputTokens;
  if(required>model.contextWindow||request.requestedMaxOutputTokens>model.maxOutputTokens)reasons.push("CONTEXT_TOO_SMALL");
  for(const capability of request.requiredCapabilities)if(!model.capabilities.includes(capability))reasons.push("CAPABILITY_MISMATCH");
  return[...new Set(reasons)];
}
