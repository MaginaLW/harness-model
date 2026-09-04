# Chapter 6 / Task 6.4 Execution Plan

**Goal:** Add a least-privilege pull-request quality Gate that produces authoritative CI evidence and deterministic Gate output.

**Route / verification:** REVIEW / V1.

**Allowed scope:** `.github/workflows/ai-quality-gate.yml`, `tools/ci/resolve_task.py`, `tests/integration/test_github_workflow.py`, `docs/operations/github-branch-protection.md`, and Chapter 6 / overall progress records.

**Forbidden actions:** no secret access, write permission, `pull_request_target`, deployment, branch-protection mutation, push, merge, or external repository administration.

## Steps

1. Define pull-request triggers, read-only permissions, concurrency cancellation, timeout, full history, and Python 3.11 installation.
2. Resolve exactly one task from explicit input/environment or base-to-head task paths and pass that output to both CI verify and Gate.
3. Upload only the runner-temp evidence, Gate JSON, and redacted logs for fourteen days, even on failure.
4. Document the administrator-owned branch-protection checklist and bypass audit boundary.
5. Test workflow structure and absence of dangerous trigger/permission forms.
6. Test resolver boundaries, command dataflow, repository identity independence from checkout path, and fixed-subject Gate enforcement.
7. Run focused and full verification and record completion evidence.
