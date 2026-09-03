# TASK-0031 PR #3 CI receipt

- Pull request: `https://github.com/MaginaLW/harness-model/pull/3`
- Base: `main@0989da65702a756c229b0dc7a1c14d56639ad384`
- Head/attestation: `codex/formal-ci-canary-r2@ff7c78c6c4028a32ee78ff1c95af2ff9db68d110`
- Required check: `ai-quality-gate` — `COMPLETED/SUCCESS`
- Actions run: `33495236530`
- Job: `99815763364`
- Run event: `pull_request`
- Run conclusion: `success`
- Started: `2026-09-01T10:01:14Z`
- Completed: `2026-09-01T10:07:01Z`

## Formal-path results

- Bootstrap quality checks: skipped as required for formal governance mode.
- Locked environment installation, governance detection, exact-head branch attachment, contract
  validation, repository identity, and TASK-0031 resolution: passed.
- `Verify and Gate`: passed.
- CI evidence: V1, `mode=ci`, `conclusion=passed`, 10/10 required checks passed, no reason
  codes, subject `f75f59e9ac245cebc75f4052fbdbd80604376aa7`, attestation head
  `ff7c78c6c4028a32ee78ff1c95af2ff9db68d110`, and governance-only attestation true.
- Unit tests: passed.
- Regression: `1603 passed` on Linux.
- Coverage: `1603 passed`; coverage XML generated.
- Diff coverage: passed; the documentation-only diff had no coverable lines.
- External Gate: `passed=true`, empty `reason_codes` and `recovery_argv`.

## Diagnostics artifact

- Name: `ai-flow-TASK-0031`
- Artifact ID: `9795615054`
- Artifact digest: `sha256:bc50e056ca01d7f0ff88145f10741cc77a92cc06ee077d00b879f16388e0b343`
- Size: `28721` bytes
- Expires: `2026-09-15T10:06:54Z`
- Downloaded evidence file SHA-256:
  `a1949b1882399b8e1df1423c4a762debd6e93365b1bf22ace2ce154632eb68d9`
- Downloaded Gate file SHA-256:
  `d69efb9b43f76e921257e51b0a034327d4b8d5aecdebaae67eacc3ba11502419`

The artifact was downloaded to a uniquely named OS-temporary directory for read-only
verification. Only that verified temporary directory was removed afterward; the GitHub artifact
and durable PR/check records remain unchanged.
