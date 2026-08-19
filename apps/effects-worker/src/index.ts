import type { ActionIntent, ApprovalRequest, EffectReceipt } from "../../../packages/core/src/types.js";
import { sha256 } from "../../../packages/core/src/hash.js";
import type { D1Like } from "../../../packages/memory/src/store.js";
import { verifyApprovalSignature } from "../../../packages/policy/src/policy.js";
import { APPROVAL_CHAIN_VERSION, EffectKernel, POLICY_VERSION, type EffectAdapter } from "../../../packages/effects/src/kernel.js";
import { D1ReceiptStore } from "../../../packages/effects/src/d1-store.js";
import { GitHubIssueCommentEffectAdapter, NotionEffectAdapter } from "../../../packages/effects/src/adapters.js";

interface EffectsEnv {
  DB: D1Like;
  APPROVAL_SIGNING_KEY?: string;
  GITHUB_WRITE_TOKEN?: string;
  NOTION_WRITE_TOKEN?: string;
  ARIA_GIT_SHA?: string;
}
class D1SafeOutboundAdapter implements EffectAdapter {
  readonly connector = "safe-outbound";
  readonly operation = "send";
  constructor(private readonly db: D1Like) {}
  async execute(parameters: Record<string, unknown>, idempotencyKey: string): Promise<Record<string, unknown>> {
    const existing = await this.db.prepare("SELECT payload_json,result_hash FROM safe_outbound WHERE idempotency_key=?1").bind(idempotencyKey).first<{payload_json:string;result_hash:string}>();
    if (existing) return { simulated: true, exactPayload: JSON.parse(existing.payload_json), idempotencyKey, resultHash: existing.result_hash };
    const resultHash = await sha256(parameters);
    await this.db.prepare("INSERT OR IGNORE INTO safe_outbound (idempotency_key,payload_json,result_hash,created_at) VALUES (?1,?2,?3,datetime('now'))").bind(idempotencyKey,JSON.stringify(parameters),resultHash).run();
    return { simulated: true, exactPayload: parameters, idempotencyKey, resultHash };
  }
}
async function canonicalApproval(db: D1Like, id: string): Promise<ApprovalRequest | undefined> {
  const row = await db.prepare("SELECT id,action_hash,policy_version,approval_chain_version,action_class,requested_by,reason,scope,expires_at,state,actor,signature,consumed_at FROM approvals WHERE id=?1").bind(id).first<Record<string,unknown>>();
  if (!row) return undefined;
  return { id:String(row.id), actionHash:String(row.action_hash), policyVersion:String(row.policy_version), approvalChainVersion:String(row.approval_chain_version), actionClass:String(row.action_class) as ApprovalRequest["actionClass"], requestedBy:String(row.requested_by) as ApprovalRequest["requestedBy"], reason:String(row.reason), scope:String(row.scope), expiresAt:String(row.expires_at), state:String(row.state) as ApprovalRequest["state"], ...(row.actor?{actor:String(row.actor)}:{}), ...(row.signature?{signature:String(row.signature)}:{}), ...(row.consumed_at?{consumedAt:String(row.consumed_at)}:{}) };
}
async function countSafeOutbound(db: D1Like): Promise<number> { const row=await db.prepare("SELECT COUNT(*) AS n FROM safe_outbound").first<{n:number}>(); return Number(row?.n ?? 0); }
export default {
  async fetch(request: Request, env: EffectsEnv): Promise<Response> {
    const url = new URL(request.url);
    if (request.method !== "POST" || url.pathname !== "/internal/execute-intent") return new Response("NOT_FOUND", { status: 404 });
    if (!env.APPROVAL_SIGNING_KEY) return Response.json({ error: "APPROVAL_SIGNING_KEY_REQUIRED" }, { status: 503 });
    try {
      const body = await request.json() as { intent?: ActionIntent; approval?: ApprovalRequest; currentPreconditionHash?: string; now?: string };
      if (!body.intent || !body.approval || !body.currentPreconditionHash || !body.now) throw new Error("EFFECT_REQUEST_SCHEMA_INVALID");
      const storedApproval = await canonicalApproval(env.DB, body.approval.id);
      if (!storedApproval || storedApproval.state !== "APPROVED") throw new Error("CANONICAL_APPROVAL_NOT_APPROVED");
      if (!(await verifyApprovalSignature(storedApproval, env.APPROVAL_SIGNING_KEY))) throw new Error("APPROVAL_SIGNATURE_INVALID");
      if (storedApproval.actionHash !== body.intent.actionDigest) throw new Error("APPROVAL_DIGEST_MISMATCH");
      const adapters: EffectAdapter[] = [new D1SafeOutboundAdapter(env.DB)];
      if (env.GITHUB_WRITE_TOKEN) adapters.push(new GitHubIssueCommentEffectAdapter(env.GITHUB_WRITE_TOKEN));
      if (env.NOTION_WRITE_TOKEN) adapters.push(new NotionEffectAdapter(env.NOTION_WRITE_TOKEN));
      const kernel = new EffectKernel(new D1ReceiptStore(env.DB), adapters, (approval) => verifyApprovalSignature(approval, env.APPROVAL_SIGNING_KEY!));
      const receipt: EffectReceipt = await kernel.execute({ intent: body.intent, approval: storedApproval, currentPolicyVersion: POLICY_VERSION, currentApprovalChainVersion: APPROVAL_CHAIN_VERSION, currentPreconditionHash: body.currentPreconditionHash, now: body.now });
      return Response.json({ receipt, observableCount: await countSafeOutbound(env.DB), gatewaySha: env.ARIA_GIT_SHA ?? "unknown" });
    } catch (error) {
      return Response.json({ error: error instanceof Error ? error.message : "EFFECT_GATEWAY_ERROR" }, { status: 400 });
    }
  }
};
