-- ORDER-004 durable commercial safety/effect guard.
-- Revalidated both before ActionIntent creation and inside aria-effects.

CREATE TABLE IF NOT EXISTS sniper_contact_controls (
  case_id TEXT PRIMARY KEY,
  do_not_contact INTEGER NOT NULL DEFAULT 0,
  explicit_refusal INTEGER NOT NULL DEFAULT 0,
  reason TEXT,
  evidence_refs_json TEXT NOT NULL DEFAULT '[]',
  updated_at TEXT NOT NULL,
  FOREIGN KEY(case_id) REFERENCES sniper_opportunities(id)
);

CREATE TABLE IF NOT EXISTS sniper_commercial_effects (
  effect_id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  operation TEXT NOT NULL,
  target TEXT NOT NULL,
  intent_id TEXT NOT NULL,
  receipt_id TEXT NOT NULL,
  state TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(intent_id),
  FOREIGN KEY(case_id) REFERENCES sniper_opportunities(id)
);
CREATE INDEX IF NOT EXISTS idx_sniper_commercial_effects_case_time
  ON sniper_commercial_effects(case_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sniper_commercial_effects_operation_time
  ON sniper_commercial_effects(operation, created_at DESC);
