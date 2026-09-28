import type { OperatingStageId } from "./operatingModel.js";

export type TelemetryAdoption = "RUNTIME_AUTHORITY" | "ADAPTER_CANDIDATE" | "REFERENCE_ONLY" | "REJECT";

export interface ObservabilityReference {
  id:
    | "ARIA_TELEMETRY_FABRIC"
    | "LANGFUSE"
    | "AGENTOPS"
    | "LAMINAR"
    | "DIFY"
    | "FLOWISE"
    | "PHOENIX"
    | "OPENLIT"
    | "HELICONE"
    | "AUTOGEN_STUDIO"
    | "OBSERVRA";
  source: string;
  license: string | null;
  adoption: TelemetryAdoption;
  standards: string[];
  notes: string[];
}

export const OBSERVABILITY_REFERENCES: ObservabilityReference[] = [
  {
    id: "ARIA_TELEMETRY_FABRIC",
    source: "internal://packages/sniper/src/telemetry.ts",
    license: null,
    adoption: "RUNTIME_AUTHORITY",
    standards: ["OTEL_COMPATIBLE", "OPENINFERENCE_COMPATIBLE"],
    notes: ["Canonical telemetry contract and dashboard source of truth."]
  },
  {
    id: "LANGFUSE",
    source: "https://github.com/langfuse/langfuse",
    license: "MIT-core with separately licensed EE directories",
    adoption: "REFERENCE_ONLY",
    standards: ["TRACING"],
    notes: ["Strong tracing/self-host reference; license surface must be pinned before any code reuse."]
  },
  {
    id: "AGENTOPS",
    source: "https://github.com/AgentOps-AI/agentops",
    license: "MIT",
    adoption: "REFERENCE_ONLY",
    standards: ["AGENT_TRACING"],
    notes: ["Useful session replay and agent health patterns; not required as runtime authority."]
  },
  {
    id: "LAMINAR",
    source: "https://github.com/lmnr-ai/lmnr",
    license: "Apache-2.0",
    adoption: "ADAPTER_CANDIDATE",
    standards: ["OpenTelemetry"],
    notes: ["OTel-native agent observability, realtime trace viewing and SQL over traces."]
  },
  {
    id: "DIFY",
    source: "https://github.com/langgenius/dify",
    license: "Modified Apache-2.0 with additional conditions",
    adoption: "REFERENCE_ONLY",
    standards: ["WORKFLOW_OBSERVABILITY"],
    notes: ["License includes multi-tenant restrictions; do not adopt as platform dependency."]
  },
  {
    id: "FLOWISE",
    source: "https://github.com/FlowiseAI/Flowise",
    license: "Apache-2.0 core with commercial portions",
    adoption: "REJECT",
    standards: ["VISUAL_AGENT_FLOW"],
    notes: ["Upstream repository is archived; do not add as a new dependency."]
  },
  {
    id: "PHOENIX",
    source: "https://github.com/Arize-ai/phoenix",
    license: "Elastic License 2.0",
    adoption: "REFERENCE_ONLY",
    standards: ["OpenTelemetry", "OpenInference"],
    notes: ["Excellent OpenInference reference, but ELv2 restricts hosted/managed-service use."]
  },
  {
    id: "OPENLIT",
    source: "https://github.com/openlit/openlit",
    license: "Apache-2.0",
    adoption: "ADAPTER_CANDIDATE",
    standards: ["OpenTelemetry"],
    notes: ["Strong OTel-native traces, costs, tokens, tools and agent steps."]
  },
  {
    id: "HELICONE",
    source: "https://github.com/Helicone/helicone",
    license: "Apache-2.0",
    adoption: "REFERENCE_ONLY",
    standards: ["LLM_GATEWAY", "TRACING"],
    notes: ["Useful cost/latency tracing patterns; its gateway role overlaps with aria-models."]
  },
  {
    id: "AUTOGEN_STUDIO",
    source: "https://github.com/microsoft/autogen",
    license: "See upstream component licenses",
    adoption: "REJECT",
    standards: ["AGENT_SESSION_UI"],
    notes: ["AutoGen is in maintenance mode and recommends Microsoft Agent Framework for new projects."]
  },
  {
    id: "OBSERVRA",
    source: "https://github.com/open-agent-ai-security/observra",
    license: "Apache-2.0",
    adoption: "ADAPTER_CANDIDATE",
    standards: ["OpenTelemetry", "CIM"],
    notes: ["Framework-agnostic normalized agent telemetry with OTel export."]
  }
];

export function assertSingleTelemetryAuthority(refs: ObservabilityReference[]): void {
  const runtime = refs.filter(x => x.adoption === "RUNTIME_AUTHORITY");
  if (runtime.length !== 1 || runtime[0]?.id !== "ARIA_TELEMETRY_FABRIC") {
    throw new Error("TELEMETRY_RUNTIME_AUTHORITY_CONFLICT");
  }
}

export type TelemetryKind =
  | "AGENT"
  | "LLM"
  | "TOOL"
  | "DECISION"
  | "MEMORY"
  | "EFFECT"
  | "JOB"
  | "POLICY";

export type TelemetryStatus = "OK" | "ERROR" | "DENIED" | "ABSTAINED";

export interface TelemetrySpanInput {
  traceId: string;
  spanId: string;
  parentSpanId: string | null;
  caseId: string | null;
  agentRole: string | null;
  stage: OperatingStageId | "GLOBAL" | null;
  kind: TelemetryKind;
  operation: string;
  status: TelemetryStatus;
  startedAt: string;
  endedAt: string;
  provider: string | null;
  model: string | null;
  inputTokens: number;
  outputTokens: number;
  actualCostUsd: number;
  errorCode: string | null;
  inputDigest: string | null;
  outputDigest: string | null;
  attributes: Record<string, unknown>;
}

export interface TelemetrySpan extends TelemetrySpanInput {
  latencyMs: number;
  contentPolicy: "METADATA_ONLY";
}

function finiteNonNegative(value: number, code: string): number {
  if (!Number.isFinite(value) || value < 0) throw new Error(code);
  return value;
}

export function normalizeTelemetrySpan(input: TelemetrySpanInput): TelemetrySpan {
  if (!input.traceId || !input.spanId || !input.operation) throw new Error("TELEMETRY_IDENTITY_REQUIRED");
  const start = Date.parse(input.startedAt);
  const end = Date.parse(input.endedAt);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) throw new Error("TELEMETRY_TIME_INVALID");
  if (input.actualCostUsd > 0) throw new Error("TELEMETRY_PAID_EXECUTION_FORBIDDEN");
  finiteNonNegative(input.actualCostUsd, "TELEMETRY_COST_INVALID");
  finiteNonNegative(input.inputTokens, "TELEMETRY_INPUT_TOKENS_INVALID");
  finiteNonNegative(input.outputTokens, "TELEMETRY_OUTPUT_TOKENS_INVALID");
  return {
    ...input,
    attributes: structuredClone(input.attributes),
    latencyMs: end - start,
    contentPolicy: "METADATA_ONLY"
  };
}

export interface TelemetryTreeNode {
  span: TelemetrySpan;
  children: TelemetryTreeNode[];
}

export function buildTraceTree(spans: TelemetrySpan[]): TelemetryTreeNode[] {
  const byId = new Map<string, TelemetryTreeNode>();
  for (const span of spans) byId.set(span.spanId, { span: structuredClone(span), children: [] });
  const roots: TelemetryTreeNode[] = [];
  for (const span of spans) {
    const node = byId.get(span.spanId)!;
    const parent = span.parentSpanId ? byId.get(span.parentSpanId) : undefined;
    if (parent && parent !== node) parent.children.push(node);
    else roots.push(node);
  }
  const sort = (nodes: TelemetryTreeNode[]): void => {
    nodes.sort((a,b) => Date.parse(a.span.startedAt) - Date.parse(b.span.startedAt) || a.span.spanId.localeCompare(b.span.spanId));
    for (const n of nodes) sort(n.children);
  };
  sort(roots);
  return roots;
}

export function summarizeTelemetry(spans: TelemetrySpan[]) {
  const latencies = spans.map(x=>x.latencyMs).sort((a,b)=>a-b);
  const p95Index = latencies.length === 0 ? -1 : Math.max(0, Math.ceil(latencies.length * 0.95) - 1);
  const byAgent: Record<string,{spans:number;errors:number;tokens:number}> = {};
  for(const span of spans){
    const key=span.agentRole ?? "SYSTEM";
    const row=byAgent[key] ?? {spans:0,errors:0,tokens:0};
    row.spans += 1;
    if(span.status === "ERROR") row.errors += 1;
    row.tokens += span.inputTokens + span.outputTokens;
    byAgent[key]=row;
  }
  return {
    spans: spans.length,
    traces: new Set(spans.map(x=>x.traceId)).size,
    errors: spans.filter(x=>x.status==="ERROR").length,
    denied: spans.filter(x=>x.status==="DENIED").length,
    abstained: spans.filter(x=>x.status==="ABSTAINED").length,
    inputTokens: spans.reduce((s,x)=>s+x.inputTokens,0),
    outputTokens: spans.reduce((s,x)=>s+x.outputTokens,0),
    actualCostUsd: spans.reduce((s,x)=>s+x.actualCostUsd,0),
    p95LatencyMs: p95Index >= 0 ? latencies[p95Index]! : 0,
    byAgent
  };
}
