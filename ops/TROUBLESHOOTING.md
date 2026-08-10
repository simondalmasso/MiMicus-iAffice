# Troubleshooting

- `SchemaMismatch`: compare `docs/NETWORK_COMPATIBILITY.md` with current official Networks page; upgrade the version manifest/routes deliberately.
- HTTP 429/network error: client retries reads with bounded exponential backoff. Increase watch interval rather than adding a paid provider.
- Stale/catching-up RPC: do not use the scan for a gate decision until a fresh official endpoint succeeds.
- Malformed/partial response: scan records an incident; missing eligibility inputs fail closed.
- Empty historical route: do not interpret as zero historical activity without understanding endpoint semantics.
- SQLite restart: rerun with the same `--db`; schema initialization is idempotent and WAL mode is enabled.
- Any write-lock exception: do not bypass it under ORDER-001.
