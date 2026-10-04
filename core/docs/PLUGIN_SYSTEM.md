# Plugin system

MiMicus uses a small Python-native plugin kernel inspired by capability/plugin separation, implemented clean-room.

A manifest is immutable and records `id`, `version`, `kind`, `capabilities`, dependencies, config schema, provenance, source SHA-256, and a canonical manifest hash. Supported V0.1 kinds are model provider, agent factory, falsifier, memory backend, storage backend, coalition policy, communication policy, sandbox, and telemetry.

Mounting follows a deterministic topological dependency order. Missing dependencies and cycles fail closed. Capabilities have exactly one owner; conflicts fail. Unmounting happens in reverse order and removes registered capabilities.

No automatic remote plugin installation exists. An out-of-tree plugin path is accepted only when it is inside an explicit allow-listed root and its bytes match an expected SHA-256. Plugin text stored in a database has no load path.

Profiles in `profiles/` are `offline`, `openai`, and `test`.
