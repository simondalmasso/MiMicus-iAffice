import type { ComputeGovernor, ReservationRequest } from "./computeGovernor.js";
import type { ComputeReservation, QuotaPool } from "./computeTypes.js";
export interface ComputeGovernorStub{fetch(input:Request|string,init?:RequestInit):Promise<Response>;}
async function post<T>(stub:ComputeGovernorStub,path:string,body:unknown):Promise<T>{const response=await stub.fetch(`https://compute-governor.internal${path}`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body)});const json=await response.json() as T&{error?:string};if(!response.ok)throw new Error(json.error??`COMPUTE_GOVERNOR_HTTP_${response.status}`);return json;}
async function get<T>(stub:ComputeGovernorStub,path:string):Promise<T>{const response=await stub.fetch(`https://compute-governor.internal${path}`);const json=await response.json() as T&{error?:string};if(!response.ok)throw new Error(json.error??`COMPUTE_GOVERNOR_HTTP_${response.status}`);return json;}
export class DurableComputeGovernorClient implements ComputeGovernor{
 constructor(private readonly stub:ComputeGovernorStub){}
 async configure(pool:QuotaPool):Promise<void>{await post(this.stub,"/configure",{pool});}
 reserve(request:ReservationRequest):Promise<ComputeReservation>{return post(this.stub,"/reserve",request);}
 commit(reservationId:string,actualUsage:number,now:string):Promise<ComputeReservation>{return post(this.stub,"/commit",{reservationId,actualUsage,now});}
 release(reservationId:string,now:string):Promise<ComputeReservation>{return post(this.stub,"/release",{reservationId,now});}
 async markUnknown(reservationId:string):Promise<void>{await post(this.stub,"/unknown",{reservationId});}
 async expire(now:string):Promise<number>{return (await post<{expired:number}>(this.stub,"/expire",{now})).expired;}
 get(reservationId:string):Promise<ComputeReservation|undefined>{return get<ComputeReservation|null>(this.stub,`/reservation/${encodeURIComponent(reservationId)}`).then(x=>x??undefined);}
 list():Promise<ComputeReservation[]>{return get(this.stub,"/reservations");}
 pool(id:string):Promise<QuotaPool|undefined>{return get<Record<string,unknown>|null>(this.stub,`/pool/${encodeURIComponent(id)}`).then(row=>row?({quotaPoolId:String(row.quota_pool_id),providerId:String(row.provider_id),...(row.model_id?{modelId:String(row.model_id)}:{}),dimension:String(row.dimension) as QuotaPool["dimension"],verifiedFreeCeiling:row.verified_free_ceiling===null?null:Number(row.verified_free_ceiling),localHardFraction:Number(row.local_hard_fraction),consumed:Number(row.consumed),reserved:Number(row.reserved),...(row.upstream_remaining!==null&&row.upstream_remaining!==undefined?{upstreamRemaining:Number(row.upstream_remaining)}:{}),...(row.resets_at?{resetsAt:String(row.resets_at)}:{}),evidenceId:String(row.evidence_id),updatedAt:String(row.updated_at)}):undefined);}
}
