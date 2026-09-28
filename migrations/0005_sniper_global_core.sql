-- ORDER-004 global decision core.
-- Stores company-level strategy and portfolio allocation separately from per-case cognition.

CREATE TABLE IF NOT EXISTS sniper_global_goals (
  goal_id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  weight REAL NOT NULL,
  status TEXT NOT NULL,
  constraints_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sniper_global_decisions (
  decision_id TEXT PRIMARY KEY,
  portfolio_hash TEXT NOT NULL,
  policy_json TEXT NOT NULL,
  ranked_cases_json TEXT NOT NULL,
  active_cases_json TEXT NOT NULL,
  deferred_cases_json TEXT NOT NULL,
  human_attention_json TEXT NOT NULL,
  system1_json TEXT,
  reasons_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sniper_global_decisions_created
  ON sniper_global_decisions(created_at DESC);

CREATE TABLE IF NOT EXISTS sniper_global_allocations (
  allocation_id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  owner_role TEXT NOT NULL,
  objective TEXT NOT NULL,
  priority_score REAL NOT NULL,
  state TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(decision_id) REFERENCES sniper_global_decisions(decision_id)
);
CREATE INDEX IF NOT EXISTS idx_sniper_global_alloc_case
  ON sniper_global_allocations(case_id, updated_at DESC);
