# Controlled pilot runbook

## Fixed boundaries

- Chapters 1–6 and the four golden E2E scenarios must pass before `pilot_base` is recorded.
- The main worktree must be clean. Every target worktree and artifact path must be an explicit
  sibling of the main repository and must not already exist.
- Local branch, worktree, and commit creation require user authorization. The user's instruction
  to continue and complete Chapter 7 authorizes these local writes for this run.
- Push, merge, deployment, deletion, paid calls, credential access, and real external actions are
  outside that authorization.
- Every worktree must retain the same `.ai/repository-id` and begin at the same `pilot_base`.

## Worktree registry

| Artifact ID | Branch | Worktree | Expected route |
| --- | --- | --- | --- |
| `PILOT-AUTO` | `pilot/auto-doc` | `../harness-model-pilot-auto` | AUTO |
| `PILOT-ASK` | `pilot/ask-report` | `../harness-model-pilot-ask` | ASK |
| `PILOT-REVIEW` | `pilot/review-policy` | `../harness-model-pilot-review` | REVIEW |
| `PILOT-BLOCK` | `pilot/block-dry-run` | `../harness-model-pilot-block` | BLOCK, then an authorized safe recovery |

Before operating in a worktree, compare its absolute path, current branch, HEAD, and repository ID
with this registry and the external `pilot-base.txt`. A Gate decision is valid only in its matching
worktree at that pilot's recorded attestation HEAD.

## Human decision and approval points

- ASK presents Markdown, JSON, and dual-format options. A real user chooses one; the implementer
  must create only that selected output. No default or inferred choice is permitted.
- REVIEW requires spec approval before implementation and code approval after V1 evidence. The code
  approver must be someone other than the implementer or an explicitly independent reviewer.
- BLOCK first proves the deletion request is denied. Recovery records evidence and changes the work
  to a dry-run inventory; files under `examples/scenarios/**` are never deleted or modified.
- An action approval never substitutes for spec or code approval and never executes an action.

## Artifact contract

Each `PILOT-*` external directory contains, at minimum:

- `task-id.txt`, `pilot-base.txt`, `branch.txt`, and `repository-id.txt`;
- a sanitized summary of task state sequence, classification route and V level, approvals, key
  commands, human observations, and explicitly unverified items;
- `ci-evidence.json` produced first in a fresh operating-system temporary directory;
- deterministic `gate.json` produced against that external evidence;
- recorded `subject_commit` and `attestation_head` values.

Do not copy complete raw logs, absolute temporary paths, credentials, tokens, or unrelated task
records into the artifact directory.

## Per-pilot completion

1. Create the AI Flow task with exact scope and forbidden actions.
2. Confirm classification; never lower route or V manually.
3. Complete required answer/freeze/approval steps before `begin`.
4. Commit only the declared business change, run local verification, and retain its evidence.
5. Commit only the current task's governance attestation where required.
6. Run CI read-only verification in a fresh OS temporary directory, then Gate with that evidence.
7. Copy sanitized outputs to the matching external artifact directory and re-check version bindings.
8. Run the repository test suite in that same worktree.

Pilot completion does not authorize pushing, merging, deleting branches/worktrees, or re-running an
old pilot's Gate from a later pilot branch.
