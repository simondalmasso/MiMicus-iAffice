-- ORDER-004 canonical observability fabric.
-- Metadata/digests only by default. Raw prompts/responses are intentionally excluded.

CREATE TABLE IF NOT EXISTS sniper_telemetry_spans (
  trace_id TEXT NOT NULL,
  span_id TEXT PRIMARY KEY,
  parent_span_id TEXT,
  case_id TEXT,
  agent_role TEXT,
  stage TEXT,
  kind TEXT NOT NULL,
  operation TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT NOT NULL,
  latency_ms INTEGER NOT NULL,
  provider TEXT,
  model TEXT,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  actual_cost_usd REAL NOT NULL DEFAULT 0,
  error_code TEXT,
  input_digest TEXT,
  output_digest TEXT,
  attributes_json TEXT NOT NULL,
  content_policy TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sniper_telemetry_trace
  ON sniper_telemetry_spans(trace_id, started_at ASC);
CREATE INDEX IF NOT EXISTS idx_sniper_telemetry_case
  ON sniper_telemetry_spans(case_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sniper_telemetry_agent
  ON sniper_telemetry_spans(agent_role, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sniper_telemetry_status
  ON sniper_telemetry_spans(status, started_at DESC);

CREATE TABLE IF NOT EXISTS sniper_telemetry_exporters (
  exporter_id TEXT PRIMARY KEY,
  provider_id TEXT NOT NULL,
  state TEXT NOT NULL,
  endpoint_hint TEXT,
  standard TEXT NOT NULL,
  zero_cost_verified INTEGER NOT NULL DEFAULT 0,
  license_verified INTEGER NOT NULL DEFAULT 0,
  last_health_at TEXT,
  updated_at TEXT NOT NULL
);
