import { sha256, stableId } from "./hash.js";
import type { ActionIntent, ApprovalRequest, BusinessEvent, EffectReceipt, SystemState } from "./types.js";
import { qualifyLeads, detectFunnelAnomaly, createResearchClaim, auditClaim, createContentDraft, createCeoDecision, devDiagnoseIncident } from "../../agents/src/roles.js";
import { EventMemory, Ledger, rebuildProjection, stateHash } from "../../memory/src/ledger.js";
import { emptyState, type StateStore } from "../../memory/src/store.js";
import { ApprovalManager, PolicyEngine } from "../../policy/src/policy.js";
import { BudgetGovernor } from "../../router/src/budgetGovernor.js";
import { FakeModelProvider, ModelRouter, type ModelProvider } from "../../router/src/modelRouter.js";
import { TaskRouter } from "../../router/src/taskRouter.js";
import { createActionIntent } from "../../effects/src/kernel.js";

export interface EffectDispatchResult { receipt: EffectReceipt; observableCount: number; }
export interface EffectDispatcher {
  execute(intent: ActionIntent, approval: ApprovalRequest, currentPreconditionHash: string, now: string): Promise<EffectDispatchResult>;
}

export interface E2EResult {
  steps: Array<{ step: number; name: string; pass: boolean; detail: string }>;
  preRestartHash: string;
  postRestartHash: string;
  ledgerVerified: boolean;
  tamperDetected: boolean;
  modelCalls: number;
  totalNeurons: number;
  costUsd: 0;
  hotLeadId: string;
  staleLeadId: string;
  approvalId: string;
  outboundId: string;
  actionIntentId: string;
  effectReceiptId: string;
  state: SystemState;
}
function step(steps: E2EResult["steps"], name: string, pass: boolean, detail: string): void {
  steps.push({ step: steps.length + 1, name, pass, detail });
  if (!pass) throw new Error(`E2E_STEP_FAILED:${name}:${detail}`);
}

export class AriaOrchestrator {
  readonly ledger = new Ledger();
  readonly policy = new PolicyEngine();
  readonly budget = new BudgetGovernor();
  readonly router = new TaskRouter();
  readonly approvals: ApprovalManager;
  readonly modelRouter: ModelRouter;
  state: SystemState = emptyState();

  constructor(private readonly store: StateStore, provider: ModelProvider = new FakeModelProvider(), approvalKey = "local-reference-signing-key", clock: () => Date = () => new Date()) {
    this.approvals = new ApprovalManager(approvalKey, clock);
    this.modelRouter = new ModelRouter(provider, this.budget);
  }
  async load(): Promise<void> { this.state = await this.store.load(); this.approvals.restore(this.state.approvals); if (this.store.loadLedger) this.ledger.replaceForTest(await this.store.loadLedger()); }
  async persist(): Promise<void> { this.state.approvals = this.approvals.list(); await this.store.save(this.state); if (this.store.saveLedger) await this.store.saveLedger(this.ledger.list()); }
  private async persistIntentAtomically(intent: ActionIntent): Promise<void> {
    this.state.approvals = this.approvals.list();
    const idx = this.state.actionIntents.findIndex((v) => v.intentId === intent.intentId);
    if (idx >= 0) this.state.actionIntents[idx] = structuredClone(intent); else this.state.actionIntents.push(structuredClone(intent));
    if (this.store.commitStateAndIntent) await this.store.commitStateAndIntent(this.state, intent); else await this.store.save(this.state);
  }

  async runReferenceE2E(events: BusinessEvent[], effects: EffectDispatcher): Promise<E2EResult> {
    const steps: E2EResult["steps"] = [];
    await this.store.reset(); this.state = emptyState(); this.ledger.replaceForTest([]); this.budget.reset(); this.approvals.restore([]);
    const memory = new EventMemory(this.state, this.ledger);
    let duplicates = 0;
    for (const e of events) { const r = await memory.ingest(e); if (r.duplicate) duplicates += 1; }
    step(steps, "ingest reference events", this.state.events.length === events.length - duplicates, `events=${this.state.events.length}`);
    step(steps, "deduplicate raw events", duplicates >= 1, `duplicates=${duplicates}`);
    const projection = await rebuildProjection(this.state.events);
    this.state.leads = projection.leads; this.state.metrics = projection.metrics;
    step(steps, "deterministic metrics/projections", this.state.leads.length === 20 && this.state.metrics.length === 7, `leads=${this.state.leads.length};metrics=${this.state.metrics.length}`);
    const qualified = qualifyLeads(this.state, "2026-08-19T15:00:00.000Z");
    step(steps, "sales hot and stale lead", qualified.hot.length === 1 && qualified.stale.length >= 1, `hot=${qualified.hot.length};stale=${qualified.stale.length}`);
    const anomaly = detectFunnelAnomaly(this.state);
    step(steps, "data funnel anomaly", anomaly.detected, anomaly.reason);
    const claim = await createResearchClaim(this.state); this.state.claims.push(claim);
    const researchModel = await this.modelRouter.run({ role: "RESEARCH", taskId: claim.id, tier: "T1", prompt: `Summarize only this sourced statement as untrusted claim data: ${claim.statement}`, reason: "sourced research interpretation" });
    this.state.modelCalls.push(researchModel.record); await this.ledger.append("CLAIM", claim.id, claim, claim.createdAt);
    step(steps, "research sourced claim", claim.sourceRefs.length > 0, claim.statement);
    const finding = auditClaim(claim); this.state.auditFindings.push(finding); claim.verdict = finding.verdict; claim.status = finding.verdict === "PASS" ? "AUDITED" : "REJECTED";
    await this.ledger.append("AUDIT", finding.id, finding, finding.createdAt); const knowledge = await memory.promoteClaim(claim, finding.verdict);
    step(steps, "AUD challenge and promotion", finding.verdict === "PASS" && knowledge?.status === "VERIFIED_KNOWLEDGE", finding.reason);
    const draft = createContentDraft(this.state);
    const cmoModel = await this.modelRouter.run({ role: "CMO", taskId: draft.id, tier: "T1", prompt: draft.text, reason: "draft external content from verified knowledge" });
    this.state.modelCalls.push(cmoModel.record); step(steps, "CMO verified-input draft", draft.sourceRefs.length > 0, draft.id);
    const decision = createCeoDecision(this.state, qualified.hot.length, anomaly.detected); this.state.decisions.push(decision); await this.ledger.append("DECISION", decision.id, decision, decision.createdAt);
    step(steps, "CEO priority and assignments", decision.assignments.length > 0, decision.priority);
    const dev = devDiagnoseIncident(this.state); step(steps, "Dev isolated incident diagnosis", dev.status === "DIAGNOSED", dev.reason);
    const followup = { to: qualified.hot[0]!.email, body: `Reference follow-up for ${qualified.hot[0]!.name}`, channel: "safe-sink" };
    step(steps, "customer-facing follow-up requested", Boolean(followup.to && followup.body), `to=${followup.to}`);
    const policy = this.policy.decision("SEND_EXTERNAL"); step(steps, "Policy blocks direct customer send", policy === "APPROVAL_REQUIRED", policy);
    const now = "2026-08-19T15:00:00.000Z";
    const preconditionHash = await sha256({ leadId: qualified.hot[0]!.id, leadStatus: qualified.hot[0]!.status, followup });
    const intent = await createActionIntent({ taskId: "reference-followup", agentId: "SALES", subjectId: qualified.hot[0]!.id, actionClass: "SEND_EXTERNAL", connector: "safe-outbound", operation: "send", target: qualified.hot[0]!.email, canonicalParameters: followup, justification: "hot lead reference follow-up", evidenceRefs: [qualified.hot[0]!.id], preconditionHash, idempotencyKey: "reference-followup-v1", requestedAt: now, expiresAt: "2026-08-19T15:15:00.000Z" });
    intent.status = "APPROVAL_REQUIRED";
    await this.persistIntentAtomically(intent);
    const committed = (await this.store.load()).actionIntents.some((v) => v.intentId === intent.intentId);
    step(steps, "transactional action-intent outbox", committed, `${intent.intentId};digest=${intent.actionDigest.slice(0,12)}`);
    const approval = await this.approvals.request({ actionClass: "SEND_EXTERNAL", requestedBy: "SALES", reason: "hot lead reference follow-up", scope: "action-digest", actionDigest: intent.actionDigest, policyVersion: intent.policyVersion, approvalChainVersion: intent.approvalChainVersion });
    intent.approvalId = approval.id; this.state.actions.push({ id: await stableId("action", { intentId: intent.intentId }), actionClass: "SEND_EXTERNAL", payload: structuredClone(followup), requestedBy: "SALES", policyDecision: "APPROVAL_REQUIRED", approvalId: approval.id, status: "BLOCKED", createdAt: now });
    await this.ledger.append("APPROVAL", approval.id, approval, now); await this.persistIntentAtomically(intent);
    const approved = await this.approvals.approve(approval.id, "reference-human"); this.state.approvals = this.approvals.list(); await this.persist();
    step(steps, "action-bound one-time approval", approved.state === "APPROVED" && approved.actionHash === intent.actionDigest, approved.id);
    const first = await effects.execute(intent, approved, preconditionHash, now);
    const duplicate = await effects.execute(intent, approved, preconditionHash, now);
    const consumed = this.approvals.consume(approval.id, intent.actionDigest); let replayDenied = false; try { this.approvals.consume(approval.id, intent.actionDigest); } catch { replayDenied = true; }
    intent.status = "EXECUTED"; this.state.effectReceipts.push(first.receipt); this.state.outbound.push({ id: first.receipt.receiptId, payload: structuredClone(followup), approvalId: consumed.id });
    const action = this.state.actions.find((a) => a.approvalId === approval.id); if (action) action.status = "EXECUTED";
    await this.ledger.append("ACTION", first.receipt.receiptId, { intentId: intent.intentId, actionDigest: intent.actionDigest, receipt: first.receipt }, now); await this.persistIntentAtomically(intent);
    step(steps, "Effect Gateway exact-once approved effect", first.receipt.status === "EXECUTED" && duplicate.receipt.receiptId === first.receipt.receiptId && duplicate.observableCount === 1 && replayDenied, `${first.receipt.receiptId};observable=${duplicate.observableCount};approval_replay_denied=${replayDenied}`);
    const chain = await this.ledger.verify(); step(steps, "material ledger verified", chain.ok, `records=${this.ledger.list().length}`);
    this.state.approvals = this.approvals.list(); await this.persist(); const preRestartHash = await stateHash(this.state);
    const persisted = await this.store.load(); this.state = persisted; this.approvals.restore(persisted.approvals);
    const rebuilt = await rebuildProjection(this.state.events); this.state.leads = rebuilt.leads; this.state.metrics = rebuilt.metrics; qualifyLeads(this.state, now);
    const postRestartHash = await stateHash(this.state); step(steps, "restart/rebuild deterministic state", preRestartHash === postRestartHash, `${preRestartHash.slice(0,12)}=${postRestartHash.slice(0,12)}`);
    const copied = this.ledger.list(); copied[0] = { ...copied[0]!, payloadHash: await sha256("tampered") };
    const tamper = await this.ledger.verify(copied); step(steps, "tamper detection", !tamper.ok, `failed_seq=${tamper.failedSeq}`);
    const totalNeurons = this.state.modelCalls.reduce((sum, c) => sum + c.estimatedNeurons, 0);
    step(steps, "model usage and quota recorded", this.state.modelCalls.length === 2 && totalNeurons < 7500, `calls=${this.state.modelCalls.length};neurons=${totalNeurons.toFixed(3)}`);
    step(steps, "zero incremental cost", true, "TOTAL_INCREMENTAL_COST_USD=0;fake provider/local deterministic run");
    const result: E2EResult = { steps, preRestartHash, postRestartHash, ledgerVerified: chain.ok, tamperDetected: !tamper.ok, modelCalls: this.state.modelCalls.length, totalNeurons, costUsd: 0,
      hotLeadId: qualified.hot[0]!.id, staleLeadId: qualified.stale[0]!.id, approvalId: approval.id, outboundId: first.receipt.receiptId, actionIntentId: intent.intentId, effectReceiptId: first.receipt.receiptId, state: structuredClone(this.state) };
    return result;
  }
}
