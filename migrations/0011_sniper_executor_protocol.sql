-- ORDER-004 signed executor protocol state.
-- Adds durable replay/idempotency metadata to executor runs.

ALTER TABLE sniper_executor_runs ADD COLUMN nonce TEXT;
ALTER TABLE sniper_executor_runs ADD COLUMN request_envelope_json TEXT;
ALTER TABLE sniper_executor_runs ADD COLUMN expires_at TEXT;
ALTER TABLE sniper_executor_runs ADD COLUMN response_signature TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sniper_executor_runs_nonce
  ON sniper_executor_runs(nonce)
  WHERE nonce IS NOT NULL;
