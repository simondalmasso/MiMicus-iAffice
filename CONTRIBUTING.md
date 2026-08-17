# Contributing

Use Python 3.12 and install the committed lock. Run format, lint, typing, unit/integration coverage, process E2E, benchmark, migration, package and replay gates before requesting review.

Changes to trusted falsifier primitives require source review plus compatibility, security, fossil-regression and tamper tests. Runtime mutation must remain declarative. Do not add an alternate orchestration framework as a transitive control plane without an architecture decision that proves MiMicus retains authority over routing, falsification, memory, trust and mutation.
