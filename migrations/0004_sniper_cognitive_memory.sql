-- ORDER-004 cognitive memory: working, episodic, semantic/procedural promotion and decision trace.

CREATE TABLE IF NOT EXISTS sniper_memory_episodes (
  episode_id TEXT PRIMARY KEY,
  opportunity_id TEXT NOT NULL,
  agent_role TEXT NOT NULL,
  tactic_id TEXT NOT NULL,
  observation TEXT NOT NULL,
  outcome TEXT NOT NULL,
  audited INTEGER NOT NULL DEFAULT 0,
  evidence_refs_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sniper_memory_episode_opp
  ON sniper_memory_episodes(opportunity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sniper_memory_episode_tactic
  ON sniper_memory_episodes(tactic_id, created_at DESC);

CREATE TABLE IF NOT EXISTS sniper_decision_trace (
  decision_id TEXT PRIMARY KEY,
  opportunity_id TEXT NOT NULL,
  context_json TEXT NOT NULL,
  selected_move TEXT NOT NULL,
  selected_tactic_id TEXT NOT NULL,
  selected_score REAL NOT NULL,
  alternatives_json TEXT NOT NULL,
  reasons_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sniper_decision_trace_opp
  ON sniper_decision_trace(opportunity_id, created_at DESC);

CREATE TABLE IF NOT EXISTS sniper_semantic_patterns (
  pattern_id TEXT PRIMARY KEY,
  scope_key TEXT NOT NULL,
  statement TEXT NOT NULL,
  confidence REAL NOT NULL,
  evidence_refs_json TEXT NOT NULL,
  support_count INTEGER NOT NULL DEFAULT 1,
  contradiction_count INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sniper_semantic_scope
  ON sniper_semantic_patterns(scope_key, confidence DESC);
