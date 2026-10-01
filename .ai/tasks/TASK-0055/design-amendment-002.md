# TASK-0055 platform API lookup amendment (2026-10-01)

This is an additional same-route spec_changed admission, not a reduction of REVIEW/V2. Previous frozen specification 3c014d67a353f93c22377aff85584532a397cc41fd5cbb0cec4ff6e6b75d7e88 is preserved byte-exact as spec-snapshots/spec-003.md. All earlier specifications, failures, approvals, reviews and dependency evidence remain unchanged.

The importer transport stage e03bfb1 and separately committed maintenance safety tests/documentation 72294c1 were verified with the complete two importer test modules: 305 passed, one pre-existing FIFO skip, actual exit 0. Source SHA256 was 0a77f2b9ace59cc92acd0b38f30820b401d7e2d219b94735a7e44c5e87165209. Independent raw-capture checks matched all 13 handback entries. This is focused Windows evidence only, not current whole V2 or Linux execution. The failed initial run is retained.

Additional full Linux-platform mypy diagnosis failed with four attribute errors across 44 source files; stdout SHA256 2df2bcb83f2846553d5d93c0922bbf537ed1dc87259ba59a52748c719ea2041f. Windows file mypy and Ruff/format passed. This diagnosis is a real remaining issue, not waived by earlier TASK-0056 or focused test passes.

## Exact newly admitted production work

In src/aiflow/external_review.py, change only three Windows-specific attribute access expressions: ctypes.windll in _lexical_path and subprocess.CREATE_NO_WINDOW / subprocess.CREATE_NEW_PROCESS_GROUP in the newly admitted transport. In src/aiflow/verification_temporary.py, change only ctypes.windll in _drive_type. Use getattr(module, literal_name) without a default. Preserve the same underlying Win32 API, arguments, flags, integer conversion, platform guards and allowed drive types. No fallback, replacement signal, cast that hides a changed value, default zero flag on Windows, exception remapping, path acceptance change, PID/session ownership change or deadline change is admitted. The previous importer-only production-purpose restriction is broadened solely by these two existing drive-guard lookup expressions; the original 32 allowed patterns remain identical.

The TASK-0056 control checkout, source 9dca04dc18e1551dc86987eb594f84f9d37b47ad and its 106 imported tracked ledger blobs remain immutable. The new derived verification_temporary.py expression is TASK-0055 work with its own validation, not a re-opening or substitution of the dependency pass.

All I1-I8, source/report matching, zero-write refusal, original writer interruption/recovery boundaries, transport waits/retained-process limitations, quality thresholds, 14 required checks, five fixed mutations and every original budget/selector/MINENV remain required. Real report acceptance F remains missing authentic input; no provider or paid call is introduced.

## Validation and role plan

Admission is serial: append DU/spec and stage commit, native sync, spec_changed resolution, classify/freeze, actual author-independent design Review, status-directed owner-delegated spec approval under the existing human authorization, then begin. Only after begin may root perform the four substitutions.

Parallel preparation uses two sub-agents: one actual independent design/implementation reviewer, one actual independent native verifier preparing capture only. Root owns specification, four production expressions, governance and unified commits. Existing safety test author is not a formal independent reviewer/verifier. No agent modifies shared source/refs during native verification.

After implementation, run Ruff/format and full mypy on Windows plus additional --platform linux static analysis, and meaningful existing importer/temp-root unit tests. Full native TASK-0055 V2 on its own fixed source/HEAD remains serial and mandatory; Linux real integration execution is verified by exact publication-head CI. Then actual independent implementation Review, same verifier finalize, current code approval, Gate and exact post-commit Gate. Publication remains separately admitted, with fresh exact-candidate/base/head approvals and unchanged branch protection.
