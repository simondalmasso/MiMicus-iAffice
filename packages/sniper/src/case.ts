import type { OfferDecision, PersuasionCase } from "./engine.js";

export interface CaseOpportunity {
  id: string;
  businessId: string;
  businessName: string;
  category: string;
  locality: string;
  status: string;
  score: number;
  reasons: string[];
  offer: OfferDecision;
  persuasion: PersuasionCase;
  contacts: Array<Record<string, unknown>>;
  evidenceRefs: string[];
  nextOwner: string;
  nextAction: string;
  createdAt: string;
  updatedAt: string;
}

export interface CaseNegotiation {
  state: string;
  currentOfferArs?: number | null;
  floorPriceArs?: number | null;
  objections: string[];
  concessions: string[];
  nextAction: string;
  humanGate: boolean;
  humanGateReasons: string[];
  lastContactAt?: string | null;
  updatedAt: string;
}

export interface CaseDelivery {
  serviceKind: string;
  state: string;
  acceptance: unknown;
  artifactRefs: string[];
  dueAt?: string | null;
  updatedAt: string;
}

export interface CasePayment {
  state: string;
  amountArs: number;
  provider: string;
  externalReference?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CaseActivity {
  stream: string;
  actor: string;
  eventType: string;
  detail: Record<string, unknown>;
  createdAt: string;
}

export interface CaseEpisode {
  episodeId: string;
  agentRole: string;
  tacticId: string;
  observation: string;
  outcome: string;
  audited: boolean;
  evidenceRefs: string[];
  createdAt: string;
}

export interface CaseDecision {
  decisionId: string;
  selectedMove: string;
  selectedTacticId: string;
  selectedScore: number;
  reasons: string[];
  alternatives: unknown[];
  createdAt: string;
}

export interface CaseDemo {
  jobId: string;
  servicePackId: string;
  executorId: string;
  executorClass: string;
  state: string;
  requestedDeliverables: string[];
  artifactManifest: unknown;
  auditVerdict: string | null;
  auditEvidenceRefs: string[];
  createdAt: string;
  updatedAt: string;
}

export interface CaseCommercialEffect {
  operation: string;
  target: string;
  state: string;
  createdAt: string;
}

export interface CaseCommercialControl {
  doNotContact: boolean;
  explicitRefusal: boolean;
  reason: string | null;
  evidenceRefs: string[];
  updatedAt: string | null;
  effects: CaseCommercialEffect[];
}

export interface CaseEvaluationInput {
  opportunity: CaseOpportunity;
  negotiations: CaseNegotiation[];
  deliveries: CaseDelivery[];
  payments: CasePayment[];
  activity: CaseActivity[];
  episodes: CaseEpisode[];
  decisions: CaseDecision[];
  demos?: CaseDemo[];
  commercialControl?: CaseCommercialControl;
}

export function buildCaseEvaluation(input: CaseEvaluationInput) {
  const o = input.opportunity;
  return {
    caseId: o.id,
    business: {
      businessId: o.businessId,
      name: o.businessName,
      category: o.category,
      locality: o.locality,
      contacts: o.contacts
    },
    state: {
      status: o.status,
      nextOwner: o.nextOwner,
      nextAction: o.nextAction,
      createdAt: o.createdAt,
      updatedAt: o.updatedAt
    },
    evaluation: {
      score: o.score,
      reasons: [...o.reasons]
    },
    evidence: {
      refs: [...o.evidenceRefs],
      observedFacts: [...o.persuasion.observedFacts],
      quantifiedScenario: o.persuasion.quantifiedClaim
    },
    recommendation: {
      primary: [...o.offer.primary],
      secondary: [...o.offer.secondary],
      why: [...o.offer.why],
      demoBrief: o.persuasion.demoBrief,
      isInference: true
    },
    demos: (input.demos ?? []).map(x => structuredClone(x)),
    commercial: {
      controls: structuredClone(input.commercialControl ?? {
        doNotContact:false, explicitRefusal:false, reason:null, evidenceRefs:[], updatedAt:null, effects:[]
      }),
      negotiations: input.negotiations.map(x => structuredClone(x)),
      deliveries: input.deliveries.map(x => structuredClone(x)),
      payments: input.payments.map(x => structuredClone(x))
    },
    cognition: {
      decisions: input.decisions.map(x => structuredClone(x))
    },
    memory: {
      episodes: input.episodes.map(x => structuredClone(x))
    },
    timeline: input.activity.map(x => structuredClone(x))
  };
}