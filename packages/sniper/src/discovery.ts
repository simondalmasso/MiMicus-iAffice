import type { BusinessSignal, ContactPoint } from "./engine.js";

export interface DiscoverySourcePolicy {
  id: string;
  freeVerified: boolean;
  termsVerified: boolean;
  automatedAccessAllowed: boolean;
  publicBusinessDataOnly: boolean;
}

export interface DiscoveryJobRequest {
  jobId: string;
  locality: string;
  categories: string[];
  maxCandidates: number;
  sources: DiscoverySourcePolicy[];
  createdAt: string;
}

export interface DiscoveryJobDecision {
  allowed: boolean;
  reasons: string[];
}

export interface RawBusinessFinding {
  sourceId: string;
  sourceRef: string;
  name: string;
  category: string;
  locality: string;
  websiteUrl: string | null;
  businessContacts: ContactPoint[];
  rating: number | null;
  reviewCount: number | null;
  observedAt: string;
}

export interface DedupedBusinessFinding extends RawBusinessFinding {
  evidenceRefs: string[];
  sourceRefs: string[];
}

export interface DigitalAuditEvidence {
  evidenceRef: string;
  httpOk: boolean;
  performanceScore: number | null;
  accessibilityScore: number | null;
  mobileReadabilityScore: number | null;
  ecommerce: boolean | null;
  crm: boolean | null;
  whatsappAutomation: boolean | null;
  socialActive: boolean | null;
  booking: boolean | null;
  paymentsOnline: boolean | null;
  analytics: boolean | null;
}

export function evaluateDiscoveryJob(job: DiscoveryJobRequest): DiscoveryJobDecision {
  const reasons:string[]=[];
  if(!job.jobId) reasons.push("JOB_ID_REQUIRED");
  if(!job.locality.trim()) reasons.push("LOCALITY_REQUIRED");
  if(job.categories.length===0) reasons.push("CATEGORY_REQUIRED");
  if(!Number.isInteger(job.maxCandidates)||job.maxCandidates<1||job.maxCandidates>500) reasons.push("MAX_CANDIDATES_INVALID");
  if(job.sources.length===0) reasons.push("SOURCE_REQUIRED");
  for(const source of job.sources){
    if(!source.freeVerified) reasons.push("SOURCE_ZERO_COST_NOT_VERIFIED");
    if(!source.termsVerified) reasons.push("SOURCE_TERMS_NOT_VERIFIED");
    if(!source.automatedAccessAllowed) reasons.push("SOURCE_AUTOMATION_NOT_ALLOWED");
    if(!source.publicBusinessDataOnly) reasons.push("SOURCE_DATA_SCOPE_INVALID");
  }
  return {allowed:reasons.length===0,reasons:[...new Set(reasons)]};
}

function normalizedDomain(url:string|null):string|null{
  if(!url)return null;
  try{
    const u=new URL(url);
    return u.hostname.toLowerCase().replace(/^www\./,"");
  }catch{return null}
}

function normalizedName(value:string):string{
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"").replace(/(srl|sa|sas)$/,"");
}

function contactKey(contacts:ContactPoint[]):string|null{
  const preferred=contacts.find(x=>["EMAIL","WHATSAPP","PHONE"].includes(x.kind));
  return preferred?String(preferred.value).trim().toLowerCase():null;
}

export function dedupeBusinessFindings(findings: RawBusinessFinding[]): DedupedBusinessFinding[] {
  const groups=new Map<string,DedupedBusinessFinding>();
  for(const finding of findings){
    const domain=normalizedDomain(finding.websiteUrl);
    const contact=contactKey(finding.businessContacts);
    const key=domain?"domain:"+domain:contact?"contact:"+contact:"name:"+normalizedName(finding.name)+":"+normalizedName(finding.locality);
    const existing=groups.get(key);
    if(!existing){
      groups.set(key,{...structuredClone(finding),evidenceRefs:[finding.sourceRef],sourceRefs:[finding.sourceRef]});
      continue;
    }
    existing.evidenceRefs=[...new Set([...existing.evidenceRefs,finding.sourceRef])];
    existing.sourceRefs=[...new Set([...existing.sourceRefs,finding.sourceRef])];
    if((finding.reviewCount??0)>(existing.reviewCount??0)){
      existing.rating=finding.rating;
      existing.reviewCount=finding.reviewCount;
    }
    if(!existing.websiteUrl&&finding.websiteUrl) existing.websiteUrl=finding.websiteUrl;
    const seen=new Set(existing.businessContacts.map(x=>x.kind+":"+x.value));
    for(const contactPoint of finding.businessContacts){
      const k=contactPoint.kind+":"+contactPoint.value;
      if(!seen.has(k)){existing.businessContacts.push(structuredClone(contactPoint));seen.add(k);}
    }
    if(Date.parse(finding.observedAt)>Date.parse(existing.observedAt)) existing.observedAt=finding.observedAt;
  }
  return [...groups.values()];
}

function scorePart(value:number|null):number|null{
  if(value===null||!Number.isFinite(value))return null;
  return Math.max(0,Math.min(100,value));
}

export function websiteQualityFromEvidence(audit:DigitalAuditEvidence):number|null{
  if(!audit.httpOk)return 0;
  const values=[scorePart(audit.performanceScore),scorePart(audit.accessibilityScore),scorePart(audit.mobileReadabilityScore)].filter((x):x is number=>x!==null);
  if(values.length===0)return null;
  return Math.round(values.reduce((s,x)=>s+x,0)/values.length);
}

function stableBusinessId(finding:RawBusinessFinding):string{
  const domain=normalizedDomain(finding.websiteUrl);
  if(domain)return "domain:"+domain;
  const contact=contactKey(finding.businessContacts);
  if(contact)return "contact:"+contact;
  return "name:"+normalizedName(finding.name)+":"+normalizedName(finding.locality);
}

export function findingToBusinessSignal(finding:RawBusinessFinding,audit:DigitalAuditEvidence):BusinessSignal{
  const allowedContacts=finding.businessContacts.filter(x=>
    ["PUBLIC_BUSINESS_LISTING","BUSINESS_WEBSITE","BUSINESS_SOCIAL","OWNER_PROVIDED","OTHER_PUBLIC"].includes(x.provenance)
  );
  return {
    businessId:stableBusinessId(finding),
    name:finding.name,
    category:finding.category,
    locality:finding.locality,
    observedAt:finding.observedAt,
    demand:{rating:finding.rating,reviewCount:finding.reviewCount},
    digital:{
      websiteUrl:finding.websiteUrl,
      websiteQuality:websiteQualityFromEvidence(audit),
      ecommerce:audit.ecommerce,
      crm:audit.crm,
      whatsappAutomation:audit.whatsappAutomation,
      socialActive:audit.socialActive,
      booking:audit.booking,
      paymentsOnline:audit.paymentsOnline,
      analytics:audit.analytics
    },
    contacts:allowedContacts.map(x=>structuredClone(x)),
    evidenceRefs:[finding.sourceRef,audit.evidenceRef]
  };
}
