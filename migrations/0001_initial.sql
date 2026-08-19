PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY, type TEXT NOT NULL, entity_id TEXT, observed_at TEXT NOT NULL, created_at TEXT NOT NULL,
  source TEXT NOT NULL, actor TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE, hash TEXT NOT NULL, trust TEXT NOT NULL,
  evidence_type TEXT NOT NULL, payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS event_sources (id TEXT PRIMARY KEY, event_id TEXT NOT NULL, uri TEXT NOT NULL, trust TEXT NOT NULL, observed_at TEXT NOT NULL, hash TEXT NOT NULL, FOREIGN KEY(event_id) REFERENCES events(id));
CREATE TABLE IF NOT EXISTS entities (id TEXT PRIMARY KEY, type TEXT NOT NULL, canonical_name TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS leads (id TEXT PRIMARY KEY, entity_id TEXT, name TEXT NOT NULL, email TEXT NOT NULL, intent_score REAL NOT NULL, last_activity_at TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS content_items (id TEXT PRIMARY KEY, status TEXT NOT NULL, body TEXT NOT NULL, source_refs_json TEXT NOT NULL, created_at TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS campaign_metrics (id TEXT PRIMARY KEY, day TEXT NOT NULL, impressions INTEGER NOT NULL, clicks INTEGER NOT NULL, leads INTEGER NOT NULL, conversions INTEGER NOT NULL, source TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, entity_id TEXT, statement TEXT NOT NULL, source_refs_json TEXT NOT NULL, observed_at TEXT NOT NULL, confidence REAL NOT NULL, status TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS claims (id TEXT PRIMARY KEY, entity_id TEXT, statement TEXT NOT NULL, source_refs_json TEXT NOT NULL, observed_at TEXT NOT NULL, created_at TEXT NOT NULL, confidence REAL NOT NULL, agent_origin TEXT NOT NULL, evidence_hash TEXT NOT NULL, status TEXT NOT NULL, verdict TEXT);
CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, taxonomy TEXT NOT NULL, source_uri TEXT, observed_at TEXT NOT NULL, payload_hash TEXT NOT NULL, metadata_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS knowledge (id TEXT PRIMARY KEY, type TEXT NOT NULL, entity_id TEXT, statement TEXT NOT NULL, source_refs_json TEXT NOT NULL, observed_at TEXT NOT NULL, created_at TEXT NOT NULL, confidence REAL NOT NULL, freshness_policy TEXT NOT NULL, expires_at TEXT, agent_origin TEXT NOT NULL, evidence_hash TEXT NOT NULL, authority_level TEXT NOT NULL, supersedes TEXT, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, priority TEXT NOT NULL, rationale TEXT NOT NULL, evidence_refs_json TEXT NOT NULL, assignments_json TEXT NOT NULL, audit_verdict TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, type TEXT NOT NULL, entity_id TEXT, priority INTEGER NOT NULL, risk TEXT NOT NULL, status TEXT NOT NULL, requested_by TEXT NOT NULL, due_at TEXT, input_json TEXT NOT NULL, created_at TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS task_runs (id TEXT PRIMARY KEY, task_id TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT, status TEXT NOT NULL, route_json TEXT NOT NULL, output_hash TEXT, FOREIGN KEY(task_id) REFERENCES tasks(id));
CREATE TABLE IF NOT EXISTS agent_runs (id TEXT PRIMARY KEY, task_id TEXT NOT NULL, role TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT, status TEXT NOT NULL, evidence_refs_json TEXT NOT NULL, output_hash TEXT);
CREATE TABLE IF NOT EXISTS agent_scores (id TEXT PRIMARY KEY, role TEXT NOT NULL, period TEXT NOT NULL, success_rate REAL NOT NULL, quality_score REAL NOT NULL, model_calls INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_calls (id TEXT PRIMARY KEY, role TEXT NOT NULL, task_id TEXT NOT NULL, model_id TEXT NOT NULL, tier TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL, estimated_neurons REAL NOT NULL, latency_ms INTEGER NOT NULL, reason_selected TEXT NOT NULL, fallback_reason TEXT, result_hash TEXT NOT NULL, quota_state TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS tool_calls (id TEXT PRIMARY KEY, task_id TEXT, role TEXT NOT NULL, tool_name TEXT NOT NULL, action_class TEXT NOT NULL, policy_decision TEXT NOT NULL, args_hash TEXT NOT NULL, result_hash TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, action_hash TEXT NOT NULL, policy_version TEXT NOT NULL, approval_chain_version TEXT NOT NULL, action_class TEXT NOT NULL, requested_by TEXT NOT NULL, reason TEXT NOT NULL, scope TEXT NOT NULL, expires_at TEXT NOT NULL, state TEXT NOT NULL, actor TEXT, signature TEXT, consumed_at TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, action_class TEXT NOT NULL, requested_by TEXT NOT NULL, policy_decision TEXT NOT NULL, approval_id TEXT, status TEXT NOT NULL, payload_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS action_intents (
  intent_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, agent_id TEXT NOT NULL, subject_id TEXT NOT NULL, action_class TEXT NOT NULL, connector TEXT NOT NULL, operation TEXT NOT NULL, target TEXT NOT NULL,
  canonical_parameters_json TEXT NOT NULL, action_digest TEXT NOT NULL UNIQUE, justification TEXT NOT NULL, evidence_refs_json TEXT NOT NULL, policy_version TEXT NOT NULL, approval_chain_version TEXT NOT NULL,
  precondition_hash TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE, requested_at TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL, approval_id TEXT, intent_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS effect_receipts (
  receipt_id TEXT PRIMARY KEY, intent_id TEXT NOT NULL, action_digest TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE, connector TEXT NOT NULL, operation TEXT NOT NULL, status TEXT NOT NULL, result_hash TEXT NOT NULL, executed_at TEXT NOT NULL, attempt INTEGER NOT NULL, detail TEXT NOT NULL, receipt_json TEXT NOT NULL,
  FOREIGN KEY(intent_id) REFERENCES action_intents(intent_id)
);
CREATE TABLE IF NOT EXISTS safe_outbound (idempotency_key TEXT PRIMARY KEY, payload_json TEXT NOT NULL, result_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS connectors (id TEXT PRIMARY KEY, kind TEXT NOT NULL, capabilities_json TEXT NOT NULL, enabled INTEGER NOT NULL, health TEXT NOT NULL, config_hash TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS connector_cursors (connector_id TEXT PRIMARY KEY, cursor TEXT NOT NULL, etag TEXT, updated_at TEXT NOT NULL, FOREIGN KEY(connector_id) REFERENCES connectors(id));
CREATE TABLE IF NOT EXISTS budget_ledger (id TEXT PRIMARY KEY, resource TEXT NOT NULL, amount REAL NOT NULL, state TEXT NOT NULL, observed_at TEXT NOT NULL, source TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, severity TEXT NOT NULL, status TEXT NOT NULL, summary TEXT NOT NULL, evidence_refs_json TEXT NOT NULL, opened_at TEXT NOT NULL, resolved_at TEXT, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS memory_compactions (id TEXT PRIMARY KEY, started_at TEXT NOT NULL, completed_at TEXT NOT NULL, expired_count INTEGER NOT NULL, superseded_count INTEGER NOT NULL, before_hash TEXT NOT NULL, after_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_findings (id TEXT PRIMARY KEY, target_id TEXT NOT NULL, verdict TEXT NOT NULL, reason TEXT NOT NULL, evidence_refs_json TEXT NOT NULL, created_at TEXT NOT NULL, strategy TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS daily_snapshots (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, state_hash TEXT NOT NULL, counts_json TEXT NOT NULL, state_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS ledger (seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, ref_id TEXT NOT NULL, timestamp TEXT NOT NULL, payload_hash TEXT NOT NULL, previous_hash TEXT NOT NULL, chain_hash TEXT NOT NULL UNIQUE);
CREATE INDEX IF NOT EXISTS idx_events_type_observed ON events(type, observed_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_entity_status ON knowledge(entity_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority DESC);
CREATE INDEX IF NOT EXISTS idx_model_calls_task ON model_calls(task_id);
CREATE INDEX IF NOT EXISTS idx_budget_resource_time ON budget_ledger(resource, observed_at);
CREATE INDEX IF NOT EXISTS idx_action_intents_status ON action_intents(status, requested_at);
CREATE INDEX IF NOT EXISTS idx_effect_receipts_intent ON effect_receipts(intent_id);
