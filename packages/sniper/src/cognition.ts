import type { HumanGateDecision, LearningObservation, SniperRole, TacticStats } from "./engine.js";

export type OpportunityStage =
  | "DISCOVERED"
  | "QUALIFIED"
  | "DEMO_READY"
  | "CONTACTED"
  | "ENGAGED"
  | "NEGOTIATING"
  | "WON"
  | "DELIVERING"
  | "DELIVERED"
  | "LOST"
  | "DEFERRED";

export type DecisionMove =
  | "ENRICH_CONTACT"
  | "BUILD_DEMO"
  | "SEND_DIAGNOSTIC"
  | "FOLLOW_UP_WITH_VALUE"
  | "NEGOTIATE"
  | "SEND_PROPOSAL"
  | "DELIVER"
  | "COLLECT"
  | "ESCALATE_HUMAN"
  | "DEFER";

export interface CognitiveContext {
  opportunityId: string;
  stage: OpportunityStage;
  contactsAvailable: boolean;
  demoReady: boolean;
  replyState: "NONE" | "NO_REPLY" | "ENGAGED" | "POSITIVE" | "NEGATIVE";
  objection: string | null;
  attempts: number;
  daysSinceLastTouch: number;
  humanGate: HumanGateDecision;
  tacticStats: TacticStats[];
}

export interface RankedDecision {
  move: DecisionMove;
  score: number;
  reasons: string[];
  tacticId: string;
}

export interface CognitiveDecision extends RankedDecision {
  alternatives: RankedDecision[];
}

export interface MemoryEpisode {
  episodeId: string;
  opportunityId: string;
  agentRole: SniperRole;
  tacticId: string;
  observation: string;
  outcome: LearningObservation["outcome"];
  audited: boolean;
  evidenceRefs: string[];
  createdAt: string;
}

export interface MemoryPromotion {
  promoted: boolean;
  kind: "EPISODIC_ONLY" | "PROCEDURAL_CANDIDATE";
  reason: string;
  tacticId: string;
  outcome: LearningObservation["outcome"];
}

function learnedScore(stats: TacticStats[], tacticId: string): number {
  const row = stats.find(x => x.tacticId === tacticId);
  return row?.score ?? 0.35;
}

function fatiguePenalty(attempts: number): number {
  if (attempts <= 1) return 0;
  if (attempts === 2) return 0.08;
  if (attempts === 3) return 0.18;
  return 0.35;
}

export function rankDecisionCandidates(context: CognitiveContext): RankedDecision[] {
  const candidates: RankedDecision[] = [];
  const push = (move: DecisionMove, tacticId: string, fit: number, reasons: string[]): void => {
    const learned = learnedScore(context.tacticStats, tacticId);
    const fatigue = ["SEND_DIAGNOSTIC","FOLLOW_UP_WITH_VALUE","SEND_PROPOSAL"].includes(move) ? fatiguePenalty(context.attempts) : 0;
    const recencyBonus = move === "FOLLOW_UP_WITH_VALUE" && context.daysSinceLastTouch >= 3 ? 0.12 : 0;
    const score = Math.max(0, Math.min(1, fit * 0.62 + learned * 0.38 + recencyBonus - fatigue));
    candidates.push({ move, score, reasons, tacticId });
  };

  if (context.humanGate.required) {
    push("ESCALATE_HUMAN", "human-gate", 1, [...context.humanGate.reasons]);
  } else {
    if (!context.contactsAvailable) push("ENRICH_CONTACT", "public-contact-enrichment", 0.98, ["NO_CONTACT_PATH"]);
    if (!context.demoReady && ["QUALIFIED","DISCOVERED"].includes(context.stage)) {
      push("BUILD_DEMO", "demo-first", 0.97, ["PROOF_BEFORE_PITCH"]);
    }
    if (context.demoReady && ["QUALIFIED","DEMO_READY"].includes(context.stage)) {
      push("SEND_DIAGNOSTIC", "demo-first", 0.9, ["DIAGNOSIS_PLUS_DEMO_AVAILABLE"]);
    }
    if (context.stage === "CONTACTED" && context.replyState === "NO_REPLY") {
      push("FOLLOW_UP_WITH_VALUE", "value-followup", context.daysSinceLastTouch >= 3 ? 0.9 : 0.55, [
        context.daysSinceLastTouch >= 3 ? "FOLLOWUP_WINDOW_OPEN" : "TOO_SOON_FOR_HARD_FOLLOWUP"
      ]);
    }
    if (["ENGAGED","NEGOTIATING"].includes(context.stage) && context.replyState === "ENGAGED") {
      push("NEGOTIATE", "diagnostic-negotiation", 0.94, [context.objection ? "ACTIVE_OBJECTION" : "ACTIVE_BUYER_DIALOGUE"]);
      push("SEND_PROPOSAL", "proposal-after-dialogue", context.objection ? 0.64 : 0.88, [
        context.objection ? "RESOLVE_OBJECTION_FIRST" : "BUYER_SIGNAL_SUPPORTS_PROPOSAL"
      ]);
    }
    if (context.stage === "WON") push("DELIVER", "fast-fulfillment", 1, ["COMMERCIAL_WIN_RECORDED"]);
    if (context.stage === "DELIVERED") push("COLLECT", "completion-collection", 1, ["DELIVERY_ACCEPTANCE_READY"]);
  }

  if (candidates.length === 0) push("DEFER", "evidence-gap", 0.65, ["NO_HIGH_CONFIDENCE_NEXT_MOVE"]);
  return candidates.sort((a,b) => b.score - a.score || a.move.localeCompare(b.move));
}

export function chooseNextMove(context: CognitiveContext): CognitiveDecision {
  const ranked = rankDecisionCandidates(context);
  const first = ranked[0]!;
  return { ...first, alternatives: ranked.slice(1, 4) };
}

export function promoteEpisode(episode: MemoryEpisode): MemoryPromotion {
  if (!episode.audited) {
    return { promoted: false, kind: "EPISODIC_ONLY", reason: "AUDIT_REQUIRED", tacticId: episode.tacticId, outcome: episode.outcome };
  }
  if (episode.evidenceRefs.length === 0) {
    return { promoted: false, kind: "EPISODIC_ONLY", reason: "EVIDENCE_REQUIRED", tacticId: episode.tacticId, outcome: episode.outcome };
  }
  if (episode.outcome === "UNKNOWN") {
    return { promoted: false, kind: "EPISODIC_ONLY", reason: "OUTCOME_REQUIRED", tacticId: episode.tacticId, outcome: episode.outcome };
  }
  return { promoted: true, kind: "PROCEDURAL_CANDIDATE", reason: "AUDITED_OUTCOME_EVIDENCE", tacticId: episode.tacticId, outcome: episode.outcome };
}
