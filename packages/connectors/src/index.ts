import { sha256, stableId } from "../../core/src/hash.js";
import type { ActionRecord, AgentRole, BusinessEvent, EvidenceTaxonomy } from "../../core/src/types.js";
import { PolicyEngine } from "../../policy/src/policy.js";

export interface ConnectorResult<T> { ok: boolean; data?: T; cursor?: string; etag?: string; retryAfterMs?: number; error?: string; }

export class WebhookIngestConnector {
  constructor(private readonly secret: string, private readonly maxBytes = 64 * 1024) {
    if (!secret) throw new Error("WEBHOOK_SECRET_REQUIRED");
  }

  async authenticate(raw: string, providedSignature: string): Promise<boolean> {
    const expected = await sha256(`${this.secret}:${raw}`);
    if (expected.length !== providedSignature.length) return false;
    let diff = 0;
    for (let i = 0; i < expected.length; i += 1) diff |= expected.charCodeAt(i) ^ providedSignature.charCodeAt(i);
    return diff === 0;
  }

  async parse(raw: string, signature: string, now = new Date().toISOString()): Promise<BusinessEvent> {
    if (new TextEncoder().encode(raw).byteLength > this.maxBytes) throw new Error("WEBHOOK_BODY_TOO_LARGE");
    if (!(await this.authenticate(raw, signature))) throw new Error("WEBHOOK_AUTH_FAILED");
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const required = ["type", "idempotencyKey", "payload"];
    for (const key of required) if (!(key in parsed)) throw new Error(`WEBHOOK_SCHEMA_INVALID:${key}`);
    if (typeof parsed.payload !== "object" || parsed.payload === null || Array.isArray(parsed.payload)) throw new Error("WEBHOOK_SCHEMA_INVALID:payload");
    const material = {
      type: String(parsed.type), idempotencyKey: String(parsed.idempotencyKey), payload: parsed.payload as Record<string, unknown>,
      observedAt: typeof parsed.observedAt === "string" ? parsed.observedAt : now,
      createdAt: now, source: "webhook", actor: "connector:webhook", trust: "AUTHORIZED_EXTERNAL" as const,
      evidenceType: "LIVE_EXTERNAL" as EvidenceTaxonomy
    };
    const hash = await sha256(material);
    return { ...material, id: await stableId("evt", { key: material.idempotencyKey, hash }), hash };
  }
}

function isPrivateIpv4(host: string): boolean {
  const m = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!m) return false;
  const parts = m.slice(1).map(Number);
  if (parts.some((x) => x < 0 || x > 255)) return true;
  const [a, b] = parts as [number, number, number, number];
  return a === 10 || a === 127 || a === 0 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || a >= 224;
}

export function validatePublicUrl(raw: string, allowHosts: readonly string[]): URL {
  const url = new URL(raw);
  if (url.protocol !== "https:") throw new Error("SSRF_SCHEME_DENIED");
  const host = url.hostname.toLowerCase().replace(/\.$/, "");
  if (host === "localhost" || host === "localhost.localdomain" || host.endsWith(".local") || host === "::1" || host.startsWith("[") || isPrivateIpv4(host)) throw new Error("SSRF_PRIVATE_NETWORK_DENIED");
  if (!allowHosts.some((allowed) => host === allowed || host.endsWith(`.${allowed}`))) throw new Error("SSRF_HOST_NOT_ALLOWLISTED");
  if (url.username || url.password) throw new Error("SSRF_CREDENTIAL_URL_DENIED");
  return url;
}

export class GenericRESTReadConnector {
  constructor(private readonly allowHosts: readonly string[], private readonly fetcher: typeof fetch = fetch) {}
  async get<T>(rawUrl: string, options: { etag?: string; cursor?: string; maxRetries?: number } = {}): Promise<ConnectorResult<T>> {
    const url = validatePublicUrl(rawUrl, this.allowHosts);
    if (options.cursor) url.searchParams.set("cursor", options.cursor);
    const maxRetries = options.maxRetries ?? 2;
    for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
      const headers = new Headers({ accept: "application/json" });
      if (options.etag) headers.set("if-none-match", options.etag);
      const response = await this.fetcher(url, { method: "GET", headers, redirect: "error" });
      if (response.status === 304) return options.etag ? { ok: true, etag: options.etag } : { ok: true };
      if (response.status === 429 || response.status >= 500) {
        const retryAfter = Number(response.headers.get("retry-after") ?? "0");
        if (attempt === maxRetries) return { ok: false, error: `HTTP_${response.status}`, retryAfterMs: retryAfter * 1000 };
        continue;
      }
      if (!response.ok) return { ok: false, error: `HTTP_${response.status}` };
      const data = await response.json() as T;
      const etag = response.headers.get("etag"), cursor = response.headers.get("x-next-cursor");
      return { ok: true, data, ...(etag ? { etag } : {}), ...(cursor ? { cursor } : {}) };
    }
    return { ok: false, error: "UNREACHABLE" };
  }
}

export class GitHubConnector {
  constructor(private readonly rest: GenericRESTReadConnector, private readonly policy: PolicyEngine) {}
  private readAllowed(): boolean { return this.policy.decision("READ_PUBLIC", { sourceAllowlisted: true }) === "ALLOW"; }
  async readRepo(owner: string, repo: string): Promise<ConnectorResult<Record<string, unknown>>> {
    if (!this.readAllowed()) return { ok: false, error: "POLICY_DENIED" };
    return this.rest.get(`https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`);
  }
  async readIssue(owner: string, repo: string, issueNumber: number): Promise<ConnectorResult<Record<string, unknown>>> {
    if (!this.readAllowed()) return { ok: false, error: "POLICY_DENIED" };
    if (!Number.isInteger(issueNumber) || issueNumber <= 0) return { ok: false, error: "GITHUB_ISSUE_NUMBER_INVALID" };
    return this.rest.get(`https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/issues/${issueNumber}`);
  }
  async readPullRequest(owner: string, repo: string, prNumber: number): Promise<ConnectorResult<Record<string, unknown>>> {
    if (!this.readAllowed()) return { ok: false, error: "POLICY_DENIED" };
    if (!Number.isInteger(prNumber) || prNumber <= 0) return { ok: false, error: "GITHUB_PR_NUMBER_INVALID" };
    return this.rest.get(`https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/pulls/${prNumber}`);
  }
  writeCapability(requestedBy: AgentRole): ActionRecord {
    const policyDecision = this.policy.decision("CODE_WRITE", { isolatedCodeWorkspace: true });
    return { id: `github-write-${Date.now()}`, actionClass: "CODE_WRITE", payload: { scope: "isolated-branch", externalEffect: false }, requestedBy, policyDecision, status: policyDecision === "ALLOW" ? "APPROVED" : "BLOCKED", createdAt: new Date().toISOString() };
  }
}

export class NotionMirrorConnector {
  private cursor = "";
  constructor(private readonly minIntervalMs = 500, private readonly fetcher: typeof fetch = fetch, private readonly readToken?: string) {}
  checkpoint(): string { return this.cursor; }
  throttleMs(lastRequestAt: number, now: number): number { return Math.max(0, this.minIntervalMs - (now - lastRequestAt)); }
  async readPage(pageId: string, options: { lastRequestAt?: number; now?: number } = {}): Promise<ConnectorResult<Record<string, unknown>>> {
    if (!/^[A-Za-z0-9-]+$/.test(pageId)) return { ok: false, error: "NOTION_PAGE_ID_INVALID" };
    if (!this.readToken) return { ok: false, error: "NOTION_READ_CAPABILITY_NOT_CONFIGURED" };
    const delay = this.throttleMs(options.lastRequestAt ?? 0, options.now ?? Date.now());
    if (delay > 0) await new Promise<void>((resolve) => setTimeout(resolve, delay));
    const response = await this.fetcher(`https://api.notion.com/v1/pages/${encodeURIComponent(pageId)}`, { method: "GET", headers: { authorization: `Bearer ${this.readToken}`, accept: "application/json", "notion-version": "2025-09-03" }, redirect: "error" });
    if (response.status === 429) return { ok: false, error: "HTTP_429", retryAfterMs: Number(response.headers.get("retry-after") ?? "1") * 1000 };
    if (!response.ok) return { ok: false, error: `HTTP_${response.status}` };
    return { ok: true, data: await response.json() as Record<string, unknown> };
  }
  planUpsert(pageId: string, payload: Record<string, unknown>, cursor: string): { connector: string; operation: string; target: string; canonicalParameters: Record<string, unknown>; cursor: string } {
    if (!/^[A-Za-z0-9-]+$/.test(pageId)) throw new Error("NOTION_PAGE_ID_INVALID");
    this.cursor = cursor;
    return { connector: "notion", operation: "upsert-page", target: pageId, canonicalParameters: structuredClone(payload), cursor };
  }
}

export class CSVImportExportConnector {
  parse(csv: string): Array<Record<string, string>> {
    const lines = csv.trim().split(/\r?\n/); if (lines.length === 0 || !lines[0]) return [];
    const headers = this.parseLine(lines[0]);
    return lines.slice(1).filter(Boolean).map((line) => { const values = this.parseLine(line); return Object.fromEntries(headers.map((h, i) => [h, values[i] ?? ""])); });
  }
  stringify(rows: Array<Record<string, unknown>>): string {
    if (rows.length === 0) return ""; const headers = Object.keys(rows[0]!);
    return [headers, ...rows.map((row) => headers.map((h) => String(row[h] ?? "")))].map((cols) => cols.map(this.escape).join(",")).join("\n");
  }
  private parseLine(line: string): string[] {
    const out: string[] = []; let current = "", quoted = false;
    for (let i = 0; i < line.length; i += 1) { const ch = line[i]!; if (ch === '"' && line[i + 1] === '"' && quoted) { current += '"'; i += 1; } else if (ch === '"') quoted = !quoted; else if (ch === "," && !quoted) { out.push(current); current = ""; } else current += ch; }
    out.push(current); return out;
  }
  private escape(value: string): string { return /[",\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value; }
}

export interface SwarmRuntimeEnvelope { taskId: string; authority: string[]; evidenceRefs: string[]; budget: Record<string, number>; payload: Record<string, unknown>; }
export interface SwarmRuntimeResult { taskId: string; claims: string[]; provenance: string[]; auditVerdict: "PASS" | "FAIL" | "UNCERTAIN"; }
export class LocalSwarmRuntimeAdapter {
  async dispatch(envelope: SwarmRuntimeEnvelope): Promise<SwarmRuntimeResult> { if (envelope.authority.includes("MONEY_MUTATION")) throw new Error("SWARM_AUTHORITY_DENIED"); return { taskId: envelope.taskId, claims: [`handled:${String(envelope.payload.kind ?? "task")}`], provenance: envelope.evidenceRefs, auditVerdict: "PASS" }; }
}

export function redactSecrets(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactSecrets);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([k, v]) => [/authorization/i, /cookie/i, /token/i, /secret/i, /password/i].some((p) => p.test(k)) ? [k, "[REDACTED]"] : [k, redactSecrets(v)]));
  if (typeof value === "string") return value.replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [REDACTED]");
  return value;
}
