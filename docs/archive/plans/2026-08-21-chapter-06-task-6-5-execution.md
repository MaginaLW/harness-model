# Chapter 6 / Task 6.5 Execution Plan

**Goal:** Prove that package, local CLI/wrapper, and CI Gate entrypoints preserve the same deterministic decision and do not mutate governed inputs.

**Route / verification:** REVIEW / V1.

**Allowed scope:** `tests/integration/test_gate_parity.py`, `tests/fixtures/parity/`, `docs/implementation/chapter-06-agent-ci.md`, and Chapter 6 / overall progress records.

**Forbidden actions:** no production rule changes, external CI run, GitHub administration, push, merge, deployment, credential access, or mutation of fixture source records.

## Steps

1. Add eight parity scenarios for pass, missing ASK/REVIEW material, stale evidence, blocked work, ambiguous task resolution, governance attestation, and out-of-scope tail changes.
2. Compare structured package and local/CI command results using the same Gate decision.
3. Hash fixture sources before and after every entrypoint and require machine JSON on rejection.
4. Document what Agent, Skill, Hook, CI, and branch protection can and cannot enforce and identify their shared core interfaces.
5. Run focused and full verification and record completion evidence.
