const encoder = new TextEncoder();

export function canonicalize(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .filter(([, v]) => v !== undefined)
    .sort(([a], [b]) => a.localeCompare(b));
  return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${canonicalize(v)}`).join(",")}}`;
}

export async function sha256(value: unknown): Promise<string> {
  const bytes = encoder.encode(typeof value === "string" ? value : canonicalize(value));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function stableId(prefix: string, value: unknown): Promise<string> {
  return `${prefix}_${(await sha256(value)).slice(0, 24)}`;
}

export function nowIso(clock: () => Date = () => new Date()): string {
  return clock().toISOString();
}
