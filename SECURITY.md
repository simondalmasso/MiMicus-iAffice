# Security policy

Report suspected vulnerabilities privately to the repository owner before public disclosure when feasible.

MiMicus V0.2.2 deliberately forbids production execution of source text supplied by an LLM, database, memory item, mutation candidate or untrusted plugin. Runtime falsifier mutations remain declarative `FalsifierSpec` values constrained to source-controlled trusted primitives. Out-of-tree plugin loading requires an explicit allowed root and expected SHA-256.

The combined MiMicus iAffice release also enforces:

- one LAYA / `MiMicusEngine` control plane;
- deny-by-default external effects;
- exact-envelope, time-bounded, one-use effect approvals;
- no blind retry after an uncertain remote effect outcome;
- loopback-only local commercial observer;
- causal replay anchored to the append-only event ledger;
- observational Cloudflare cockpit with no command ingress into LAYA.

Security invariants and failure injection are documented in [core/docs/THREAT_MODEL.md](core/docs/THREAT_MODEL.md).

The exact-head CI runs tests, coverage, Ruff, mypy and package build gates from `core/`.
