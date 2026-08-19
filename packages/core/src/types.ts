export type EvidenceTaxonomy =
  | "LIVE_DEPLOYED"
  | "LIVE_EXTERNAL"
  | "OFFICIAL_DOC"
  | "SOURCE_CODE"
  | "DETERMINISTIC_TEST"
  | "DERIVED"
  | "REFERENCE_FIXTURE"
  | "ASSUMPTION"
  | "UNKNOWN";

export type AgentRole = "CEO" | "RESEARCH" | "CMO" | "SALES" | "DATA" | "DEV" | "AUD";
export type AuditVerdict = "PASS" | "FAIL" | "UNCERTAIN";
export type KnowledgeStatus =
  | "RAW_EVENT"
  | "FACT_CANDIDATE"
  | "CLAIM"
  | "AUDITED"
  | "VERIFIED_KNOWLEDGE"
  | "SUPERSEDED"
  | "EXPIRED"
  | "REVOKED"
  | "CONFLICT";

export type ActionClass =
  | "READ_PUBLIC"
  | "READ_PRIVATE"
  | "INTERNAL_WRITE"
  | "DRAFT_EXTERNAL"
  | "SEND_EXTERNAL"
  | "PUBLISH_CONTENT"
  | "MONEY_MUTATION"
  | "DESTRUCTIVE_MUTATION"
  | "CREDENTIAL_MUTATION"
  | "CODE_WRITE"
  | "CODE_MERGE"
  | "DEPLOY";

export type PolicyDecision = "ALLOW" | "APPROVAL_REQUIRED" | "DENY";
export type ModelTier = "T0" | "T1" | "T2" | "T3" | "T4";
export type QuotaResource =
  | "worker_requests"
  | "d1_rows_read"
  | "d1_rows_write"
  | "queue_ops"
  | "workflow_steps"
  | "ai_neurons";

export interface StableRecord {
  id: string;
  createdAt: string;
  source: string;
  actor: string;
  idempotencyKey: string;
  hash: string;
}

export interface BusinessEvent extends StableRecord {
  type: string;
  entityId?: string;
  observedAt: string;
  payload: Record<string, unknown>;
  trust: "TRUSTED_INTERNAL" | "AUTHORIZED_EXTERNAL" | "UNTRUSTED_EXTERNAL" | "REFERENCE_FIXTURE";
  evidenceType: EvidenceTaxonomy;
}

export interface LedgerRecord {
  seq: number;
  kind: "EVENT" | "DECISION" | "APPROVAL" | "ACTION" | "CLAIM" | "AUDIT";
  refId: string;
  timestamp: string;
  payloadHash: string;
  previousHash: string;
  chainHash: string;
}

export interface Lead {
  id: string;
  name: string;
  email: string;
  intentScore: number;
  lastActivityAt: string;
  source: string;
  status: "NEW" | "HOT" | "STALE" | "QUALIFIED" | "DISQUALIFIED";
  reason: string;
}

export interface CampaignMetric {
  id: string;
  day: string;
  impressions: number;
  clicks: number;
  leads: number;
  conversions: number;
  source: string;
}

export interface Claim {
  id: string;
  entityId?: string;
  statement: string;
  sourceRefs: string[];
  observedAt: string;
  createdAt: string;
  confidence: number;
  agentOrigin: AgentRole;
  evidenceHash: string;
  status: "CLAIM" | "AUDITED" | "VERIFIED" | "REJECTED" | "UNCERTAIN";
  verdict?: AuditVerdict;
}

export interface KnowledgeItem {
  id: string;
  type: string;
  entityId?: string;
  statement: string;
  sourceRefs: string[];
  observedAt: string;
  createdAt: string;
  confidence: number;
  freshnessPolicy: string;
  expiresAt?: string;
  agentOrigin: AgentRole;
  evidenceHash: string;
  authorityLevel: "UNVERIFIED" | "AUDITED" | "VERIFIED";
  supersedes?: string;
  status: KnowledgeStatus;
}

export interface Task {
  id: string;
  type: string;
  entityId?: string;
  priority: number;
  risk: "LOW" | "MEDIUM" | "HIGH";
  status: "QUEUED" | "RUNNING" | "DONE" | "BLOCKED" | "DEFERRED";
  requestedBy: AgentRole | "SYSTEM";
  dueAt?: string;
  input: Record<string, unknown>;
  createdAt: string;
}

export interface RouteDecision {
  taskId: string;
  coalition: AgentRole[];
  modelTier: ModelTier;
  deterministicFirst: boolean;
  reason: string;
}

export interface Decision {
  id: string;
  createdAt: string;
  priority: string;
  rationale: string;
  evidenceRefs: string[];
  assignments: Array<{ role: AgentRole; task: string }>;
  auditVerdict: AuditVerdict;
}

export interface ApprovalRequest {
  id: string;
  actionHash: string;
  policyVersion: string;
  approvalChainVersion: string;
  actionClass: ActionClass;
  requestedBy: AgentRole;
  reason: string;
  scope: string;
  expiresAt: string;
  state: "PENDING" | "APPROVED" | "REJECTED" | "CONSUMED" | "EXPIRED";
  actor?: string;
  signature?: string;
  consumedAt?: string;
}

export type ActionIntentStatus = "PENDING" | "APPROVAL_REQUIRED" | "READY" | "RETRYABLE" | "EXECUTING" | "EXECUTED" | "DENIED" | "EXPIRED";

export interface ActionIntent {
  intentId: string;
  taskId: string;
  agentId: AgentRole;
  subjectId: string;
  actionClass: ActionClass;
  connector: string;
  operation: string;
  target: string;
  canonicalParameters: Record<string, unknown>;
  actionDigest: string;
  justification: string;
  evidenceRefs: string[];
  policyVersion: string;
  approvalChainVersion: string;
  preconditionHash: string;
  idempotencyKey: string;
  requestedAt: string;
  expiresAt: string;
  status: ActionIntentStatus;
  approvalId?: string;
}

export interface EffectReceipt {
  receiptId: string;
  intentId: string;
  actionDigest: string;
  idempotencyKey: string;
  connector: string;
  operation: string;
  status: "EXECUTED" | "REJECTED" | "RETRYABLE";
  resultHash: string;
  executedAt: string;
  attempt: number;
  detail: string;
}

export interface ActionRecord {
  id: string;
  actionClass: ActionClass;
  payload: Record<string, unknown>;
  requestedBy: AgentRole;
  policyDecision: PolicyDecision;
  approvalId?: string;
  status: "DRAFT" | "BLOCKED" | "APPROVED" | "EXECUTED" | "REJECTED";
  createdAt: string;
}

export interface ModelCallRecord {
  id: string;
  role: AgentRole;
  taskId: string;
  modelId: string;
  tier: ModelTier;
  inputTokens: number;
  outputTokens: number;
  estimatedNeurons: number;
  latencyMs: number;
  reasonSelected: string;
  fallbackReason?: string;
  resultHash: string;
  quotaState: "OK" | "SOFT_CAP" | "HARD_CAP" | "FREE_QUOTA_EXHAUSTED" | "ERROR";
}

export interface AuditFinding {
  id: string;
  targetId: string;
  verdict: AuditVerdict;
  reason: string;
  evidenceRefs: string[];
  createdAt: string;
  strategy: string;
}

export interface Snapshot {
  id: string;
  createdAt: string;
  stateHash: string;
  counts: Record<string, number>;
}

export interface SystemState {
  events: BusinessEvent[];
  leads: Lead[];
  metrics: CampaignMetric[];
  claims: Claim[];
  knowledge: KnowledgeItem[];
  tasks: Task[];
  decisions: Decision[];
  approvals: ApprovalRequest[];
  actions: ActionRecord[];
  modelCalls: ModelCallRecord[];
  auditFindings: AuditFinding[];
  actionIntents: ActionIntent[];
  effectReceipts: EffectReceipt[];
  outbound: Array<{ id: string; payload: Record<string, unknown>; approvalId: string }>;
}
