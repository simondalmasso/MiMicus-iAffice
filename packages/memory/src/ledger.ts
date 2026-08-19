import { canonicalize, sha256, stableId } from "../../core/src/hash.js";
import type { BusinessEvent, Claim, KnowledgeItem, LedgerRecord, SystemState } from "../../core/src/types.js";

export class Ledger {
  private records: LedgerRecord[] = [];

  list(): LedgerRecord[] { return structuredClone(this.records); }

  async append(kind: LedgerRecord["kind"], refId: string, payload: unknown, timestamp: string): Promise<LedgerRecord> {
    const previousHash = this.records.at(-1)?.chainHash ?? "GENESIS";
    const payloadHash = await sha256(payload);
    const chainHash = await sha256({ seq: this.records.length + 1, kind, refId, timestamp, payloadHash, previousHash });
    const record: LedgerRecord = { seq: this.records.length + 1, kind, refId, timestamp, payloadHash, previousHash, chainHash };
    this.records.push(record);
    return structuredClone(record);
  }

  async verify(records: LedgerRecord[] = this.records): Promise<{ ok: boolean; failedSeq?: number }> {
    let previousHash = "GENESIS";
    for (const record of records) {
      if (record.previousHash !== previousHash) return { ok: false, failedSeq: record.seq };
      const expected = await sha256({
        seq: record.seq, kind: record.kind, refId: record.refId, timestamp: record.timestamp,
        payloadHash: record.payloadHash, previousHash: record.previousHash
      });
      if (expected !== record.chainHash) return { ok: false, failedSeq: record.seq };
      previousHash = record.chainHash;
    }
    return { ok: true };
  }

  replaceForTest(records: LedgerRecord[]): void { this.records = structuredClone(records); }
}

export class EventMemory {
  constructor(private readonly state: SystemState, private readonly ledger: Ledger) {}

  async ingest(event: Omit<BusinessEvent, "id" | "hash"> & { id?: string; hash?: string }): Promise<{ event: BusinessEvent; duplicate: boolean }> {
    const existing = this.state.events.find((e) => e.idempotencyKey === event.idempotencyKey);
    if (existing) return { event: existing, duplicate: true };
    const hash = event.hash ?? await sha256({ ...event, id: undefined, hash: undefined });
    const id = event.id ?? await stableId("evt", { key: event.idempotencyKey, hash });
    const material: BusinessEvent = { ...event, id, hash };
    this.state.events.push(material);
    await this.ledger.append("EVENT", id, material, material.createdAt);
    return { event: material, duplicate: false };
  }

  async promoteClaim(claim: Claim, verdict: "PASS" | "FAIL" | "UNCERTAIN"): Promise<KnowledgeItem | null> {
    if (verdict !== "PASS") return null;
    const conflict = this.state.knowledge.find((k) =>
      k.entityId === claim.entityId && k.type === "fact" && k.status === "VERIFIED_KNOWLEDGE" && k.statement !== claim.statement
    );
    const item: KnowledgeItem = {
      id: await stableId("kn", { claim: claim.id, statement: claim.statement }),
      type: "fact",
      ...(claim.entityId ? { entityId: claim.entityId } : {}),
      statement: claim.statement,
      sourceRefs: claim.sourceRefs,
      observedAt: claim.observedAt,
      createdAt: claim.createdAt,
      confidence: claim.confidence,
      freshnessPolicy: "P7D",
      agentOrigin: claim.agentOrigin,
      evidenceHash: claim.evidenceHash,
      authorityLevel: "VERIFIED",
      status: conflict ? "CONFLICT" : "VERIFIED_KNOWLEDGE"
    };
    if (conflict) {
      conflict.status = "CONFLICT";
    }
    this.state.knowledge.push(item);
    return item;
  }

  expire(now: string): number {
    let count = 0;
    for (const item of this.state.knowledge) {
      if (item.expiresAt && item.status === "VERIFIED_KNOWLEDGE" && item.expiresAt <= now) {
        item.status = "EXPIRED";
        count += 1;
      }
    }
    return count;
  }

  revoke(id: string): boolean {
    const item = this.state.knowledge.find((k) => k.id === id);
    if (!item) return false;
    item.status = "REVOKED";
    return true;
  }
}

export async function stateHash(state: SystemState): Promise<string> {
  const stable = {
    events: state.events,
    leads: state.leads,
    metrics: state.metrics,
    claims: state.claims,
    knowledge: state.knowledge,
    tasks: state.tasks,
    decisions: state.decisions,
    approvals: state.approvals,
    actions: state.actions,
    modelCalls: state.modelCalls,
    auditFindings: state.auditFindings,
    outbound: state.outbound
  };
  return sha256(canonicalize(stable));
}

export async function rebuildProjection(events: BusinessEvent[]): Promise<Pick<SystemState, "events" | "leads" | "metrics">> {
  const leads: SystemState["leads"] = [];
  const metrics: SystemState["metrics"] = [];
  const dedup = new Map<string, BusinessEvent>();
  for (const event of events) {
    if (!dedup.has(event.idempotencyKey)) dedup.set(event.idempotencyKey, event);
  }
  for (const event of dedup.values()) {
    if (event.type === "lead") {
      const p = event.payload;
      leads.push({
        id: String(p.id), name: String(p.name), email: String(p.email), intentScore: Number(p.intentScore),
        lastActivityAt: String(p.lastActivityAt), source: String(p.source), status: "NEW", reason: "ingested"
      });
    }
    if (event.type === "campaign_metric") {
      const p = event.payload;
      metrics.push({ id: String(p.id), day: String(p.day), impressions: Number(p.impressions), clicks: Number(p.clicks), leads: Number(p.leads), conversions: Number(p.conversions), source: String(p.source) });
    }
  }
  return { events: [...dedup.values()], leads, metrics };
}
