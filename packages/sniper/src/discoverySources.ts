export type DiscoveryCapability =
  | "PUBLIC_DIRECTORY_SEARCH"
  | "PUBLIC_WEB_CRAWL"
  | "PUBLIC_WEB_AUDIT"
  | "BROWSER_INTERACTION";

export type DiscoveryRuntimeCost = "FREE_SELF_HOSTED" | "FREE_API_VERIFIED" | "PAID" | "UNKNOWN";
export type DiscoverySourceHealth = "HEALTHY" | "UNKNOWN" | "DEGRADED";
export type DiscoverySourceAdmissionState = "ENABLED" | "QUARANTINED" | "REJECTED";

export interface DiscoverySourceCandidate {
  id:
    | "FIRECRAWL_SELF_HOSTED"
    | "CRAWL4AI_SELF_HOSTED"
    | "BROWSER_USE_SELF_HOSTED"
    | "BROWSER_USE_CLOUD"
    | "SCRAPLING_SELF_HOSTED";
  label: string;
  source: string;
  license: string;
  revisionPin: string | null;
  capabilities: DiscoveryCapability[];
  runtimeCost: DiscoveryRuntimeCost;
  zeroCostVerified: boolean;
  targetTermsVerified: boolean;
  automationAllowed: boolean;
  publicBusinessDataOnly: boolean;
  localityScope: "ANY";
  health: DiscoverySourceHealth;
  notes: string[];
}

export interface DiscoverySourceAdmission {
  state: DiscoverySourceAdmissionState;
  reasons: string[];
}

export const DISCOVERY_SOURCE_CANDIDATES: DiscoverySourceCandidate[] = [
  {
    id:"FIRECRAWL_SELF_HOSTED",
    label:"Firecrawl self-hosted",
    source:"https://github.com/firecrawl/firecrawl",
    license:"AGPL-3.0",
    revisionPin:null,
    capabilities:["PUBLIC_WEB_CRAWL","PUBLIC_WEB_AUDIT"],
    runtimeCost:"FREE_SELF_HOSTED",
    zeroCostVerified:false,
    targetTermsVerified:false,
    automationAllowed:false,
    publicBusinessDataOnly:true,
    localityScope:"ANY",
    health:"UNKNOWN",
    notes:[
      "AGPL network-use obligations require dedicated license review before deployment.",
      "Hosted API is not assumed free.",
      "Target-site terms remain independent from crawler license."
    ]
  },
  {
    id:"CRAWL4AI_SELF_HOSTED",
    label:"Crawl4AI self-hosted",
    source:"https://github.com/unclecode/crawl4ai",
    license:"Apache-2.0",
    revisionPin:null,
    capabilities:["PUBLIC_WEB_CRAWL","PUBLIC_WEB_AUDIT","BROWSER_INTERACTION"],
    runtimeCost:"FREE_SELF_HOSTED",
    zeroCostVerified:false,
    targetTermsVerified:false,
    automationAllowed:false,
    publicBusinessDataOnly:true,
    localityScope:"ANY",
    health:"UNKNOWN",
    notes:[
      "Open-source self-hosted path is distinct from hosted pay-as-you-go cloud.",
      "Target-source automation permission must be verified separately."
    ]
  },
  {
    id:"BROWSER_USE_SELF_HOSTED",
    label:"Browser Use self-hosted",
    source:"https://github.com/browser-use/browser-use",
    license:"MIT",
    revisionPin:null,
    capabilities:["BROWSER_INTERACTION","PUBLIC_WEB_AUDIT"],
    runtimeCost:"FREE_SELF_HOSTED",
    zeroCostVerified:false,
    targetTermsVerified:false,
    automationAllowed:false,
    publicBusinessDataOnly:true,
    localityScope:"ANY",
    health:"UNKNOWN",
    notes:[
      "Only self-hosted library path is eligible for zero-spend review.",
      "Hosted cloud browser is a separate paid product."
    ]
  },
  {
    id:"BROWSER_USE_CLOUD",
    label:"Browser Use Cloud",
    source:"https://browser-use.com",
    license:"SERVICE",
    revisionPin:null,
    capabilities:["BROWSER_INTERACTION","PUBLIC_WEB_AUDIT"],
    runtimeCost:"PAID",
    zeroCostVerified:false,
    targetTermsVerified:false,
    automationAllowed:false,
    publicBusinessDataOnly:true,
    localityScope:"ANY",
    health:"UNKNOWN",
    notes:["Upstream currently advertises paid browser-hour usage; incompatible with ORDER-003 zero-spend."]
  },
  {
    id:"SCRAPLING_SELF_HOSTED",
    label:"Scrapling self-hosted",
    source:"https://github.com/D4Vinci/Scrapling",
    license:"BSD-3-Clause",
    revisionPin:null,
    capabilities:["PUBLIC_WEB_CRAWL","PUBLIC_WEB_AUDIT"],
    runtimeCost:"FREE_SELF_HOSTED",
    zeroCostVerified:false,
    targetTermsVerified:false,
    automationAllowed:false,
    publicBusinessDataOnly:true,
    localityScope:"ANY",
    health:"UNKNOWN",
    notes:["Library license is permissive; target-site permission is still a separate gate."]
  }
];

export function evaluateDiscoverySourceAdmission(candidate: DiscoverySourceCandidate | undefined): DiscoverySourceAdmission {
  if(!candidate) return {state:"REJECTED",reasons:["SOURCE_NOT_FOUND"]};
  const rejected:string[]=[];
  const quarantined:string[]=[];
  if(candidate.runtimeCost==="PAID") rejected.push("PAID_RUNTIME_FORBIDDEN");
  if(!candidate.publicBusinessDataOnly) rejected.push("NON_PUBLIC_BUSINESS_DATA_FORBIDDEN");
  if(!candidate.license) rejected.push("LICENSE_UNVERIFIED");
  if(candidate.license==="AGPL-3.0") quarantined.push("AGPL_NETWORK_USE_REVIEW_REQUIRED");
  if(candidate.runtimeCost==="UNKNOWN") quarantined.push("RUNTIME_COST_UNKNOWN");
  if(!candidate.zeroCostVerified) quarantined.push("ZERO_COST_RUNTIME_NOT_VERIFIED");
  if(!candidate.revisionPin) quarantined.push("REVISION_PIN_REQUIRED");
  if(!candidate.targetTermsVerified) quarantined.push("TARGET_TERMS_NOT_VERIFIED");
  if(!candidate.automationAllowed) quarantined.push("TARGET_AUTOMATION_NOT_VERIFIED");
  if(candidate.health!=="HEALTHY") quarantined.push("HEALTH_NOT_VERIFIED");
  if(rejected.length) return {state:"REJECTED",reasons:rejected};
  if(quarantined.length) return {state:"QUARANTINED",reasons:[...new Set(quarantined)]};
  return {state:"ENABLED",reasons:["LICENSE_COST_TERMS_AUTOMATION_HEALTH_VERIFIED"]};
}

export function selectDiscoverySources(
  candidates: DiscoverySourceCandidate[],
  request:{capability:DiscoveryCapability;locality:string}
):DiscoverySourceCandidate[]{
  if(!request.locality.trim()) return [];
  return candidates
    .filter(x=>evaluateDiscoverySourceAdmission(x).state==="ENABLED")
    .filter(x=>x.capabilities.includes(request.capability))
    .sort((a,b)=>a.id.localeCompare(b.id));
}
