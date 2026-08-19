import { sha256, stableId } from "../../core/src/hash.js";
import type { ActionIntent, ApprovalRequest, EffectReceipt } from "../../core/src/types.js";

export const POLICY_VERSION = "aria-policy-v1";
export const APPROVAL_CHAIN_VERSION = "aria-approval-v1";
export const INTENT_SCHEMA_VERSION = "aria-action-intent-v1";

export interface ActionIntentDraft {
  taskId: string;
  agentId: ActionIntent["agentId"];
  subjectId: string;
  actionClass: ActionIntent["actionClass"];
  connector: string;
  operation: string;
  target: string;
  canonicalParameters: Record<string, unknown>;
  justification: string;
  evidenceRefs: string[];
  preconditionHash: string;
  idempotencyKey: string;
  requestedAt: string;
  expiresAt: string;
}

export function actionDigestMaterial(input: Omit<ActionIntent, "intentId" | "actionDigest" | "status" | "approvalId">): Record<string, unknown> {
  return {
    actor: input.agentId,
    subject: input.subjectId,
    operation: input.operation,
    target: input.target,
    connector: input.connector,
    actionClass: input.actionClass,
    schemaVersion: INTENT_SCHEMA_VERSION,
    parameters: input.canonicalParameters,
    policyVersion: input.policyVersion,
    approvalChainVersion: input.approvalChainVersion,
    preconditions: input.preconditionHash
  };
}

export async function computeActionDigest(input: Omit<ActionIntent, "intentId" | "actionDigest" | "status" | "approvalId">): Promise<string> {
  return sha256(actionDigestMaterial(input));
}

export async function createActionIntent(draft: ActionIntentDraft): Promise<ActionIntent> {
  const base: Omit<ActionIntent, "intentId" | "actionDigest" | "status" | "approvalId"> = {
    ...draft,
    policyVersion: POLICY_VERSION,
    approvalChainVersion: APPROVAL_CHAIN_VERSION
  };
  const actionDigest = await computeActionDigest(base);
  const intentId = await stableId("intent", { actionDigest, idempotencyKey: draft.idempotencyKey });
  return { ...base, intentId, actionDigest, status: "PENDING" };
}

export function isAuthorityExpansion(parent: ActionIntent, child: ActionIntent): boolean {
  if (parent.actionClass !== child.actionClass || parent.connector !== child.connector || parent.operation !== child.operation || parent.target !== child.target) return true;
  const parentKeys = Object.keys(parent.canonicalParameters);
  for (const [key, value] of Object.entries(child.canonicalParameters)) {
    if (!parentKeys.includes(key)) return true;
    if (JSON.stringify(parent.canonicalParameters[key]) !== JSON.stringify(value)) return true;
  }
  return false;
}

export interface EffectAdapter {
  connector: string;
  operation: string;
  execute(parameters: Record<string, unknown>, idempotencyKey: string): Promise<Record<string, unknown>>;
}

export interface EffectExecutionInput {
  intent: ActionIntent;
  approval?: ApprovalRequest;
  currentPolicyVersion: string;
  currentApprovalChainVersion: string;
  currentPreconditionHash: string;
  now: string;
}

export interface ReceiptStore {
  findByIdempotencyKey(key: string): Promise<EffectReceipt | undefined>;
  persist(receipt: EffectReceipt, intentStatus: ActionIntent["status"]): Promise<void>;
}

export class InMemoryReceiptStore implements ReceiptStore {
  readonly receipts: EffectReceipt[] = [];
  async findByIdempotencyKey(key: string): Promise<EffectReceipt | undefined> { return this.receipts.find((r) => r.idempotencyKey === key); }
  async persist(receipt: EffectReceipt): Promise<void> { const i = this.receipts.findIndex((r) => r.idempotencyKey === receipt.idempotencyKey); if (i >= 0) this.receipts[i] = structuredClone(receipt); else this.receipts.push(structuredClone(receipt)); }
}

export class EffectKernel {
  private readonly adapters = new Map<string, EffectAdapter>();
  constructor(private readonly receiptStore: ReceiptStore, adapters: EffectAdapter[], private readonly approvalVerifier: (approval: ApprovalRequest) => Promise<boolean>) {
    for (const adapter of adapters) this.adapters.set(`${adapter.connector}:${adapter.operation}`, adapter);
  }

  async execute(input: EffectExecutionInput): Promise<EffectReceipt> {
    const { intent } = input;
    const existing = await this.receiptStore.findByIdempotencyKey(intent.idempotencyKey);
    if (existing?.status === "EXECUTED") return existing;

    const expectedDigest = await computeActionDigest({
      taskId: intent.taskId, agentId: intent.agentId, subjectId: intent.subjectId, actionClass: intent.actionClass,
      connector: intent.connector, operation: intent.operation, target: intent.target, canonicalParameters: intent.canonicalParameters,
      justification: intent.justification, evidenceRefs: intent.evidenceRefs, policyVersion: intent.policyVersion,
      approvalChainVersion: intent.approvalChainVersion, preconditionHash: intent.preconditionHash,
      idempotencyKey: intent.idempotencyKey, requestedAt: intent.requestedAt, expiresAt: intent.expiresAt
    });
    if (expectedDigest !== intent.actionDigest) throw new Error("ACTION_DIGEST_MISMATCH");
    if (intent.policyVersion !== input.currentPolicyVersion) throw new Error("STALE_POLICY_VERSION");
    if (intent.approvalChainVersion !== input.currentApprovalChainVersion) throw new Error("STALE_APPROVAL_CHAIN_VERSION");
    if (intent.expiresAt <= input.now) throw new Error("INTENT_EXPIRED");
    if (intent.preconditionHash !== input.currentPreconditionHash) throw new Error("STALE_PRECONDITION");
    if (!input.approval || input.approval.state !== "APPROVED") throw new Error("VALID_APPROVAL_REQUIRED");
    if (!(await this.approvalVerifier(input.approval))) throw new Error("APPROVAL_SIGNATURE_INVALID");
    if (input.approval.actionHash !== intent.actionDigest) throw new Error("APPROVAL_DIGEST_MISMATCH");
    if (input.approval.policyVersion !== intent.policyVersion || input.approval.approvalChainVersion !== intent.approvalChainVersion) throw new Error("APPROVAL_VERSION_MISMATCH");
    if (input.approval.expiresAt <= input.now) throw new Error("APPROVAL_EXPIRED");

    const adapter = this.adapters.get(`${intent.connector}:${intent.operation}`);
    if (!adapter) throw new Error("UNKNOWN_EFFECT_OPERATION");
    try {
      const result = await adapter.execute(intent.canonicalParameters, intent.idempotencyKey);
      const receipt: EffectReceipt = {
        receiptId: await stableId("effect", { intentId: intent.intentId, idempotencyKey: intent.idempotencyKey }),
        intentId: intent.intentId, actionDigest: intent.actionDigest, idempotencyKey: intent.idempotencyKey,
        connector: intent.connector, operation: intent.operation, status: "EXECUTED", resultHash: await sha256(result),
        executedAt: input.now, attempt: (existing?.attempt ?? 0) + 1, detail: "IDEMPOTENT_EFFECT_EXECUTED"
      };
      await this.receiptStore.persist(receipt, "EXECUTED");
      return receipt;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const retryable = /FREE_QUOTA_EXHAUSTED|429|5\d\d|TIMEOUT/.test(message);
      const receipt: EffectReceipt = {
        receiptId: await stableId("effect", { intentId: intent.intentId, idempotencyKey: intent.idempotencyKey, status: retryable ? "retry" : "reject" }),
        intentId: intent.intentId, actionDigest: intent.actionDigest, idempotencyKey: intent.idempotencyKey,
        connector: intent.connector, operation: intent.operation, status: retryable ? "RETRYABLE" : "REJECTED",
        resultHash: await sha256({ error: message }), executedAt: input.now, attempt: (existing?.attempt ?? 0) + 1,
        detail: retryable ? "FREE_OR_TRANSIENT_FAILURE_NO_PAID_FALLBACK" : `FAIL_CLOSED:${message}`
      };
      await this.receiptStore.persist(receipt, retryable ? "RETRYABLE" : "DENIED");
      if (retryable) return receipt;
      throw error;
    }
  }
}

export class SafeOutboundEffectAdapter implements EffectAdapter {
  readonly connector = "safe-outbound";
  readonly operation = "send";
  private readonly effects = new Map<string, Record<string, unknown>>();
  get observableCount(): number { return this.effects.size; }
  async execute(parameters: Record<string, unknown>, idempotencyKey: string): Promise<Record<string, unknown>> {
    const existing = this.effects.get(idempotencyKey);
    if (existing) return structuredClone(existing);
    const result = { simulated: true, exactPayload: structuredClone(parameters), idempotencyKey };
    this.effects.set(idempotencyKey, result);
    return structuredClone(result);
  }
}
