# TASK-0018 paid external call incident

## Recorded facts

- During an independent read-only implementation review, the Codex native sub-agent
  `/root/task17_architecture` started
  `C:\Users\Admin\.grok\bin\grok.exe` with model `grok-4.6`.
- The request reached the external service and returned with `stopReason: cancelled`.
- The returned usage report listed `total_cost_usd: 0.0112557`.
- The call produced no file changes and no completed review findings or readiness
  conclusion. No Grok output is accepted as TASK-0018 evidence.
- TASK-0018 explicitly forbade `paid_external_call`; therefore the invocation was
  unauthorized and was recorded as event 14 with reason `new_permissions`, moving the
  task from `IMPLEMENTING` to `BLOCKED`.

## Cause and containment

The repository-wide `AGENTS.md` permits Grok Build as an optional external reviewer,
but the delegated review prompt did not restate TASK-0018's narrower prohibition.
The sub-agent selected the global optional reviewer despite the task-local forbidden
action. The primary agent stopped implementation as soon as the completed call and
reported cost were disclosed.

For the remainder of TASK-0018:

- all implementation, review, and verification work is local;
- Grok and every other external or paid service are prohibited;
- native sub-agent prompts must state the external-call prohibition explicitly;
- existing uncommitted work is preserved and reassessed;
- this incident record is not retroactive approval and grants no new permission.

## Authorized recovery

The user confirmed that this incident must remain recorded, existing work should be
preserved, later external or paid calls remain prohibited, and only local tools may be
used to resolve the block and reclassify TASK-0018 to `REVIEW / V1`. Any subsequently
required spec approval remains version-bound and must be recorded through AI Flow
before implementation resumes.
