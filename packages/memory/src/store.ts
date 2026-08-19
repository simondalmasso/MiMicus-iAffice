import type { ActionIntent, LedgerRecord, SystemState } from "../../core/src/types.js";
import { sha256 } from "../../core/src/hash.js";

export interface StateStore {
  load(): Promise<SystemState>;
  save(state: SystemState): Promise<void>;
  reset(): Promise<void>;
  loadLedger?(): Promise<LedgerRecord[]>;
  saveLedger?(records: LedgerRecord[]): Promise<void>;
  commitStateAndIntent?(state: SystemState, intent: ActionIntent): Promise<void>;
}

export function emptyState(): SystemState {
  return {
    events: [], leads: [], metrics: [], claims: [], knowledge: [], tasks: [], decisions: [], approvals: [], actions: [],
    modelCalls: [], auditFindings: [], actionIntents: [], effectReceipts: [], outbound: []
  };
}

export class InMemoryStateStore implements StateStore {
  private state: SystemState = emptyState();
  private ledger: LedgerRecord[] = [];
  async load(): Promise<SystemState> { return structuredClone(this.state); }
  async save(state: SystemState): Promise<void> { this.state = structuredClone(state); }
  async reset(): Promise<void> { this.state = emptyState(); this.ledger = []; }
  async loadLedger(): Promise<LedgerRecord[]> { return structuredClone(this.ledger); }
  async saveLedger(records: LedgerRecord[]): Promise<void> { this.ledger = structuredClone(records); }
}

export interface D1Prepared {
  bind(...values: unknown[]): D1Prepared;
  first<T = unknown>(): Promise<T | null>;
  all<T = unknown>(): Promise<{ results: T[] }>;
  run(): Promise<unknown>;
}
export interface D1Like { prepare(sql: string): D1Prepared; batch(statements: D1Prepared[]): Promise<unknown[]>; }
function val(value: unknown): string { return JSON.stringify(value); }

export class D1StateStore implements StateStore {
  constructor(private readonly db: D1Like) {}
  async load(): Promise<SystemState> {
    const row = await this.db.prepare("SELECT state_json FROM daily_snapshots WHERE id = 'runtime-current'").first<{state_json:string}>();
    if (!row) return emptyState();
    return JSON.parse(row.state_json) as SystemState;
  }
  async save(state: SystemState): Promise<void> {
    const json = JSON.stringify(state);
    const statements: D1Prepared[] = [this.db.prepare("INSERT INTO daily_snapshots (id, created_at, state_hash, counts_json, state_json) VALUES ('runtime-current', datetime('now'), ?1, ?2, ?3) ON CONFLICT(id) DO UPDATE SET created_at=excluded.created_at, state_hash=excluded.state_hash, counts_json=excluded.counts_json, state_json=excluded.state_json").bind(await sha256(state), val({events:state.events.length,tasks:state.tasks.length,knowledge:state.knowledge.length}), json)];
    for (const e of state.events) statements.push(this.db.prepare("INSERT OR IGNORE INTO events (id,type,entity_id,observed_at,created_at,source,actor,idempotency_key,hash,trust,evidence_type,payload_json) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12)").bind(e.id,e.type,e.entityId??null,e.observedAt,e.createdAt,e.source,e.actor,e.idempotencyKey,e.hash,e.trust,e.evidenceType,val(e.payload)));
    for (const lead of state.leads) statements.push(this.db.prepare("INSERT INTO leads (id,entity_id,name,email,intent_score,last_activity_at,source,status,reason,hash) VALUES (?1,NULL,?2,?3,?4,?5,?6,?7,?8,?9) ON CONFLICT(id) DO UPDATE SET intent_score=excluded.intent_score,last_activity_at=excluded.last_activity_at,status=excluded.status,reason=excluded.reason,hash=excluded.hash").bind(lead.id,lead.name,lead.email,lead.intentScore,lead.lastActivityAt,lead.source,lead.status,lead.reason,await sha256(lead)));
    for (const metric of state.metrics) statements.push(this.db.prepare("INSERT INTO campaign_metrics (id,day,impressions,clicks,leads,conversions,source,hash) VALUES (?1,?2,?3,?4,?5,?6,?7,?8) ON CONFLICT(id) DO UPDATE SET impressions=excluded.impressions,clicks=excluded.clicks,leads=excluded.leads,conversions=excluded.conversions,hash=excluded.hash").bind(metric.id,metric.day,metric.impressions,metric.clicks,metric.leads,metric.conversions,metric.source,await sha256(metric)));
    for (const claim of state.claims) statements.push(this.db.prepare("INSERT INTO claims (id,entity_id,statement,source_refs_json,observed_at,created_at,confidence,agent_origin,evidence_hash,status,verdict) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11) ON CONFLICT(id) DO UPDATE SET status=excluded.status,verdict=excluded.verdict").bind(claim.id,claim.entityId??null,claim.statement,val(claim.sourceRefs),claim.observedAt,claim.createdAt,claim.confidence,claim.agentOrigin,claim.evidenceHash,claim.status,claim.verdict??null));
    for (const item of state.knowledge) statements.push(this.db.prepare("INSERT INTO knowledge (id,type,entity_id,statement,source_refs_json,observed_at,created_at,confidence,freshness_policy,expires_at,agent_origin,evidence_hash,authority_level,supersedes,status) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15) ON CONFLICT(id) DO UPDATE SET status=excluded.status,authority_level=excluded.authority_level,supersedes=excluded.supersedes").bind(item.id,item.type,item.entityId??null,item.statement,val(item.sourceRefs),item.observedAt,item.createdAt,item.confidence,item.freshnessPolicy,item.expiresAt??null,item.agentOrigin,item.evidenceHash,item.authorityLevel,item.supersedes??null,item.status));
    for (const decision of state.decisions) statements.push(this.db.prepare("INSERT INTO decisions (id,created_at,priority,rationale,evidence_refs_json,assignments_json,audit_verdict,hash) VALUES (?1,?2,?3,?4,?5,?6,?7,?8) ON CONFLICT(id) DO UPDATE SET priority=excluded.priority,rationale=excluded.rationale,audit_verdict=excluded.audit_verdict,hash=excluded.hash").bind(decision.id,decision.createdAt,decision.priority,decision.rationale,val(decision.evidenceRefs),val(decision.assignments),decision.auditVerdict,await sha256(decision)));
    for (const task of state.tasks) statements.push(this.db.prepare("INSERT INTO tasks (id,type,entity_id,priority,risk,status,requested_by,due_at,input_json,created_at,hash) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11) ON CONFLICT(id) DO UPDATE SET priority=excluded.priority,status=excluded.status,input_json=excluded.input_json,hash=excluded.hash").bind(task.id,task.type,task.entityId??null,task.priority,task.risk,task.status,task.requestedBy,task.dueAt??null,val(task.input),task.createdAt,await sha256(task)));
    for (const approval of state.approvals) statements.push(this.db.prepare("INSERT INTO approvals (id,action_hash,policy_version,approval_chain_version,action_class,requested_by,reason,scope,expires_at,state,actor,signature,consumed_at,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14) ON CONFLICT(id) DO UPDATE SET state=excluded.state,actor=excluded.actor,signature=excluded.signature,consumed_at=excluded.consumed_at").bind(approval.id,approval.actionHash,approval.policyVersion,approval.approvalChainVersion,approval.actionClass,approval.requestedBy,approval.reason,approval.scope,approval.expiresAt,approval.state,approval.actor??null,approval.signature??null,approval.consumedAt??null,approval.expiresAt));
    for (const action of state.actions) statements.push(this.db.prepare("INSERT INTO actions (id,action_class,requested_by,policy_decision,approval_id,status,payload_hash,created_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8) ON CONFLICT(id) DO UPDATE SET status=excluded.status,approval_id=excluded.approval_id").bind(action.id,action.actionClass,action.requestedBy,action.policyDecision,action.approvalId??null,action.status,await sha256(action.payload),action.createdAt));
    for (const intent of state.actionIntents) statements.push(this.db.prepare("INSERT INTO action_intents (intent_id,task_id,agent_id,subject_id,action_class,connector,operation,target,canonical_parameters_json,action_digest,justification,evidence_refs_json,policy_version,approval_chain_version,precondition_hash,idempotency_key,requested_at,expires_at,status,approval_id,intent_json) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20,?21) ON CONFLICT(intent_id) DO UPDATE SET status=excluded.status,approval_id=excluded.approval_id,intent_json=excluded.intent_json").bind(intent.intentId,intent.taskId,intent.agentId,intent.subjectId,intent.actionClass,intent.connector,intent.operation,intent.target,val(intent.canonicalParameters),intent.actionDigest,intent.justification,val(intent.evidenceRefs),intent.policyVersion,intent.approvalChainVersion,intent.preconditionHash,intent.idempotencyKey,intent.requestedAt,intent.expiresAt,intent.status,intent.approvalId??null,val(intent)));
    for (const receipt of state.effectReceipts) statements.push(this.db.prepare("INSERT INTO effect_receipts (receipt_id,intent_id,action_digest,idempotency_key,connector,operation,status,result_hash,executed_at,attempt,detail,receipt_json) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12) ON CONFLICT(idempotency_key) DO UPDATE SET status=excluded.status,result_hash=excluded.result_hash,executed_at=excluded.executed_at,attempt=excluded.attempt,detail=excluded.detail,receipt_json=excluded.receipt_json").bind(receipt.receiptId,receipt.intentId,receipt.actionDigest,receipt.idempotencyKey,receipt.connector,receipt.operation,receipt.status,receipt.resultHash,receipt.executedAt,receipt.attempt,receipt.detail,val(receipt)));
    for (const model of state.modelCalls) statements.push(this.db.prepare("INSERT OR IGNORE INTO model_calls (id,role,task_id,model_id,tier,input_tokens,output_tokens,estimated_neurons,latency_ms,reason_selected,fallback_reason,result_hash,quota_state) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13)").bind(model.id,model.role,model.taskId,model.modelId,model.tier,model.inputTokens,model.outputTokens,model.estimatedNeurons,model.latencyMs,model.reasonSelected,model.fallbackReason??null,model.resultHash,model.quotaState));
    for (const finding of state.auditFindings) statements.push(this.db.prepare("INSERT INTO audit_findings (id,target_id,verdict,reason,evidence_refs_json,created_at,strategy,hash) VALUES (?1,?2,?3,?4,?5,?6,?7,?8) ON CONFLICT(id) DO UPDATE SET verdict=excluded.verdict,reason=excluded.reason,hash=excluded.hash").bind(finding.id,finding.targetId,finding.verdict,finding.reason,val(finding.evidenceRefs),finding.createdAt,finding.strategy,await sha256(finding)));
    await this.db.batch(statements);
  }
  async commitStateAndIntent(state: SystemState, intent: ActionIntent): Promise<void> {
    const next = structuredClone(state);
    const idx = next.actionIntents.findIndex((value) => value.intentId === intent.intentId);
    if (idx >= 0) next.actionIntents[idx] = structuredClone(intent); else next.actionIntents.push(structuredClone(intent));
    const json = JSON.stringify(next);
    await this.db.batch([
      this.db.prepare("INSERT INTO daily_snapshots (id,created_at,state_hash,counts_json,state_json) VALUES ('runtime-current',datetime('now'),?1,?2,?3) ON CONFLICT(id) DO UPDATE SET created_at=excluded.created_at,state_hash=excluded.state_hash,counts_json=excluded.counts_json,state_json=excluded.state_json").bind(await sha256(next),val({events:next.events.length,tasks:next.tasks.length,knowledge:next.knowledge.length}),json),
      this.db.prepare("INSERT INTO action_intents (intent_id,task_id,agent_id,subject_id,action_class,connector,operation,target,canonical_parameters_json,action_digest,justification,evidence_refs_json,policy_version,approval_chain_version,precondition_hash,idempotency_key,requested_at,expires_at,status,approval_id,intent_json) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20,?21) ON CONFLICT(intent_id) DO UPDATE SET status=excluded.status,approval_id=excluded.approval_id,intent_json=excluded.intent_json").bind(intent.intentId,intent.taskId,intent.agentId,intent.subjectId,intent.actionClass,intent.connector,intent.operation,intent.target,val(intent.canonicalParameters),intent.actionDigest,intent.justification,val(intent.evidenceRefs),intent.policyVersion,intent.approvalChainVersion,intent.preconditionHash,intent.idempotencyKey,intent.requestedAt,intent.expiresAt,intent.status,intent.approvalId??null,val(intent))
    ]);
  }
  async loadLedger(): Promise<LedgerRecord[]> {
    const result = await this.db.prepare("SELECT seq,kind,ref_id,timestamp,payload_hash,previous_hash,chain_hash FROM ledger ORDER BY seq").all<Record<string,unknown>>();
    return result.results.map((row) => ({seq:Number(row.seq),kind:String(row.kind) as LedgerRecord["kind"],refId:String(row.ref_id),timestamp:String(row.timestamp),payloadHash:String(row.payload_hash),previousHash:String(row.previous_hash),chainHash:String(row.chain_hash)}));
  }
  async saveLedger(records: LedgerRecord[]): Promise<void> {
    const statements = records.map((record) => this.db.prepare("INSERT OR IGNORE INTO ledger (seq,kind,ref_id,timestamp,payload_hash,previous_hash,chain_hash) VALUES (?1,?2,?3,?4,?5,?6,?7)").bind(record.seq,record.kind,record.refId,record.timestamp,record.payloadHash,record.previousHash,record.chainHash));
    if (statements.length) await this.db.batch(statements);
  }
  async reset(): Promise<void> { await this.db.batch([this.db.prepare("DELETE FROM daily_snapshots WHERE id='runtime-current'"),this.db.prepare("DELETE FROM ledger"),this.db.prepare("DELETE FROM events")]); }
}
