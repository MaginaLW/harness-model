# Task Specification

## 目标

Govern and accept the already authorized local deployment of the two existing exception-reporting paragraphs from accepted main commit 39898f30b8914402d737fab9f59bebf8d8656f53. Do not author new rule semantics.

## 范围

Source and target are the same repository identity. Source relative paths are AGENTS.md (the single exception-reporting bullet) and docs/operations/low-intervention.md (item 5, three lines). The local target is the active checkout on codex/agent-bridge-phased-adoption, starting at e30632c466d3934197838dc2b7ca0a7f1b264f8a. The parent agent has applied those two paragraphs as an uncommitted candidate; this task records the required governance and validates that deployment, preserving every other target byte and all staged product WIP. The owner explicitly approved this same rule deployment and its validation, commits and ordinary branch push in the current chat; independent review and existing CLI gates still apply.

## 非目标

No new rule wording, product code, Policy, schema, runner, CI, thresholds, public/private data transfer, production/device action, merge, force push, deletion or paid/model call. Old TASK-0140 remains FAILED with its original evidence; it is not relabeled as passed, merged or canceled.

## 验收条件

The main LF paragraph SHA-256 values are AGENTS 05cc3c782be2cf1a2dc6c32af06f3120b5854e3fd7f1db4d1c771799296e2acd and low-intervention baf336869b58dcd308b8fd8c356cc1628e77b95c19182d996f48fc132b51ebd5. The target retains its existing CRLF working-tree representation: raw paragraph hashes are respectively 97eda7538de0299c05c56b37c7b0fdcac8de477bd35a1ce06a4c132f4de4b5a3 and c422eda9c67d215a7dea912988899c11bed0c05dcdfe9fe41e92f98fc7de6eb3. After only CRLF-to-LF canonicalization, both paragraphs must be byte-identical to the source; no unrelated text may change. Reproduce source/target readback, diff/whitespace and CLI contract/scope checks; complete the verification level selected by unchanged current Policy, then obtain actual independent implementation review and required owner/action records before accepting local deployment. Upstream PR 148 CI success is source provenance, not this task's verification result.

## 禁止动作

Only the two specified local rule paragraphs are approved deployment targets. No modification of the target's staged product code, other rule sections, other tasks or shared virtual environment. No automatic deployment of any other material or expansion of current owner authorization. Ordinary isolated-branch push only under applicable repository authorization; no direct main push or merge.

## 错误行为

Reject unexpected target drift, mismatching source paragraphs, changes outside the two sections, unavailable mandatory tools, failed checks or missing approvals. Preserve failed evidence and report the precise unmet condition. Do not substitute the old failed run or upstream CI for this task's Gate, change risk facts to obtain a lower route, or bypass a safety refusal.

## 回滚

Restore only the two prior target paragraphs from the recorded pre-deployment target commit through the authorized local edit workflow, preserving all other WIP. Keep task records, evidence, logs and the old failed branch append-only. The main-based source copy remains unchanged apart from this task's governance artifacts.
