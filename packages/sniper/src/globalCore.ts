export type GlobalRoute = "RESEARCH" | "DEMO" | "OUTREACH" | "NEGOTIATE" | "DELIVER" | "DEFER";

export interface GlobalCaseSignal {
  caseId: string;
  status: string;
  score: number;
  evidenceCount: number;
  contactable: boolean;
  demoReady: boolean;
  humanGate: boolean;
  daysIdle: number;
  strategicTags: string[];
  auditedWinRate: number;
}

export interface GlobalPolicy {
  preferredTags: string[];
  maxConcurrentCases: number;
  minEvidenceCount: number;
}

export interface GlobalRankedCase extends GlobalCaseSignal {
  globalScore: number;
  reasons: string[];
}

export interface GlobalFocusItem extends GlobalRankedCase {
  ownerRole: string;
  nextObjective: string;
}

export interface GlobalFocusPlan {
  active: GlobalFocusItem[];
  deferred: GlobalRankedCase[];
  humanAttention: GlobalRankedCase[];
}

export interface TypedQuestionChoice {
  type: "choice";
  instructions: string;
  criteria: Record<string,string>;
}
export interface TypedQuestionScore {
  type: "score";
  instructions: string;
  criteria: string[];
}
export interface TypedQuestionNoul {
  type: "noul";
  instructions: string;
}
export interface GlobalTypedQuestions {
  route: TypedQuestionChoice;
  priority: TypedQuestionScore;
  human_attention: TypedQuestionNoul;
}

function clamp01(value:number):number{return Math.max(0,Math.min(1,value));}

export function rankPortfolioCases(cases: GlobalCaseSignal[], policy: GlobalPolicy): GlobalRankedCase[] {
  const preferred = new Set(policy.preferredTags.map(x=>x.toLowerCase()));
  return cases.map(c=>{
    const reasons:string[]=[];
    let score = Math.max(0,Math.min(100,c.score)) * 0.55;
    score += clamp01(c.auditedWinRate) * 25;
    score += Math.min(5, Math.max(0,c.evidenceCount)) ;
    if(c.contactable){score += 4;reasons.push("CONTACT_PATH_AVAILABLE");}
    if(c.demoReady){score += 4;reasons.push("DEMO_READY");}
    if(c.status==="NEGOTIATING"){score += 8;reasons.push("ACTIVE_NEGOTIATION");}
    if(c.status==="WON"){score += 6;reasons.push("WON_REQUIRES_FULFILLMENT");}
    if(c.status==="DELIVERING"){score += 5;reasons.push("ACTIVE_DELIVERY");}
    if(c.daysIdle>=5){score += 3;reasons.push("STALE_CASE_REQUIRES_DECISION");}
    if(c.strategicTags.some(t=>preferred.has(t.toLowerCase()))){score += 10;reasons.push("STRATEGIC_TAG_MATCH");}
    if(c.evidenceCount<policy.minEvidenceCount){score -= 35;reasons.push("INSUFFICIENT_EVIDENCE");}
    if(!c.contactable && ["QUALIFIED","DEMO_READY","CONTACTED"].includes(c.status)){score -= 10;reasons.push("NO_CONTACT_PATH");}
    if(c.status==="DEFERRED"){score -= 22;reasons.push("CURRENTLY_DEFERRED");}
    if(c.status==="LOST"){score -= 40;reasons.push("CASE_LOST");}
    if(c.humanGate){score -= 100;reasons.push("HUMAN_GATE_REQUIRED");}
    return {...c,globalScore:Math.max(0,Math.min(100,score)),reasons};
  }).sort((a,b)=>b.globalScore-a.globalScore || a.caseId.localeCompare(b.caseId));
}

function ownership(c:GlobalRankedCase):Pick<GlobalFocusItem,"ownerRole"|"nextObjective">{
  if(c.status==="WON" || c.status==="DELIVERING") return {ownerRole:"DELIVERY",nextObjective:"FULFILL_COMMITMENT"};
  if(c.status==="DELIVERED") return {ownerRole:"PAYMENTS",nextObjective:"COLLECT_AND_CLOSE"};
  if(c.status==="NEGOTIATING") return {ownerRole:"NEGOTIATOR",nextObjective:"ADVANCE_NEGOTIATION"};
  if(!c.demoReady) return {ownerRole:"DEMO",nextObjective:"BUILD_PROOF"};
  if(!c.contactable) return {ownerRole:"SCOUT",nextObjective:"ENRICH_PUBLIC_CONTACT"};
  return {ownerRole:"SALES",nextObjective:"START_OR_ADVANCE_OUTREACH"};
}

export function planGlobalFocus(cases: GlobalCaseSignal[], policy: GlobalPolicy): GlobalFocusPlan {
  const ranked=rankPortfolioCases(cases,policy);
  const humanAttention=ranked.filter(x=>x.humanGate);
  const eligible=ranked.filter(x=>!x.humanGate && x.evidenceCount>=policy.minEvidenceCount && !["LOST","DEFERRED"].includes(x.status));
  const active=eligible.slice(0,Math.max(0,policy.maxConcurrentCases)).map(x=>({...x,...ownership(x)}));
  const activeIds=new Set(active.map(x=>x.caseId));
  const humanIds=new Set(humanAttention.map(x=>x.caseId));
  const deferred=ranked.filter(x=>!activeIds.has(x.caseId)&&!humanIds.has(x.caseId));
  return {active,deferred,humanAttention};
}

export function buildGlobalTypedQuestions(caseSignal: GlobalCaseSignal): GlobalTypedQuestions {
  return {
    route:{
      type:"choice",
      instructions:`Choose the best next portfolio route for case ${caseSignal.caseId}, based only on supplied state and policy.`,
      criteria:{
        RESEARCH:"more evidence is required before commercial action",
        DEMO:"build concrete proof before contact",
        OUTREACH:"evidence and proof are sufficient to initiate or continue contact",
        NEGOTIATE:"the buyer is actively engaged and commercial terms should advance",
        DELIVER:"the commercial commitment is won and fulfillment should take priority",
        DEFER:"do not allocate scarce active capacity now"
      }
    },
    priority:{
      type:"score",
      instructions:"How much scarce company attention should this case receive now?",
      criteria:["very low","low","medium","high","critical"]
    },
    human_attention:{
      type:"noul",
      instructions:"Does this case require human attention instead of autonomous execution?"
    }
  };
}

export interface SystemOneGlobalResult {
  answers?: {
    route?: {choice?:string;probabilities?:Record<string,number>;answer_confidence?:number};
    priority?: {score?:number;answer_confidence?:number};
    human_attention?: {noul?:number;answer_confidence?:number};
  };
}

export function interpretGlobalSystemOne(result:SystemOneGlobalResult,minConfidence=0.6){
  const reasons:string[]=[];
  const routeAnswer=result.answers?.route;
  const confidence=Number(routeAnswer?.answer_confidence ?? 0);
  let route:GlobalRoute|null=null;
  const candidate=routeAnswer?.choice;
  if(confidence>=minConfidence && candidate && ["RESEARCH","DEMO","OUTREACH","NEGOTIATE","DELIVER","DEFER"].includes(candidate)){
    route=candidate as GlobalRoute;
  }else{
    reasons.push("LOW_CONFIDENCE_ROUTE");
  }
  const priorityConfidence=Number(result.answers?.priority?.answer_confidence ?? 0);
  const humanConfidence=Number(result.answers?.human_attention?.answer_confidence ?? 0);
  if(priorityConfidence<minConfidence) reasons.push("LOW_CONFIDENCE_PRIORITY");
  if(humanConfidence<minConfidence) reasons.push("LOW_CONFIDENCE_HUMAN_ATTENTION");
  return {
    route,
    priorityScore:priorityConfidence>=minConfidence ? Number(result.answers?.priority?.score ?? 0) : null,
    humanAttentionProbability:humanConfidence>=minConfidence ? Number(result.answers?.human_attention?.noul ?? 0) : null,
    routeConfidence:confidence,
    abstained:route===null,
    reasons
  };
}
