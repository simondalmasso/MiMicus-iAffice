import type { D1Like } from "../../memory/src/store.js";
import { sha256, stableId } from "../../core/src/hash.js";
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
import { buildCaseEvaluation } from "./case.js";
import { planGlobalFocus, rankPortfolioCases, type GlobalCaseSignal, type GlobalPolicy } from "./globalCore.js";
import { OBSERVABILITY_REFERENCES, buildTraceTree, normalizeTelemetrySpan, summarizeTelemetry, type TelemetrySpan, type TelemetrySpanInput } from "./telemetry.js";
import { buildAgencyOperationsSnapshot, OPERATING_STAGES } from "./operatingModel.js";
import { SKILL_SOURCE_CANDIDATES, evaluateSkillAdmission, type SkillHealth } from "./skillRegistry.js";
import { evaluateDiscoveryJob, findingToBusinessSignal, type DigitalAuditEvidence, type DiscoveryJobRequest, type RawBusinessFinding } from "./discovery.js";
import { DISCOVERY_SOURCE_CANDIDATES, evaluateDiscoverySourceAdmission, type DiscoverySourceHealth } from "./discoverySources.js";
import { buildDemoArtifactManifest, evaluateDemoJob, type DemoArtifactManifest, type DemoArtifactRef, type DemoJobRequest } from "./demoJobs.js";
import { EXECUTOR_CANDIDATES, evaluateExecutorAdmission, type ExecutorCandidate, type ExecutorHealth } from "./executorRegistry.js";
import { applySemanticObservation, smoothedOutcomeRate, type SemanticPatternState } from "./learning.js";
import { createExecutorEnvelope, executorRequestPath, verifySignedExecutorResult, type ExecutorJobKind, type SignedExecutorEnvelope, type SignedExecutorResult } from "./executorProtocol.js";

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

function demoJobKind(executorClass:string):ExecutorJobKind{
  if(executorClass==="WEB_BUILD")return "DEMO_WEB_BUILD";
  if(executorClass==="BROWSER_3D")return "DEMO_BROWSER_3D";
  if(executorClass==="HEAVY_3D")return "DEMO_HEAVY_3D";
  throw new Error("DEMO_EXECUTOR_CLASS_INVALID");
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


  async recordEpisode(episode: MemoryEpisode): Promise<{ promotion: ReturnType<typeof promoteEpisode>; tactic?: TacticStats; idempotent?: boolean }> {
    if (!episode.episodeId || !episode.opportunityId || !episode.agentRole || !episode.tacticId || !episode.observation || !episode.createdAt) throw new Error("SNIPER_EPISODE_SCHEMA_INVALID");

    const existing=await this.db.prepare(
      "SELECT opportunity_id,agent_role,tactic_id,observation,outcome,audited,evidence_refs_json,created_at FROM sniper_memory_episodes WHERE episode_id=?1"
    ).bind(episode.episodeId).first<Record<string,unknown>>();

    const normalizedEvidence=[...episode.evidenceRefs].sort();
    if(existing){
      const same=
        String(existing.opportunity_id)===episode.opportunityId &&
        String(existing.agent_role)===episode.agentRole &&
        String(existing.tactic_id)===episode.tacticId &&
        String(existing.observation)===episode.observation &&
        String(existing.outcome)===episode.outcome &&
        Number(existing.audited)===(episode.audited?1:0) &&
        JSON.stringify(parse<string[]>(existing.evidence_refs_json,[]).sort())===JSON.stringify(normalizedEvidence) &&
        String(existing.created_at)===episode.createdAt;
      if(!same)throw new Error("SNIPER_EPISODE_REPLAY_CONFLICT");
      return {promotion:promoteEpisode(episode),idempotent:true};
    }

    await this.db.prepare(
      "INSERT INTO sniper_memory_episodes (episode_id,opportunity_id,agent_role,tactic_id,observation,outcome,audited,evidence_refs_json,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)"
    ).bind(episode.episodeId,episode.opportunityId,episode.agentRole,episode.tacticId,episode.observation,episode.outcome,episode.audited?1:0,JSON.stringify(normalizedEvidence),episode.createdAt).run();

    const promotion=promoteEpisode(episode);
    let tactic:TacticStats|undefined;
    if(promotion.promoted){
      tactic=await this.learn(episode.tacticId,{outcome:episode.outcome,audited:true},episode.evidenceRefs,episode.createdAt);
      if(episode.outcome==="WON"||episode.outcome==="LOST"){
        const opportunity=await this.get(episode.opportunityId);
        if(opportunity){
          const statement="tactic:"+episode.tacticId+":commercial_outcome";
          const supports=episode.outcome==="WON";
          await this.recordSemanticObservation({scopeKey:"category:"+opportunity.category.toLowerCase(),statement,supports,audited:true,evidenceRefs:episode.evidenceRefs},episode.createdAt);
          await this.recordSemanticObservation({scopeKey:"category:"+opportunity.category.toLowerCase()+"|locality:"+opportunity.locality.toLowerCase(),statement,supports,audited:true,evidenceRefs:episode.evidenceRefs},episode.createdAt);
        }
      }
    }
    await this.activity(episode.opportunityId,"MEMORY",episode.agentRole,"EPISODE_RECORDED",{tacticId:episode.tacticId,outcome:episode.outcome,audited:episode.audited,promoted:promotion.promoted},episode.createdAt);
    return {promotion,...(tactic?{tactic}:{}),idempotent:false};
  }

  async decide(context: CognitiveContext, now = new Date().toISOString()): Promise<ReturnType<typeof chooseNextMove> & { decisionId:string }> {
    const decision=chooseNextMove(context);
    const decisionId=await stableId("sniper-decision",{context,move:decision.move,tacticId:decision.tacticId,now});
    await this.db.prepare(
      "INSERT OR IGNORE INTO sniper_decision_trace (decision_id,opportunity_id,context_json,selected_move,selected_tactic_id,selected_score,alternatives_json,reasons_json,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)"
    ).bind(decisionId,context.opportunityId,JSON.stringify(context),decision.move,decision.tacticId,decision.score,JSON.stringify(decision.alternatives),JSON.stringify(decision.reasons),now).run();
    await this.activity(context.opportunityId,"DECISION","ORCHESTRATOR","NEXT_MOVE_SELECTED",{decisionId,move:decision.move,tacticId:decision.tacticId,score:decision.score,reasons:decision.reasons},now);
    await this.recordTelemetrySpan({traceId:decisionId,spanId:decisionId,parentSpanId:null,caseId:context.opportunityId,agentRole:"ORCHESTRATOR",stage:"PROSPECT",kind:"DECISION",operation:"NEXT_MOVE_SELECTED",status:"OK",startedAt:now,endedAt:now,provider:null,model:null,inputTokens:0,outputTokens:0,actualCostUsd:0,errorCode:null,inputDigest:null,outputDigest:null,attributes:{move:decision.move,tacticId:decision.tacticId,score:decision.score,reasons:decision.reasons}} ,now);
    return {...decision,decisionId};
  }


  async recordSemanticObservation(input:{
    scopeKey:string;
    statement:string;
    supports:boolean;
    audited:boolean;
    evidenceRefs:string[];
  }, now=new Date().toISOString()):Promise<SemanticPatternState & {evidenceRefs:string[]}> {
    if(!input.scopeKey||!input.statement)throw new Error("SEMANTIC_PATTERN_SCHEMA_INVALID");
    if(input.evidenceRefs.length===0)throw new Error("SEMANTIC_EVIDENCE_REQUIRED");
    const patternId=await stableId("sniper-semantic-pattern",{scopeKey:input.scopeKey,statement:input.statement});
    const row=await this.db.prepare(
      "SELECT pattern_id,scope_key,statement,confidence,evidence_refs_json,support_count,contradiction_count,status FROM sniper_semantic_patterns WHERE pattern_id=?1"
    ).bind(patternId).first<Record<string,unknown>>();
    const base:SemanticPatternState=row?{
      patternId:String(row.pattern_id),
      scopeKey:String(row.scope_key),
      statement:String(row.statement),
      confidence:Number(row.confidence),
      supportCount:Number(row.support_count),
      contradictionCount:Number(row.contradiction_count),
      status:String(row.status) as SemanticPatternState["status"]
    }:{
      patternId,scopeKey:input.scopeKey,statement:input.statement,confidence:0.5,supportCount:0,contradictionCount:0,status:"CANDIDATE"
    };
    const next=applySemanticObservation(base,{supports:input.supports,audited:input.audited});
    const previousEvidence=row?parse<string[]>(row.evidence_refs_json,[]):[];
    const evidenceRefs=[...new Set([...previousEvidence,...input.evidenceRefs])];
    if(input.audited){
      await this.db.prepare(
        "INSERT INTO sniper_semantic_patterns (pattern_id,scope_key,statement,confidence,evidence_refs_json,support_count,contradiction_count,status,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9) ON CONFLICT(pattern_id) DO UPDATE SET confidence=excluded.confidence,evidence_refs_json=excluded.evidence_refs_json,support_count=excluded.support_count,contradiction_count=excluded.contradiction_count,status=excluded.status,updated_at=excluded.updated_at"
      ).bind(patternId,input.scopeKey,input.statement,next.confidence,JSON.stringify(evidenceRefs),next.supportCount,next.contradictionCount,next.status,now).run();
      await this.activity(null,"LEARNING","MEMORY","SEMANTIC_PATTERN_UPDATED",{patternId,scopeKey:input.scopeKey,statement:input.statement,supports:input.supports,confidence:next.confidence,status:next.status,evidenceRefs},now);
    }
    return {...next,evidenceRefs};
  }

  async contextualOutcomeRates():Promise<Map<string,{wins:number;losses:number;rate:number;support:number}>>{
    const rows=await this.db.prepare(
      "SELECT o.category,o.locality,e.outcome FROM sniper_memory_episodes e JOIN sniper_opportunities o ON o.id=e.opportunity_id WHERE e.audited=1 AND e.outcome IN ('WON','LOST')"
    ).all<Record<string,unknown>>();
    const counts=new Map<string,{wins:number;losses:number}>();
    const add=(key:string,outcome:string)=>{
      const row=counts.get(key)??{wins:0,losses:0};
      if(outcome==="WON")row.wins+=1;else row.losses+=1;
      counts.set(key,row);
    };
    for(const row of rows.results){
      const category=String(row.category).toLowerCase();
      const locality=String(row.locality).toLowerCase();
      const outcome=String(row.outcome);
      add("category:"+category,outcome);
      add("category:"+category+"|locality:"+locality,outcome);
    }
    const rates=new Map<string,{wins:number;losses:number;rate:number;support:number}>();
    for(const [key,count] of counts){
      rates.set(key,{...count,rate:smoothedOutcomeRate(count.wins,count.losses),support:count.wins+count.losses});
    }
    return rates;
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


  async caseView(id: string): Promise<ReturnType<typeof buildCaseEvaluation> | null> {
    const opportunity = await this.get(id);
    if (!opportunity) return null;
    const [negotiations, deliveries, payments, activity, episodes, decisions, demos, contactControl, commercialEffects] = await Promise.all([
      this.db.prepare("SELECT state,current_offer_ars,floor_price_ars,objections_json,concessions_json,next_action,human_gate,human_gate_reasons_json,last_contact_at,updated_at FROM sniper_negotiations WHERE opportunity_id=?1 ORDER BY updated_at DESC").bind(id).all<Record<string,unknown>>(),
      this.db.prepare("SELECT service_kind,state,acceptance_json,artifact_refs_json,due_at,updated_at FROM sniper_deliveries WHERE opportunity_id=?1 ORDER BY updated_at DESC").bind(id).all<Record<string,unknown>>(),
      this.db.prepare("SELECT state,amount_ars,provider,external_reference,created_at,updated_at FROM sniper_payments WHERE opportunity_id=?1 ORDER BY updated_at DESC").bind(id).all<Record<string,unknown>>(),
      this.db.prepare("SELECT stream,actor,event_type,detail_json,created_at FROM sniper_activity WHERE opportunity_id=?1 ORDER BY created_at DESC LIMIT 300").bind(id).all<Record<string,unknown>>(),
      this.db.prepare("SELECT episode_id,agent_role,tactic_id,observation,outcome,audited,evidence_refs_json,created_at FROM sniper_memory_episodes WHERE opportunity_id=?1 ORDER BY created_at DESC LIMIT 200").bind(id).all<Record<string,unknown>>(),
      this.db.prepare("SELECT decision_id,selected_move,selected_tactic_id,selected_score,alternatives_json,reasons_json,created_at FROM sniper_decision_trace WHERE opportunity_id=?1 ORDER BY created_at DESC LIMIT 200").bind(id).all<Record<string,unknown>>(),
      this.db.prepare("SELECT job_id,service_pack_id,executor_id,executor_class,state,requested_deliverables_json,artifact_manifest_json,audit_verdict,audit_evidence_refs_json,created_at,updated_at FROM sniper_demo_jobs WHERE case_id=?1 ORDER BY updated_at DESC LIMIT 100").bind(id).all<Record<string,unknown>>(),
      this.db.prepare("SELECT do_not_contact,explicit_refusal,reason,evidence_refs_json,updated_at FROM sniper_contact_controls WHERE case_id=?1").bind(id).first<Record<string,unknown>>(),
      this.db.prepare("SELECT operation,target,state,created_at FROM sniper_commercial_effects WHERE case_id=?1 ORDER BY created_at DESC LIMIT 100").bind(id).all<Record<string,unknown>>()
    ]);
    return buildCaseEvaluation({
      opportunity: {
        id: opportunity.id,
        businessId: opportunity.businessId,
        businessName: opportunity.businessName,
        category: opportunity.category,
        locality: opportunity.locality,
        status: opportunity.status,
        score: opportunity.score,
        reasons: opportunity.reasons,
        offer: opportunity.offer,
        persuasion: opportunity.persuasion,
        contacts: opportunity.contacts as unknown as Array<Record<string,unknown>>,
        evidenceRefs: opportunity.evidenceRefs,
        nextOwner: opportunity.nextOwner,
        nextAction: opportunity.nextAction,
        createdAt: opportunity.createdAt,
        updatedAt: opportunity.updatedAt
      },
      negotiations: negotiations.results.map(x=>({
        state:String(x.state),
        currentOfferArs:x.current_offer_ars===null||x.current_offer_ars===undefined?null:Number(x.current_offer_ars),
        floorPriceArs:x.floor_price_ars===null||x.floor_price_ars===undefined?null:Number(x.floor_price_ars),
        objections:parse<string[]>(x.objections_json,[]),
        concessions:parse<string[]>(x.concessions_json,[]),
        nextAction:String(x.next_action),
        humanGate:Number(x.human_gate)===1,
        humanGateReasons:parse<string[]>(x.human_gate_reasons_json,[]),
        lastContactAt:x.last_contact_at==null?null:String(x.last_contact_at),
        updatedAt:String(x.updated_at)
      })),
      deliveries: deliveries.results.map(x=>({
        serviceKind:String(x.service_kind),
        state:String(x.state),
        acceptance:parse(x.acceptance_json,{}),
        artifactRefs:parse<string[]>(x.artifact_refs_json,[]),
        dueAt:x.due_at==null?null:String(x.due_at),
        updatedAt:String(x.updated_at)
      })),
      payments: payments.results.map(x=>({
        state:String(x.state),
        amountArs:Number(x.amount_ars),
        provider:String(x.provider),
        externalReference:x.external_reference==null?null:String(x.external_reference),
        createdAt:String(x.created_at),
        updatedAt:String(x.updated_at)
      })),
      activity: activity.results.map(x=>({
        stream:String(x.stream),
        actor:String(x.actor),
        eventType:String(x.event_type),
        detail:parse<Record<string,unknown>>(x.detail_json,{}),
        createdAt:String(x.created_at)
      })),
      episodes: episodes.results.map(x=>({
        episodeId:String(x.episode_id),
        agentRole:String(x.agent_role),
        tacticId:String(x.tactic_id),
        observation:String(x.observation),
        outcome:String(x.outcome),
        audited:Number(x.audited)===1,
        evidenceRefs:parse<string[]>(x.evidence_refs_json,[]),
        createdAt:String(x.created_at)
      })),
      decisions: decisions.results.map(x=>({
        decisionId:String(x.decision_id),
        selectedMove:String(x.selected_move),
        selectedTacticId:String(x.selected_tactic_id),
        selectedScore:Number(x.selected_score),
        reasons:parse<string[]>(x.reasons_json,[]),
        alternatives:parse<unknown[]>(x.alternatives_json,[]),
        createdAt:String(x.created_at)
      })),
      demos: demos.results.map(x=>({
        jobId:String(x.job_id),
        servicePackId:String(x.service_pack_id),
        executorId:String(x.executor_id),
        executorClass:String(x.executor_class),
        state:String(x.state),
        requestedDeliverables:parse<string[]>(x.requested_deliverables_json,[]),
        artifactManifest:x.artifact_manifest_json?parse(x.artifact_manifest_json,{}):null,
        auditVerdict:x.audit_verdict==null?null:String(x.audit_verdict),
        auditEvidenceRefs:parse<string[]>(x.audit_evidence_refs_json,[]),
        createdAt:String(x.created_at),
        updatedAt:String(x.updated_at)
      })),
      commercialControl:{
        doNotContact:Number(contactControl?.do_not_contact??0)===1,
        explicitRefusal:Number(contactControl?.explicit_refusal??0)===1,
        reason:contactControl?.reason==null?null:String(contactControl.reason),
        evidenceRefs:contactControl?parse<string[]>(contactControl.evidence_refs_json,[]):[],
        updatedAt:contactControl?.updated_at==null?null:String(contactControl.updated_at),
        effects:commercialEffects.results.map(x=>({
          operation:String(x.operation),
          target:String(x.target),
          state:String(x.state),
          createdAt:String(x.created_at)
        }))
      }
    });
  }


  async globalSignals(now = new Date().toISOString()): Promise<GlobalCaseSignal[]> {
    const opportunities=await this.list(500);
    const outcomeRates=await this.contextualOutcomeRates();
    const negotiationRows=await this.db.prepare(
      "SELECT opportunity_id,human_gate,updated_at FROM sniper_negotiations ORDER BY updated_at DESC"
    ).all<Record<string,unknown>>();
    const latestGate=new Map<string,boolean>();
    for(const row of negotiationRows.results){
      const id=String(row.opportunity_id);
      if(!latestGate.has(id)) latestGate.set(id,Number(row.human_gate)===1);
    }
    const nowMs=Date.parse(now);
    return opportunities.map(o=>{
      const updated=Date.parse(o.updatedAt);
      const daysIdle=Number.isFinite(nowMs)&&Number.isFinite(updated)?Math.max(0,Math.floor((nowMs-updated)/86400000)):0;
      const demoReady=["DEMO_READY","CONTACTED","ENGAGED","NEGOTIATING","WON","DELIVERING","DELIVERED"].includes(o.status);
      const localKey="category:"+o.category.toLowerCase()+"|locality:"+o.locality.toLowerCase();
      const categoryKey="category:"+o.category.toLowerCase();
      const localRate=outcomeRates.get(localKey);
      const categoryRate=outcomeRates.get(categoryKey);
      const learnedRate=localRate&&localRate.support>=2?localRate.rate:(categoryRate?.rate??0.5);
      return {
        caseId:o.id,
        status:o.status,
        score:o.score,
        evidenceCount:o.evidenceRefs.length,
        contactable:o.contacts.length>0,
        demoReady,
        humanGate:latestGate.get(o.id)??false,
        daysIdle,
        strategicTags:[o.category,o.locality],
        auditedWinRate:learnedRate
      };
    });
  }

  async planGlobal(policy: GlobalPolicy, now = new Date().toISOString()) {
    if(!Number.isInteger(policy.maxConcurrentCases)||policy.maxConcurrentCases<1||policy.maxConcurrentCases>100) throw new Error("GLOBAL_POLICY_MAX_CONCURRENT_INVALID");
    if(!Number.isInteger(policy.minEvidenceCount)||policy.minEvidenceCount<0||policy.minEvidenceCount>1000) throw new Error("GLOBAL_POLICY_MIN_EVIDENCE_INVALID");
    if(!Array.isArray(policy.preferredTags)) throw new Error("GLOBAL_POLICY_TAGS_INVALID");
    const signals=await this.globalSignals(now);
    const ranked=rankPortfolioCases(signals,policy);
    const plan=planGlobalFocus(signals,policy);
    const portfolioHash=await stableId("sniper-global-portfolio",signals.map(x=>({caseId:x.caseId,status:x.status,score:x.score,evidenceCount:x.evidenceCount,humanGate:x.humanGate,daysIdle:x.daysIdle})));
    const decisionId=await stableId("sniper-global-decision",{portfolioHash,policy,active:plan.active.map(x=>x.caseId),human:plan.humanAttention.map(x=>x.caseId),now});
    const reasons=[
      `ACTIVE=${plan.active.length}`,
      `DEFERRED=${plan.deferred.length}`,
      `HUMAN_ATTENTION=${plan.humanAttention.length}`,
      `CAPACITY=${policy.maxConcurrentCases}`
    ];
    await this.db.prepare(
      "INSERT OR IGNORE INTO sniper_global_decisions (decision_id,portfolio_hash,policy_json,ranked_cases_json,active_cases_json,deferred_cases_json,human_attention_json,system1_json,reasons_json,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,NULL,?8,?9)"
    ).bind(decisionId,portfolioHash,JSON.stringify(policy),JSON.stringify(ranked),JSON.stringify(plan.active),JSON.stringify(plan.deferred),JSON.stringify(plan.humanAttention),JSON.stringify(reasons),now).run();
    for(const item of plan.active){
      const allocationId=await stableId("sniper-global-allocation",{decisionId,caseId:item.caseId,owner:item.ownerRole,objective:item.nextObjective});
      await this.db.prepare(
        "INSERT OR IGNORE INTO sniper_global_allocations (allocation_id,decision_id,case_id,owner_role,objective,priority_score,state,created_at,updated_at) VALUES (?1,?2,?3,?4,?5,?6,'ACTIVE',?7,?7)"
      ).bind(allocationId,decisionId,item.caseId,item.ownerRole,item.nextObjective,item.globalScore,now).run();
    }
    await this.activity(null,"GLOBAL","GLOBAL_CORE","PORTFOLIO_PLAN_UPDATED",{decisionId,portfolioHash,policy,reasons,active:plan.active.map(x=>({caseId:x.caseId,ownerRole:x.ownerRole,nextObjective:x.nextObjective,globalScore:x.globalScore})),humanAttention:plan.humanAttention.map(x=>x.caseId)},now);
    await this.recordTelemetrySpan({traceId:decisionId,spanId:decisionId,parentSpanId:null,caseId:null,agentRole:"GLOBAL_CORE",stage:"GLOBAL",kind:"DECISION",operation:"PORTFOLIO_PLAN",status:"OK",startedAt:now,endedAt:now,provider:null,model:null,inputTokens:0,outputTokens:0,actualCostUsd:0,errorCode:null,inputDigest:portfolioHash,outputDigest:null,attributes:{policy,reasons,activeCases:plan.active.map(x=>x.caseId),humanAttention:plan.humanAttention.map(x=>x.caseId)}} ,now);
    return {decisionId,portfolioHash,policy,ranked,...plan,reasons,system1:{provider:"LAYA_COMPATIBLE",state:"NOT_CONNECTED"}};
  }

  async latestGlobalPlan(): Promise<Record<string,unknown> | null> {
    const row=await this.db.prepare(
      "SELECT decision_id,portfolio_hash,policy_json,ranked_cases_json,active_cases_json,deferred_cases_json,human_attention_json,system1_json,reasons_json,created_at FROM sniper_global_decisions ORDER BY created_at DESC LIMIT 1"
    ).first<Record<string,unknown>>();
    if(!row)return null;
    return {
      decisionId:String(row.decision_id),
      portfolioHash:String(row.portfolio_hash),
      policy:parse(row.policy_json,{}),
      ranked:parse(row.ranked_cases_json,[]),
      active:parse(row.active_cases_json,[]),
      deferred:parse(row.deferred_cases_json,[]),
      humanAttention:parse(row.human_attention_json,[]),
      system1:row.system1_json?parse(row.system1_json,{}):{provider:"LAYA_COMPATIBLE",state:"NOT_CONNECTED"},
      reasons:parse(row.reasons_json,[]),
      createdAt:String(row.created_at)
    };
  }

  async globalOverview(now = new Date().toISOString()): Promise<Record<string,unknown>> {
    const signals=await this.globalSignals(now);
    const latest=await this.latestGlobalPlan();
    return {
      architecture:{
        system1:"typed calibrated decision service; Laya-compatible candidate",
        system2:"aria-models reasoning / specialist deliberation",
        authority:"deterministic policy + audited memory + human gate"
      },
      portfolio:{total:signals.length,signals},
      latest
    };
  }


  async recordTelemetrySpan(input: TelemetrySpanInput, createdAt = new Date().toISOString()): Promise<TelemetrySpan> {
    const span=normalizeTelemetrySpan(input);
    await this.db.prepare(
      "INSERT OR REPLACE INTO sniper_telemetry_spans (trace_id,span_id,parent_span_id,case_id,agent_role,stage,kind,operation,status,started_at,ended_at,latency_ms,provider,model,input_tokens,output_tokens,actual_cost_usd,error_code,input_digest,output_digest,attributes_json,content_policy,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20,?21,?22,?23)"
    ).bind(
      span.traceId,span.spanId,span.parentSpanId,span.caseId,span.agentRole,span.stage,span.kind,span.operation,span.status,
      span.startedAt,span.endedAt,span.latencyMs,span.provider,span.model,span.inputTokens,span.outputTokens,span.actualCostUsd,
      span.errorCode,span.inputDigest,span.outputDigest,JSON.stringify(span.attributes),span.contentPolicy,createdAt
    ).run();
    return span;
  }

  async telemetrySpans(limit = 500, caseId?: string): Promise<TelemetrySpan[]> {
    const safe=Math.max(1,Math.min(2000,Math.trunc(limit)));
    const result=caseId
      ? await this.db.prepare("SELECT * FROM sniper_telemetry_spans WHERE case_id=?1 ORDER BY started_at DESC LIMIT ?2").bind(caseId,safe).all<Record<string,unknown>>()
      : await this.db.prepare("SELECT * FROM sniper_telemetry_spans ORDER BY started_at DESC LIMIT ?1").bind(safe).all<Record<string,unknown>>();
    return result.results.map(row=>this.mapTelemetryRow(row));
  }

  async telemetryTrace(traceId: string): Promise<{traceId:string;spans:TelemetrySpan[];tree:ReturnType<typeof buildTraceTree>;summary:ReturnType<typeof summarizeTelemetry>}> {
    const result=await this.db.prepare("SELECT * FROM sniper_telemetry_spans WHERE trace_id=?1 ORDER BY started_at ASC").bind(traceId).all<Record<string,unknown>>();
    const spans=result.results.map(row=>this.mapTelemetryRow(row));
    return {traceId,spans,tree:buildTraceTree(spans),summary:summarizeTelemetry(spans)};
  }

  async telemetryOverview(limit = 500): Promise<Record<string,unknown>> {
    const spans=await this.telemetrySpans(limit);
    const traceIds=[...new Set(spans.map(x=>x.traceId))].slice(0,50);
    return {
      authority:"ARIA_TELEMETRY_FABRIC",
      standards:["OTEL_COMPATIBLE","OPENINFERENCE_COMPATIBLE"],
      contentPolicy:"METADATA_ONLY",
      summary:summarizeTelemetry(spans),
      recentSpans:spans.slice(0,100),
      recentTraceIds:traceIds,
      adapters:OBSERVABILITY_REFERENCES.map(x=>({id:x.id,source:x.source,license:x.license,adoption:x.adoption,standards:x.standards,notes:x.notes}))
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



  async skillRegistryOverview(): Promise<Record<string,unknown>> {
    const rows=await this.db.prepare(
      "SELECT source_id,revision_pin,benchmark_score,health,admission_state,admission_reasons_json,verified_at,updated_at FROM sniper_skill_registry ORDER BY source_id"
    ).all<Record<string,unknown>>();
    const persisted=new Map(rows.results.map(row=>[String(row.source_id),row]));
    const sources=SKILL_SOURCE_CANDIDATES.map(source=>{
      const row=persisted.get(source.id);
      const effective=row?{
        ...source,
        revisionPin:String(row.revision_pin),
        benchmarkScore:Number(row.benchmark_score),
        health:String(row.health) as SkillHealth
      }:source;
      const admission=evaluateSkillAdmission(effective);
      return {
        ...effective,
        admission,
        verifiedAt:row?String(row.verified_at):null,
        updatedAt:row?String(row.updated_at):null
      };
    });
    return {
      policy:{
        directExternalWrite:false,
        secretData:false,
        paidSkills:false,
        revisionPinRequired:true,
        benchmarkRequired:true,
        healthRequired:true
      },
      totals:{
        sources:sources.length,
        enabled:sources.filter(x=>x.admission.state==="ENABLED").length,
        quarantined:sources.filter(x=>x.admission.state==="QUARANTINED").length,
        rejected:sources.filter(x=>x.admission.state==="REJECTED").length
      },
      sources
    };
  }

  async verifySkillSource(input:{
    sourceId:string;
    revisionPin:string;
    benchmarkScore:number;
    health:SkillHealth;
    verifiedAt?:string;
  }, now=new Date().toISOString()):Promise<Record<string,unknown>> {
    const source=SKILL_SOURCE_CANDIDATES.find(x=>x.id===input.sourceId);
    if(!source) throw new Error("SKILL_SOURCE_NOT_FOUND");
    if(!input.revisionPin || input.revisionPin.length<7) throw new Error("SKILL_REVISION_PIN_INVALID");
    if(!Number.isFinite(input.benchmarkScore)||input.benchmarkScore<0||input.benchmarkScore>1) throw new Error("SKILL_BENCHMARK_INVALID");
    if(!["HEALTHY","UNKNOWN","DEGRADED"].includes(input.health)) throw new Error("SKILL_HEALTH_INVALID");
    const effective={...source,revisionPin:input.revisionPin,benchmarkScore:input.benchmarkScore,health:input.health};
    const admission=evaluateSkillAdmission(effective);
    const verifiedAt=input.verifiedAt??now;
    await this.db.prepare(
      "INSERT INTO sniper_skill_registry (source_id,revision_pin,benchmark_score,health,admission_state,admission_reasons_json,verified_at,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8) ON CONFLICT(source_id) DO UPDATE SET revision_pin=excluded.revision_pin,benchmark_score=excluded.benchmark_score,health=excluded.health,admission_state=excluded.admission_state,admission_reasons_json=excluded.admission_reasons_json,verified_at=excluded.verified_at,updated_at=excluded.updated_at"
    ).bind(source.id,input.revisionPin,input.benchmarkScore,input.health,admission.state,JSON.stringify(admission.reasons),verifiedAt,now).run();
    await this.activity(null,"SKILL","AUD","SKILL_SOURCE_VERIFIED",{sourceId:source.id,revisionPin:input.revisionPin,benchmarkScore:input.benchmarkScore,health:input.health,admission},now);
    return {...effective,admission,verifiedAt,updatedAt:now};
  }


  async discoverySourcesOverview(): Promise<Record<string,unknown>> {
    const rows=await this.db.prepare(
      "SELECT source_id,revision_pin,zero_cost_verified,target_terms_verified,automation_allowed,health,admission_state,admission_reasons_json,evidence_refs_json,verified_at,updated_at FROM sniper_discovery_sources ORDER BY source_id"
    ).all<Record<string,unknown>>();
    const persisted=new Map(rows.results.map(row=>[String(row.source_id),row]));
    const sources=DISCOVERY_SOURCE_CANDIDATES.map(source=>{
      const row=persisted.get(source.id);
      const effective=row?{
        ...source,
        revisionPin:String(row.revision_pin),
        zeroCostVerified:Number(row.zero_cost_verified)===1,
        targetTermsVerified:Number(row.target_terms_verified)===1,
        automationAllowed:Number(row.automation_allowed)===1,
        health:String(row.health) as DiscoverySourceHealth
      }:source;
      const admission=evaluateDiscoverySourceAdmission(effective);
      return {
        ...effective,
        admission,
        evidenceRefs:row?parse<string[]>(row.evidence_refs_json,[]):[],
        verifiedAt:row?String(row.verified_at):null,
        updatedAt:row?String(row.updated_at):null
      };
    });
    return {
      policy:{
        zeroCostRequired:true,
        targetTermsRequired:true,
        automationPermissionRequired:true,
        publicBusinessDataOnly:true,
        privatePersonalEnrichment:false
      },
      totals:{
        sources:sources.length,
        enabled:sources.filter(x=>x.admission.state==="ENABLED").length,
        quarantined:sources.filter(x=>x.admission.state==="QUARANTINED").length,
        rejected:sources.filter(x=>x.admission.state==="REJECTED").length
      },
      sources
    };
  }

  async verifyDiscoverySource(input:{
    sourceId:string;
    revisionPin:string;
    zeroCostVerified:boolean;
    targetTermsVerified:boolean;
    automationAllowed:boolean;
    health:DiscoverySourceHealth;
    evidenceRefs:string[];
    verifiedAt?:string;
  }, now=new Date().toISOString()):Promise<Record<string,unknown>> {
    const source=DISCOVERY_SOURCE_CANDIDATES.find(x=>x.id===input.sourceId);
    if(!source) throw new Error("DISCOVERY_SOURCE_NOT_FOUND");
    if(!input.revisionPin||input.revisionPin.length<7) throw new Error("DISCOVERY_REVISION_PIN_INVALID");
    if(!["HEALTHY","UNKNOWN","DEGRADED"].includes(input.health)) throw new Error("DISCOVERY_HEALTH_INVALID");
    if(input.evidenceRefs.length===0) throw new Error("DISCOVERY_EVIDENCE_REQUIRED");
    const effective={...source,revisionPin:input.revisionPin,zeroCostVerified:input.zeroCostVerified,targetTermsVerified:input.targetTermsVerified,automationAllowed:input.automationAllowed,health:input.health};
    const admission=evaluateDiscoverySourceAdmission(effective);
    const verifiedAt=input.verifiedAt??now;
    await this.db.prepare(
      "INSERT INTO sniper_discovery_sources (source_id,revision_pin,zero_cost_verified,target_terms_verified,automation_allowed,health,admission_state,admission_reasons_json,evidence_refs_json,verified_at,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11) ON CONFLICT(source_id) DO UPDATE SET revision_pin=excluded.revision_pin,zero_cost_verified=excluded.zero_cost_verified,target_terms_verified=excluded.target_terms_verified,automation_allowed=excluded.automation_allowed,health=excluded.health,admission_state=excluded.admission_state,admission_reasons_json=excluded.admission_reasons_json,evidence_refs_json=excluded.evidence_refs_json,verified_at=excluded.verified_at,updated_at=excluded.updated_at"
    ).bind(source.id,input.revisionPin,input.zeroCostVerified?1:0,input.targetTermsVerified?1:0,input.automationAllowed?1:0,input.health,admission.state,JSON.stringify(admission.reasons),JSON.stringify(input.evidenceRefs),verifiedAt,now).run();
    await this.activity(null,"DISCOVERY","AUD","DISCOVERY_SOURCE_VERIFIED",{sourceId:source.id,revisionPin:input.revisionPin,admission,evidenceRefs:input.evidenceRefs},now);
    return {...effective,admission,evidenceRefs:input.evidenceRefs,verifiedAt,updatedAt:now};
  }

  async createDiscoveryJob(input:{
    jobId:string;
    locality:string;
    categories:string[];
    maxCandidates:number;
    sourceIds:string[];
  }, now=new Date().toISOString()):Promise<Record<string,unknown>> {
    const overview=await this.discoverySourcesOverview() as {sources:Array<Record<string,unknown>>};
    const enabled=new Map(overview.sources.filter(x=>(x.admission as {state?:string}|undefined)?.state==="ENABLED").map(x=>[String(x.id),x]));
    const selected=input.sourceIds.map(id=>enabled.get(id)).filter((x):x is Record<string,unknown>=>Boolean(x));
    const request:DiscoveryJobRequest={
      jobId:input.jobId,
      locality:input.locality,
      categories:input.categories,
      maxCandidates:input.maxCandidates,
      sources:selected.map(x=>({
        id:String(x.id),
        freeVerified:Boolean(x.zeroCostVerified),
        termsVerified:Boolean(x.targetTermsVerified),
        automatedAccessAllowed:Boolean(x.automationAllowed),
        publicBusinessDataOnly:Boolean(x.publicBusinessDataOnly)
      })),
      createdAt:now
    };
    const missing=input.sourceIds.filter(id=>!enabled.has(id));
    const decision=evaluateDiscoveryJob(request);
    if(missing.length) decision.reasons.push("SOURCE_NOT_ENABLED:"+missing.join(","));
    decision.allowed=decision.allowed&&missing.length===0;
    const state=decision.allowed?"QUEUED":"BLOCKED";
    await this.db.prepare(
      "INSERT INTO sniper_discovery_jobs (job_id,locality,categories_json,max_candidates,source_ids_json,state,decision_reasons_json,created_at,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?8)"
    ).bind(input.jobId,input.locality,JSON.stringify(input.categories),input.maxCandidates,JSON.stringify(input.sourceIds),state,JSON.stringify(decision.reasons),now).run();
    await this.activity(null,"DISCOVERY","GLOBAL_CORE","DISCOVERY_JOB_CREATED",{jobId:input.jobId,locality:input.locality,categories:input.categories,sourceIds:input.sourceIds,state,reasons:decision.reasons},now);
    return {jobId:input.jobId,state,decision,locality:input.locality,categories:input.categories,maxCandidates:input.maxCandidates,sourceIds:input.sourceIds,createdAt:now};
  }

  async listDiscoveryJobs(limit=100):Promise<Array<Record<string,unknown>>> {
    const safe=Math.max(1,Math.min(500,Math.trunc(limit)));
    const rows=await this.db.prepare(
      "SELECT job_id,locality,categories_json,max_candidates,source_ids_json,state,decision_reasons_json,found_count,deduped_count,case_count,error_code,created_at,started_at,completed_at,updated_at FROM sniper_discovery_jobs ORDER BY updated_at DESC LIMIT ?1"
    ).bind(safe).all<Record<string,unknown>>();
    return rows.results.map(row=>({
      jobId:String(row.job_id),
      locality:String(row.locality),
      categories:parse(row.categories_json,[]),
      maxCandidates:Number(row.max_candidates),
      sourceIds:parse(row.source_ids_json,[]),
      state:String(row.state),
      decisionReasons:parse(row.decision_reasons_json,[]),
      foundCount:Number(row.found_count),
      dedupedCount:Number(row.deduped_count),
      caseCount:Number(row.case_count),
      errorCode:row.error_code==null?null:String(row.error_code),
      createdAt:String(row.created_at),
      startedAt:row.started_at==null?null:String(row.started_at),
      completedAt:row.completed_at==null?null:String(row.completed_at),
      updatedAt:String(row.updated_at)
    }));
  }

  async recordDiscoveryFinding(input:{
    jobId:string;
    findingId:string;
    finding:RawBusinessFinding;
    auditId:string;
    audit:DigitalAuditEvidence;
    rawEvidenceDigest?:string|null;
  }, now=new Date().toISOString()):Promise<{case:OpportunityRecord;findingId:string;auditId:string}> {
    const job=await this.db.prepare("SELECT state FROM sniper_discovery_jobs WHERE job_id=?1").bind(input.jobId).first<Record<string,unknown>>();
    if(!job) throw new Error("DISCOVERY_JOB_NOT_FOUND");
    if(!["QUEUED","RUNNING"].includes(String(job.state))) throw new Error("DISCOVERY_JOB_NOT_ACTIVE");
    const signal=findingToBusinessSignal(input.finding,input.audit);
    await this.db.prepare(
      "INSERT OR IGNORE INTO sniper_discovery_findings (finding_id,job_id,source_id,source_ref,business_key,business_name,category,locality,website_url,contacts_json,demand_json,raw_evidence_digest,observed_at,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14)"
    ).bind(input.findingId,input.jobId,input.finding.sourceId,input.finding.sourceRef,signal.businessId,input.finding.name,input.finding.category,input.finding.locality,input.finding.websiteUrl,JSON.stringify(input.finding.businessContacts),JSON.stringify({rating:input.finding.rating,reviewCount:input.finding.reviewCount}),input.rawEvidenceDigest??null,input.finding.observedAt,now).run();
    await this.db.prepare(
      "INSERT OR IGNORE INTO sniper_digital_audits (audit_id,job_id,finding_id,evidence_ref,audit_json,created_at) VALUES (?1,?2,?3,?4,?5,?6)"
    ).bind(input.auditId,input.jobId,input.findingId,input.audit.evidenceRef,JSON.stringify(input.audit),now).run();
    const record=await this.ingest(signal,now);
    await this.db.prepare(
      "UPDATE sniper_discovery_jobs SET found_count=found_count+1,deduped_count=(SELECT COUNT(DISTINCT business_key) FROM sniper_discovery_findings WHERE job_id=?1),case_count=(SELECT COUNT(DISTINCT business_key) FROM sniper_discovery_findings WHERE job_id=?1),state='RUNNING',started_at=COALESCE(started_at,?2),updated_at=?2 WHERE job_id=?1"
    ).bind(input.jobId,now).run();
    await this.activity(record.id,"DISCOVERY","SCOUT","DISCOVERY_FINDING_INGESTED",{jobId:input.jobId,findingId:input.findingId,auditId:input.auditId,sourceId:input.finding.sourceId},now);
    return {case:record,findingId:input.findingId,auditId:input.auditId};
  }



  async executorRegistryOverview(): Promise<Record<string,unknown>> {
    const rows=await this.db.prepare(
      "SELECT executor_id,endpoint,cost_class,zero_cost_verified,health,admission_state,admission_reasons_json,evidence_refs_json,last_health_at,verified_at,updated_at FROM sniper_executor_registry ORDER BY executor_id"
    ).all<Record<string,unknown>>();
    const persisted=new Map(rows.results.map(row=>[String(row.executor_id),row]));
    const executors=EXECUTOR_CANDIDATES.map(base=>{
      const row=persisted.get(base.id);
      const effective:ExecutorCandidate=row?{
        ...base,
        endpoint:row.endpoint==null?null:String(row.endpoint),
        costClass:String(row.cost_class) as ExecutorCandidate["costClass"],
        zeroCostVerified:Number(row.zero_cost_verified)===1,
        health:String(row.health) as ExecutorHealth
      }:base;
      const admission=evaluateExecutorAdmission(effective);
      return {
        ...effective,
        admission,
        evidenceRefs:row?parse<string[]>(row.evidence_refs_json,[]):[],
        lastHealthAt:row?.last_health_at==null?null:String(row.last_health_at),
        verifiedAt:row?String(row.verified_at):null,
        updatedAt:row?String(row.updated_at):null
      };
    });
    return {
      policy:{
        canonicalState:"D1_CLOUDFLARE_ONLY",
        jobExecutorMustBeEnabled:true,
        zeroCostRequired:true,
        healthRequired:true,
        arbitraryEndpointDenied:true
      },
      totals:{
        executors:executors.length,
        enabled:executors.filter(x=>x.admission.state==="ENABLED").length,
        quarantined:executors.filter(x=>x.admission.state==="QUARANTINED").length,
        rejected:executors.filter(x=>x.admission.state==="REJECTED").length
      },
      executors
    };
  }

  async verifyExecutor(input:{
    executorId:string;
    endpoint:string|null;
    costClass:ExecutorCandidate["costClass"];
    zeroCostVerified:boolean;
    health:ExecutorHealth;
    evidenceRefs:string[];
    lastHealthAt?:string|null;
    verifiedAt?:string;
  }, now=new Date().toISOString()):Promise<Record<string,unknown>> {
    const base=EXECUTOR_CANDIDATES.find(x=>x.id===input.executorId);
    if(!base) throw new Error("EXECUTOR_NOT_FOUND");
    if(input.evidenceRefs.length===0) throw new Error("EXECUTOR_EVIDENCE_REQUIRED");
    if(!["FREE_VERIFIED","FREE_USER_CONFIRMED","UNKNOWN","PAID"].includes(input.costClass)) throw new Error("EXECUTOR_COST_CLASS_INVALID");
    if(!["HEALTHY","UNKNOWN","DEGRADED"].includes(input.health)) throw new Error("EXECUTOR_HEALTH_INVALID");
    const effective:ExecutorCandidate={...base,endpoint:input.endpoint,costClass:input.costClass,zeroCostVerified:input.zeroCostVerified,health:input.health};
    const admission=evaluateExecutorAdmission(effective);
    const verifiedAt=input.verifiedAt??now;
    await this.db.prepare(
      "INSERT INTO sniper_executor_registry (executor_id,endpoint,cost_class,zero_cost_verified,health,admission_state,admission_reasons_json,evidence_refs_json,last_health_at,verified_at,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11) ON CONFLICT(executor_id) DO UPDATE SET endpoint=excluded.endpoint,cost_class=excluded.cost_class,zero_cost_verified=excluded.zero_cost_verified,health=excluded.health,admission_state=excluded.admission_state,admission_reasons_json=excluded.admission_reasons_json,evidence_refs_json=excluded.evidence_refs_json,last_health_at=excluded.last_health_at,verified_at=excluded.verified_at,updated_at=excluded.updated_at"
    ).bind(base.id,input.endpoint,input.costClass,input.zeroCostVerified?1:0,input.health,admission.state,JSON.stringify(admission.reasons),JSON.stringify(input.evidenceRefs),input.lastHealthAt??null,verifiedAt,now).run();
    await this.activity(null,"EXECUTOR","AUD","EXECUTOR_VERIFIED",{executorId:base.id,endpoint:input.endpoint,costClass:input.costClass,zeroCostVerified:input.zeroCostVerified,health:input.health,admission,evidenceRefs:input.evidenceRefs},now);
    return {...effective,admission,evidenceRefs:input.evidenceRefs,lastHealthAt:input.lastHealthAt??null,verifiedAt,updatedAt:now};
  }

  private async resolvedExecutor(executorId:string):Promise<ExecutorCandidate|null>{
    const base=EXECUTOR_CANDIDATES.find(x=>x.id===executorId);
    if(!base)return null;
    const row=await this.db.prepare(
      "SELECT endpoint,cost_class,zero_cost_verified,health FROM sniper_executor_registry WHERE executor_id=?1"
    ).bind(executorId).first<Record<string,unknown>>();
    if(!row)return base;
    return {
      ...base,
      endpoint:row.endpoint==null?null:String(row.endpoint),
      costClass:String(row.cost_class) as ExecutorCandidate["costClass"],
      zeroCostVerified:Number(row.zero_cost_verified)===1,
      health:String(row.health) as ExecutorHealth
    };
  }

  async createDemoJob(request:DemoJobRequest, now=new Date().toISOString()):Promise<Record<string,unknown>> {
    const opportunity=await this.get(request.caseId);
    if(!opportunity) throw new Error("DEMO_CASE_NOT_FOUND");
    const executor=await this.resolvedExecutor(request.executorId);
    const executorAdmission=evaluateExecutorAdmission(executor??undefined);
    const trustedRequest:DemoJobRequest={...request,executorCostVerifiedZero:Boolean(executor?.zeroCostVerified)};
    const decision=evaluateDemoJob(trustedRequest);
    if(!executor||executorAdmission.state!=="ENABLED")decision.reasons.push("EXECUTOR_NOT_ENABLED");
    else if(!executor.capabilities.includes(decision.executorClass))decision.reasons.push("EXECUTOR_CAPABILITY_MISMATCH");
    decision.allowed=decision.allowed&&executorAdmission.state==="ENABLED"&&Boolean(executor?.capabilities.includes(decision.executorClass));
    const state=decision.allowed?"QUEUED":"BLOCKED";
    await this.db.prepare(
      "INSERT INTO sniper_demo_jobs (job_id,case_id,service_pack_id,evidence_refs_json,requested_deliverables_json,executor_id,executor_class,zero_cost_verified,state,decision_reasons_json,created_at,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?11)"
    ).bind(request.jobId,request.caseId,request.servicePackId,JSON.stringify(request.evidenceRefs),JSON.stringify(request.requestedDeliverables),request.executorId,decision.executorClass,(executor?.zeroCostVerified?1:0),state,JSON.stringify(decision.reasons),now).run();
    await this.activity(request.caseId,"DEMO","DEMO","DEMO_JOB_CREATED",{jobId:request.jobId,servicePackId:request.servicePackId,executorId:request.executorId,executorClass:decision.executorClass,state,reasons:decision.reasons},now);
    return {...trustedRequest,executorClass:decision.executorClass,state,decision,executorAdmission};
  }


  async prepareDemoExecutorRun(jobId:string, signingSecret:string, now=new Date().toISOString()):Promise<{
    runId:string;
    endpoint:string;
    path:string;
    envelope:SignedExecutorEnvelope;
    reused:boolean;
  }> {
    const job=await this.db.prepare(
      "SELECT job_id,case_id,service_pack_id,evidence_refs_json,requested_deliverables_json,executor_id,executor_class,state FROM sniper_demo_jobs WHERE job_id=?1"
    ).bind(jobId).first<Record<string,unknown>>();
    if(!job)throw new Error("DEMO_JOB_NOT_FOUND");
    if(!["QUEUED","BUILDING"].includes(String(job.state)))throw new Error("DEMO_JOB_NOT_DISPATCHABLE");

    const executor=await this.resolvedExecutor(String(job.executor_id));
    const admission=evaluateExecutorAdmission(executor??undefined);
    if(!executor||admission.state!=="ENABLED"||!executor.endpoint)throw new Error("EXECUTOR_NOT_ENABLED");
    const jobKind=demoJobKind(String(job.executor_class));
    if(!executor.capabilities.includes(String(job.executor_class) as ExecutorCandidate["capabilities"][number]))throw new Error("EXECUTOR_CAPABILITY_MISMATCH");

    const previous=await this.db.prepare(
      "SELECT run_id,state,request_envelope_json,expires_at FROM sniper_executor_runs WHERE job_kind=?1 AND job_id=?2 ORDER BY created_at DESC LIMIT 1"
    ).bind(jobKind,jobId).first<Record<string,unknown>>();
    if(previous&&["DISPATCH_READY","DISPATCHED"].includes(String(previous.state))&&previous.request_envelope_json&&previous.expires_at&&Date.parse(String(previous.expires_at))>Date.parse(now)){
      const envelope=parse<SignedExecutorEnvelope>(previous.request_envelope_json,{} as SignedExecutorEnvelope);
      return {runId:String(previous.run_id),endpoint:executor.endpoint,path:executorRequestPath(jobKind),envelope,reused:true};
    }

    const count=await this.db.prepare(
      "SELECT COUNT(*) AS n FROM sniper_executor_runs WHERE job_kind=?1 AND job_id=?2"
    ).bind(jobKind,jobId).first<{n:number}>();
    const attempt=Number(count?.n??0)+1;
    const evidenceRefs=parse<string[]>(job.evidence_refs_json,[]);
    const requestedDeliverables=parse<string[]>(job.requested_deliverables_json,[]);
    const opportunity=await this.get(String(job.case_id));
    if(!opportunity)throw new Error("DEMO_CASE_NOT_FOUND");
    const payload={
      businessName:opportunity.businessName,
      category:opportunity.category,
      locality:opportunity.locality,
      servicePackId:String(job.service_pack_id),
      requestedDeliverables,
      evidenceRefs,
      observedFacts:[...opportunity.persuasion.observedFacts],
      demoBrief:opportunity.persuasion.demoBrief
    };
    const payloadDigest="sha256:"+await sha256(payload);
    const runId=await stableId("executor-run",{executorId:executor.id,jobKind,jobId,attempt});
    const nonce=await stableId("executor-nonce",{runId,payloadDigest,now});
    const expiresAt=new Date(Date.parse(now)+10*60*1000).toISOString();
    const envelope=await createExecutorEnvelope({
      runId,executorId:executor.id,jobKind,jobId,caseId:String(job.case_id),payload,
      artifactInputRefs:evidenceRefs,issuedAt:now,expiresAt,nonce
    },signingSecret);
    const requestDigest="sha256:"+await sha256(envelope.body);
    await this.db.prepare(
      "INSERT INTO sniper_executor_runs (run_id,executor_id,job_kind,job_id,case_id,state,request_digest,created_at,updated_at,nonce,request_envelope_json,expires_at) VALUES (?1,?2,?3,?4,?5,'DISPATCH_READY',?6,?7,?7,?8,?9,?10)"
    ).bind(runId,executor.id,jobKind,jobId,String(job.case_id),requestDigest,now,nonce,JSON.stringify(envelope),expiresAt).run();
    await this.db.prepare(
      "UPDATE sniper_demo_jobs SET state='BUILDING',started_at=COALESCE(started_at,?2),updated_at=?2 WHERE job_id=?1"
    ).bind(jobId,now).run();
    await this.activity(String(job.case_id),"EXECUTOR","DEMO","EXECUTOR_RUN_PREPARED",{runId,jobId,executorId:executor.id,jobKind,attempt,expiresAt},now);
    return {runId,endpoint:executor.endpoint,path:executorRequestPath(jobKind),envelope,reused:false};
  }

  async markExecutorDispatched(runId:string, now=new Date().toISOString()):Promise<void>{
    const row=await this.db.prepare("SELECT state,case_id,job_id,executor_id FROM sniper_executor_runs WHERE run_id=?1").bind(runId).first<Record<string,unknown>>();
    if(!row)throw new Error("EXECUTOR_RUN_NOT_FOUND");
    if(!["DISPATCH_READY","DISPATCHED"].includes(String(row.state)))throw new Error("EXECUTOR_RUN_STATE_INVALID");
    await this.db.prepare("UPDATE sniper_executor_runs SET state='DISPATCHED',started_at=COALESCE(started_at,?2),updated_at=?2 WHERE run_id=?1").bind(runId,now).run();
    await this.activity(row.case_id==null?null:String(row.case_id),"EXECUTOR","DEMO","EXECUTOR_RUN_DISPATCHED",{runId,jobId:String(row.job_id),executorId:String(row.executor_id)},now);
  }

  async completeExecutorRun(signed:SignedExecutorResult, signingSecret:string, now=new Date().toISOString()):Promise<Record<string,unknown>>{
    if(!(await verifySignedExecutorResult(signed,signingSecret)))throw new Error("EXECUTOR_RESULT_SIGNATURE_INVALID");
    const result=signed.result;
    const row=await this.db.prepare(
      "SELECT run_id,executor_id,job_kind,job_id,case_id,state,result_digest FROM sniper_executor_runs WHERE run_id=?1"
    ).bind(result.runId).first<Record<string,unknown>>();
    if(!row)throw new Error("EXECUTOR_RUN_NOT_FOUND");
    if(["SUCCEEDED","FAILED"].includes(String(row.state))){
      if(String(row.result_digest??"")===result.resultDigest){
        return {runId:result.runId,jobId:result.jobId,state:result.state,artifactCount:result.artifacts.length,costUsd:0,idempotent:true};
      }
      throw new Error("EXECUTOR_RESULT_FINAL_CONFLICT");
    }
    if(!["DISPATCH_READY","DISPATCHED"].includes(String(row.state)))throw new Error("EXECUTOR_RUN_STATE_INVALID");
    if(String(row.executor_id)!==result.executorId||String(row.job_kind)!==result.jobKind||String(row.job_id)!==result.jobId||(row.case_id==null?null:String(row.case_id))!==result.caseId)throw new Error("EXECUTOR_RESULT_IDENTITY_MISMATCH");

    if(result.state==="SUCCEEDED"){
      const demo=await this.db.prepare(
        "SELECT state,artifact_manifest_json FROM sniper_demo_jobs WHERE job_id=?1"
      ).bind(result.jobId).first<Record<string,unknown>>();
      if(!demo)throw new Error("DEMO_JOB_NOT_FOUND");
      const demoState=String(demo.state);
      if(["QUEUED","BUILDING"].includes(demoState)){
        await this.recordDemoArtifacts({jobId:result.jobId,artifacts:result.artifacts},now);
      }else if(["AUDIT_REQUIRED","READY"].includes(demoState)){
        const manifest=demo.artifact_manifest_json?parse<{artifacts?:DemoArtifactRef[]}>(demo.artifact_manifest_json,{}):{};
        const existingDigest=await sha256(manifest.artifacts??[]);
        const incomingDigest=await sha256(result.artifacts);
        if(existingDigest!==incomingDigest)throw new Error("EXECUTOR_ARTIFACT_REPLAY_CONFLICT");
      }else{
        throw new Error("DEMO_JOB_RESULT_STATE_INVALID");
      }
    }else{
      await this.db.prepare(
        "UPDATE sniper_demo_jobs SET state='FAILED',error_code=?2,completed_at=COALESCE(completed_at,?3),updated_at=?3 WHERE job_id=?1 AND state NOT IN ('READY','FAILED')"
      ).bind(result.jobId,result.errorCode??"EXECUTOR_FAILED",now).run();
    }

    await this.db.prepare(
      "UPDATE sniper_executor_runs SET state=?2,result_digest=?3,response_signature=?4,completed_at=?5,error_code=?6,updated_at=?5 WHERE run_id=?1"
    ).bind(result.runId,result.state,result.resultDigest,signed.signature,now,result.errorCode).run();

    await this.recordTelemetrySpan({
      traceId:result.runId,spanId:result.runId,parentSpanId:null,caseId:result.caseId,agentRole:"DEMO",stage:"EXECUTE",kind:"JOB",
      operation:result.jobKind,status:result.state==="SUCCEEDED"?"OK":"ERROR",startedAt:result.telemetry.startedAt,endedAt:result.telemetry.endedAt,
      provider:result.executorId,model:null,inputTokens:0,outputTokens:0,actualCostUsd:result.actualCostUsd,errorCode:result.errorCode,
      inputDigest:null,outputDigest:result.resultDigest,attributes:{cpuMs:result.telemetry.cpuMs,memoryPeakMb:result.telemetry.memoryPeakMb,artifactCount:result.artifacts.length}
    },now);
    await this.activity(result.caseId,"EXECUTOR","DEMO","EXECUTOR_RUN_COMPLETED",{runId:result.runId,jobId:result.jobId,state:result.state,resultDigest:result.resultDigest,errorCode:result.errorCode},now);
    return {runId:result.runId,jobId:result.jobId,state:result.state,artifactCount:result.artifacts.length,costUsd:0,idempotent:false};
  }


  async resolvePrivateArtifact(runId:string,name:string):Promise<{
    endpoint:string;
    path:string;
    kind:DemoArtifactRef["kind"];
    digest:string;
    ref:string;
  }|null>{
    if(!/^[A-Za-z0-9_.-]+$/.test(runId)||!/^[A-Za-z0-9_.-]+$/.test(name))throw new Error("ARTIFACT_PATH_INVALID");
    const run=await this.db.prepare(
      "SELECT executor_id,job_id,state FROM sniper_executor_runs WHERE run_id=?1"
    ).bind(runId).first<Record<string,unknown>>();
    if(!run||String(run.state)!=="SUCCEEDED")return null;
    const demo=await this.db.prepare(
      "SELECT artifact_manifest_json FROM sniper_demo_jobs WHERE job_id=?1"
    ).bind(String(run.job_id)).first<Record<string,unknown>>();
    if(!demo?.artifact_manifest_json)return null;
    const manifest=parse<DemoArtifactManifest|null>(demo.artifact_manifest_json,null);
    if(!manifest)return null;
    const expectedRef="executor://"+String(run.executor_id)+"/"+runId+"/"+name;
    const artifact=manifest.artifacts.find(x=>x.ref===expectedRef);
    if(!artifact)return null;
    const executor=await this.resolvedExecutor(String(run.executor_id));
    if(!executor||!executor.endpoint||evaluateExecutorAdmission(executor).state!=="ENABLED")return null;
    return {
      endpoint:executor.endpoint,
      path:"/v1/artifacts/"+encodeURIComponent(runId)+"/"+encodeURIComponent(name),
      kind:artifact.kind,
      digest:artifact.digest,
      ref:artifact.ref
    };
  }

  async recordDemoArtifacts(input:{jobId:string;artifacts:DemoArtifactRef[]}, now=new Date().toISOString()):Promise<Record<string,unknown>> {
    const row=await this.db.prepare("SELECT * FROM sniper_demo_jobs WHERE job_id=?1").bind(input.jobId).first<Record<string,unknown>>();
    if(!row) throw new Error("DEMO_JOB_NOT_FOUND");
    if(!["QUEUED","BUILDING"].includes(String(row.state))) throw new Error("DEMO_JOB_NOT_BUILDABLE");
    const request:DemoJobRequest={
      jobId:String(row.job_id),
      caseId:String(row.case_id),
      servicePackId:String(row.service_pack_id) as DemoJobRequest["servicePackId"],
      evidenceRefs:parse(row.evidence_refs_json,[]),
      requestedDeliverables:parse(row.requested_deliverables_json,[]),
      privatePreview:true,
      productionDeploy:false,
      executorId:String(row.executor_id),
      executorCostVerifiedZero:Number(row.zero_cost_verified)===1,
      createdAt:String(row.created_at)
    };
    const manifest=buildDemoArtifactManifest(request,input.artifacts);
    await this.db.prepare(
      "UPDATE sniper_demo_jobs SET state='AUDIT_REQUIRED',artifact_manifest_json=?2,started_at=COALESCE(started_at,?3),updated_at=?3 WHERE job_id=?1"
    ).bind(input.jobId,JSON.stringify(manifest),now).run();
    await this.activity(request.caseId,"DEMO","DEMO","DEMO_ARTIFACTS_READY",{jobId:input.jobId,artifactCount:input.artifacts.length,state:"AUDIT_REQUIRED"},now);
    return {jobId:input.jobId,state:"AUDIT_REQUIRED",manifest};
  }

  async auditDemo(input:{jobId:string;verdict:"PASS"|"FAIL"|"UNCERTAIN";evidenceRefs:string[]}, now=new Date().toISOString()):Promise<Record<string,unknown>> {
    if(input.evidenceRefs.length===0) throw new Error("DEMO_AUDIT_EVIDENCE_REQUIRED");
    const row=await this.db.prepare("SELECT case_id,state FROM sniper_demo_jobs WHERE job_id=?1").bind(input.jobId).first<Record<string,unknown>>();
    if(!row) throw new Error("DEMO_JOB_NOT_FOUND");
    if(String(row.state)!=="AUDIT_REQUIRED") throw new Error("DEMO_AUDIT_STATE_INVALID");
    const state=input.verdict==="PASS"?"READY":input.verdict==="FAIL"?"FAILED":"AUDIT_REQUIRED";
    await this.db.prepare(
      "UPDATE sniper_demo_jobs SET state=?2,audit_verdict=?3,audit_evidence_refs_json=?4,completed_at=CASE WHEN ?2 IN ('READY','FAILED') THEN ?5 ELSE completed_at END,updated_at=?5 WHERE job_id=?1"
    ).bind(input.jobId,state,input.verdict,JSON.stringify(input.evidenceRefs),now).run();
    const caseId=String(row.case_id);
    await this.activity(caseId,"DEMO","AUD","DEMO_AUDITED",{jobId:input.jobId,verdict:input.verdict,state,evidenceRefs:input.evidenceRefs},now);
    if(input.verdict==="PASS"){
      const opportunity=await this.get(caseId);
      if(opportunity&&["QUALIFIED","DISCOVERED"].includes(opportunity.status)){
        await this.setStatus(caseId,"DEMO_READY","SALES","PREPARE_EVIDENCE_BACKED_OUTREACH",now);
      }
    }
    return {jobId:input.jobId,caseId,verdict:input.verdict,state,evidenceRefs:input.evidenceRefs};
  }

  async listDemoJobs(limit=100):Promise<Array<Record<string,unknown>>> {
    const safe=Math.max(1,Math.min(500,Math.trunc(limit)));
    const rows=await this.db.prepare(
      "SELECT job_id,case_id,service_pack_id,evidence_refs_json,requested_deliverables_json,executor_id,executor_class,zero_cost_verified,state,decision_reasons_json,artifact_manifest_json,audit_verdict,audit_evidence_refs_json,error_code,created_at,started_at,completed_at,updated_at FROM sniper_demo_jobs ORDER BY updated_at DESC LIMIT ?1"
    ).bind(safe).all<Record<string,unknown>>();
    return rows.results.map(row=>({
      jobId:String(row.job_id),
      caseId:String(row.case_id),
      servicePackId:String(row.service_pack_id),
      evidenceRefs:parse(row.evidence_refs_json,[]),
      requestedDeliverables:parse(row.requested_deliverables_json,[]),
      executorId:String(row.executor_id),
      executorClass:String(row.executor_class),
      zeroCostVerified:Number(row.zero_cost_verified)===1,
      state:String(row.state),
      decisionReasons:parse(row.decision_reasons_json,[]),
      artifactManifest:row.artifact_manifest_json?parse(row.artifact_manifest_json,{}):null,
      auditVerdict:row.audit_verdict==null?null:String(row.audit_verdict),
      auditEvidenceRefs:parse(row.audit_evidence_refs_json,[]),
      errorCode:row.error_code==null?null:String(row.error_code),
      createdAt:String(row.created_at),
      startedAt:row.started_at==null?null:String(row.started_at),
      completedAt:row.completed_at==null?null:String(row.completed_at),
      updatedAt:String(row.updated_at)
    }));
  }

  async operationsOverview(): Promise<Record<string,unknown>> {
    const opportunities=await this.list(500);
    const cases=opportunities.map(o=>({
      caseId:o.id,
      businessName:o.businessName,
      status:o.status,
      owner:o.nextOwner,
      nextAction:o.nextAction,
      score:o.score
    }));
    return {
      stages:OPERATING_STAGES,
      workstreams:buildAgencyOperationsSnapshot(cases),
      totalCases:cases.length
    };
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


  private mapTelemetryRow(row: Record<string, unknown>): TelemetrySpan {
    return {
      traceId:String(row.trace_id),
      spanId:String(row.span_id),
      parentSpanId:row.parent_span_id==null?null:String(row.parent_span_id),
      caseId:row.case_id==null?null:String(row.case_id),
      agentRole:row.agent_role==null?null:String(row.agent_role),
      stage:row.stage==null?null:String(row.stage) as TelemetrySpan["stage"],
      kind:String(row.kind) as TelemetrySpan["kind"],
      operation:String(row.operation),
      status:String(row.status) as TelemetrySpan["status"],
      startedAt:String(row.started_at),
      endedAt:String(row.ended_at),
      latencyMs:Number(row.latency_ms),
      provider:row.provider==null?null:String(row.provider),
      model:row.model==null?null:String(row.model),
      inputTokens:Number(row.input_tokens),
      outputTokens:Number(row.output_tokens),
      actualCostUsd:Number(row.actual_cost_usd),
      errorCode:row.error_code==null?null:String(row.error_code),
      inputDigest:row.input_digest==null?null:String(row.input_digest),
      outputDigest:row.output_digest==null?null:String(row.output_digest),
      attributes:parse<Record<string,unknown>>(row.attributes_json,{}),
      contentPolicy:"METADATA_ONLY"
    };
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