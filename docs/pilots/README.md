# Chapter 7 controlled pilots

These pilots exercise the repository's own AI Flow lifecycle in four isolated local Git
worktrees. They do not push, merge, deploy, delete worktrees, or perform a real external action.

| Pilot | Branch | Worktree | Governed business change |
| --- | --- | --- | --- |
| AUTO | `pilot/auto-doc` | `../harness-model-pilot-auto` | Add `docs/operations/evidence-expiry-example.md` |
| ASK | `pilot/ask-report` | `../harness-model-pilot-ask` | Create only the report format selected by the user |
| REVIEW | `pilot/review-policy` | `../harness-model-pilot-review` | Add `package_publish` to forbidden automatic actions plus tests |
| BLOCK | `pilot/block-dry-run` | `../harness-model-pilot-block` | Preserve scenarios and create only a dry-run inventory |

All four branches start at the same `pilot_base`. Durable, sanitized results live outside Git in
`../harness-model-pilot-artifacts/PILOT-*`; each task's authoritative governance record remains in
that task's own worktree.

Use [pilot-runbook.md](pilot-runbook.md) for the authorization points, commands, evidence fields,
and completion checks.
