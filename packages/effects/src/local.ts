import type { ActionIntent, ApprovalRequest } from "../../core/src/types.js";
import type { EffectDispatcher, EffectDispatchResult } from "../../core/src/orchestrator.js";
import { APPROVAL_CHAIN_VERSION, EffectKernel, InMemoryReceiptStore, POLICY_VERSION, SafeOutboundEffectAdapter, type EffectAdapter } from "./kernel.js";
import { verifyApprovalSignature } from "../../policy/src/policy.js";

export class LocalEffectGateway implements EffectDispatcher {
  readonly store = new InMemoryReceiptStore();
  readonly safeOutbound: SafeOutboundEffectAdapter;
  readonly kernel: EffectKernel;
  constructor(extraAdapters: EffectAdapter[] = [], signingKey = "local-reference-signing-key") {
    this.safeOutbound = new SafeOutboundEffectAdapter();
    this.kernel = new EffectKernel(this.store, [this.safeOutbound, ...extraAdapters], (approval) => verifyApprovalSignature(approval, signingKey));
  }
  async execute(intent: ActionIntent, approval: ApprovalRequest, currentPreconditionHash: string, now: string): Promise<EffectDispatchResult> {
    const receipt = await this.kernel.execute({ intent, approval, currentPolicyVersion: POLICY_VERSION, currentApprovalChainVersion: APPROVAL_CHAIN_VERSION, currentPreconditionHash, now });
    return { receipt, observableCount: this.safeOutbound.observableCount };
  }
}
