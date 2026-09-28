-- ORDER-004 Sniper autonomous revenue engine.
-- Append-only/operational tables are separate from canonical ORDER-002 memory.
-- External effects remain governed by ActionIntent -> Policy -> approval -> aria-effects.

CREATE TABLE IF NOT EXISTS sniper_opportunities (
  id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL,
  business_name TEXT NOT NULL,
  category TEXT NOT NULL,
  locality TEXT NOT NULL,
  status TEXT NOT NULL,
  score INTEGER NOT NULL,
  signal_json TEXT NOT NULL,
  reasons_json TEXT NOT NULL,
  offer_json TEXT NOT NULL,
  persuasion_json TEXT NOT NULL,
  contacts_json TEXT NOT NULL,
  evidence_refs_json TEXT NOT NULL,
  next_owner TEXT NOT NULL,
  next_action TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sniper_opportunities_status_score
  ON sniper_opportunities(status, score DESC);
CREATE INDEX IF NOT EXISTS idx_sniper_opportunities_business
  ON sniper_opportunities(business_id);

CREATE TABLE IF NOT EXISTS sniper_negotiations (
  id TEXT PRIMARY KEY,
  opportunity_id TEXT NOT NULL,
  state TEXT NOT NULL,
  current_offer_ars INTEGER,
  floor_price_ars INTEGER,
  objections_json TEXT NOT NULL,
  concessions_json TEXT NOT NULL,
  next_action TEXT NOT NULL,
  human_gate INTEGER NOT NULL DEFAULT 0,
  human_gate_reasons_json TEXT NOT NULL,
  last_contact_at TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(opportunity_id) REFERENCES sniper_opportunities(id)
);
CREATE INDEX IF NOT EXISTS idx_sniper_negotiations_opportunity
  ON sniper_negotiations(opportunity_id);

CREATE TABLE IF NOT EXISTS sniper_deliveries (
  id TEXT PRIMARY KEY,
  opportunity_id TEXT NOT NULL,
  service_kind TEXT NOT NULL,
  state TEXT NOT NULL,
  acceptance_json TEXT NOT NULL,
  artifact_refs_json TEXT NOT NULL,
  due_at TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(opportunity_id) REFERENCES sniper_opportunities(id)
);

CREATE TABLE IF NOT EXISTS sniper_payments (
  id TEXT PRIMARY KEY,
  opportunity_id TEXT NOT NULL,
  state TEXT NOT NULL,
  amount_ars INTEGER NOT NULL,
  provider TEXT NOT NULL,
  external_reference TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(opportunity_id) REFERENCES sniper_opportunities(id)
);

CREATE TABLE IF NOT EXISTS sniper_tactic_learning (
  tactic_id TEXT PRIMARY KEY,
  attempts INTEGER NOT NULL DEFAULT 0,
  replies INTEGER NOT NULL DEFAULT 0,
  meetings INTEGER NOT NULL DEFAULT 0,
  wins INTEGER NOT NULL DEFAULT 0,
  losses INTEGER NOT NULL DEFAULT 0,
  score REAL NOT NULL DEFAULT 0,
  evidence_refs_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sniper_activity (
  id TEXT PRIMARY KEY,
  opportunity_id TEXT,
  stream TEXT NOT NULL,
  actor TEXT NOT NULL,
  event_type TEXT NOT NULL,
  detail_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sniper_activity_created
  ON sniper_activity(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sniper_activity_opportunity
  ON sniper_activity(opportunity_id, created_at DESC);
