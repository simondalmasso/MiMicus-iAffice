-- ORDER-004 private demo lifecycle.
-- Demos are evidence-backed, private, non-production artifacts and require AUD before commercial use.

CREATE TABLE IF NOT EXISTS sniper_demo_jobs (
  job_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  service_pack_id TEXT NOT NULL,
  evidence_refs_json TEXT NOT NULL,
  requested_deliverables_json TEXT NOT NULL,
  executor_id TEXT NOT NULL,
  executor_class TEXT NOT NULL,
  zero_cost_verified INTEGER NOT NULL DEFAULT 0,
  state TEXT NOT NULL,
  decision_reasons_json TEXT NOT NULL,
  artifact_manifest_json TEXT,
  audit_verdict TEXT,
  audit_evidence_refs_json TEXT NOT NULL DEFAULT '[]',
  error_code TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(case_id) REFERENCES sniper_opportunities(id)
);
CREATE INDEX IF NOT EXISTS idx_sniper_demo_jobs_case
  ON sniper_demo_jobs(case_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sniper_demo_jobs_state
  ON sniper_demo_jobs(state, updated_at DESC);
