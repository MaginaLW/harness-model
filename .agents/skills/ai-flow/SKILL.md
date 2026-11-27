---
name: ai-flow
description: Orchestrate repository code, configuration, CI, and other behavior-changing work through the executable AI Flow. Purely read-only explanation does not require creating a task.
---

# AI Flow

Use this Skill for work that may change repository code, configuration, CI, generated artifacts, or repository behavior. For a purely read-only explanation or inspection, report findings without creating a task. This Skill coordinates the existing CLI; it grants no permission and never computes Policy decisions itself.

## Governance activation

Whether a change needs a task, and what maintenance mode does not relax, is decided by [AGENTS.md](../../../AGENTS.md), the single shared authority; this Skill does not restate it. When you take a change through AI Flow, the governed lifecycle below applies in full.

## Start and inspect

Run `aiflow list` (optionally `--all`, repeatable `--state <STATE>`, `--format json`) to inspect current tasks read-only, and `aiflow status TASK-ID` (and optionally `aiflow advise TASK-ID` for read-only, non-scoring next-step guidance) before resuming an existing task. For new work, run `aiflow start ...`, then complete the task decision units and [specification template](../../../.ai/templates/spec.md). Treat the CLI-reported state, current [Policy](../../../.ai/policy/), and task record as authoritative. If a command rejects the state or freshness, stop and follow its recovery guidance instead of editing state files.

## Governed lifecycle

1. In `NEW`, record explicit risk facts with `aiflow facts TASK-ID ...` and complete the specification, then run `aiflow classify TASK-ID --actor ACTOR`.
2. Freeze a complete specification with `aiflow freeze TASK-ID --actor ACTOR`. If classification enters `WAITING_FOR_ASK`, prepare the [ASK document](../../../.ai/templates/ask.md) with 2–4 substantively different options, each stating benefits, costs, and risks; attach the compact `A01` optional `0–3` interruption-rating prompt, obtain the human selection, and use `aiflow answer ...`. Do not choose on the human's behalf.
3. If the task is `WAITING_FOR_SPEC_REVIEW`, prepare explicit review questions and, when human direction or non-delegated risk acceptance is actually required, attach `A01 | optional 0–3` before `aiflow approve TASK-ID --type spec ...`. The Agent prepares material; the program validates and records it; a human owns directional and risk decisions.
4. Run `aiflow begin TASK-ID --actor ACTOR` only when the CLI has made the task ready. Implement only the recorded scope with surgical changes, reuse existing helpers first, keep defensive validation at untrusted/I/O boundaries, and execute in-workspace checks directly without unnecessary prompt-triggering command wrappers. Use `aiflow status TASK-ID` whenever the permitted next step is uncertain.
5. After committing within scope, run `aiflow sync TASK-ID --actor ACTOR` before `aiflow verify TASK-ID --actor ACTOR`. A targeted or provisional result is diagnostic and cannot replace final evidence; avoid speculative test bloat or unrequested full-suite loops.
6. For `WAITING_FOR_FINAL_REVIEW`, complete the [review package](../../../.ai/templates/review-package.md) including the five-point delivery-boundary check, resolve its explicit questions, attach `A01 | optional 0–3` when requesting human approval, and obtain `aiflow approve TASK-ID --type code ...`. Code approval never authorizes an external action.
7. Run `aiflow gate TASK-ID`. A passing Gate records readiness; it does not push, merge, deploy, spend money, use credentials, or perform another external action.
8. After an authorized actor completes the merge externally, record that fact with `aiflow close TASK-ID --result merged --actor ACTOR --merge-commit COMMIT` and summarize `S / Q / U / H` decision opportunities (`S`=Stop/Wait, `Q`=Self-questioned/Deferred, `U`=Unneeded interruption, `H`=High-value guard) solely from observed facts without creating an external private ledger.

## Escalation and recovery

Run `aiflow escalate ...` when scope expands, a new dependency appears, permissions/network/credentials are needed, verification becomes unavailable, or failures repeat. Also escalate when risk, specification, or Policy changes invalidate the current decision. Do not lower route or verification level. For an `ESCALATED` or `BLOCKED` task, record current task-local evidence with `aiflow resolve ...`, then re-run classification only as the CLI permits. For an interrupted `VERIFYING` run (REC-11), confirm no verification process is still running, then use `aiflow verify TASK-ID --abandon ...` before retrying via `aiflow begin TASK-ID --actor ACTOR` and re-running full verification.

When any step stops to ask the user or handle a `0/1` or repeated-interruption signal, fix the execution misread immediately in the same turn, propose an exact project-rule diff (applying minimal permission rule consolidation across adjacent operations rather than broad wildcards, and asking opt-in permission before drafting any host popup-reduction rules after more than two low-score interruptions), and specify the four-part window tuple (`trigger_source`, `check_window`, `stop_condition`, `consecutive_failure_cap`) for any timed wait or polling loop.

Never edit task state directly, fabricate evidence, skip required commands, replace a required human decision, or use code approval as action approval. An action approval only records a version-bound authorization; it does not perform the action. For destructive or external actions, consult the standing authorization in [AGENTS.md](../../../AGENTS.md) under “常设授权”. Act only when its conditions are met and the task permits the action. Obtain separate owner approval for actions outside that authorization.

Use [AGENTS.md](../../../AGENTS.md) for stable repository principles and the [implementation guide](../../../docs/implementation/chapter-04-governance-workflows.md) for user-facing governance examples. The CLI help and executable Policy remain the source of current commands and determinations.
