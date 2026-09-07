# Thin local wrappers and Hooks

These adapters call the executable AI Flow core. They provide earlier feedback; they do not replace CLI validation, CI Gate, repository branch protection, or explicit approval for external actions.

The supported high-risk checks and unknown pre-command categories fail closed. The wrappers do not install themselves, consume an approval, execute a command, or turn a diagnostic result into permission for a real external operation.

## Verification wrapper

Run `python tools/gauntlet.py --task TASK-ID`. Add `--provisional` for diagnostic evidence that cannot satisfy Gate, and `--format json` for machine-readable output. The wrapper does not read verification Policy or choose checks; `aiflow.verification_service.verify_task` remains authoritative.

## Pre-commit

Run `python tools/hooks/pre_commit.py --task TASK-ID` from a Git pre-commit integration or an Agent before requesting a commit. Omitting `--task` is accepted only when exactly one non-merged task exists. The check delegates task status, changed-path collection, scope matching, and workflow prerequisites to core services. It never runs `git commit`, edits the index, or fixes files.

## Pre-command

Run `python tools/hooks/pre_command.py --action ACTION --target TARGET [--task TASK-ID]` before a normalized external action. A blank target fails before Policy loading, task lookup, or observation construction. Only an explicitly Policy-allowed `read` category passes without reading `--task` or creating an observation. Unknown categories return denial (exit 2) before task lookup or observation; blank categories are invalid input (exit 1). For an active-Policy forbidden canonical high-risk action (`push`, `merge`, `deploy`, `delete`, `secret_export`, or `paid_external_call`), `--task` is optional only when exactly one non-`MERGED` task can be resolved; ambiguity, an invalid explicit task, target-contract failure, or stale binding fails closed. The wrapper records the structured observation through the shared service and then always returns denial (exit 2). It never consumes an action approval and never executes the action, including when an approval exists.

The adapter accepts a structured canonical action and opaque `--target`, not a command line. It does not parse or interpret PowerShell, cmd, bash, aliases, pipes, redirection, quotes, wildcards, variable/command expansion, argv, stdin, environment, stdout, stderr, or credentials. It is neither a general command interceptor nor an OS sandbox.

Policy `2.3.0` explicitly lists `allowed_automatic_actions: [read]`. The evaluator now
defaults to denial rather than treating an unmatched category as safe; older Policy
bundles without that list remain readable but grant no implicit `read` allowance. This
closes the local unknown-category gap documented before [TASK-0047](../../.ai/tasks/TASK-0047/spec.md).
An allowed category still says nothing about the opaque target or a subsequent command;
calling a category `read` cannot authenticate what an unrelated client really executes.

## What the high-risk action approval requirement is actually worth

`.ai/policy/permissions.yaml` forbids `push`, `merge`, `deploy`, `delete`, `secret_export`
and `paid_external_call` from running automatically, and requires a separate action
approval for each. **No code path checks that requirement for `push` or `merge`.** Recorded
so that no reader mistakes the Policy declaration for an enforced control:

- The CLI has no `push`, `merge` or `deploy` subcommand. `close` is documented as recording
  an externally completed merge, not performing one.
- `src/aiflow/gate.py` and `src/aiflow/status_service.py` both skip `approval_type ==
  "action"` when computing approval freshness, so the Gate never requires one.
- `src/aiflow/freshness.py`'s `action_approval` branch has no production caller; the only
  code that constructs `used_action_sha256s` hardcodes it to `()`.
  It remains a non-executing compatibility helper, not an authorization consumer.
- The pre-command wrapper above denies these actions unconditionally. It is a denier, not an
  authorizer, so it cannot let an approved push through and installing it would block every
  push. `.git/hooks/` ships empty and the wrapper does not install itself.
- The only action type whose single-use semantics are enforced in code is
  `targeted_mutation_v2`, in `src/aiflow/mutation_evidence.py`.

Consequently the approval requirement for `push` and `merge` is a **process convention
observed by humans**, not a machine-checked control. Compliance is visible in the ledger
after the fact, not prevented before it.

Making it enforceable was attempted and rejected. TASK-0043's design review found that an
`action` approval is mintable by the agent it would gate — `approvals.json` is an unsigned
working-tree file, action approvals have no state gate, and `actor` is an unauthenticated
free string — so a client-side authorizer would let the controlled party issue its own
permission. Any future attempt has to enforce server side, in CI or branch protection, and
needs identity that this phase does not have.

A future trusted executor would need server-verified human identity, exact repository,
ref, head and action binding, expiry, atomic single-use consumption, immutable outcome
receipts, and protection/required-CI rechecks immediately before its fixed operation.
Those capabilities are not provided by this local refusal repair; no external executor
or identity service is configured by it.

## `aiflow observe`

The closed protocol is:

```text
aiflow observe TASK-ID --input FILE --mode {apply,dry-run,ci} [--actor ACTOR]
```

`TASK-ID`, `--input`, and `--mode` are required and explicit. `FILE` must be one local UTF-8 JSON object. The command does not discover an active task and does not accept facts from stdin, environment variables, free shell text, extra argv payloads, or the network. Duplicate JSON keys, unknown fields, non-object JSON, unreadable input, observation-contract errors, stale/mismatched bindings, and invalid task state all exit 1.

Mode, source, and actor form a closed contract:

| Mode | Required source | Actor rule | Task-directory effect |
| --- | --- | --- | --- |
| `apply` | `cli` | non-empty `--actor` required | may append task-local audit and may perform only monotonic escalation through the existing workflow |
| `dry-run` | `cli` | `--actor` forbidden | zero writes to the complete task directory |
| `ci` | `ci` | `--actor` forbidden | zero writes to the complete task directory |

Every valid observation produces a non-authorizing decision with `execution_allowed=false` and exits 2. There is no observation success path that exits 0 to allow the described action. `apply` records facts; it does not execute or approve what was observed. `dry-run` and `ci` evaluate the same current bindings without ledger writes.

Semantic parity is deliberately narrow: within the supported paths, compare only the decision schema, disposition, reason, current route, current verification level, `execution_allowed`, required conditions, and target route. Source is part of the canonical observation identity, so Hook/CLI/CI digests may differ; mode, ledger effect, event metadata, JSON bytes, and user-visible wording are not parity claims.

## Evidence and platform boundary

Current Hook E2E evidence covers exactly two families: pre-commit observations for `scope_out_of_bounds`, and pre-command observations for the six Policy-forbidden canonical high-risk actions. It does not claim that every observation kind originates in a Hook.

The supported tests ran on Windows and retain four existing skips where symlink capability is unavailable. This is not evidence of live Hook installation or behavior on Linux/macOS. No claim is made for an uninstalled Hook, IDE save, GUI or remote Git, a client that bypasses the wrapper, or system-wide interception. Git/agent Hook integration remains optional; platforms without it are governed by the AI Flow CLI and CI Gate.

Claude Code and other Agents may call these scripts explicitly from their platform Hook configuration. A generic Git client may invoke the pre-commit script from its repository-local Hook. Platforms without such integration remain governed by the AI Flow CLI and CI Gate; phase one does not claim system-wide interception.
