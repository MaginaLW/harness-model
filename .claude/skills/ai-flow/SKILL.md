---
name: ai-flow
description: Orchestrate repository code, configuration, CI, and other behavior-changing work through the executable AI Flow. Purely read-only explanation does not require creating a task.
---

# AI Flow

Use this Skill for work that may change repository code, configuration, CI, generated artifacts, or repository behavior. For a purely read-only explanation or inspection, report findings without creating a task. This Skill coordinates the existing CLI; it grants no permission and never computes Policy decisions itself.

## Governance activation

The project owner has ended bootstrap mode. The bootstrap marker is intentionally absent, and the governed lifecycle below applies to repository code, configuration, CI, and other behavior-changing work. Do not recreate a task-free bootstrap exception without a new explicit project-owner decision.

## Start and inspect

Run `aiflow status TASK-ID` before resuming an existing task. For new work, run `aiflow start ...`, then complete the task decision units and [specification template](../../../.ai/templates/spec.md). Treat the CLI-reported state, current [Policy](../../../.ai/policy/), and task record as authoritative. If a command rejects the state or freshness, stop and follow its recovery guidance instead of editing state files.

## Governed lifecycle

1. In `NEW`, finish the scoped task facts and specification, then run `aiflow classify TASK-ID --actor ACTOR`.
2. Freeze a complete specification with `aiflow freeze TASK-ID --actor ACTOR`. If classification enters `WAITING_FOR_ASK`, prepare the [ASK document](../../../.ai/templates/ask.md) with 2–4 substantively different options, each stating benefits, costs, and risks; obtain the human selection and use `aiflow answer ...`. Do not choose on the human's behalf.
3. If the task is `WAITING_FOR_SPEC_REVIEW`, prepare explicit review questions and obtain direction/risk acceptance before `aiflow approve TASK-ID --type spec ...`. The Agent prepares material; the program validates and records it; a human owns directional and risk decisions.
4. Run `aiflow begin TASK-ID --actor ACTOR` only when the CLI has made the task ready. Implement only the recorded scope. Use `aiflow status TASK-ID` whenever the permitted next step is uncertain.
5. Run `aiflow verify TASK-ID --actor ACTOR`. A targeted or provisional result is diagnostic and cannot replace final evidence.
6. For `WAITING_FOR_FINAL_REVIEW`, complete the [review package](../../../.ai/templates/review-package.md), resolve its explicit questions, and obtain `aiflow approve TASK-ID --type code ...`. Code approval never authorizes an external action.
7. Run `aiflow gate TASK-ID`. A passing Gate records readiness; it does not push, merge, deploy, spend money, use credentials, or perform another external action.
8. After an authorized actor completes the merge externally, record that fact with `aiflow close TASK-ID --actor ACTOR --merge-commit COMMIT`.

## Escalation and recovery

Run `aiflow escalate ...` when scope expands, a new dependency appears, permissions/network/credentials are needed, verification becomes unavailable, or failures repeat. Also escalate when risk, specification, or Policy changes invalidate the current decision. Do not lower route or verification level. For an `ESCALATED` or `BLOCKED` task, record current task-local evidence with `aiflow resolve ...`, then re-run classification only as the CLI permits.

Never edit task state directly, fabricate evidence, skip required commands, replace a required human decision, or use code approval as action approval. An action approval only records a version-bound authorization; it does not perform the action. Stop before every destructive or external action and obtain its separate approval.

Use [AGENTS.md](../../../AGENTS.md) for stable repository principles and the [implementation guide](../../../docs/implementation/chapter-04-governance-workflows.md) for user-facing governance examples. The CLI help and executable Policy remain the source of current commands and determinations.
