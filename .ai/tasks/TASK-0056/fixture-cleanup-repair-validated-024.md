# Fixture cleanup repair fixed and module validated 024

Safe source commit `9dca04dc18e1551dc86987eb594f84f9d37b47ad` modifies only
`tests/integration/test_begin_close_commands.py`. It restores retained direct
child recovery for all post-spawn exceptions, keeps the triggering exception
object and arguments, and bounds taskkill helper wait5/kill/wait1, direct wait5
and final communicate5. Completed nonzero commands skip recovery. Numeric
group signaling requires current direct-child liveness; known-reaped decode
failures do not signal a group. Undrained reader streams remain untouched.

All old test statements and the original real 10-second pipe-holding-child
test remain. Eight necessary new cases cover first/secondary failures,
completed nonzero commands, a real retained CPython base child interrupted
after spawn, and a reaped decode failure. The real interruption test checks
PID/retained Windows creation identity and terminal state before fallback
cleanup. It makes no claim about unretained exited-parent descendants.

Candidate raw SHA:
`5c48579f53030d0746ad7f544eb44febc8965970f72bb83933c6302b99af2084`.
Independent static pre-review SHA:
`9aab670d9b4db3d7dfd5304df399b32195d157d27fc6c6dd760fea8f46119a66`.
Actual Ruff/format/compile passed. Complete begin/close module then ran with
the locked 3.13 runtime and original two-key computed MINENV: 42 passed,
zero skips, 28.16s, actual exit 0, no timeout, source unchanged. The retained
pytest root exited; no global historical descendant absence is inferred.
Raw stdout SHA:
`1ce84d0cdda9193cba408f2144d1e5efca51ddd15030d1b791658a76396bb7d9`.
Stderr was empty. This module pass is not full native V2 or formal Review.

Native sync binds the new subject without changing the frozen specification,
classification, scope, Policy or state. Current status remains
WAITING_FOR_FINAL_REVIEW, classification fresh, old evidence stale, Missing
code_approval. Existing valid specification approval is not requested again.
The old REV-0009 REQUEST_CHANGES, source113ec passed snapshot and consumed
action005 remain immutable. RF-001 runtime closure awaits current full V2
and a fresh independent implementation Review; it is not marked resolved.

New-source warm cost and original prerequisites are serial, followed by a
fresh separately bound single-use action006 and default complete V2. The
waiting state supports native verification_restarted; no manual state edit or
gate reduction is used. All 14 checks, five fixed mutations, 85/90 coverage
thresholds and original deadlines remain. TASK-0055/publication/F stay
conditional; no push, merge or provider execution occurred here.
