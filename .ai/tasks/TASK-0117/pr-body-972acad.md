## Summary

Permit the project owner’s explicitly authorized, specific push or merge without proactively invoking the pre-command wrapper that always refuses these actions. Preserve explicit or unknown task prohibitions, actual Hook and server refusals, action records, independent review, Gate, required CI and merge commits. The wrapper itself still denies these actions, and its records do not authenticate the actor or enforce single use.

## Verification

- TASK-0117 independently reviewed its design and implementation; its local V1 recorded all 10 required checks passing. The shared pytest run reported 4010 passed and 146 baseline resource-bundle skips. Core coverage was 89%, analysis coverage 98%; the documentation diff has no measurable covered lines.
- The V1 main verifier used independently reviewed CLI source `2cf78ea653b75c421d2fbbde155e55d92e508e78`; a preflight probe verified that its runner children import the target checkout. The guest used a local mirror and independently checked setuptools 84.2.1 outside uv.lock. This is local V1, not the required GitHub check.
- A clean checkout of audit head `972acad880ca52389d9388f7c0d8e56e5f42754a` passed task validation, scope and Gate. Original local logs are not included.

## Action provenance

The owner expressly authorized this bounded exception and conditional delivery. The push approval is bound to subject `fd7c8f239c5e1f2b8e0f4c59f2be8e07be941faa`, audit head `972acad880ca52389d9388f7c0d8e56e5f42754a`, and action SHA-256 `2b5498682f80b07835b954dfd5e9c954537797dacb8cc39019bfde917b1e1707`. It was recorded locally after the audit head, so it is not contained in that head. A PowerShell time-parsing precheck emitted a non-terminating error; the single push proceeded, and independent and subsequent UTC checks confirmed the approval was unexpired. Future preflights must fail closed.

GitHub's required check and the exact PR head must pass verification before a separately recorded merge action. This PR does not alter existing task prohibitions or authorize deployments, force pushes or repository settings changes.
