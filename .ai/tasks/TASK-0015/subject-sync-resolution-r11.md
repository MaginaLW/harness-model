# TASK-0015 mutation-detector synchronized-subject resolution (r11)

- Condition: `spec_changed`
- Previous subject: `c1a66567ba844f51d569aa3adb818febd1a0793e`
- Current synchronized subject: `9d48321d825a09a299bd7df0e70b716b2b598430`
- Required route and verification level: `REVIEW + V2`

The third user-approved action completed a genuine five-mutation run with a canonical immutable artifact. Four mutations were killed and `MUT-V2-003` survived, so V2 correctly failed with `MUTATION_EVIDENCE_NOT_KILLED`. The action is consumed and non-replayable; the failed artifact remains historical evidence and is not promoted to passing evidence.

Independent diagnosis proved that the survivor exposed a declared-detector false negative rather than a production approval bypass. The detector's synthetic artifact independently failed the loader after the target guard was disabled, so its broad rejection assertion still passed. The synchronized subject isolates the guard by forcing only the downstream mutation fact to pass and asserting that baseline code never reaches that seam. Baseline rejects the nonpassing required check; the fixed `MUT-V2-003` operator reaches the passing seam and makes the assertion fail. Production code, manifest identity, operator, and detector reference are unchanged.

Focused regression passed 92 tests. Final branch-coverage verification passed 948 tests with four Windows platform-condition skips; Ruff, formatting, mypy, diff-check, AI Flow validation, 87% total coverage, and 91% task-base diff coverage passed. Two independent reviewers found no P0-P3 issue and marked the retry implementation checkpoint safe.

The specification, Policy, scope, REVIEW/V2 route, permissions, and separate single-use action approval requirement are unchanged. Actions `165b0ba2…` and `afeaeaf1…` are consumed; `36fbb908…` is unused but stale on an older subject. None can authorize this subject. A new explicit user approval is required before any real mutation run. No push, merge, deploy, repository-data deletion, credential use, paid external call, or network call occurred.
