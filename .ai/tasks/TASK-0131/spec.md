# Task Specification

## 目标

Allow the fixed Node verification pipeline to accept an existing pretest clean/rebuild only when the complete rebuilt dist content is identical to the separately verified build.

## 范围

Change only src/aiflow/node_execution.py. Preserve the fixed checks, commands, process receipts, source/dependency/root protections and coverage thresholds. Add an explicit semantic-contract binding for the rebuild rule. Retain the first build inventory and the final check inventory in private run originals; the read-only consumer must compare their complete canonical content and validate the current final inventory. Permit identity replacement only immediately after the successful fixed node_check execution; other phases retain identity protection. Companion tests and usage documentation are separate task-free changes.

## 非目标

No installed V2 or CI activation, target writes, target Policy installation, permissions changes, source-native mutation redesign, model/WeChat execution, private material export or repository settings.

## 验收条件

A real ordinary-wheel synthetic lifecycle with pretest npm run build must first reproduce the existing failure and then pass V0 and V1 after the fix. Existing no-pretest lifecycles remain valid. Modified, missing, additional, linked or unsafe dist files are rejected; changes outside dist, source/dependency changes, failed or incomplete checks and later output drift remain rejected. Missing or tampered build/final inventory and stale semantic/material bindings fail read-only recheck. Run the repository's applicable complete verification, full tests, coverage, Ruff, formatting, mypy and whitespace gates without changing any threshold.

## 禁止动作

Do not modify the original checkout, agent-bridge, authorization files, target CI or remote settings. No deployment, deletion of existing work, credentials export, paid calls, force push or history rewrite. Source-repository delivery is limited to the current reviewed candidate and applicable standing authorization.

## 错误行为

Return failed or unverified evidence for unknown output state, non-identical rebuild, missing originals, process failure or cleanup uncertainty. Do not relabel a failed execution as passed or downgrade classification. Old engine/material evidence must not become current under a new semantic digest.

## 回滚

Use a normal revert of this scoped change; keep task history, reviews and failed originals. No removal of target resources or unrelated work is needed.
