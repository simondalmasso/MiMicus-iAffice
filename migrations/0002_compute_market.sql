PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS compute_providers (
 provider_id TEXT PRIMARY KEY, provider_name TEXT NOT NULL, provider_type TEXT NOT NULL, api_protocol TEXT NOT NULL, trust_class TEXT NOT NULL,
 base_url_id TEXT NOT NULL, credential_binding_name TEXT, account_mode TEXT NOT NULL, free_type TEXT NOT NULL, billing_safety TEXT NOT NULL,
 privacy_class TEXT NOT NULL, retention_class TEXT NOT NULL, training_use_class TEXT NOT NULL, tos_status TEXT NOT NULL,
 source_policy_hash TEXT NOT NULL, pricing_policy_hash TEXT NOT NULL, enabled INTEGER NOT NULL, production_eligible INTEGER NOT NULL,
 public_only INTEGER NOT NULL, route_state TEXT NOT NULL, grant_remaining_units REAL, overage_possible INTEGER, retired_reason TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_verified_at TEXT NOT NULL, verification_expires_at TEXT NOT NULL,
 record_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS compute_models (
 provider_id TEXT NOT NULL, model_id TEXT NOT NULL, provider_model_name TEXT NOT NULL, model_alias TEXT NOT NULL, identity_assurance TEXT NOT NULL, model_family TEXT NOT NULL,
 capabilities_json TEXT NOT NULL, context_window INTEGER NOT NULL, max_output_tokens INTEGER NOT NULL, supports_tools INTEGER NOT NULL,
 supports_structured_output INTEGER NOT NULL, supports_vision INTEGER NOT NULL, supports_reasoning INTEGER NOT NULL, supports_coding INTEGER NOT NULL,
 pricing_mode TEXT NOT NULL, published_input_price_usd REAL, published_output_price_usd REAL, free_pool_id TEXT NOT NULL,
 quota_dimensions_json TEXT NOT NULL, benchmark_profile_id TEXT NOT NULL, enabled INTEGER NOT NULL, route_state TEXT NOT NULL,
 last_seen_at TEXT NOT NULL, catalog_expires_at TEXT NOT NULL, record_json TEXT NOT NULL,
 PRIMARY KEY(provider_id,model_id), FOREIGN KEY(provider_id) REFERENCES compute_providers(provider_id)
);
CREATE TABLE IF NOT EXISTS compute_evidence (
 evidence_id TEXT PRIMARY KEY, provider_id TEXT NOT NULL, model_id TEXT, evidence_class TEXT NOT NULL, claim_type TEXT NOT NULL,
 source_identifier TEXT NOT NULL, retrieved_at TEXT NOT NULL, expires_at TEXT NOT NULL, content_hash TEXT NOT NULL, result TEXT NOT NULL, detail TEXT NOT NULL,
 FOREIGN KEY(provider_id) REFERENCES compute_providers(provider_id)
);
CREATE TABLE IF NOT EXISTS compute_health (
 id TEXT PRIMARY KEY, provider_id TEXT NOT NULL, model_id TEXT, state TEXT NOT NULL, consecutive_failures INTEGER NOT NULL, opened_at TEXT,
 retry_after TEXT, last_success_at TEXT, last_failure_at TEXT, detail TEXT NOT NULL, observed_at TEXT NOT NULL,
 FOREIGN KEY(provider_id) REFERENCES compute_providers(provider_id)
);
CREATE TABLE IF NOT EXISTS compute_quota_snapshots (
 id TEXT PRIMARY KEY, quota_pool_id TEXT NOT NULL, provider_id TEXT NOT NULL, model_id TEXT, dimension TEXT NOT NULL, verified_free_ceiling REAL,
 local_hard_fraction REAL NOT NULL, consumed REAL NOT NULL, reserved REAL NOT NULL, upstream_remaining REAL, resets_at TEXT, evidence_id TEXT NOT NULL,
 observed_at TEXT NOT NULL, payload_hash TEXT NOT NULL, FOREIGN KEY(provider_id) REFERENCES compute_providers(provider_id)
);
CREATE TABLE IF NOT EXISTS compute_reservations (
 reservation_id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE, route_decision_id TEXT NOT NULL, provider_id TEXT NOT NULL, model_id TEXT NOT NULL,
 quota_pool_id TEXT NOT NULL, estimated_input INTEGER NOT NULL, reserved_output INTEGER NOT NULL, reserved_usage_units REAL NOT NULL,
 created_at TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL, actual_usage REAL, uncertainty TEXT, reservation_json TEXT NOT NULL,
 FOREIGN KEY(provider_id,model_id) REFERENCES compute_models(provider_id,model_id)
);
CREATE TABLE IF NOT EXISTS compute_route_decisions (
 route_decision_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, data_class TEXT NOT NULL, prompt_hash TEXT NOT NULL, estimated_input_tokens INTEGER NOT NULL,
 required_context_window INTEGER NOT NULL, required_capabilities_json TEXT NOT NULL, candidates_json TEXT NOT NULL, selected_provider_id TEXT, selected_model_id TEXT,
 selected_score INTEGER, reason TEXT NOT NULL, created_at TEXT NOT NULL, decision_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS compute_calls (
 execution_id TEXT PRIMARY KEY, reservation_id TEXT NOT NULL, route_decision_id TEXT NOT NULL, task_id TEXT NOT NULL, role TEXT NOT NULL, data_class TEXT NOT NULL,
 provider_id TEXT NOT NULL, model_id TEXT NOT NULL, adapter_version TEXT NOT NULL, provider_config_hash TEXT NOT NULL, prompt_hash TEXT NOT NULL,
 max_output_tokens INTEGER NOT NULL, required_capabilities_json TEXT NOT NULL, policy_version TEXT NOT NULL, requested_at TEXT NOT NULL, expires_at TEXT NOT NULL,
 execution_digest TEXT NOT NULL UNIQUE, provider_request_id TEXT, input_tokens INTEGER, output_tokens INTEGER, usage_units REAL, latency_ms INTEGER,
 finish_reason TEXT, response_hash TEXT, quota_headers_json TEXT, status TEXT NOT NULL, error_class TEXT, completed_at TEXT,
 FOREIGN KEY(reservation_id) REFERENCES compute_reservations(reservation_id)
);
CREATE TABLE IF NOT EXISTS compute_benchmarks (
 id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, provider_id TEXT NOT NULL, model_id TEXT NOT NULL, task_class TEXT NOT NULL, score REAL NOT NULL,
 schema_success_rate REAL NOT NULL, success_rate REAL NOT NULL, latency_p50_ms INTEGER NOT NULL, latency_p95_ms INTEGER NOT NULL, qualified INTEGER NOT NULL,
 measured_at TEXT NOT NULL, evidence_class TEXT NOT NULL, corpus_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS compute_incidents (
 id TEXT PRIMARY KEY, provider_id TEXT, model_id TEXT, kind TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL, reason_code TEXT NOT NULL,
 summary TEXT NOT NULL, evidence_refs_json TEXT NOT NULL, opened_at TEXT NOT NULL, resolved_at TEXT, incident_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_compute_models_state ON compute_models(route_state,enabled);
CREATE INDEX IF NOT EXISTS idx_compute_evidence_expiry ON compute_evidence(provider_id,claim_type,expires_at);
CREATE INDEX IF NOT EXISTS idx_compute_health_provider ON compute_health(provider_id,model_id,observed_at);
CREATE INDEX IF NOT EXISTS idx_compute_quota_pool ON compute_quota_snapshots(quota_pool_id,observed_at);
CREATE INDEX IF NOT EXISTS idx_compute_reservations_status ON compute_reservations(status,expires_at);
CREATE INDEX IF NOT EXISTS idx_compute_routes_task ON compute_route_decisions(task_id,created_at);
CREATE INDEX IF NOT EXISTS idx_compute_calls_provider ON compute_calls(provider_id,model_id,requested_at);
CREATE INDEX IF NOT EXISTS idx_compute_incidents_status ON compute_incidents(status,opened_at);
