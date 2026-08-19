import type { EffectAdapter } from "./kernel.js";

export class NotionEffectAdapter implements EffectAdapter {
  readonly connector = "notion";
  readonly operation = "upsert-page";
  constructor(private readonly token: string, private readonly fetcher: typeof fetch = fetch) { if (!token) throw new Error("NOTION_WRITE_TOKEN_REQUIRED"); }
  async execute(parameters: Record<string, unknown>, idempotencyKey: string): Promise<Record<string, unknown>> {
    const pageId = String(parameters.pageId ?? "");
    const body = parameters.body;
    if (!/^[A-Za-z0-9-]+$/.test(pageId) || typeof body !== "object" || body === null) throw new Error("NOTION_EFFECT_SCHEMA_INVALID");
    const response = await this.fetcher(`https://api.notion.com/v1/pages/${encodeURIComponent(pageId)}`, {
      method: "PATCH", headers: { authorization: `Bearer ${this.token}`, "content-type": "application/json", "notion-version": "2025-09-03", "idempotency-key": idempotencyKey }, body: JSON.stringify(body)
    });
    if (response.status === 429) throw new Error("FREE_QUOTA_EXHAUSTED_OR_RATE_LIMIT_429");
    if (!response.ok) throw new Error(`NOTION_EFFECT_HTTP_${response.status}`);
    return await response.json() as Record<string, unknown>;
  }
}

export class GitHubIssueCommentEffectAdapter implements EffectAdapter {
  readonly connector = "github";
  readonly operation = "issue-comment";
  constructor(private readonly token: string, private readonly fetcher: typeof fetch = fetch) { if (!token) throw new Error("GITHUB_WRITE_TOKEN_REQUIRED"); }
  async execute(parameters: Record<string, unknown>, idempotencyKey: string): Promise<Record<string, unknown>> {
    const owner = String(parameters.owner ?? ""), repo = String(parameters.repo ?? ""), issue = Number(parameters.issue), body = String(parameters.body ?? "");
    if (!/^[A-Za-z0-9_.-]+$/.test(owner) || !/^[A-Za-z0-9_.-]+$/.test(repo) || !Number.isInteger(issue) || issue <= 0 || !body) throw new Error("GITHUB_EFFECT_SCHEMA_INVALID");
    const response = await this.fetcher(`https://api.github.com/repos/${owner}/${repo}/issues/${issue}/comments`, {
      method: "POST", headers: { authorization: `Bearer ${this.token}`, accept: "application/vnd.github+json", "content-type": "application/json", "x-github-api-version": "2022-11-28", "idempotency-key": idempotencyKey }, body: JSON.stringify({ body })
    });
    if (response.status === 429 || response.status >= 500) throw new Error(`FREE_QUOTA_EXHAUSTED_OR_TRANSIENT_${response.status}`);
    if (!response.ok) throw new Error(`GITHUB_EFFECT_HTTP_${response.status}`);
    return await response.json() as Record<string, unknown>;
  }
}
