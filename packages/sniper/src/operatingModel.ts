export type OperatingStageId = "ANALYZE" | "PROSPECT" | "EXECUTE" | "DELIVER" | "COLLECT";

export interface OperatingStage {
  id: OperatingStageId;
  label: string;
  purpose: string;
  canonicalRoles: string[];
  examples: string[];
  externalEffectBoundary: string[];
}

export const OPERATING_STAGES: OperatingStage[] = [
  {
    id: "ANALYZE",
    label: "Analizan",
    purpose: "Turn public market signals into evidence-backed cases and opportunities.",
    canonicalRoles: ["SCOUT","MARKET_RESEARCH","QUALIFIER","UX_AUDITOR","ANALYTICS"],
    examples: ["market scan","website audit","SEO/local presence audit","competitive benchmark","gap diagnosis"],
    externalEffectBoundary: []
  },
  {
    id: "PROSPECT",
    label: "Prospectan",
    purpose: "Select the right offer, build proof, start or advance commercial conversations.",
    canonicalRoles: ["SALES","NEGOTIATOR","COPY","DEMO","CRM"],
    examples: ["contact enrichment","demo-first outreach","objection handling","proposal","follow-up"],
    externalEffectBoundary: ["SEND_OUTREACH","SCHEDULE_EXTERNAL_MEETING","SEND_PROPOSAL"]
  },
  {
    id: "EXECUTE",
    label: "Ejecutan",
    purpose: "Produce the contracted or approved digital artifact.",
    canonicalRoles: ["WEB","DESIGN","SOCIAL","CATALOG","AUTOMATION","PRODUCT","COPY"],
    examples: ["landing build","CRM workflow","creative production","catalog build","automation implementation"],
    externalEffectBoundary: ["PUBLISH_CONTENT","DEPLOY_CUSTOMER_WORK"]
  },
  {
    id: "DELIVER",
    label: "Entregan",
    purpose: "Verify quality, stage, obtain required approval and complete delivery.",
    canonicalRoles: ["DELIVERY","AUD","WEB","AUTOMATION","ANALYTICS"],
    examples: ["QA","staging","acceptance checks","handoff","production release"],
    externalEffectBoundary: ["DEPLOY_CUSTOMER_WORK","SEND_DELIVERY_NOTICE","TRANSFER_CREDENTIALS"]
  },
  {
    id: "COLLECT",
    label: "Cobran",
    purpose: "Create payment requests, reconcile payment state and invoice through authorized connectors.",
    canonicalRoles: ["PAYMENTS","DELIVERY","AUD"],
    examples: ["payment request","webhook reconciliation","invoice request","receipt delivery"],
    externalEffectBoundary: ["CREATE_PAYMENT_REQUEST","ISSUE_INVOICE","SEND_RECEIPT"]
  }
];

export type ExternalOperation =
  | "SEND_OUTREACH"
  | "SCHEDULE_EXTERNAL_MEETING"
  | "SEND_PROPOSAL"
  | "PUBLISH_CONTENT"
  | "DEPLOY_CUSTOMER_WORK"
  | "SEND_DELIVERY_NOTICE"
  | "TRANSFER_CREDENTIALS"
  | "CREATE_PAYMENT_REQUEST"
  | "ISSUE_INVOICE"
  | "SEND_RECEIPT";

export type EffectActionClass =
  | "DRAFT_EXTERNAL"
  | "SEND_EXTERNAL"
  | "PUBLISH_CONTENT"
  | "MONEY_MUTATION"
  | "DEPLOY"
  | "CREDENTIAL_MUTATION";

export function requiredEffectClass(operation: ExternalOperation): EffectActionClass {
  switch(operation){
    case "SEND_OUTREACH":
    case "SCHEDULE_EXTERNAL_MEETING":
    case "SEND_PROPOSAL":
    case "SEND_DELIVERY_NOTICE":
    case "SEND_RECEIPT":
      return "SEND_EXTERNAL";
    case "PUBLISH_CONTENT":
      return "PUBLISH_CONTENT";
    case "DEPLOY_CUSTOMER_WORK":
      return "DEPLOY";
    case "TRANSFER_CREDENTIALS":
      return "CREDENTIAL_MUTATION";
    case "CREATE_PAYMENT_REQUEST":
    case "ISSUE_INVOICE":
      return "MONEY_MUTATION";
  }
}

export interface OperatingCase {
  caseId: string;
  businessName: string;
  status: string;
  owner: string;
  nextAction: string;
  score: number;
}

export function mapCaseToOperatingStage(status: string): OperatingStageId {
  if (["DISCOVERED","QUALIFIED","DEFERRED"].includes(status)) return "ANALYZE";
  if (["DEMO_READY","CONTACTED","ENGAGED","NEGOTIATING"].includes(status)) return "PROSPECT";
  if (status === "WON") return "EXECUTE";
  if (status === "DELIVERING") return "DELIVER";
  if (status === "DELIVERED") return "COLLECT";
  if (status === "LOST") return "ANALYZE";
  return "ANALYZE";
}

export function buildAgencyOperationsSnapshot(cases: OperatingCase[]) {
  const snapshot: Record<OperatingStageId, OperatingCase[]> = {
    ANALYZE: [],
    PROSPECT: [],
    EXECUTE: [],
    DELIVER: [],
    COLLECT: []
  };
  for (const c of cases) snapshot[mapCaseToOperatingStage(c.status)].push({...c});
  for (const stage of OPERATING_STAGES) {
    snapshot[stage.id].sort((a,b)=>b.score-a.score || a.caseId.localeCompare(b.caseId));
  }
  return snapshot;
}
