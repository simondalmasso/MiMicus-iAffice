-- ORDER-004 governed cloud executor registry.
-- Heavy jobs may run outside Cloudflare, but canonical state remains in D1/control plane.

CREATE TABLE IF NOT EXISTS sniper_executor_registry (
  executor_id TEXT PRIMARY KEY,
  endpoint TEXT,
  cost_class TEXT NOT NULL,
  zero_cost_verified INTEGER NOT NULL DEFAULT 0,
  health TEXT NOT NULL,
  admission_state TEXT NOT NULL,
  admission_reasons_json TEXT NOT NULL,
  evidence_refs_json TEXT NOT NULL,
  last_health_at TEXT,
  verified_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sniper_executor_runs (
  run_id TEXT PRIMARY KEY,
  executor_id TEXT NOT NULL,
  job_kind TEXT NOT NULL,
  job_id TEXT NOT NULL,
  case_id TEXT,
  state TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  result_digest TEXT,
  started_at TEXT,
  completed_at TEXT,
  error_code TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(executor_id) REFERENCES sniper_executor_registry(executor_id)
);
CREATE INDEX IF NOT EXISTS idx_sniper_executor_runs_executor
  ON sniper_executor_runs(executor_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sniper_executor_runs_job
  ON sniper_executor_runs(job_kind, job_id);
