# Connectors

Core/read boundary:

- `WebhookIngestConnector`: authenticated JSON ingest, request-size limit, schema validation, stable idempotency material.
- `GenericRESTReadConnector`: HTTPS-only allowlist, private-network SSRF rejection, ETag/cursor support, retry and 429 handling.
- `GitHubConnector`: read API plus declarative isolated-branch capability planning; no direct write API.
- `NotionMirrorConnector`: pure mirror planner with <=2 req/s default throttle calculation and cursor checkpointing; it never owns a token.
- `CSVImportExportConnector`: deterministic bootstrap/export.
- `LocalSwarmRuntimeAdapter`: optional MiMicus-style delegation that cannot widen authority.

Effect boundary (`aria-effects` only):

- `SafeOutboundEffectAdapter`: credential-free exact-payload reference sink with idempotency; no real customer contact.
- `NotionEffectAdapter`: PATCH page operation, token only in the Effect Worker, 429 becomes retryable/free-quota state.
- `GitHubIssueCommentEffectAdapter`: scoped issue-comment operation, token only in the Effect Worker, idempotency key forwarded.

D1 remains canonical if any mirror fails. Side-effecting adapters are not registered as agent tools.
