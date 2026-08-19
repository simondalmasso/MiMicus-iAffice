import type { ComputeBenchmarkProfile, ProviderHealthRecord } from "./computeTypes.js";
export interface ScoreInputs{benchmark:ComputeBenchmarkProfile;health:ProviderHealthRecord;quotaHeadroom:number;providerDiversity:boolean;roleSuccessRate?:number;}
export interface ScoreBreakdown{quality:number;schema:number;reliability:number;latency:number;quota:number;diversity:number;role:number;total:number;}
export function scoreRoute(input:ScoreInputs):ScoreBreakdown{
  const clamp=(n:number)=>Math.max(0,Math.min(1,n));const quality=clamp(input.benchmark.score)*3000,schema=clamp(input.benchmark.schemaSuccessRate)*1000,reliability=clamp(input.benchmark.successRate)*2000;
  const latency=Math.max(0,1500-Math.min(1500,input.benchmark.latencyP95Ms/4));const quota=clamp(input.quotaHeadroom)*1500;const diversity=input.providerDiversity?500:0;const role=clamp(input.roleSuccessRate??.8)*500;
  const healthPenalty=input.health.state==="HEALTHY"?0:input.health.state==="UNKNOWN"?250:1000;const total=Math.round(quality+schema+reliability+latency+quota+diversity+role-healthPenalty);
  return{quality:Math.round(quality),schema:Math.round(schema),reliability:Math.round(reliability),latency:Math.round(latency),quota:Math.round(quota),diversity,role:Math.round(role),total};
}
