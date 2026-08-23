# Phase 02 future chapters blueprint

Status: read-only planning hypothesis captured while TASK-0013 is blocked. This
document does not initialize Chapter 12 or 13, freeze future specifications,
authorize implementation, change active Policy, or expand TASK-0013 scope. Every
future task must be re-derived from the repository state that exists after its
declared dependencies complete.

## Chapter 12: runtime observations and complete Hooks

The current `pre_commit.py` and `pre_command.py` are Phase 01 thin refusal
wrappers. They call shared scope/permission primitives but do not emit bound
observation facts, persist audit events, trigger monotonic escalation, or prove
Hook/CLI/CI parity.

Provisional shared model:

```text
ObservationKind:
  scope_out_of_bounds
  policy_changed
  controlled_file_changed
  high_risk_command
  evidence_missing

ObservationSource:
  hook_pre_commit
  hook_pre_command
  cli
  ci

ObservationDecision:
  record | escalate | refuse
  stable reason code
  optional REVIEW/BLOCK target
  required recovery conditions
```

The facts bind task, base/subject commit, Policy hash, source, kind, and only the
minimal safe path/action/evidence summary. They never store credentials, free
shell text, environment, stdout, or stderr. A single pure core maps facts to a
decision; Hook adapters may not copy a Policy/route table. CI evaluates the same
facts read-only and never mutates a detached checkout's task ledger.

Provisional six-task sequence:

1. **12.1 observation contracts** — versioned observation schema, immutable
   parser/types, contract/state compatibility, unknown-field refusal.
2. **12.2 shared decisions and persistence** — deterministic
   record/escalate/refuse mapping, task-local non-state observation/refusal
   events, and reuse of existing monotonic `escalate_task` behavior.
3. **12.3 edit/scope Hook** — make `pre_commit.py` submit scope, Policy, and
   controlled-file observations; support deterministic dry-run/JSON output.
4. **12.4 structured pre-command Hook** — bind task/action/target, record refusal
   facts, and never parse or execute a free shell command.
5. **12.5 Hook/CLI/CI parity** — add a thin `aiflow observe` adapter and shared
   fixtures proving identical decisions across core, CLI, Hook, and CI dry-run.
6. **12.6 operations and recovery** — document supported command forms,
   escalation/refusal recovery, platform gaps, and update Chapter 12/overall
   projections only after exit evidence passes.

12.3 and 12.4 may become parallel only after 12.1-12.2 are integrated. 12.5
depends on both, and 12.6 is last. Each remains a separately governed task; any
active Policy change forces reclassification/refreeze/reapproval.

Parity fixtures must cover in-scope edits, out-of-scope edits, Policy and
controlled-file changes, all six forbidden automatic action categories, missing
or stale evidence, task ambiguity, binding drift, path escape, unknown fields,
and AUTO/ASK/REVIEW/BLOCK monotonicity.

Supported-boundary statements remain mandatory:

- a Git hook cannot intercept IDE saves, GUI/remote Git, or clients that do not
  install it;
- pre-command accepts structured categories and cannot safely interpret arbitrary
  PowerShell/cmd/bash syntax, aliases, pipes, redirections, or expansion;
- GitHub Actions dry-run does not prove every Windows/macOS host behavior;
- the system is not a general command or operating-system sandbox.

## Chapter 13: real REVIEW + V2 bootstrap and Phase 02 baseline

Strict provisional sequence:

1. **13.1 pilot freeze** — only after Chapters 8-12 exit evidence is current,
   select a real cross-module change whose deterministic classification is
   `REVIEW + V2`, freeze scope/spec, and obtain design/spec approval.
2. **13.2 isolated implementation and V2 pre-evidence** — in an independently
   authorized local worktree, complete design review, implementation, and
   verification by an actor different from the implementer.
3. **13.3 final review/approval/CI/Gate** — implementation review, V2 finalize,
   code approval, separate CI evidence, CI simulation, and read-only Gate.
4. **13.4 negative E2E replay** — same actor, survived or missing mutation,
   scope/Policy/permission escalation, stale review/evidence, and every other
   frozen refusal path must fail closed.
5. **13.5 six-input matrix and evidence index** — bind each Phase 02 input to
   artifact paths, commit/attestation hashes, reproduce argv, outcome, and known
   limits; reconcile but do not silently rewrite historical task ledgers.
6. **13.6 baseline projection** — update Chapter 12/13 and overall state,
   README, CHANGELOG, operations, and Phase 03 inputs; then run the complete
   Phase 02 acceptance and create the baseline commit.

A strong current pilot candidate is the executable action-consumption ledger that
TASK-0013 deliberately leaves as a manual fallback: a versioned action-use
contract, current/single-use consume/refusal service, CLI integration, approval
freshness, tests, and operations. It crosses contracts, approval/task state, CLI,
and E2E behavior without requiring a Policy change. This is not selected now;
13.1 must reassess whether it remains the highest-value real gap.

The six-input matrix is:

| Input | Required evidence |
|---|---|
| P2-REV-01 | Chapter 8 review context/records/freshness plus pilot design and implementation review refs |
| P2-V2-01 | Chapters 9-10 ordered V2 Policy/evidence/Gate replay plus pilot final V2 evidence |
| P2-VER-01 | Chapter 10 actor/context integrity plus pilot implementer/verifier separation |
| P2-MUT-01 | Chapter 11 canonical manifest, isolated logs/results, all-killed facts, and pilot targeted-mutation pass |
| P2-ESC-01 | Chapter 12 observation-to-escalation/refusal replay plus pilot negative escalation E2E |
| P2-HOOK-01 | Chapter 12 Hook/CLI/CI same-input parity evidence and documented limitations |

No row may be satisfied by narrative alone.

## Historical ledger and final commands

Tasks that remain `APPROVED_FOR_MERGE` cannot be treated as `MERGED` merely
because their subjects are ancestors of main. Each close needs its own explicit
authorization and real integration commit. TASK-0008 remains an append-only
superseded/blocked record unless a future governed decision changes its
disposition.

The final command family, with the then-current pilot ID and distinct verifier,
includes task validate/scope/status, Ruff check/format, mypy, full pytest and
coverage/diff coverage, local V2 verify and finalize, implementation review,
code approval, contained CI verify, Gate, `git diff --check`, and every frozen
negative E2E. Local code-approval evidence and CI Gate evidence remain separate.
