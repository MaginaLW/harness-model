# Agent Bridge Full Engine Integration Execution Plan

> **For agentic workers:** Follow applicable delegation and workspace rules; execute independent tasks in parallel when permitted and useful, and review their results.

**Goal:** Deliver installed-engine V2, Node CI and a reviewed, non-overwriting agent-bridge application using that repository's own identity, rules, tasks and checks.

**Approach:** Reuse delivered resource distribution, initialization and Node local V0/V1. First establish fixed installed-engine mutation execution/replay, then connect the complete Node V2 lifecycle, then implement same-candidate CI and real-target acceptance. The owner has explicitly reopened this complete scope; real target application waits for the active target session to finish and a fresh ownership/baseline check.

**Materials:** [Installed-engine mutation design candidate](../specs/installed-engine-governance-mutations.md), [Node verification](../../operations/node-verification.md), [initialization](../../operations/initialization.md), [resource bundle](../../operations/resource-bundle.md), [cross-repository boundaries](../../operations/sdk-and-engine-plan.md#完整引擎跨仓初始化), current source and target `AGENTS.md`, target `package.json` and `docs/local-bridge.md`.

**Validation:** Ordinary source wheel and sdist-rebuilt wheel are verified outside the source checkout; five real fixed mutations and rejection paths replay from originals; complete independent local V2 and same-candidate CI reach their applicable Gate; both repositories retain their original checks. Real target adoption requires its own reviewed diff, applicable natural task and verifiable target results.

---

## Dependencies and ownership

The strong serial chain is current candidate/contracts → pretest rebuild compatibility → installed mutation primitive/replay → complete Node V2 consumers → CI original-material handoff → disposable end-to-end acceptance → target application after target-session completion. Do not open a public capability before all its consumers are ready. A V0/V1 success is not complete V2/CI support.

Suggested concurrency is **3–4 agents including the integrator**. Before implementation, mutation/probe research and Node lifecycle/CI consumer mapping may run independently. After contracts freeze, divide source writing by module; keep shared Schema/Policy, snapshot and consumer integration with one integrator. Companion tests/docs may use a separate owner only after signatures stabilize. Independent reviewer/verifier receives a fixed candidate and does not edit its implementation. Final integration, reviews, verification and commits are serial.

## Task 1: Freeze the current source and acceptance contracts

**Artifacts / Locations:** Review source `AGENTS.md`, native Policy, `src/aiflow/{policy,verification,node_execution,evidence,approval,gate}.py` and the linked design; use the CLI ledger for governed specifications and decisions.

- Preserve prior failed/blocked tasks, spent actions, unmerged candidates and existing WIP. Keep companion tests/docs and governed implementation separate; do not rewrite frozen scope or borrow old approvals.
- Recheck the delivered Node V0/V1 contract, installed-engine material inventory, existing five mutations and every affected consumer. Freeze exact new profile/evidence/Policy, artifact and failure-attribution contracts before activation.
- Prepare one narrowly scoped governed task for the installed mutation primitive. Keep safe companion tests/docs separate according to project rules. Verification, task facts and approvals use current CLI conclusions rather than copied historical status.
- Exit: independently reviewed frozen scope and reproducible check commands, with all original checks and thresholds retained; no Node V2/CI capability claim.

## Prerequisites: Keep validation inside the workspace and preserve pretest

First propagate only the three fixed standard temporary-directory roles from a validated caller-selected root into native check subprocesses. Keep Policy environment choices and verification argv closed. Use an exact acceptance clone and a sibling temporary root within the selected project workspace, and retain the complete task and originals in that acceptance clone. No system temporary-directory exception or retired CLI option is assumed.

The target currently uses `pretest: npm run build`; removing it would lose its stale-build protection. Reproduce the existing fixed runner's rejection with a real ordinary-wheel fixture. In a separate source-only task, permit replacement of dist identity only after the successful fixed check and only when every path, kind, size and content digest equals the separately verified build. Retain both inventories for read-only replay; all other phases retain identity protection. Prove V0/V1 acceptance and rejection of changed/extra/missing/unsafe output before proceeding.

The target also needs the fixed test flags and the exact coverage provider expected by the supported profile. Prepare these as a separate target diff after its active session finishes. Its current instructions do not declare coverage thresholds: the profile's 85% total/90% changed TS line thresholds are proposed new target requirements and must be explicitly included in the reviewed target Policy, not described as pre-existing gates.

## Task 2: Execute and replay fixed installed-engine mutations

**Artifacts / Locations:** Implement fixed package-owned probes/runner/replay and their bound declarations; extend packaging/material binding only as required. Companion tests exercise an installed wheel, not the source import path.

- Follow the design's exact five consumer/operator mappings, isolated installed-byte copies, loaded-module checks and stage/assertion attribution. No arbitrary mutation or command API.
- Reuse existing inventory/copy budgets, Windows Job process protection and current single-use action transaction rules. Retain immutable raw evidence and expose one zero-write/zero-process replay consumer.
- Build a direct wheel and sdist/rebuilt wheel. Outside the checkout and without parent resources, run five actual baseline/mutant pairs; replay originals independently. Prove survived, unrelated assertions, phase/import failures, malformed reports, process failure, changed engine/materials, concurrent launches and interruption reject.
- Run independent review, current native verification and required CI for this source-only slice. Exit: installed mutation primitive/replay proven, native safeguards unchanged, Node V2 still explicitly rejected.

## Task 3: Connect the entire local Node V2 lifecycle

**Artifacts / Locations:** Governed Policy/Schema, verification and Node execution, evidence/snapshot, verifier/review, approval/recovery, freshness/status and Gate consumers; separate companion lifecycle tests and use documentation. Follow the explicit [Node V2 installed lifecycle contract](../specs/node-v2-installed-lifecycle.md). The native installed-engine primitive is delivered in [PR #147](https://github.com/MaginaLW/harness-model/pull/147), with both ordinary origins, independent native verification, implementation review, Gate and current-head required CI accepted. Preserve its immutable acceptance originals. The separate local Node V2 candidate still requires its complete ordinary-installed lifecycle and its own source gates before publication.

- Implement the reviewed new profile/evidence version while preserving existing Node V0/V1 and native Python contracts. Full V1 remains the prefix; fixed target acceptance/integration, actual installed mutations and independent verifier are required.
- Extend the five probes to the real Node V2 guard paths and verify their public-consumer reachability. Do not count probes against only the native evidence branch as Node protection.
- Implement task-bound pre evidence, implementation review of its stable snapshot and same-verifier finalization. Code approval and Gate reject pre, stale or incomplete evidence. Every production consumer replays the same originals; reject unavailable capability before recovery/writes/processes.
- In independent Git fixtures with an ordinary wheel, run task/facts/classification/spec/design → independent verify/pre → implementation review → same verifier/final → code approval/Gate. Test all five safeguard failures and subject/spec/Policy/classification/context/review/snapshot/engine/material drift.
- Exit: independently reviewed local installed V2 success and rejection evidence, plus current native verification and required CI. Node CI and real-target adoption remain unclaimed.

## Task 4: Add Node CI with reproducible originals

**Artifacts / Locations:** Fixed artifact transport/CI consumer and target workflow candidate; preserve existing source CI and its thresholds.

- Freeze the exact content inventory, relative references, limits and local-versus-CI host identities. Do not rewrite local absolute paths/inodes into fictitious current facts. Review authorized material transfer separately from artifact validation.
- Build/install the same declared engine content and prepare fresh CI materials. Check the exact target subject, full checks, coverage and actual engine mutations; retain receipts and originals for read-only replay.
- Bind CI to current local-final evidence, verifier/context and design/implementation reviews. Gate requires both; missing originals, public-summary-only input, wrong head or changed engine/dependencies must reject.
- Run supported-runner local/CI fixtures and independent review, native verification and required CI. Exit: actual same-candidate CI acceptance and rejection results, with no assumption that remote branch protection is configured.

## Task 5: Apply to agent-bridge after target work finishes

**Artifacts / Locations:** Target's exact initialization preview/review, `.ai` installation and separately reviewed instruction/workflow diffs; preserve target history and WIP.

- Wait for the active target session, then re-read its instructions, Git identity/branch/HEAD, `.ai`, scripts, CI and worktree ownership. Do not stash/reset/overwrite or include other work in integration commits. If ownership remains uncertain, retain a reviewable candidate and withhold target writes.
- Rehearse the exact target Policy/profile against the independently installed wheel and disposable source snapshot. Preserve original target checks and verify unsupported inputs, conflict, interrupted init, stale evidence and full V2/CI failure paths.
- Review and apply the non-overwriting initialization; instruction and workflow changes remain explicit diffs. Establish a new target identity, not this repository's UUID, maintenance marker, approvals or standing authorization.
- Use a naturally occurring target task for full acceptance. If none is available, mark real-task acceptance incomplete instead of manufacturing a business change. Run both repositories' applicable original checks; inspect actual target CI and remote protection without treating local Gate as their substitute.
- Exit: concrete target changes and task/evidence/Gate/CI results reviewed and delivered under target rules. Production, credentials, model/WeChat calls and repository settings are outside this integration unless separately authorized.

## Final verification and delivery

Inspect final source and target diffs independently, including all new files and ignored evidence locations. The source retains complete tests, all required checks, 85% total/90% diff coverage, whitespace, Ruff, format, mypy, five original mutations and branch protection. Target checks remain target-owned. Commit only each reviewed, verified slice; publishing and merge follow each repository's applicable authorization and current-head checks. Report implemented capability, observed evidence and remaining incomplete acceptance separately.
