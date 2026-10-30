## Problem and change

New task records can store the creating checkout's absolute path, and verification evidence can include known local paths in command summaries or CI reproduction commands. Sharing these artifacts can expose local environment details.

New task creation omits the optional creation path. Newly generated command summaries replace the known Python executable, repository root and verification run directory with placeholders; CI reproduction commands use placeholders for the run directory and evidence output. Actual execution arguments, environment, timeouts, output locations and result parsing remain unchanged, as does existing secret redaction. Older task records, recovery markers, evidence and logs retain their original contents and behavior.

The replacement is limited to known paths. It does not promise to anonymize arbitrary paths, test output, raw logs or historical records. Review any material intended for publication separately.

## Validation and review

- TASK-0120 native local V1 on subject `669364e00e4b045760e03ccdfecdde25b7a47f11` passed all 10 required checks. One shared pytest run reported 4029 passed and 146 baseline resource-bundle skips. Core coverage was 89%, analysis coverage 98% and core diff coverage 90%.
- Independent design review `REV-0001` and implementation review `REV-0002` approved the bounded change. A clean checkout of audit head `0504a5c258d09d66a3b874d04b921d32bf6e8762` passed task validation, scope and Gate.
- The target checkout's own CLI executed local V1 in an isolated guest using a loopback mirror and independently checked setuptools 84.2.1 outside uv.lock. Raw logs are not included. GitHub required CI for the actual PR head remains pending.

The task-free test-first commit and the governed source change are delivered together. Tests cover new and legacy task creation and recovery, real execution and secret handling, known-path boundaries and CI reproduction placeholders.

## Delivery conditions

The project owner authorized this bounded delivery. The push approval is bound to subject `669364e00e4b045760e03ccdfecdde25b7a47f11`, audit head `0504a5c258d09d66a3b874d04b921d32bf6e8762`, and action SHA-256 `29431fcec735ce54f0d09df3e48f62b5c9d6c7621842b1efd36516b242b89adc`; it was recorded locally after the audit head and is not included in that head. The owner-authorized hook exception does not override an installed Hook or a server refusal. Retain existing task restrictions, independent review, Gate, branch protection, required checks and merge-commit rules. The repository is configured to delete the already-merged source branch automatically; the source commit must remain reachable through the merge commit.
