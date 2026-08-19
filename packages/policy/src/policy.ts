import { sha256, stableId } from "../../core/src/hash.js";
import type { ActionClass, AgentRole, ApprovalRequest, PolicyDecision } from "../../core/src/types.js";
import { APPROVAL_CHAIN_VERSION, POLICY_VERSION } from "../../effects/src/kernel.js";

const matrix: Record<ActionClass, PolicyDecision> = {
  READ_PUBLIC: "ALLOW",
  READ_PRIVATE: "ALLOW",
  INTERNAL_WRITE: "ALLOW",
  DRAFT_EXTERNAL: "ALLOW",
  SEND_EXTERNAL: "APPROVAL_REQUIRED",
  PUBLISH_CONTENT: "APPROVAL_REQUIRED",
  MONEY_MUTATION: "DENY",
  DESTRUCTIVE_MUTATION: "APPROVAL_REQUIRED",
  CREDENTIAL_MUTATION: "DENY",
  CODE_WRITE: "ALLOW",
  CODE_MERGE: "APPROVAL_REQUIRED",
  DEPLOY: "APPROVAL_REQUIRED"
};

export class PolicyEngine {
  readonly version = POLICY_VERSION;
  readonly approvalChainVersion = APPROVAL_CHAIN_VERSION;
  decision(actionClass: ActionClass, context: { sourceAllowlisted?: boolean; scopedPrivateCapability?: boolean; isolatedCodeWorkspace?: boolean } = {}): PolicyDecision {
    if (actionClass === "READ_PUBLIC" && context.sourceAllowlisted !== true) return "DENY";
    if (actionClass === "READ_PRIVATE" && context.scopedPrivateCapability !== true) return "DENY";
    if (actionClass === "CODE_WRITE" && context.isolatedCodeWorkspace !== true) return "DENY";
    return matrix[actionClass];
  }
  policyMatrix(): Record<ActionClass, PolicyDecision> { return { ...matrix }; }
}


export async function verifyApprovalSignature(approval: ApprovalRequest, signingKey: string): Promise<boolean> {
  if (!approval.signature || !approval.actor || !signingKey) return false;
  const expected = await sha256(`${signingKey}:${approval.id}:${approval.actionHash}:${approval.policyVersion}:${approval.approvalChainVersion}:${approval.actor}:${approval.expiresAt}`);
  return expected === approval.signature;
}

export class ApprovalManager {
  private approvals = new Map<string, ApprovalRequest>();
  constructor(private readonly signingKey: string, private readonly clock: () => Date = () => new Date()) {
    if (!signingKey) throw new Error("APPROVAL_SIGNING_KEY_REQUIRED");
  }

  async request(input: { actionClass: ActionClass; requestedBy: AgentRole; reason: string; scope: string; actionDigest: string; ttlMs?: number; policyVersion?: string; approvalChainVersion?: string }): Promise<ApprovalRequest> {
    const now = this.clock();
    if (!/^[a-f0-9]{64}$/i.test(input.actionDigest)) throw new Error("ACTION_DIGEST_REQUIRED");
    const expiresAt = new Date(now.getTime() + (input.ttlMs ?? 15 * 60_000)).toISOString();
    const id = await stableId("approval", { actionHash: input.actionDigest, requestedBy: input.requestedBy, at: now.toISOString() });
    const approval: ApprovalRequest = {
      id, actionHash: input.actionDigest, policyVersion: input.policyVersion ?? POLICY_VERSION,
      approvalChainVersion: input.approvalChainVersion ?? APPROVAL_CHAIN_VERSION,
      actionClass: input.actionClass, requestedBy: input.requestedBy, reason: input.reason, scope: input.scope,
      expiresAt, state: "PENDING"
    };
    this.approvals.set(id, approval);
    return structuredClone(approval);
  }

  async approve(id: string, actor: string): Promise<ApprovalRequest> {
    const approval = this.mustGet(id); this.assertPendingAndFresh(approval);
    const signature = await sha256(`${this.signingKey}:${approval.id}:${approval.actionHash}:${approval.policyVersion}:${approval.approvalChainVersion}:${actor}:${approval.expiresAt}`);
    approval.actor = actor; approval.signature = signature; approval.state = "APPROVED";
    return structuredClone(approval);
  }

  reject(id: string, actor: string): ApprovalRequest {
    const approval = this.mustGet(id); this.assertPendingAndFresh(approval); approval.actor = actor; approval.state = "REJECTED"; return structuredClone(approval);
  }

  consume(id: string, actionDigest: string): ApprovalRequest {
    const approval = this.mustGet(id);
    if (approval.state !== "APPROVED") throw new Error("APPROVAL_NOT_APPROVED_OR_ALREADY_CONSUMED");
    if (approval.expiresAt <= this.clock().toISOString()) { approval.state = "EXPIRED"; throw new Error("APPROVAL_EXPIRED"); }
    if (approval.actionHash !== actionDigest) throw new Error("APPROVAL_SCOPE_HASH_MISMATCH");
    approval.state = "CONSUMED"; approval.consumedAt = this.clock().toISOString(); return structuredClone(approval);
  }

  get(id: string): ApprovalRequest | undefined { const value = this.approvals.get(id); return value ? structuredClone(value) : undefined; }
  list(): ApprovalRequest[] { return [...this.approvals.values()].map((a) => structuredClone(a)); }
  restore(items: ApprovalRequest[]): void { this.approvals.clear(); for (const item of items) this.approvals.set(item.id, structuredClone(item)); }
  private mustGet(id: string): ApprovalRequest { const approval = this.approvals.get(id); if (!approval) throw new Error("APPROVAL_NOT_FOUND"); return approval; }
  private assertPendingAndFresh(approval: ApprovalRequest): void { if (approval.state !== "PENDING") throw new Error("APPROVAL_NOT_PENDING"); if (approval.expiresAt <= this.clock().toISOString()) { approval.state = "EXPIRED"; throw new Error("APPROVAL_EXPIRED"); } }
}
