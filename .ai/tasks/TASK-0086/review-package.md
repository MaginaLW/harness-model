# Single-run SDK review client

## 审核目标

Review fixed subject `c2855df8bd0da26eb888a2e8378bf1dd1bf5feba` against the frozen specification and current native V1 evidence. This task implements and validates the opt-in client; the owner's real subscription run is a separate explicit goal step.

## 背景

The owner selected one actual document-contract review using the existing Codex login, followed by the existing PR feedback reader. The earlier input-only/root-deny sandbox requirement was Agent-added and was removed through a fresh frozen specification and independent design approval. No new execution environment or permission framework is required.

## 代码地图

`src/aiflow/sdk_review.py` provides the isolated module entry point, fixed Git input, report validation and owned runtime lifecycle. `pyproject.toml` and `uv.lock` add the optional pinned SDK/runtime. Separate task-free tests exercise real Git inputs and fake SDK responses; the README and SDK contract document preview, execution and feedback use. The existing CLI and feedback readers are unchanged.

## 语义变更

Default preview never imports or starts the optional SDK. Explicit execution reserves a new ignored output directory, verifies the existing ChatGPT login and actual standard read-only/never/tool-network-disabled configuration, disables unnecessary tools and runs one bounded turn. The application validates the report and binds its own input manifest and lifecycle; unknown or failed runs are not replayed. SDK and runtime are pinned to 0.163.0, while model selection follows the existing configuration.

## 风险

Ordinary read-only is not an input-directory read whitelist or proof of complete model context. Existing global instructions require an explicit expected hash. Normal SDK state and sandbox maintenance may occur; no manual ACL, global configuration, authentication migration or WSL installation is added. Tokens do not establish settled cost or actual model identity. Real scoring, automatic triggers, Desktop attachment, research samples and T0/T1 remain outside this implementation.

## 证据

已验证：current native V1 passed all ten required checks and 3959 tests in 898.82 seconds. Core/analysis total coverage is 89/97 percent; core diff coverage is 95.7 percent, with no analysis source changes. Ruff, format and strict mypy passed. All 101 SDK regressions also passed under the native process runner's exact reduced environment. Actual pinned-runtime metadata-only preflight reached a verified readOnly/never/network-disabled thread and was deliberately stopped before inference; the owned runtime was closed.

Original failures remain preserved: literal quoted MCP override keys, inherited notification configuration/default endpoint recognition, and the first native V1's 32 failures before client construction. Two red counterexamples established the eager Path.home default evaluation; the only subsequent source change makes both explicit CODEX_HOME fallbacks lazy without changing the native environment. Current `evidence.json` and its task-relative logs are authoritative; the previous failed canonical evidence remains in the subject history and its archived run.

未验证：context-bound final implementation review, final Gate, required remote CI/publication, a valid real SDK report and actual PR feedback readback. Offline success does not complete the owner's real engineering pilot or establish statistical or production effectiveness.

## 审核问题

- Do default preview, fixed Git inputs and output reservation prevent accidental runtime construction or replay?
- Do actual SDK method shapes, configuration checks, bounded waits and cancellation/close states preserve failures and unknowns without expanding the existing access baseline?
- Does the final subject include the demonstrated compatibility/home fixes and meaningful regressions while preserving the original gates and evidence?

## 推荐结论

APPROVE for this bounded implementation if independent review finds no unresolved defect; require the current Gate and remote CI before merge. The real authorized run and feedback still require their own actual receipts.
