# Policy engine

`PolicyEngine` is code authority. Default matrix: allowlisted `READ_PUBLIC`, scoped `READ_PRIVATE`, provenance-backed `INTERNAL_WRITE`, `DRAFT_EXTERNAL`, and isolated `CODE_WRITE` may run automatically. `SEND_EXTERNAL`, `PUBLISH_CONTENT`, `DESTRUCTIVE_MUTATION`, `CODE_MERGE`, and `DEPLOY` require approval. `MONEY_MUTATION` and `CREDENTIAL_MUTATION` are denied in V1.

For any external effect, policy ALLOW/APPROVAL_REQUIRED never grants direct agent tool authority. The agent may only produce an `ActionIntent`. `POLICY_VERSION=aria-policy-v1` and `APPROVAL_CHAIN_VERSION=aria-approval-v1` are included in the action digest and checked again by `aria-effects`.

Human approval binds exactly one action digest and expiry. The signer is deterministic code, not an LLM. Consumption is one-time. An altered target, operation, connector, action class, parameter scope, policy version or state witness requires a new policy decision and, where protected, a new approval.
