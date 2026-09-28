-- ORDER-004 governed market discovery.
-- Discovery adapters remain disabled until source runtime and target terms are verified.

CREATE TABLE IF NOT EXISTS sniper_discovery_sources (
  source_id TEXT PRIMARY KEY,
  revision_pin TEXT NOT NULL,
  zero_cost_verified INTEGER NOT NULL DEFAULT 0,
  target_terms_verified INTEGER NOT NULL DEFAULT 0,
  automation_allowed INTEGER NOT NULL DEFAULT 0,
  health TEXT NOT NULL,
  admission_state TEXT NOT NULL,
  admission_reasons_json TEXT NOT NULL,
  evidence_refs_json TEXT NOT NULL,
  verified_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sniper_discovery_jobs (
  job_id TEXT PRIMARY KEY,
  locality TEXT NOT NULL,
  categories_json TEXT NOT NULL,
  max_candidates INTEGER NOT NULL,
  source_ids_json TEXT NOT NULL,
  state TEXT NOT NULL,
  decision_reasons_json TEXT NOT NULL,
  found_count INTEGER NOT NULL DEFAULT 0,
  deduped_count INTEGER NOT NULL DEFAULT 0,
  case_count INTEGER NOT NULL DEFAULT 0,
  error_code TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sniper_discovery_jobs_state
  ON sniper_discovery_jobs(state, updated_at DESC);

CREATE TABLE IF NOT EXISTS sniper_discovery_findings (
  finding_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  business_key TEXT NOT NULL,
  business_name TEXT NOT NULL,
  category TEXT NOT NULL,
  locality TEXT NOT NULL,
  website_url TEXT,
  contacts_json TEXT NOT NULL,
  demand_json TEXT NOT NULL,
  raw_evidence_digest TEXT,
  observed_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(job_id) REFERENCES sniper_discovery_jobs(job_id)
);
CREATE INDEX IF NOT EXISTS idx_sniper_discovery_findings_job
  ON sniper_discovery_findings(job_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sniper_discovery_findings_business
  ON sniper_discovery_findings(business_key);

CREATE TABLE IF NOT EXISTS sniper_digital_audits (
  audit_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  finding_id TEXT NOT NULL,
  evidence_ref TEXT NOT NULL,
  audit_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(job_id) REFERENCES sniper_discovery_jobs(job_id),
  FOREIGN KEY(finding_id) REFERENCES sniper_discovery_findings(finding_id)
);
CREATE INDEX IF NOT EXISTS idx_sniper_digital_audits_finding
  ON sniper_digital_audits(finding_id, created_at DESC);
