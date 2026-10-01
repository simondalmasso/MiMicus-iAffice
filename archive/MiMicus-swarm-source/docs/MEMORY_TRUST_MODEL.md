# Persistent immune memory trust model

MiMicus memory authority is policy state, not a vector-search score. V0.2 persists memory items, status transitions and derivation links, then reapplies gates after process restart.

Lifecycle states are `candidate`, `quarantined`, `private_verified`, `shared_verified`, `rejected` and `expired`. WRITE determines whether a candidate has enough deterministic verification and provenance to leave quarantine. PROMOTION determines whether it can become shared verified memory. RETRIEVAL is checked at run start. CROSS-AGENT is checked again before verified material is injected into another agent's sealed task context.

Only `private_verified` and `shared_verified` items are repository-eligible, and eligibility alone is not sufficient: domain/retrieval and cross-agent policy are evaluated at use time. A high-authority paraphrase with an unverified origin does not become trusted by being rewritten or restarted. Derivation links preserve the authority ancestry needed to prevent laundering.

The normal engine persists transitions with transition hashes and emits linked event-ledger records. A later engine process opening the same database can reuse an eligible verified memory item; a quarantined negative fixture remains blocked after the same restart. ORDER-003 process evidence records both behaviors.

Storage technology is replaceable through the memory/storage service boundary, but provenance, authority and gate semantics remain MiMicus policy. External vector databases are not delegated authority decisions.
