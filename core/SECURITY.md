# Security policy

Report suspected vulnerabilities privately to the repository owner before public disclosure when feasible.

MiMicus V0.1 deliberately forbids production execution of source text supplied by an LLM, database, memory item, mutation candidate, or untrusted plugin. Runtime falsifier mutations are data-only `FalsifierSpec` values constrained to source-controlled trusted primitives. Out-of-tree plugin loading requires an explicit allowed root and expected SHA-256.

Security invariants and failure injection are documented in `docs/THREAT_MODEL.md`; the exact-head CI runs dynamic-code, tamper, plugin, memory, correlation, bankruptcy, evasion, timeout and budget gates.
