# External Worker Routing Execution Plan

> **For agentic workers:** REQUIRED EXECUTION FLOW: Use `subagent-driven-development` to execute this plan task-by-task when subagents are available. If no subagent capability is available, execute inline with the same task checklist and review checkpoints.

**Goal:** Establish, verify, and locally commit an auditable interaction contract in which Sol(max) performs high-order execution and final adjudication while OpenCode Go(max), DeepSeek Official(max), and explicitly independent Luna(max) provide lower-tier work through strict sequential fallback and ACP/envelope/status-file transport.

**Approach:** First repair Task 1.1's existing `needs_revalidation` gate without altering its preserved evidence or unapproved file scope. Then obtain an explicit REVIEW scope decision because the current Phase-01 MVP expressly excludes real multi-model orchestration; turn the externally tested routing candidate into a repository-owned, secret-free contract plus deterministic local validation fixtures. Implement only offline contract/transport validation and documentation in this change: no provider configuration, credential read, payment, model request, desktop automation, or automatic execution of external workers.

**Materials:** `AGENTS.md`; `README.md`; `docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md`; `docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md`; `docs/superpowers/state/README.md`; `docs/superpowers/state/overall.yaml`; `docs/superpowers/state/chapters/chapter-01.yaml`; `docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-execution.md`; `docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-tdd-replay-remediation.md`; `C:\Users\Magina\AppData\Local\Temp\aiflow-reasonix-acp-20260808-001\state\chapter-1-handoff-20260808.json`; and `C:\Users\Magina\AppData\Local\Temp\aiflow-reasonix-acp-20260808-001\routing\external-worker-routing.candidate-v2.json`.

**Validation:** Fresh requirements review then fresh quality review must pass against a hash-bound implementation manifest. Offline tests must prove priority, fallback, explicit dual-review opt-in, failure semantics, identity evidence levels, envelope integrity, and secret redaction. Final checks must pass from the approved external virtual environment, the worktree must contain only approved paths, and one local commit must bind the final subject commit, specifications, reviews, and verification evidence; no push follows.

---

## Invariants and release boundary

- Sol(max) alone approves scope, task state, safety, policy, high-order execution, final review, and final acceptance.
- `opencode-go(max) -> deepseek-official(max) -> independent-luna(max)` are peer lower-tier routes. The default is one selected route with sequential fallback, never default parallelism.
- Move to the next route only on recorded quota/exhaustion evidence. HTTP `429`, `5xx`, timeout, auth, malformed response, and transport failures stop at Sol and do not trigger automatic fallback.
- Dual independent pre-review requires an explicit user request recorded in the envelope; it does not change Sol's final authority.
- Luna must remain an explicitly labelled independent Luna v1 worker with `native_subagent=false`; do not configure it as a Sol native sub-agent or use a thread model switch to imitate that relationship.
- Identity observations are classified as `REQUESTED`, `CONTROL_PLANE_RESOLVED`, `PROVIDER_RETURNED`, or `CRYPTOGRAPHIC`; unavailable provider metadata remains an evidence gap, not a fabricated attestation.
- Repository records contain provider identifiers, requested/returned model and effort, usage summary, output hash, timestamps, and redacted diagnostics only. They never contain API keys, authorization headers, raw `.env` values, payment identifiers, prompt bodies supplied by users, or unredacted transcripts.

### Task 1: Revalidate the blocked Task 1.1 baseline before expanding implementation scope

**Artifacts / Locations:**
- Review: `docs/superpowers/state/chapters/chapter-01.yaml`
- Review: `docs/superpowers/state/overall.yaml`
- Execute: `docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-tdd-replay-remediation.md`
- Write external evidence only: `C:\Users\Magina\AppData\Local\Temp\aiflow-task-1-1-808bd85dd990446ab4135df0116cc55b\`
- Modify after passing reviews: `docs/superpowers/state/chapters/chapter-01.yaml`, `docs/superpowers/state/overall.yaml`

- [ ] **Step 1: Bind the remediation input set**

Read the two state files and verify `SPEC-BLOCKER-001` remains open, Task 1.1/chapter/overall are `needs_revalidation`, and the remediation plan still hashes to the value approved in its new REVIEW decision. Record current `HEAD`, NUL-delimited `git status --porcelain=v1 -z -uall`, hashes of `AGENTS.md`, MVP design, implementation directory, Task 1.1 execution plan, remediation plan, and the eight original Task 1.1 allowlist paths.

- [ ] **Step 2: Perform the required real red-to-green replay**

Use a fresh executor in the existing canonical Task 1.1 AuditRoot. Follow Tasks 0–4 of the remediation plan exactly: create an external `git archive HEAD` baseline; prove the baseline lacks the eight Task 1.1 engineering paths; copy the five configuration/test inputs; run the same external Python/pytest command and obtain genuine red; copy only the three final `src/aiflow` files with hashes equal to the current final sources; rerun exactly the same command and obtain green. Preserve old evidence and never reset, delete, move, stash, commit, or create a worktree.

- [ ] **Step 3: Repeat baseline verification and close the original evidence gap**

In the current worktree, execute the remediation plan's full Phase D with its approved external virtual environment. Require the plan's exact `SYNC`, lock, editable install, unit tests, Ruff, mypy, both CLI entry points, bad-argument exit contract, `git diff --check`, and NUL-status assertions to pass. Seal the replacement context/index/implementation manifest in the canonical AuditRoot with no unbound file.

- [ ] **Step 4: Obtain reviews and make the only permitted state transition**

Assign a fresh requirements/spec reviewer to verify the actual replay chronology and manifest, then a different fresh quality reviewer only if spec passes. On two PASS results, append evidence/history to `chapter-01.yaml` first, then update `overall.yaml`; only then close `SPEC-BLOCKER-001` and restore Task 1.1/chapter/overall to the state warranted by the original plan. Any review failure leaves all three at `needs_revalidation` and returns to the remediation executor.

- [ ] **Step 5: Verify the gate release**

Check the state YAML parses, history is append-only, task/chapter/overall summaries agree, the replay manifest hashes match review records, and no Task 1.2+ work is recorded. Expected: Task 1.1's original red-before-green blocker is released by fresh PASS evidence, not by relabelling prior premature-green evidence.

### Task 2: Classify and freeze the external-worker scope change

**Artifacts / Locations:**
- Create: `docs/superpowers/specs/2026-08-08-external-worker-routing-spec.md`
- Create: `docs/superpowers/decisions/2026-08-08-external-worker-routing-scope.json`
- Create: `docs/superpowers/reviews/2026-08-08-external-worker-routing-spec-review.json`
- Review: `docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md`
- Review: external candidate v2 and handoff JSON named above

- [ ] **Step 1: Record why this is REVIEW rather than an implicit Phase-01 addition**

Create the decision JSON with `route: "REVIEW"`, `verification_level: "V1"`, `subject_commit` set only after implementation is frozen, and explicit rationale that MVP §4.2 excludes supplier-neutral multi-model orchestration. Include allowed paths, prohibited actions, approvals required, invalidation conditions, and hashes/paths for the external candidate and handoff. Do not copy any secret-bearing Desktop configuration into this decision.

- [ ] **Step 2: Write the repository-owned routing specification**

Define the exact roles, fallback order, quota evidence requirement, non-quota failure handling, explicit dual-review flag, ACP-first/envelope/status-file fallback transport, identity-level vocabulary, immutable result fields, redaction rules, and fail-closed behavior. State that the first implementation validates offline envelopes only and does not invoke Reasonix, DeepSeek, OpenCode, desktop UI, or Luna.

- [ ] **Step 3: Freeze and independently review the scope specification**

Hash the decision and specification, place their hashes plus current governance hashes in the review package, and have a fresh spec reviewer verify every invariant in this plan and the user-approved topology. Expected: PASS explicitly confirms no contradiction with the Phase-01 non-goal remains unrecorded and no policy claims a runtime model identity that is not observed.

- [ ] **Step 4: Record the approved boundary**

After a PASS review and explicit user scope approval, update the decision with the resulting approval record and freeze its file hash for the implementation tasks. If scope approval is absent or review fails, do not create code/configuration or advance to Task 3.

### Task 3: Implement the offline interaction contract and deterministic selector

**Artifacts / Locations:**
- Create: `src/aiflow/external_workers/__init__.py`
- Create: `src/aiflow/external_workers/contracts.py`
- Create: `src/aiflow/external_workers/routing.py`
- Create: `src/aiflow/external_workers/redaction.py`
- Create: `.ai/schemas/external-worker-envelope.schema.json`
- Create: `.ai/policy/external-worker-routing.yaml`
- Create: `tests/unit/test_external_worker_contracts.py`
- Create: `tests/unit/test_external_worker_routing.py`
- Create: `tests/fixtures/external_workers/valid/`
- Create: `tests/fixtures/external_workers/invalid/`

- [ ] **Step 1: Define machine-readable policy and envelope schema**

Make the policy enumerate exactly `opencode-go`, `deepseek-official`, and `independent-luna`; requested model/effort; strict order; `single_route_sequential_fallback`; and a default `dual_pre_review=false`. Require envelope fields for task ID, correlation ID, input/output SHA-256, requested and observed identity, identity level, route attempt, outcome, usage summary, redacted diagnostics, and explicit user dual-review authorization. Reject unknown workers, missing required hashes, illegal identity levels, raw secret fields, and claims that Luna is native.

- [ ] **Step 2: Implement pure validation and route selection**

Implement typed, side-effect-free functions that parse the policy/envelope, validate consistency, redact known secret-bearing keys, choose the first eligible route, and return `ESCALATE_TO_SOL` for every non-quota failure. The selector may advance one route only for a normalized `quota_exhausted` result with nonempty evidence reference. It must never open a process, read Desktop home, call ACP, read environment credentials, or perform network I/O.

- [ ] **Step 3: Add deterministic positive and negative tests**

Test: OpenCode Go selected when eligible; DeepSeek selected only after quota evidence; independent Luna selected only after two quota-exhausted routes; `429`, `5xx`, timeout, auth, and transport failures escalate to Sol; dual pre-review is rejected without explicit flag/authorization; Luna `native_subagent=true` is rejected; missing provider metadata receives no stronger identity label; raw `api_key`, `authorization`, `token`, and `.env` fields are rejected/redacted; and same fixture input yields byte-identical selection output.

- [ ] **Step 4: Run focused offline checks**

Run:

```powershell
python -m pytest tests/unit/test_external_worker_contracts.py tests/unit/test_external_worker_routing.py -q
python -m ruff check src/aiflow/external_workers tests/unit/test_external_worker_contracts.py tests/unit/test_external_worker_routing.py
python -m mypy src/aiflow/external_workers
```

Expected: all pass without a network connection, Reasonix executable, Desktop process, provider configuration, credentials, or paid call.

### Task 4: Add a thin non-secret operator contract and status-file handoff examples

**Artifacts / Locations:**
- Create: `docs/operations/external-worker-routing.md`
- Create: `examples/external-workers/request-envelope.example.json`
- Create: `examples/external-workers/result-envelope.example.json`
- Create: `examples/external-workers/status-handoff.example.json`
- Modify: `README.md`

- [ ] **Step 1: Document operator-facing behavior**

Document how Sol produces a correlation-bound request envelope, how a lower-tier worker returns a hash-bound result envelope, and how the status file records selected route, attempt, final disposition, and Sol review. Include the strict priority rule and the one-worker default. Instruct operators to configure provider credentials locally in their chosen client and never place them in this repository, example files, logs, or review material.

- [ ] **Step 2: Provide safe examples**

Use only fabricated task IDs, SHA-256-like sample values, provider names, and non-sensitive text. Make examples valid against the schema and demonstrate: normal DeepSeek result with `REQUESTED_AND_ACP_CONFIG_ATTESTED`; a quota-exhausted OpenCode attempt followed by DeepSeek selection; and a timeout that returns control to Sol rather than falls through to Luna.

- [ ] **Step 3: Verify examples and documentation claims**

Add tests that load every example through the same contract validator and assert the operator documentation contains no literal API-key patterns, `Authorization:` headers, or actual Desktop paths. Expected: examples validate and docs accurately describe offline-only implementation.

### Task 5: Run V1 verification, independent reviews, and make one local commit

**Artifacts / Locations:**
- Create external evidence: `C:\Users\Magina\AppData\Local\Temp\aiflow-external-worker-routing-20260808\implementation-manifest.json`
- Create external evidence: `C:\Users\Magina\AppData\Local\Temp\aiflow-external-worker-routing-20260808\spec-review.json`
- Create external evidence: `C:\Users\Magina\AppData\Local\Temp\aiflow-external-worker-routing-20260808\quality-review.json`
- Modify after verification: `docs/superpowers/decisions/2026-08-08-external-worker-routing-scope.json`
- Commit: all and only approved, verified repository paths

- [ ] **Step 1: Build a hash-bound review package**

Freeze the approved source/spec/policy/example/test path list, file hashes, current `HEAD`, current proposed `subject_commit`, V1 commands, and external evidence locations in the implementation manifest. Redact command environments and logs before storage. Require the manifest to list no credential, provider config, or external-call artifact.

- [ ] **Step 2: Execute full V1 verification in the approved isolated environment**

Run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check pyproject.toml src tests
python -m mypy src
python -m pytest --cov=aiflow --cov-branch --cov-report=term-missing --cov-fail-under=85
git diff --check
git status --porcelain=v1 -uall
```

Expected: all tests/static checks pass, coverage meets the configured threshold, whitespace check passes, and status contains only the approved baseline/revalidation/routing files. If unrelated dirty files exist, preserve them and exclude them from the commit rather than staging broadly.

- [ ] **Step 3: Perform fresh requirement and quality reviews**

Have a fresh lower-tier worker perform the coarse independent requirements review of the manifest and implementation; then have a different fresh lower-tier worker perform quality review. Sol performs final review, checking the two reports against the exact final candidate. Any file change after either review invalidates both reports and repeats this step. Expected: all three reports PASS; neither lower-tier review authorizes a state transition, external action, or commit by itself.

- [ ] **Step 4: Finalize state, stage intentionally, and commit once**

Record the final review/verification hashes in the decision and any applicable manual progress state, binding them to the final `subject_commit`. Stage only the reviewed approved files with explicit paths, inspect `git diff --cached --check` and `git diff --cached --name-only`, then create exactly one local commit using a descriptive message such as `feat: add audited external worker routing contract`. Do not push, merge, deploy, delete, read/export credentials, or invoke a paid provider.

- [ ] **Step 5: Verify the committed result**

Run `git show --check --stat HEAD`, `git status --porcelain=v1 -uall`, the focused external-worker tests, and the full test suite from Task 5 Step 2 against the committed tree. Expected: commit contains only approved files, any pre-existing unrelated dirty paths remain untouched, all checks pass, and the report identifies the local commit SHA plus the evidence manifest/review paths.

---

## Plan self-review

- [x] **Coverage:** Every requested behavior is mapped: Sol authority; ordered lower-tier routes; optional dual pre-review; ACP/envelope/status-file transport; identity levels; quota/error semantics; secret/paid-call exclusion; verification; and one local commit.
- [x] **Placeholders:** Tasks name concrete paths, commands, evidence, and pass/fail gates; no implicit provider setup or unspecified review follows.
- [x] **Sequence:** Task 1 releases the existing Chapter-01 blocker, Task 2 authorizes the scope expansion, Tasks 3–4 implement offline artifacts, and Task 5 verifies/reviews/commits only the frozen result.
- [x] **Validation:** Each task has observable acceptance conditions; both fresh review ordering and final committed-tree checks are explicit.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-08-external-worker-routing-implementation.md`. Recommended next step: use `subagent-driven-development` so each task gets a fresh executor plus review. If this environment has no subagent capability, execute inline using the same checklist and review checkpoints.
