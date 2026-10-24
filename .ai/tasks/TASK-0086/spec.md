# Task Specification

## 目标

Implement the smallest opt-in SDK client needed for one self-managed, read-only document-contract review and prepare its actual engineering acceptance. This implementation task covers code and offline validation; a real SDK call is a separately explicit execution step of the owner's active goal, never part of normal verification.

## 范围

Add one isolated `src/aiflow/sdk_review.py` module, without adding commands to the existing AI Flow CLI or changing native review/feedback readers. Add the optional, exactly pinned `openai-codex==0.163.0` dependency and update the lock. Keep the ordinary install and offline checks independent of SDK construction.

Prepare a request from complete Git commits, explicitly selected ordinary UTF-8 `docs/**` blobs and one question. Reject unsafe paths, symlinks, duplicate selections, unavailable objects and excess bytes. Bind a portable manifest and hash to the actual application-supplied prompt. Current working files and later PR heads cannot replace the fixed candidate. Inherited global instruction sources, when intentionally selected, require an explicit expected hash and must be separately declared; unexposed internal model context is unknown.

Default preview never imports or constructs the SDK, creates its runtime or calls a model. Explicit execution requires an unused ignored output location and the pinned SDK/runtime, uses the existing ChatGPT login only, and never copies credentials or enables API-key billing. Use the official SDK transport, no custom JSON-RPC transport or alternate provider fallback.

Before the sole model turn, check actual configuration and thread receipts. Use the supported SDK read-only preset with approval never and network access disabled; disable shell, external search, MCP, plugins and subagents not needed for this fixed-text review. Retained built-ins do not mean zero tools. Ordinary read-only prevents model file writes; it does not provide an input-directory read whitelist or authenticate complete model context. The earlier root-deny profile, outside-read canary and Windows rejection were Agent-added hardening, not owner requirements, and are removed from this first engineering pilot. Do not install WSL, create other execution environments, migrate credentials, manually change ACLs or write global configuration. Normal SDK/runtime state and sandbox maintenance must be described honestly rather than claimed absolutely side-effect free. Never persist raw configuration or credentials.

One turn has a 120-second client wait and at most 10 seconds for cancellation confirmation; request interruption without retrying, distinguish confirmed final interrupted/completed from unknown, and close only the owned runtime. SDK initialization, thread creation and shutdown also need bounded waits. Record token usage separately from unknown settled cost and actual model identity. Output uses a small inline schema for outcome/summary/findings, unique RF identifiers and locations within supplied candidate files. The application binds candidate, manifest, versions and lifecycle; the model cannot self-certify them. Invalid output or incomplete execution is not success; preserve failures and prevent output reuse from replaying a call.

Companion tests in `tests/unit/test_sdk_review.py` and documentation in the explicitly allowed README and operations/spec paths are separate task-free commits. Use the existing PR v1/v2 feedback format after the real report; do not invent GitHub native reviews or fake capture input. A docs-only candidate for this real development need is engineering_pilot, not a statistical observation or independent sample.

## 非目标

No background scheduler, automatic trigger, real scoring, calibration, statistical-window start, Desktop attachment, cross-repository initializer, generic provider layer, new feedback Schema/database, authority or permission relaxation. Keep T0/T1 unset and existing route/V, quality thresholds and historical artifacts unchanged. No global configuration edit, credential export, API-key call, purchase or automatic retry.

## 验收条件

- Meaningful input, default-zero-start, output, standard read-only/never/configuration receipts, lifecycle, interruption, failure, timeout and duplicate-run tests pass without constructing a real SDK runtime in ordinary verification. Tests must reject write-capable/network-enabled or unexpected authentication/configuration receipts, without inventing unsupported input-only filesystem guarantees.
- Validate actual pinned SDK method/response compatibility using the isolated installed package, without a model call. Runtime preflight and real acceptance remain explicit, bounded goal steps.
- Full native V1 passes all required checks: complete pytest, separate core/analysis 85 percent totals and 90 percent diff coverage, Ruff, format, strict mypy and whitespace. Independent design/implementation review, Gate and required CI pass before publishing the implementation with merge commits.
- Documentation gives executable install/preview/run/feedback instructions, actual limitations and current status. Goal completion still requires a real valid report and actual PR feedback readback; offline success alone does not complete it.

## 禁止动作

Deploy, delete, secret_export and paid_external_call remain forbidden. No additional spending or API-key billing is included. Publication of the offline implementation follows existing standing authorization after its review and checks. The owner has separately selected the existing Codex login/subscription for the bounded goal execution; never infer new purchases or broader connection rights.

## 错误行为

Return bounded errors without raw prompts, credentials, private paths or configuration. No partial success, silent downgrade, automatic retry or replay. Keep a started/failed/unknown receipt rather than overwrite or call again after uncertain I/O. Do not infer runtime shutdown, cost, identity or complete model context from a local timeout or an opaque label. Continue independent implementation work when a genuine external condition remains missing.

## 回滚

Normal reviewed revert; optional SDK is unused unless explicitly invoked. Preserve original task events, reviews, failed receipts and runtime attempt evidence. Never rewrite published history or remove existing authority/quality gates.
