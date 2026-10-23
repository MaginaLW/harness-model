# Unicode maintenance review

## 审核目标

Review the fixed candidate `0a20779ae6b3bd357c3a2ff785a9fb760f76b490` against the current frozen TASK-0084 specification and native evidence.

## 背景

Valid Unicode could split JSONL event strings into invalid records, break facts output under ASCII/GBK after a successful write, or lose U+0085 through YAML folding. Independent review reproduced the YAML data-integrity defect; the earlier incomplete verification attempt was abandoned and preserved before the scope was updated.

## 代码地图

`src/aiflow/task_service.py` reads task events; `src/aiflow/cli.py` prints facts results; `src/aiflow/storage.py` serializes new YAML writes. The separate task-free correction in `tools/analysis/approval_overhead.py` covers legacy and fixed-HEAD event projections. Existing tests and usage documents contain the bounded companions.

## 语义变更

Use standard text-stream line reading, ASCII-escaped facts JSON and the existing YAML serializer's ASCII escapes. Preserve decoded values, raw UTF-8 events, sequence and contract validation, no-op behavior, exact recovery intent and private-field projection limits. No new module, option, dependency, Schema, Policy or authority is introduced.

## 风险

New YAML text uses standard escapes for Unicode; historical files are not rewritten. Existing corrupt or already folded historical values are not reconstructed. Single-writer and uncertain-I/O limits remain. Real scoring, automatic review arrangement, host connections and the observation window stay paused.

## 证据

已验证：fresh native V1 on the fixed subject passed all ten required checks, with 3835 tests passed in 1074.58 seconds and 100 percent diff coverage in both source domains. Core/analysis total coverage is 89/97 percent. The three new YAML/facts regressions first reproduced the defect and then passed after the fix; analysis regressions, facts/recovery, all 26 storage tests, Ruff, format and strict mypy passed. Current fixed-HEAD tracked-ledger snapshot reading succeeded. Independent real-writer closure confirmed normal apply/read/no-op, wrong-actor zero-write rejection and original-actor interrupted recovery with unchanged event bytes and timestamp. The authoritative current result is `evidence.json`; original run logs remain under its task-relative references.

未验证：final context-bound implementation review, Gate, remote required CI and merge-commit publication remain to be completed. The deliberately abandoned earlier run is not passing evidence; local tests do not prove real scoring, host integration or production effectiveness.

## 审核问题

- Do the standard-library corrections preserve exact Unicode values without changing validation, replay or recovery authority?
- Do the final native evidence and independent review cover the fixed candidate, with no open critical/high findings?
- Are new YAML representation changes explicit while historical bytes and failed attempts remain preserved?

## 推荐结论

APPROVE for this bounded fixed candidate, subject to the separate independent implementation review, current Gate and required remote CI before publication.
