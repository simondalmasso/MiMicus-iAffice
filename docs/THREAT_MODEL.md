# Threat model

Protected assets: canonical D1 memory, approval authority, connector credentials, customer-facing action payloads, budget headroom, source provenance, git/deploy authority and evidence integrity.

Threats and mitigations:

- Prompt injection: trust labels, instruction/data separation, schema validation, post-model policy checks; injected fixture cannot grant SEND/MONEY authority.
- Approval forgery/replay/race: action hash + signer + expiry + one-time consumed state; mismatched payloads fail.
- SSRF/exfiltration: GenericREST is HTTPS-only, hostname-allowlisted and rejects userinfo, localhost and private/link-local IPv4 targets.
- Secret leakage: redaction of auth/cookie/token/secret/password fields and bearer values; secrets are Wrangler secrets, not vars/files.
- Canonical-memory poisoning: LLM output is claim-level only; AUD is required for promotion; contradictions are retained.
- Cost escalation: free allowlist, paid denylist and 85%-or-lower hard caps; no paid fallback.
- Queue loss: retry plus DLQ and persisted task/deferred marker.
- Tampering: chained ledger verification and deterministic replay detect copied-row modification.
- Privilege escalation through delegates: connector/MiMicus results cannot gain canonical policy/memory authority.
