# Mimicus Lead Decision Gate V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, zero-cost commercial lead decision gate beneath LAYA so Facebook and Reddit setter prospects are normalized, filtered, prioritized, and returned as an auditable work queue without sending outreach or changing setter state.

**Architecture:** The absorbed Python core gains a focused `mimicus.commercial` package. A pure `DeterministicLeadDecisionService` consumes normalized `LeadCandidate` values plus an explicit immutable policy and `as_of`, then returns a hash-stable `LeadDecisionBatch`. The service is mounted through the existing plugin/runtime-services seam and exposed through an internal `MiMicusEngine.triage_prospects(...)` method; LAYA/MiMicusEngine remains the only orchestration authority.

**Tech Stack:** Python 3.12+, Pydantic 2.13.4, existing `mimicus.canonical.sha256_obj`, pytest 9, mypy, ruff; no new runtime dependency.

**Spec:** `docs/superpowers/specs/2026-10-01-mimicus-lead-decision-gate-design.md`

## Global Constraints

- LAYA / `MiMicusEngine` remains the single orchestration authority.
- V1 performs no external side effects and no canonical setter-ledger writes.
- Baseline uses no SaaS, no LLM call, no network call, no random generator, and no hidden wall clock.
- Same normalized candidates + same policy + same explicit `as_of` must produce the same decisions and hashes.
- Existing setter score is a late tie-breaker only; it cannot override hard eligibility, stage, risk, or data-quality policy.
- `contactedAt` missing on a contacted prospect is `REPAIR_DATA`; never synthesize timing.
- Existing open leads are not rejected solely because the original post is older than 48 hours.
- Only actionable stages (`replied`, `prepared`, `contacted_due`) may consume `WORK_NOW` WIP; `contacted_waiting` remains `HOLD`.
- Maximum selected WIP defaults to 3 per lane through policy.
- No changes to `data/gpt-prospectos.json`, setter handoffs, `README.md`, Worker UI/runtime, PR #9, deployment, scheduler, effect authorization, or causal replay in this plan.
- Existing Mimicus coverage gate remains >=90%.

## File Map

Create:

- `archive/MiMicus-swarm-source/src/mimicus/commercial/__init__.py` — public commercial-domain exports.
- `archive/MiMicus-swarm-source/src/mimicus/commercial/models.py` — frozen input/policy/decision models and enums.
- `archive/MiMicus-swarm-source/src/mimicus/commercial/prospect_ingest.py` — pure canonical-ledger normalization.
- `archive/MiMicus-swarm-source/src/mimicus/commercial/decision.py` — deterministic ranking/disposition implementation.
- `archive/MiMicus-swarm-source/tests/unit/test_commercial_ingest.py` — canonical schema normalization/fail-closed tests.
- `archive/MiMicus-swarm-source/tests/unit/test_commercial_decision.py` — policy/ranking/determinism tests.
- `archive/MiMicus-swarm-source/tests/integration/test_commercial_engine.py` — runtime-service + MiMicusEngine boundary tests.

Modify:

- `archive/MiMicus-swarm-source/src/mimicus/plugins/services.py` — add `LeadDecisionService` protocol and `lead_decision` field on `RuntimeServices`.
- `archive/MiMicus-swarm-source/src/mimicus/plugins/profiles.py` — mount `DeterministicLeadDecisionService` as builtin capability `lead_decision`.
- `archive/MiMicus-swarm-source/src/mimicus/orchestration/engine.py` — expose internal read-only `triage_prospects(...)` entry point.
- `archive/MiMicus-swarm-source/tests/unit/test_plugins.py` — assert service is mounted/reversible.

## Review Focus

1. **Unknown/unsupported outreach status** — must become `REPAIR_DATA`, not accidentally sort into an actionable stage. Covered in Task 1/2.
2. **Timezone-naive timestamps** — reject during normalization rather than comparing ambiguous local times. Covered in Task 1.
3. **Missing channel follow-up threshold** — contacted record must become `REPAIR_DATA`, not use an implicit default. Covered in Task 2.
4. **Duplicate prospect IDs in one input batch** — reject the batch before ranking so one prospect cannot consume two WIP slots. Covered in Task 2.
5. **Input mutation after decision** — models are frozen and hashes derive from canonical serialized content, so caller mutation cannot retroactively alter a receipt. Covered in Task 1/2.

---

### Task 1: Normalize the setter ledger into immutable commercial inputs

**Files:**
- Create: `archive/MiMicus-swarm-source/src/mimicus/commercial/__init__.py`
- Create: `archive/MiMicus-swarm-source/src/mimicus/commercial/models.py`
- Create: `archive/MiMicus-swarm-source/src/mimicus/commercial/prospect_ingest.py`
- Test: `archive/MiMicus-swarm-source/tests/unit/test_commercial_ingest.py`

**Interfaces:**
- Consumes: one finding-shaped `dict[str, Any]` or ledger-shaped `dict[str, Any]` matching the current setter schema.
- Produces:
  - `LeadCandidate`
  - `LeadDecisionPolicy`
  - `LeadDisposition`
  - `LeadStage`
  - `normalize_prospect(row: Mapping[str, Any]) -> LeadCandidate`
  - `normalize_ledger(payload: Mapping[str, Any]) -> list[LeadCandidate]`

- [ ] **Step 1: Write failing normalization tests**

Add tests asserting:

```python
def test_normalize_replied_facebook_candidate() -> None:
    candidate = normalize_prospect(_finding(status="replied", source_name="Facebook"))
    assert candidate.lane == "facebook"
    assert candidate.outreach_status == "replied"
    assert candidate.setter_score == 90

def test_normalize_requires_timezone_aware_dates() -> None:
    with pytest.raises(ValueError):
        normalize_prospect(_finding(verified_at="2026-10-01T10:00:00"))

def test_normalize_ledger_preserves_active_and_terminal_rows() -> None:
    rows = normalize_ledger({"findings": [_finding(id="a"), _finding(id="b", active=False, status="closed")]})
    assert [row.prospect_id for row in rows] == ["a", "b"]

def test_candidate_is_frozen() -> None:
    candidate = normalize_prospect(_finding())
    with pytest.raises(ValidationError):
        candidate.title = "mutated"
```

Also cover unknown source mapping and absent optional `outcome` compatibility.

- [ ] **Step 2: Run focused tests and confirm RED**

Run from `archive/MiMicus-swarm-source`:

```bash
pytest tests/unit/test_commercial_ingest.py -q
```

Expected: collection/import failure because `mimicus.commercial` does not exist.

- [ ] **Step 3: Implement frozen models in `models.py`**

Define:

```python
class LeadDisposition(StrEnum):
    WORK_NOW = "WORK_NOW"
    HOLD = "HOLD"
    REPAIR_DATA = "REPAIR_DATA"
    REJECT = "REJECT"

class LeadStage(StrEnum):
    REPLIED = "replied"
    PREPARED = "prepared"
    CONTACTED_DUE = "contacted_due"
    CONTACTED_WAITING = "contacted_waiting"
    TERMINAL = "terminal"
    UNKNOWN = "unknown"

class LeadCandidate(BaseModel): ...
class LeadDecisionPolicy(BaseModel): ...
class LeadDecision(BaseModel): ...
class LeadDecisionBatch(BaseModel): ...
```

Constraints:
- `ConfigDict(frozen=True, extra="forbid")` for domain models.
- all timestamps are timezone-aware `datetime`;
- `LeadCandidate` includes `outreach_channel: str | None` because contacted follow-up timing is channel-specific;
- `setter_score` bounded 0..100;
- policy contains `max_work_per_lane: int = 3`, explicit `follow_up_after_hours: dict[str, int]`, and a version string;
- hashes are derived with existing `sha256_obj`, never Python `hash()`.

- [ ] **Step 4: Implement pure normalization in `prospect_ingest.py`**

`normalize_prospect` maps the current JSON keys without reading files or touching GitHub. Preserve unknown outcome as absence; do not infer won/lost from `closed`.

`normalize_ledger` validates `findings` is a list and normalizes each row.

- [ ] **Step 5: Run focused tests and confirm GREEN**

Run:

```bash
pytest tests/unit/test_commercial_ingest.py -q
ruff check src/mimicus/commercial tests/unit/test_commercial_ingest.py
mypy src/mimicus/commercial
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit Task 1**

```bash
git add archive/MiMicus-swarm-source/src/mimicus/commercial archive/MiMicus-swarm-source/tests/unit/test_commercial_ingest.py
git commit -m "feat: normalize Mimicus commercial prospects"
```

---

### Task 2: Implement deterministic LAYA lead decisions

**Files:**
- Create: `archive/MiMicus-swarm-source/src/mimicus/commercial/decision.py`
- Modify: `archive/MiMicus-swarm-source/src/mimicus/commercial/__init__.py`
- Test: `archive/MiMicus-swarm-source/tests/unit/test_commercial_decision.py`

**Interfaces:**
- Consumes:
  - `list[LeadCandidate]`
  - `LeadDecisionPolicy`
  - explicit timezone-aware `as_of: datetime`
- Produces:
  - `DeterministicLeadDecisionService.decide(...) -> LeadDecisionBatch`

- [ ] **Step 1: Write failing public-behavior tests**

Tests must assert:

```python
def test_replied_outranks_prepared_even_with_lower_setter_score() -> None: ...

def test_only_three_actionable_records_per_lane_are_work_now() -> None: ...

def test_contacted_waiting_is_hold_even_when_lane_has_free_capacity() -> None: ...

def test_closed_high_score_never_becomes_work_now() -> None: ...

def test_high_scam_risk_never_becomes_work_now() -> None: ...

def test_worker_fee_and_argentina_ineligible_are_rejected() -> None: ...

def test_missing_contacted_at_is_repair_data() -> None: ...

def test_missing_followup_threshold_is_repair_data() -> None: ...

def test_old_open_lead_is_not_rejected_for_publication_age() -> None: ...

def test_input_permutation_produces_identical_batch_dump_and_hash() -> None: ...

def test_duplicate_prospect_ids_are_rejected_before_ranking() -> None: ...

def test_unknown_outreach_status_is_repair_data() -> None: ...
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```bash
pytest tests/unit/test_commercial_decision.py -q
```

Expected: import or unimplemented-service failures.

- [ ] **Step 3: Implement hard classification helpers**

Inside `decision.py`, keep helpers private and deterministic:

- hard rejection from active/eligibility/fee/risk/terminal state;
- data repair detection;
- stage derivation using only candidate + policy + explicit `as_of`;
- no I/O and no global clock.

For contacted leads:
- require `contacted_at`;
- require a configured threshold for the record's channel;
- derive `CONTACTED_DUE` or `CONTACTED_WAITING`.

- [ ] **Step 4: Implement stable lane ranking and WIP allocation**

Sort actionable candidates lexicographically by:

1. stage precedence: replied, prepared, contacted_due;
2. risk: low before medium;
3. action-metadata completeness;
4. setter score descending;
5. verified timestamp descending;
6. prospect ID ascending.

Allocate at most `policy.max_work_per_lane` `WORK_NOW` items independently for each lane.

`CONTACTED_WAITING` is always `HOLD`.

- [ ] **Step 5: Implement hashes**

For every decision:
- `input_hash = sha256_obj(candidate.model_dump(mode="json"))`
- `policy_hash = sha256_obj(policy.model_dump(mode="json"))`
- `decision_hash` hashes the semantic decision payload including input/policy hashes.

For the batch:
- canonicalize decisions by lane/rank/prospect ID before hashing;
- do not hash caller input order.

- [ ] **Step 6: Run focused tests and static checks**

Run:

```bash
pytest tests/unit/test_commercial_ingest.py tests/unit/test_commercial_decision.py -q
ruff check src/mimicus/commercial tests/unit/test_commercial_ingest.py tests/unit/test_commercial_decision.py
mypy src/mimicus/commercial
```

Expected: exit 0.

- [ ] **Step 7: Commit Task 2**

```bash
git add archive/MiMicus-swarm-source/src/mimicus/commercial archive/MiMicus-swarm-source/tests/unit/test_commercial_decision.py
git commit -m "feat: add deterministic LAYA lead decisions"
```

---

### Task 3: Mount the decision service under MiMicusEngine

**Files:**
- Modify: `archive/MiMicus-swarm-source/src/mimicus/plugins/services.py`
- Modify: `archive/MiMicus-swarm-source/src/mimicus/plugins/profiles.py`
- Modify: `archive/MiMicus-swarm-source/src/mimicus/orchestration/engine.py`
- Modify: `archive/MiMicus-swarm-source/tests/unit/test_plugins.py`
- Create: `archive/MiMicus-swarm-source/tests/integration/test_commercial_engine.py`

**Interfaces:**
- Consumes Task 1/2 public models/service.
- Produces:
  - `LeadDecisionService(Protocol)`
  - `RuntimeServices.lead_decision`
  - builtin capability `lead_decision`
  - `MiMicusEngine.triage_prospects(payload, *, policy, as_of) -> LeadDecisionBatch`

- [ ] **Step 1: Write failing plugin/runtime integration tests**

Extend plugin tests:

```python
def test_profiles_mount_lead_decision_service() -> None:
    kernel = build_kernel("offline")
    kernel.mount_all()
    assert kernel.services.get("lead_decision") is not None
```

Create engine integration tests:

```python
def test_engine_triage_prospects_uses_runtime_service(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'commercial.db'}")
    batch = engine.triage_prospects(
        {"findings": [...]},
        policy=_policy(),
        as_of=AS_OF,
    )
    assert batch.selected_by_lane["facebook"] == [...]

def test_engine_triage_has_no_provider_calls_or_ledger_mutation(tmp_path: Path) -> None:
    provider = ScriptedProvider()
    engine = MiMicusEngine(..., provider=provider)
    before = engine.repository.inspect_state(...)
    engine.triage_prospects(...)
    assert provider.generate_calls == 0
    # Assert no run/effect artifacts were created by triage.
```

Use the repository's actual safe inspection methods; do not invent a non-existent generic state accessor.

- [ ] **Step 2: Run focused integration tests and confirm RED**

Run:

```bash
pytest tests/unit/test_plugins.py tests/integration/test_commercial_engine.py -q
```

Expected: missing `lead_decision` capability / `triage_prospects` method.

- [ ] **Step 3: Add `LeadDecisionService` protocol and RuntimeServices field**

In `plugins/services.py`:

```python
class LeadDecisionService(Protocol):
    def decide(
        self,
        candidates: list[LeadCandidate],
        policy: LeadDecisionPolicy,
        *,
        as_of: datetime,
    ) -> LeadDecisionBatch: ...
```

Add `lead_decision: LeadDecisionService` to `RuntimeServices`.

No persistence method belongs in this protocol.

- [ ] **Step 4: Mount builtin deterministic service**

In `plugins/profiles.py`:
- instantiate `DeterministicLeadDecisionService`;
- mount it as builtin plugin ID `decision.commercial`;
- capability name `lead_decision`;
- pass it into `RuntimeServices`.

Keep offline/openai/test profiles behavior identical otherwise.

- [ ] **Step 5: Add `MiMicusEngine.triage_prospects`**

In `orchestration/engine.py`, add a synchronous read-only method with exact signature:

```python
def triage_prospects(
    self,
    payload: dict[str, Any],
    *,
    policy: LeadDecisionPolicy,
    as_of: datetime,
) -> LeadDecisionBatch:
    ...
```

Behavior:
1. normalize through `normalize_ledger(payload)`;
2. delegate to `self.services.lead_decision.decide(...)`;
3. return batch;
4. do not call `run`/`run_async`;
5. do not call provider;
6. do not write memory, run ledger, setter JSON, effects, or network.

- [ ] **Step 6: Run focused tests and static checks**

Run:

```bash
pytest tests/unit/test_plugins.py tests/unit/test_commercial_ingest.py tests/unit/test_commercial_decision.py tests/integration/test_commercial_engine.py -q
ruff check src/mimicus tests/unit/test_plugins.py tests/unit/test_commercial_ingest.py tests/unit/test_commercial_decision.py tests/integration/test_commercial_engine.py
mypy src/mimicus
```

Expected: exit 0.

- [ ] **Step 7: Commit Task 3**

```bash
git add archive/MiMicus-swarm-source/src/mimicus/plugins/services.py archive/MiMicus-swarm-source/src/mimicus/plugins/profiles.py archive/MiMicus-swarm-source/src/mimicus/orchestration/engine.py archive/MiMicus-swarm-source/tests/unit/test_plugins.py archive/MiMicus-swarm-source/tests/integration/test_commercial_engine.py
git commit -m "feat: mount LAYA commercial decision gate"
```

---

### Task 4: Falsify the integrated slice against the repository gates

**Files:**
- No intended production-file changes.
- Modify tests only if a test itself is proven incorrect; any production defect discovered routes back to the owning task.

**Interfaces:**
- Consumes the completed Task 1–3 branch state.
- Produces fresh verification evidence for merge-readiness of this isolated slice.

- [ ] **Step 1: Run the focused commercial suite**

Run:

```bash
cd archive/MiMicus-swarm-source
pytest tests/unit/test_commercial_ingest.py tests/unit/test_commercial_decision.py tests/integration/test_commercial_engine.py tests/unit/test_plugins.py -q
```

Expected: all pass.

- [ ] **Step 2: Run full tests with coverage gate**

Run:

```bash
pytest --cov=mimicus --cov-report=term-missing
```

Expected:
- all tests pass;
- total coverage >=90%.

- [ ] **Step 3: Run static verification**

Run:

```bash
ruff check src tests
mypy src/mimicus
python -m build
```

Expected: all exit 0.

- [ ] **Step 4: Run deterministic repeat check**

Execute one fixed commercial fixture twice with identical:
- normalized payload;
- explicit `as_of`;
- policy.

Serialize each `LeadDecisionBatch.model_dump(mode="json")` through canonical JSON and compare bytes/hashes.

Expected: exact match.

Then permute the source `findings` array and repeat.

Expected: exact same authoritative batch and hash.

- [ ] **Step 5: Verify write isolation**

Compare branch diff against its base.

Expected product changes are restricted to:
- `archive/MiMicus-swarm-source/src/mimicus/commercial/**`
- the three named Mimicus integration files;
- focused tests;
- approved spec/plan docs.

Explicitly verify no changes to:
- `data/gpt-prospectos.json`
- `HANDOFF-SETTER-*.md`
- `SETTERS.md`
- `README.md`
- `worker.js`
- `public/**`
- `wrangler.toml`.

- [ ] **Step 6: Whole-branch code review**

Use an independent review pass against:
- the approved spec;
- hard eligibility;
- fail-closed data repair;
- determinism;
- service authority boundary;
- absence of side effects;
- no accidental scheduler/effect/replay work.

Any material finding returns to the owning task and is re-verified.

- [ ] **Step 7: Final commit only if verification generated a legitimate tracked artifact**

Do not create evidence files merely to have another commit. If no tracked artifact changes are required, leave the prior implementation commit as HEAD.

## Dependency Graph

```text
Task 1: domain + ingest
          |
          v
Task 2: deterministic decision
          |
          v
Task 3: RuntimeServices + LAYA seam
          |
          v
Task 4: integrated verification/review
```

Parallel execution is intentionally not recommended. Tasks 2 and 3 consume interfaces established immediately before them, and one writer provides a cleaner audit trail for this authority-sensitive slice.

## Rollback

This slice introduces no data migration and no external state mutation.

Rollback is therefore code-only:
1. remove `MiMicusEngine.triage_prospects`;
2. remove `lead_decision` service mount/RuntimeServices field;
3. remove the `mimicus.commercial` package.

Setter operation remains unchanged because the canonical setter ledger is never mutated by this feature.

## Integration Boundary After This Plan

Successful completion authorizes only a read-only LAYA commercial decision gate.

Still separate, not included:
- completion-driven `DagExecutor`;
- `EffectPolicy` + one-use approval receipts;
- causal replay upgrade;
- Worker/read-model publication;
- explicit outcome schema change on setter `main`;
- model-backed `DecisionProvider` shadow experiments;
- autonomous outreach.
