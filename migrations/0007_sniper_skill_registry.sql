-- ORDER-004 governed skill registry.
-- External skill sources are never enabled solely by discovery/popularity.

CREATE TABLE IF NOT EXISTS sniper_skill_registry (
  source_id TEXT PRIMARY KEY,
  revision_pin TEXT NOT NULL,
  benchmark_score REAL NOT NULL,
  health TEXT NOT NULL,
  admission_state TEXT NOT NULL,
  admission_reasons_json TEXT NOT NULL,
  verified_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sniper_skill_benchmarks (
  benchmark_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  revision_pin TEXT NOT NULL,
  role TEXT NOT NULL,
  capability TEXT NOT NULL,
  score REAL NOT NULL,
  evidence_refs_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES sniper_skill_registry(source_id)
);
CREATE INDEX IF NOT EXISTS idx_sniper_skill_benchmarks_source
  ON sniper_skill_benchmarks(source_id, created_at DESC);
