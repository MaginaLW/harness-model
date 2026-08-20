# Chapter 6: Agent and CI integration

All integration surfaces delegate to the same executable core:

- `AGENTS.md` and `CLAUDE.md` state stable constraints and locations. They guide an Agent but cannot enforce repository state or replace approval.
- The `ai-flow` Skill orchestrates real CLI commands and prepares ASK/REVIEW material. It does not calculate Policy, grant permission, or accept risk for a human.
- `gauntlet.py` delegates verification; pre-commit delegates status/scope/workflow checks; pre-command delegates Policy permission checks. Hooks provide early feedback only and cannot replace CI or protected branches.
- `ai-quality-gate.yml` creates CI evidence and invokes the same read-only Gate for the PR head. It has read-only repository permission, no secrets, and performs no merge or deployment.
- GitHub branch protection makes the named quality check mandatory and controls direct pushes, force pushes, freshness, and audited bypass. Only repository administrators can configure it.

The shared authorities are `aiflow.verification_service.verify_task`, `aiflow.gate.evaluate_gate`, Policy loading, scope assessment, and workflow precondition evaluation. Adapters may format input or output; they must not reinterpret those decisions.

Parity fixtures compare the package decision with local CLI JSON and the CI evidence form of the same Gate call. They cover AUTO pass, missing ASK/REVIEW material, stale evidence, BLOCK, ambiguous task resolution, governance-only attestation, and non-governance tail changes. Rejections remain machine-readable and the fixture sources are hashed before and after evaluation.
