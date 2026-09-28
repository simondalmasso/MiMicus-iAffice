export type SkillRole =
  | "ORCHESTRATOR"
  | "SCOUT"
  | "MARKET_RESEARCH"
  | "QUALIFIER"
  | "SALES"
  | "NEGOTIATOR"
  | "UX_AUDITOR"
  | "WEB"
  | "DESIGN"
  | "SOCIAL"
  | "CATALOG"
  | "CRM"
  | "AUTOMATION"
  | "PAYMENTS"
  | "PRODUCT"
  | "ANALYTICS"
  | "COPY"
  | "DEMO"
  | "DELIVERY"
  | "AUD"
  | "MEMORY";

export type SkillDataClass = "PUBLIC" | "INTERNAL_BUSINESS" | "CONFIDENTIAL" | "SECRET";
export type SkillRuntime = "PROMPT_SKILL" | "PYTHON_SANDBOX" | "NODE_SANDBOX" | "CLOUD_JOB";
export type SkillCostClass = "FREE_VERIFIED" | "UNKNOWN" | "PAID";
export type SkillNetworkPermission = "NONE" | "PUBLIC_READ" | "EXTERNAL_READ" | "EXTERNAL_WRITE";
export type SkillHealth = "HEALTHY" | "UNKNOWN" | "DEGRADED";
export type SkillAdmissionState = "ENABLED" | "QUARANTINED" | "REJECTED";

export interface SkillSourceCandidate {
  id:
    | "COREY_MARKETING_SKILLS"
    | "ALIREZA_CLAUDE_SKILLS"
    | "ERIC_SIU_MARKETING_SKILLS"
    | "AARON_MARKETING_SKILLS"
    | "ADDY_AGENT_SKILLS"
    | "EMIL_UI_SKILLS";
  label: string;
  source: string;
  sourceVerified: boolean;
  license: string | null;
  revisionPin: string | null;
  roles: SkillRole[];
  capabilities: string[];
  runtime: SkillRuntime;
  costClass: SkillCostClass;
  networkPermission: SkillNetworkPermission;
  allowedDataClasses: SkillDataClass[];
  requiresSecrets: boolean;
  benchmarkScore: number | null;
  health: SkillHealth;
  notes: string[];
}

export const SKILL_SOURCE_CANDIDATES: SkillSourceCandidate[] = [
  {
    id:"COREY_MARKETING_SKILLS",
    label:"Marketing Skills for AI Agents",
    source:"https://github.com/coreyhaines31/marketingskills",
    sourceVerified:true,
    license:"MIT",
    revisionPin:null,
    roles:["MARKET_RESEARCH","SALES","ANALYTICS","COPY","SOCIAL","PRODUCT"],
    capabilities:["CRO","COPYWRITING","SEO","ANALYTICS","GROWTH","ATTRIBUTION","PRICING","SALES_ENABLEMENT"],
    runtime:"PROMPT_SKILL",
    costClass:"FREE_VERIFIED",
    networkPermission:"PUBLIC_READ",
    allowedDataClasses:["PUBLIC","INTERNAL_BUSINESS"],
    requiresSecrets:false,
    benchmarkScore:null,
    health:"UNKNOWN",
    notes:["Agent Skills spec compatible.","Downstream partner/tool integrations require separate admission."]
  },
  {
    id:"ALIREZA_CLAUDE_SKILLS",
    label:"Claude Skills & Plugins",
    source:"https://github.com/alirezarezvani/claude-skills",
    sourceVerified:true,
    license:"MIT",
    revisionPin:null,
    roles:["MARKET_RESEARCH","WEB","AUTOMATION","PRODUCT","ANALYTICS","COPY","AUD"],
    capabilities:["ENGINEERING","MARKETING","SECURITY","RESEARCH","C_LEVEL_ADVISORY"],
    runtime:"PYTHON_SANDBOX",
    costClass:"FREE_VERIFIED",
    networkPermission:"PUBLIC_READ",
    allowedDataClasses:["PUBLIC","INTERNAL_BUSINESS"],
    requiresSecrets:false,
    benchmarkScore:null,
    health:"UNKNOWN",
    notes:["Large library; never enable all skills wholesale.","Select individual skills and benchmark independently."]
  },
  {
    id:"ERIC_SIU_MARKETING_SKILLS",
    label:"AI Marketing Skills",
    source:"https://github.com/ericosiu/ai-marketing-skills",
    sourceVerified:true,
    license:"MIT",
    revisionPin:null,
    roles:["MARKET_RESEARCH","SALES","ANALYTICS","COPY","SOCIAL","DEMO"],
    capabilities:["GROWTH_EXPERIMENTS","SEO_OPS","CRO_AUDIT","CONTENT_OPS","COMPETITIVE_ANALYSIS","DECK_GENERATION"],
    runtime:"PYTHON_SANDBOX",
    costClass:"FREE_VERIFIED",
    networkPermission:"PUBLIC_READ",
    allowedDataClasses:["PUBLIC","INTERNAL_BUSINESS"],
    requiresSecrets:false,
    benchmarkScore:null,
    health:"UNKNOWN",
    notes:["Bundled skills may include scripts/dependencies; copy complete skill directory when admitted."]
  },
  {
    id:"AARON_MARKETING_SKILLS",
    label:"Aaron Marketing Skills",
    source:"https://github.com/aaron-he-zhu/aaron-marketing-skills",
    sourceVerified:true,
    license:"Apache-2.0",
    revisionPin:null,
    roles:["MARKET_RESEARCH","SALES","ANALYTICS","COPY","SOCIAL","AUD"],
    capabilities:["NARRATIVE","SEO_GEO","SOCIAL","EMAIL","PAID_ADS","INFLUENCER","LAUNCH","QUALITY_GATES"],
    runtime:"PYTHON_SANDBOX",
    costClass:"FREE_VERIFIED",
    networkPermission:"PUBLIC_READ",
    allowedDataClasses:["PUBLIC","INTERNAL_BUSINESS"],
    requiresSecrets:false,
    benchmarkScore:null,
    health:"UNKNOWN",
    notes:["Plain Markdown plus stdlib-oriented runtime patterns.","External connectors remain separately gated."]
  },
  {
    id:"ADDY_AGENT_SKILLS",
    label:"Addy Agent Skills",
    source:"https://github.com/addyosmani/agent-skills",
    sourceVerified:true,
    license:"MIT",
    revisionPin:null,
    roles:["WEB","PRODUCT","AUD","AUTOMATION","DEMO"],
    capabilities:["SPEC","PLAN","BUILD","TDD","CODE_REVIEW","WEB_PERFORMANCE","SHIP_GATES"],
    runtime:"PROMPT_SKILL",
    costClass:"FREE_VERIFIED",
    networkPermission:"NONE",
    allowedDataClasses:["PUBLIC","INTERNAL_BUSINESS"],
    requiresSecrets:false,
    benchmarkScore:null,
    health:"UNKNOWN",
    notes:["Good fit for Dev/AUD lifecycle gates.","Repository-level references may be required by some individual skills."]
  },
  {
    id:"EMIL_UI_SKILLS",
    label:"Skills for Designers and Engineers",
    source:"https://github.com/emilkowalski/skills",
    sourceVerified:true,
    license:"MIT",
    revisionPin:null,
    roles:["DESIGN","UX_AUDITOR","WEB","DEMO"],
    capabilities:["UI_TASTE","ANIMATION","MOBILE_NATIVE","UI_LIBRARY_SELECTION","PROTOTYPING"],
    runtime:"PROMPT_SKILL",
    costClass:"FREE_VERIFIED",
    networkPermission:"NONE",
    allowedDataClasses:["PUBLIC","INTERNAL_BUSINESS"],
    requiresSecrets:false,
    benchmarkScore:null,
    health:"UNKNOWN",
    notes:["Use for design critique and implementation quality; not as brand authority."]
  }
];

export interface SkillAdmission {
  state: SkillAdmissionState;
  reasons: string[];
}

export function evaluateSkillAdmission(candidate: SkillSourceCandidate): SkillAdmission {
  const rejected:string[]=[];
  const quarantined:string[]=[];

  if(!candidate.sourceVerified) rejected.push("SOURCE_UNVERIFIED");
  if(!candidate.license) rejected.push("LICENSE_UNVERIFIED");
  if(candidate.costClass === "PAID") rejected.push("PAID_SKILL_FORBIDDEN");
  if(candidate.networkPermission === "EXTERNAL_WRITE") rejected.push("DIRECT_EXTERNAL_WRITE_FORBIDDEN");
  if(candidate.allowedDataClasses.includes("SECRET")) rejected.push("SECRET_DATA_SKILL_FORBIDDEN");

  if(rejected.length>0) return {state:"REJECTED",reasons:rejected};

  if(candidate.costClass === "UNKNOWN") quarantined.push("COST_UNKNOWN");
  if(!candidate.revisionPin) quarantined.push("REVISION_PIN_REQUIRED");
  if(candidate.health !== "HEALTHY") quarantined.push("HEALTH_NOT_VERIFIED");
  if(candidate.benchmarkScore === null) quarantined.push("BENCHMARK_REQUIRED");
  else if(candidate.benchmarkScore < 0.6) quarantined.push("BENCHMARK_BELOW_THRESHOLD");
  if(candidate.requiresSecrets) quarantined.push("SECRET_BINDING_REVIEW_REQUIRED");

  return quarantined.length>0
    ? {state:"QUARANTINED",reasons:quarantined}
    : {state:"ENABLED",reasons:["SOURCE_LICENSE_COST_HEALTH_BENCHMARK_VERIFIED"]};
}

export function skillCanHandle(candidate: SkillSourceCandidate, role: SkillRole, dataClass: SkillDataClass): boolean {
  const admission=evaluateSkillAdmission(candidate);
  return admission.state==="ENABLED"
    && candidate.roles.includes(role)
    && candidate.allowedDataClasses.includes(dataClass);
}
