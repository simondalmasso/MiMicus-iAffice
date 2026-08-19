import { sha256, stableId } from "../../core/src/hash.js";
import type { AuditFinding, Claim, Decision, Lead, SystemState, Task } from "../../core/src/types.js";

export function qualifyLeads(state: SystemState, nowIso: string): { hot: Lead[]; stale: Lead[] } {
  const now = new Date(nowIso).getTime();
  const hot: Lead[] = [];
  const stale: Lead[] = [];
  for (const lead of state.leads) {
    const ageDays = (now - new Date(lead.lastActivityAt).getTime()) / 86_400_000;
    if (lead.intentScore >= 80 && ageDays <= 3) {
      lead.status = "HOT";
      lead.reason = `intent>=80 and activity_age_days=${ageDays.toFixed(2)}<=3`;
      hot.push(lead);
    } else if (ageDays >= 5) {
      lead.status = "STALE";
      lead.reason = `activity_age_days=${ageDays.toFixed(2)}>=5`;
      stale.push(lead);
    } else {
      lead.status = "QUALIFIED";
      lead.reason = `intent=${lead.intentScore};age_days=${ageDays.toFixed(2)}`;
    }
  }
  return { hot, stale };
}

export function detectFunnelAnomaly(state: SystemState): { detected: boolean; day?: string; reason: string } {
  const sorted = [...state.metrics].sort((a, b) => a.day.localeCompare(b.day));
  if (sorted.length < 3) return { detected: false, reason: "insufficient_history" };
  const latest = sorted.at(-1)!;
  const prior = sorted.slice(0, -1);
  const avg = prior.reduce((sum, m) => sum + (m.leads ? m.conversions / m.leads : 0), 0) / prior.length;
  const current = latest.leads ? latest.conversions / latest.leads : 0;
  if (current < avg * 0.5) return { detected: true, day: latest.day, reason: `conversion_rate=${current.toFixed(4)} below 50% of prior_average=${avg.toFixed(4)}` };
  return { detected: false, day: latest.day, reason: `conversion_rate=${current.toFixed(4)} within threshold` };
}

export async function createResearchClaim(state: SystemState): Promise<Claim> {
  const researchEvent = state.events.find((e) => e.type === "research_snippet" && e.trust !== "UNTRUSTED_EXTERNAL");
  if (!researchEvent) throw new Error("NO_AUTHORIZED_RESEARCH_SOURCE");
  const statement = String(researchEvent.payload.statement ?? "");
  const sourceRef = String(researchEvent.payload.sourceUrl ?? researchEvent.id);
  const evidenceHash = await sha256({ statement, sourceRef, observedAt: researchEvent.observedAt });
  return {
    id: await stableId("claim", { statement, sourceRef }), statement, sourceRefs: [sourceRef], observedAt: researchEvent.observedAt,
    createdAt: researchEvent.createdAt, confidence: 0.82, agentOrigin: "RESEARCH", evidenceHash, status: "CLAIM"
  };
}

export function auditClaim(claim: Claim): AuditFinding {
  const fresh = Date.now() - new Date(claim.observedAt).getTime() < 30 * 86_400_000;
  const sourced = claim.sourceRefs.length > 0 && claim.sourceRefs.every((x) => /^https?:\/\//.test(x));
  const verdict = sourced && fresh ? "PASS" : sourced ? "UNCERTAIN" : "FAIL";
  return {
    id: `audit_${claim.id}`, targetId: claim.id, verdict,
    reason: `deterministic_source_check=${sourced};freshness_under_30d=${fresh}`,
    evidenceRefs: claim.sourceRefs, createdAt: new Date().toISOString(), strategy: "deterministic provenance + freshness; not same-model re-prompt"
  };
}

export function createContentDraft(state: SystemState): { id: string; text: string; sourceRefs: string[] } {
  const verified = state.knowledge.filter((k) => k.status === "VERIFIED_KNOWLEDGE");
  if (verified.length === 0) throw new Error("CMO_REQUIRES_VERIFIED_INPUT");
  const item = verified[0]!;
  return { id: `content_${item.id}`, text: `Draft based on verified evidence: ${item.statement}`, sourceRefs: [item.id] };
}

export function createCeoDecision(state: SystemState, hotCount: number, anomaly: boolean): Decision {
  const priority = anomaly ? "Recover funnel conversion anomaly" : hotCount > 0 ? "Convert highest-intent leads" : "Maintain verified operating cadence";
  const assignments: Decision["assignments"] = anomaly
    ? [{ role: "DATA", task: "isolate anomaly segment" }, { role: "SALES", task: "protect hot lead follow-up" }]
    : [{ role: "SALES", task: "work verified hot leads" }];
  return {
    id: `decision_${state.decisions.length + 1}`, createdAt: new Date().toISOString(), priority,
    rationale: `verified_hot_leads=${hotCount};funnel_anomaly=${anomaly}`,
    evidenceRefs: [...state.knowledge.filter((k) => k.status === "VERIFIED_KNOWLEDGE").map((k) => k.id), ...state.metrics.slice(-1).map((m) => m.id)],
    assignments, auditVerdict: "PASS"
  };
}

export function devDiagnoseIncident(state: SystemState): { status: "DIAGNOSED" | "NONE"; reason: string } {
  const incident = state.events.find((e) => e.type === "incident");
  return incident ? { status: "DIAGNOSED", reason: `isolated diagnosis for ${incident.id}; code mutation requires isolated branch` } : { status: "NONE", reason: "no incident" };
}

export function makeTask(input: Pick<Task, "id" | "type" | "priority" | "risk" | "requestedBy" | "input"> & { createdAt?: string }): Task {
  return { ...input, status: "QUEUED", createdAt: input.createdAt ?? new Date().toISOString() };
}
