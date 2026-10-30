## Summary

Expand agent autonomy within owner-approved goals and risk boundaries, while keeping genuine ASK choices, existing task prohibitions, independent reviews and quality gates. Separate the conditions and timing for spec, code and local-action approvals so implementation is not blocked by requiring final verification before a spec approval.

## Verification

- TASK-0119 received independent design and implementation reviews and passed all 10 required local V1 checks. One shared pytest run reported 4010 passed and 146 baseline resource-bundle skips. Core coverage was 89%, analysis coverage 98%; the AGENTS.md diff has no measurable covered lines.
- The V1 main verifier used independently reviewed CLI source `2cf78ea653b75c421d2fbbde155e55d92e508e78`; a representative preflight child using the runner minimal environment imported the target checkout. Later V1 children were not individually traced. The guest used a local mirror and independently checked setuptools 84.2.1 outside uv.lock. This is local V1, not the required GitHub check.
- A clean checkout of audit head `ad22ac7401f4617d71563952bf31c454adc73c7b` passed task validation, scope and Gate. Original local logs are not included.

## Action provenance

The owner explicitly authorized this specific rule change and conditional delivery. The push approval is bound to subject `2e8c95dd7d50f1a6c1e95e0a8834fa98dd71396a`, audit head `ad22ac7401f4617d71563952bf31c454adc73c7b`, and action SHA-256 `e098b0d790b4b999f380a33bd9b6fe9749fef9773e3e6e6cd56ffa869e2e6175`. The action record was created locally after the audit head and is not contained in that head.

GitHub's required check and exact PR head must pass verification before a separately recorded merge action. Existing task prohibitions, actual Hook or server refusals, CI thresholds, branch protection and merge-commit requirements remain in force. The repository is configured to delete the merged source branch automatically; the source commit must remain reachable from the merge commit.
