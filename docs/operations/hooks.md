# Thin local wrappers and Hooks

These adapters call the executable AI Flow core. They provide earlier feedback; they do not replace CLI validation, CI Gate, repository branch protection, or explicit approval for external actions.

All wrappers fail closed. They do not install themselves, consume an approval, execute a command, or turn a diagnostic result into permission.

## Verification wrapper

Run `python tools/gauntlet.py --task TASK-ID`. Add `--provisional` for diagnostic evidence that cannot satisfy Gate, and `--format json` for machine-readable output. The wrapper does not read verification Policy or choose checks; `aiflow.verification_service.verify_task` remains authoritative.

## Pre-commit

Run `python tools/hooks/pre_commit.py --task TASK-ID` from a Git pre-commit integration or an Agent before requesting a commit. Omitting `--task` is accepted only when exactly one non-merged task exists. The check delegates task status, changed-path collection, scope matching, and workflow prerequisites to core services. It never runs `git commit`, edits the index, or fixes files.

## Pre-command

Run `python tools/hooks/pre_command.py --action ACTION --target TARGET [--task TASK-ID]` before a normalized external action. A blank target fails before Policy loading, task lookup, or observation construction. An action the active Policy permits automatically does not read `--task` or create an observation. For an active-Policy forbidden canonical high-risk action (`push`, `merge`, `deploy`, `delete`, `secret_export`, or `paid_external_call`), `--task` is optional only when exactly one non-`MERGED` task can be resolved; ambiguity, an invalid explicit task, target-contract failure, or stale binding fails closed. The wrapper records the structured observation through the shared service and then always returns denial (exit 2). It never consumes an action approval and never executes the action, including when an approval exists.

The adapter accepts a structured canonical action and opaque `--target`, not a command line. It does not parse or interpret PowerShell, cmd, bash, aliases, pipes, redirection, quotes, wildcards, variable/command expansion, argv, stdin, environment, stdout, stderr, or credentials. It is neither a general command interceptor nor an OS sandbox.

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
