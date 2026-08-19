import type { ComputeBenchmarkProfile, TaskClass } from "./computeTypes.js";

export const FROZEN_QUALITY_THRESHOLDS:Record<TaskClass,{score:number;schemaSuccessRate:number;successRate:number}>={
  EXTRACTION:{score:.90,schemaSuccessRate:.90,successRate:.95},CLASSIFICATION:{score:.90,schemaSuccessRate:.90,successRate:.95},STRUCTURED_JSON:{score:.92,schemaSuccessRate:.95,successRate:.95},BUSINESS_REASONING:{score:.85,schemaSuccessRate:.85,successRate:.90},AUD_CHALLENGE:{score:.88,schemaSuccessRate:.88,successRate:.92},CODING:{score:.80,schemaSuccessRate:.85,successRate:.88},SUMMARIZATION:{score:.88,schemaSuccessRate:.88,successRate:.92}
};
export const THRESHOLDS_FROZEN_AT="2026-08-19T18:50:00.000Z";
export function qualifies(profile:ComputeBenchmarkProfile):boolean{const t=FROZEN_QUALITY_THRESHOLDS[profile.taskClass];return profile.score>=t.score&&profile.schemaSuccessRate>=t.schemaSuccessRate&&profile.successRate>=t.successRate;}
export class BenchmarkRegistry{private profiles:ComputeBenchmarkProfile[]=[];upsert(p:ComputeBenchmarkProfile):void{const value={...p,qualified:qualifies(p)};const i=this.profiles.findIndex(x=>x.providerId===p.providerId&&x.modelId===p.modelId&&x.taskClass===p.taskClass);if(i>=0)this.profiles[i]=value;else this.profiles.push(value);}get(providerId:string,modelId:string,taskClass:TaskClass):ComputeBenchmarkProfile|undefined{const p=this.profiles.find(x=>x.providerId===providerId&&x.modelId===modelId&&x.taskClass===taskClass);return p?structuredClone(p):undefined;}list():ComputeBenchmarkProfile[]{return this.profiles.map(x=>structuredClone(x));}}
