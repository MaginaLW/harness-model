# Task Specification

## 目标

Prepare one default-off, explicitly enabled SDK document supplement immediately after successful generation of a native implementation-review context. The local implementation, simulation and review do not activate a real model or publish anything.

## 范围

Extend the existing `aiflow review context TASK --stage implementation` node with an explicit `--sdk-review-enable-once` flag and explicit candidate documents, reference documents, question, unused ignored SDK output directory and optional expected global-instruction hash. No SDK-related flag is enabled by default. Partial supplemental options without the enable flag, the design stage, missing required input and unready or stale native facts must reject before SDK import, construction or execution.

Generate the native context with the existing builder. For the supplemental node, require native status WAITING_FOR_FINAL_REVIEW with fresh classification and passed evidence, and exact context/subject/base/repository binding. Recheck the current context immediately before dispatch. Use the context's fixed subject as candidate and its base as reference, never the observed HEAD. Candidate documents must be explicit changed `docs/**` paths from this context; reference documents and one concrete question are explicit. Reuse `prepare_request` to read fixed ordinary Git blobs and enforce existing limits.

Extract the existing SDK execution block into one shared function in `sdk_review.py`, used by the standalone entry point and this node. Preserve existing standalone preview/execute behavior, optional dependency, existing login, pinned SDK/runtime, standard read-only/never/tool-network-disabled configuration, 30-second startup, 120-second turn, 10-second cancellation and 5-second close waits, report validation and unused output reservation. Record a small application-owned trigger binding (node, task ID and context hash) in the supplemental receipt; it is a supplied binding, not authenticated model identity or execution authorization.

One explicitly enabled invocation may dispatch at most one existing SDK turn. A failed or unknown result is retained and never retried; the same output directory is never reused. Distinct explicit invocations are not claimed globally exactly-once, and new real calls require their own concrete scope decision. A completed REQUEST_CHANGES report remains that conclusion, not an execution failure or approval.

The native context's normal stdout/file output stays compatible; supplemental status goes to stderr. An invalid input or failed/unknown supplemental execution returns failure without replacing the native context, creating a formal review record, approving code, resolving findings or advancing the task. Reuse the existing manual report/PR feedback path. Add no feedback exporter, new module, dependency, configuration file, scheduler, service or persistent queue. Companion tests and durable usage documentation are separate task-free commits.

## 非目标

No real SDK turn, repeated pilot, automatic external report, push, PR, merge, deployment, statistical scoring/routing, T0/T1, research sample admission, Desktop attachment, continuous observation, WSL/infrastructure installation, credential migration or security-access expansion. The node is prepared locally with simulated execution; activation remains a separate concrete decision.

## 验收条件

- Default context generation is unchanged and does not import even the SDK runner module, construct its client, create its runtime or call a model.
- Real Git/context tests and fake runners cover success, completed REQUEST_CHANGES, failure/unknown, disabled/partial flags, wrong stage, missing input, stale evidence/classification, wrong binding, unselected or unchanged paths, HEAD differing from subject, and output reuse. Rejection occurs before dispatch, and accepted paths dispatch once with the original candidate/reference and explicit material. Native task state/reviews/approvals remain unchanged by the supplement.
- Existing standalone SDK regressions pass after the shared-function extraction, including original lifecycle, interruption, timeout and failure behavior. Tests never start a real SDK runtime.
- Full native V1 retains all required checks, complete pytest, separate core/analysis 85 percent totals and 90 percent diff coverage, Ruff, format, strict mypy and whitespace. Independent design/implementation review and local Gate pass; external publication and required remote CI are outside this local-preparation authorization.
- Documentation specifies the node, default-off behavior, exact future activation inputs and existing feedback path, preserving old failures/unknown/candidate mismatch. It does not treat an enable flag or local actor string as human authorization, certify complete context, or claim production activation.

## 禁止动作

Push, merge, deploy, delete, secret_export and paid_external_call remain forbidden. No extra real model call or external communication. Do not retry or replace any previously rejected external action. Do not alter Policy, authorization files, quality thresholds, global configuration, authentication or OS permissions.

## 错误行为

Reject missing, invalid, stale or mismatched input before dispatch. Preserve actual SDK failure/unknown and original candidate rather than switching sources, silently downgrading, retrying or promoting a supplemental report to a native approval. Keep safe bounded errors without raw prompts, credentials, configuration or private paths. Prelaunch checks are a bounded snapshot, not an atomic lock over later repository changes.

## 回滚

Revert the local reviewed change. Without the explicit enable-once flag, the existing native context and standalone SDK paths remain available. Keep task/review/event history and original failed receipts; do not rewrite history or remove recovery material.
