import type { D1Like } from "../../memory/src/store.js";
import { stableId } from "../../core/src/hash.js";
import {
  applyLearningFeedback,
  buildDashboardSnapshot,
  buildPersuasionCase,
  chooseOffer,
  scoreOpportunity,
  type BusinessSignal,
  type LearningObservation,
  type TacticStats
} from "./engine.js";
import { chooseNextMove, promoteEpisode, type CognitiveContext, type MemoryEpisode } from "./cognition.js";

export type OpportunityStatus =
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

export interface OpportunityRecord {
  id: string;
  businessId: string;
  businessName: string;
  category: string;
  locality: string;
  status: OpportunityStatus;
  score: number;
  signal: BusinessSignal;
  reasons: string[];
  offer: ReturnType<typeof chooseOffer>;
  persuasion: ReturnType<typeof buildPersuasionCase>;
  contacts: BusinessSignal["contacts"];
  evidenceRefs: string[];
  nextOwner: string;
  nextAction: string;
  createdAt: string;
  updatedAt: string;
}

function parse<T>(value: unknown, fallback: T): T {
  if (typeof value !== "string") return fallback;
  try { return JSON.parse(value) as T; } catch { return fallback; }
}

export class SniperStore {
  constructor(private readonly db: D1Like) {}

  async ingest(signal: BusinessSignal, now = new Date().toISOString()): Promise<OpportunityRecord> {
    if (!signal.businessId || !signal.name || !signal.locality || signal.evidenceRefs.length === 0) throw new Error("SNIPER_SIGNAL_SCHEMA_INVALID");
    const scored = scoreOpportunity(signal);
    const offer = chooseOffer(signal);
    const persuasion = buildPersuasionCase(signal, offer);
    const id = await stableId("sniper-opportunity", { businessId: signal.businessId });
    const current = await this.get(id);
    const status: OpportunityStatus = scored.score >= 60 ? "QUALIFIED" : "DEFERRED";
    const record: OpportunityRecord = {
      id,
      businessId: signal.businessId,
      businessName: signal.name,
      category: signal.category,
      locality: signal.locality,
      status: current?.status === "DISCOVERED" || !current ? status : current.status,
      score: scored.score,
      signal: structuredClone(signal),
      reasons: scored.reasons,
      offer,
      persuasion,
      contacts: structuredClone(signal.contacts),
      evidenceRefs: [...signal.evidenceRefs],
      nextOwner: status === "QUALIFIED" ? "UX_AUDITOR" : "SCOUT",
      nextAction: status === "QUALIFIED" ? "BUILD_DIAGNOSTIC_AND_DEMO" : "GATHER_MORE_EVIDENCE",
      createdAt: current?.createdAt ?? now,
      updatedAt: now
    };
    await this.db.prepare(
      "INSERT INTO sniper_opportunities (id,business_id,business_name,category,locality,status,score,signal_json,reasons_json,offer_json,persuasion_json,contacts_json,evidence_refs_json,next_owner,next_action,created_at,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17) ON CONFLICT(id) DO UPDATE SET business_name=excluded.business_name,category=excluded.category,locality=excluded.locality,score=excluded.score,signal_json=excluded.signal_json,reasons_json=excluded.reasons_json,offer_json=excluded.offer_json,persuasion_json=excluded.persuasion_json,contacts_json=excluded.contacts_json,evidence_refs_json=excluded.evidence_refs_json,next_owner=excluded.next_owner,next_action=excluded.next_action,updated_at=excluded.updated_at"
    ).bind(
      record.id, record.businessId, record.businessName, record.category, record.locality, record.status, record.score,
      JSON.stringify(record.signal), JSON.stringify(record.reasons), JSON.stringify(record.offer), JSON.stringify(record.persuasion),
      JSON.stringify(record.contacts), JSON.stringify(record.evidenceRefs), record.nextOwner, record.nextAction, record.createdAt, record.updatedAt
    ).run();
    await this.activity(record.id, "PIPELINE", "QUALIFIER", "OPPORTUNITY_SCORED", { score: record.score, status: record.status, nextOwner: record.nextOwner }, now);
    return record;
  }

  async get(id: string): Promise<OpportunityRecord | null> {
    const row = await this.db.prepare("SELECT * FROM sniper_opportunities WHERE id=?1").bind(id).first<Record<string, unknown>>();
    return row ? this.mapOpportunity(row) : null;
  }

  async list(limit = 100): Promise<OpportunityRecord[]> {
    const safe = Math.max(1, Math.min(500, Math.trunc(limit)));
    const result = await this.db.prepare("SELECT * FROM sniper_opportunities ORDER BY score DESC, updated_at DESC LIMIT ?1").bind(safe).all<Record<string, unknown>>();
    return result.results.map(row => this.mapOpportunity(row));
  }

  async setStatus(id: string, status: OpportunityStatus, nextOwner: string, nextAction: string, now = new Date().toISOString()): Promise<void> {
    const existing = await this.get(id);
    if (!existing) throw new Error("SNIPER_OPPORTUNITY_NOT_FOUND");
    await this.db.prepare("UPDATE sniper_opportunities SET status=?2,next_owner=?3,next_action=?4,updated_at=?5 WHERE id=?1")
      .bind(id, status, nextOwner, nextAction, now).run();
    await this.activity(id, "PIPELINE", nextOwner, "STATUS_CHANGED", { from: existing.status, to: status, nextAction }, now);
  }

  async recordNegotiation(input: {
    id: string;
    opportunityId: string;
    state: string;
    currentOfferArs?: number;
    floorPriceArs?: number;
    objections?: string[];
    concessions?: string[];
    nextAction: string;
    humanGate: boolean;
    humanGateReasons: string[];
    lastContactAt?: string;
  }, now = new Date().toISOString()): Promise<void> {
    await this.db.prepare(
      "INSERT INTO sniper_negotiations (id,opportunity_id,state,current_offer_ars,floor_price_ars,objections_json,concessions_json,next_action,human_gate,human_gate_reasons_json,last_contact_at,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12) ON CONFLICT(id) DO UPDATE SET state=excluded.state,current_offer_ars=excluded.current_offer_ars,floor_price_ars=excluded.floor_price_ars,objections_json=excluded.objections_json,concessions_json=excluded.concessions_json,next_action=excluded.next_action,human_gate=excluded.human_gate,human_gate_reasons_json=excluded.human_gate_reasons_json,last_contact_at=excluded.last_contact_at,updated_at=excluded.updated_at"
    ).bind(
      input.id, input.opportunityId, input.state, input.currentOfferArs ?? null, input.floorPriceArs ?? null,
      JSON.stringify(input.objections ?? []), JSON.stringify(input.concessions ?? []), input.nextAction,
      input.humanGate ? 1 : 0, JSON.stringify(input.humanGateReasons), input.lastContactAt ?? null, now
    ).run();
    await this.activity(input.opportunityId, "NEGOTIATION", "NEGOTIATOR", "NEGOTIATION_UPDATED", { state: input.state, nextAction: input.nextAction, humanGate: input.humanGate }, now);
  }

  async recordPayment(input: { id: string; opportunityId: string; state: string; amountArs: number; provider: string; externalReference?: string }, now = new Date().toISOString()): Promise<void> {
    await this.db.prepare(
      "INSERT INTO sniper_payments (id,opportunity_id,state,amount_ars,provider,external_reference,created_at,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8) ON CONFLICT(id) DO UPDATE SET state=excluded.state,external_reference=excluded.external_reference,updated_at=excluded.updated_at"
    ).bind(input.id,input.opportunityId,input.state,input.amountArs,input.provider,input.externalReference ?? null,now,now).run();
    await this.activity(input.opportunityId, "PAYMENT", "PAYMENTS", "PAYMENT_UPDATED", { state: input.state, amountArs: input.amountArs, provider: input.provider }, now);
  }

  async learn(tacticId: string, observation: LearningObservation, evidenceRefs: string[], now = new Date().toISOString()): Promise<TacticStats> {
    const row = await this.db.prepare("SELECT * FROM sniper_tactic_learning WHERE tactic_id=?1").bind(tacticId).first<Record<string, unknown>>();
    const base: TacticStats = row ? {
      tacticId: String(row.tactic_id),
      attempts: Number(row.attempts),
      replies: Number(row.replies),
      meetings: Number(row.meetings),
      wins: Number(row.wins),
      losses: Number(row.losses),
      score: Number(row.score)
    } : { tacticId, attempts: 0, replies: 0, meetings: 0, wins: 0, losses: 0, score: 0 };
    const next = applyLearningFeedback(base, observation);
    if (next.attempts !== base.attempts) {
      await this.db.prepare(
        "INSERT INTO sniper_tactic_learning (tactic_id,attempts,replies,meetings,wins,losses,score,evidence_refs_json,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9) ON CONFLICT(tactic_id) DO UPDATE SET attempts=excluded.attempts,replies=excluded.replies,meetings=excluded.meetings,wins=excluded.wins,losses=excluded.losses,score=excluded.score,evidence_refs_json=excluded.evidence_refs_json,updated_at=excluded.updated_at"
      ).bind(tacticId,next.attempts,next.replies,next.meetings,next.wins,next.losses,next.score,JSON.stringify(evidenceRefs),now).run();
      await this.activity(null, "LEARNING", "MEMORY", "TACTIC_FEEDBACK_PROMOTED", { tacticId, outcome: observation.outcome, score: next.score, evidenceRefs }, now);
    }
    return next;
  }


  async recordEpisode(episode: MemoryEpisode): Promise<{ promotion: ReturnType<typeof promoteEpisode>; tactic?: TacticStats }> {
    if (!episode.episodeId || !episode.opportunityId || !episode.agentRole || !episode.tacticId || !episode.observation || !episode.createdAt) throw new Error("SNIPER_EPISODE_SCHEMA_INVALID");
    await this.db.prepare(
      "INSERT OR IGNORE INTO sniper_memory_episodes (episode_id,opportunity_id,agent_role,tactic_id,observation,outcome,audited,evidence_refs_json,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)"
    ).bind(episode.episodeId,episode.opportunityId,episode.agentRole,episode.tacticId,episode.observation,episode.outcome,episode.audited?1:0,JSON.stringify(episode.evidenceRefs),episode.createdAt).run();
    const promotion=promoteEpisode(episode);
    let tactic:TacticStats|undefined;
    if(promotion.promoted){
      tactic=await this.learn(episode.tacticId,{outcome:episode.outcome,audited:true},episode.evidenceRefs,episode.createdAt);
    }
    await this.activity(episode.opportunityId,"MEMORY",episode.agentRole,"EPISODE_RECORDED",{tacticId:episode.tacticId,outcome:episode.outcome,audited:episode.audited,promoted:promotion.promoted},episode.createdAt);
    return {promotion,...(tactic?{tactic}:{})};
  }

  async decide(context: CognitiveContext, now = new Date().toISOString()): Promise<ReturnType<typeof chooseNextMove> & { decisionId:string }> {
    const decision=chooseNextMove(context);
    const decisionId=await stableId("sniper-decision",{context,move:decision.move,tacticId:decision.tacticId,now});
    await this.db.prepare(
      "INSERT OR IGNORE INTO sniper_decision_trace (decision_id,opportunity_id,context_json,selected_move,selected_tactic_id,selected_score,alternatives_json,reasons_json,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)"
    ).bind(decisionId,context.opportunityId,JSON.stringify(context),decision.move,decision.tacticId,decision.score,JSON.stringify(decision.alternatives),JSON.stringify(decision.reasons),now).run();
    await this.activity(context.opportunityId,"DECISION","ORCHESTRATOR","NEXT_MOVE_SELECTED",{decisionId,move:decision.move,tacticId:decision.tacticId,score:decision.score,reasons:decision.reasons},now);
    return {...decision,decisionId};
  }

  async memorySummary(): Promise<Record<string,unknown>> {
    const [episodes,decisions,patterns,tactics]=await Promise.all([
      this.db.prepare("SELECT episode_id,opportunity_id,agent_role,tactic_id,observation,outcome,audited,evidence_refs_json,created_at FROM sniper_memory_episodes ORDER BY created_at DESC LIMIT 100").all<Record<string,unknown>>(),
      this.db.prepare("SELECT decision_id,opportunity_id,selected_move,selected_tactic_id,selected_score,reasons_json,created_at FROM sniper_decision_trace ORDER BY created_at DESC LIMIT 100").all<Record<string,unknown>>(),
      this.db.prepare("SELECT pattern_id,scope_key,statement,confidence,evidence_refs_json,support_count,contradiction_count,status,updated_at FROM sniper_semantic_patterns ORDER BY confidence DESC,updated_at DESC LIMIT 100").all<Record<string,unknown>>(),
      this.db.prepare("SELECT tactic_id,attempts,replies,meetings,wins,losses,score,evidence_refs_json,updated_at FROM sniper_tactic_learning ORDER BY score DESC,attempts DESC LIMIT 100").all<Record<string,unknown>>()
    ]);
    return {
      architecture:{working:"current opportunity dossier",episodic:"interaction/outcome episodes",semantic:"audited reusable patterns",procedural:"tactic and skill performance"},
      episodes:episodes.results.map(x=>({...x,evidenceRefs:parse(x.evidence_refs_json,[])})),
      decisions:decisions.results.map(x=>({...x,reasons:parse(x.reasons_json,[])})),
      patterns:patterns.results.map(x=>({...x,evidenceRefs:parse(x.evidence_refs_json,[])})),
      tactics:tactics.results.map(x=>({...x,evidenceRefs:parse(x.evidence_refs_json,[])}))
    };
  }

  async activity(opportunityId: string | null, stream: string, actor: string, eventType: string, detail: Record<string, unknown>, now = new Date().toISOString()): Promise<string> {
    const id = await stableId("sniper-activity", { opportunityId, stream, actor, eventType, detail, now });
    await this.db.prepare("INSERT OR IGNORE INTO sniper_activity (id,opportunity_id,stream,actor,event_type,detail_json,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7)")
      .bind(id, opportunityId, stream, actor, eventType, JSON.stringify(detail), now).run();
    return id;
  }

  async activityFeed(limit = 100): Promise<Array<Record<string, unknown>>> {
    const safe = Math.max(1, Math.min(500, Math.trunc(limit)));
    const result = await this.db.prepare("SELECT id,opportunity_id,stream,actor,event_type,detail_json,created_at FROM sniper_activity ORDER BY created_at DESC LIMIT ?1").bind(safe).all<Record<string, unknown>>();
    return result.results.map(row => ({ id: row.id, opportunityId: row.opportunity_id, stream: row.stream, actor: row.actor, eventType: row.event_type, detail: parse(row.detail_json, {}), createdAt: row.created_at }));
  }

  async dashboard(): Promise<ReturnType<typeof buildDashboardSnapshot> & { topOpportunities: OpportunityRecord[]; activity: Array<Record<string, unknown>>; memory: Record<string, unknown> }> {
    const opportunities = await this.list(50);
    const negotiations = await this.db.prepare("SELECT state,next_action FROM sniper_negotiations ORDER BY updated_at DESC LIMIT 50").all<{state:string;next_action:string}>();
    const deliveries = await this.db.prepare("SELECT state FROM sniper_deliveries ORDER BY updated_at DESC LIMIT 50").all<{state:string}>();
    const payments = await this.db.prepare("SELECT state,amount_ars FROM sniper_payments ORDER BY updated_at DESC LIMIT 50").all<{state:string;amount_ars:number}>();
    const learnings = await this.db.prepare("SELECT tactic_id,score FROM sniper_tactic_learning ORDER BY score DESC LIMIT 20").all<{tactic_id:string;score:number}>();
    const snapshot = buildDashboardSnapshot({
      opportunities: opportunities.map(x => ({ status: x.status })),
      negotiations: negotiations.results.map(x => ({ state: x.state, nextAction: x.next_action })),
      deliveries: deliveries.results,
      payments: payments.results.map(x => ({ state: x.state, amountArs: Number(x.amount_ars) })),
      learnings: learnings.results.map(x => ({ tacticId: x.tactic_id, score: Number(x.score) }))
    });
    return { ...snapshot, topOpportunities: opportunities.slice(0, 15), activity: await this.activityFeed(50), memory: await this.memorySummary() };
  }

  private mapOpportunity(row: Record<string, unknown>): OpportunityRecord {
    return {
      id: String(row.id),
      businessId: String(row.business_id),
      businessName: String(row.business_name),
      category: String(row.category),
      locality: String(row.locality),
      status: String(row.status) as OpportunityStatus,
      score: Number(row.score),
      signal: parse(row.signal_json, {} as BusinessSignal),
      reasons: parse<string[]>(row.reasons_json, []),
      offer: parse(row.offer_json, { primary: [], secondary: [], why: [] }),
      persuasion: parse(row.persuasion_json, { observedFacts: [], demoBrief: "", quantifiedClaim: null, rules: [] }),
      contacts: parse(row.contacts_json, []),
      evidenceRefs: parse<string[]>(row.evidence_refs_json, []),
      nextOwner: String(row.next_owner),
      nextAction: String(row.next_action),
      createdAt: String(row.created_at),
      updatedAt: String(row.updated_at)
    };
  }
}