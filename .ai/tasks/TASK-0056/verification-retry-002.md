# Diagnosed fixture correction and third complete V2 admission

The second complete V2 remains FAILED. Its consumed action002, original
logs, verifier context, snapshot and receipt remain preserved. The admitted
design amendment is frozen at
`0a2f502b9310411d71e6502e871a00e5d1cf600dca7b4ebcbb27f414a4ff1751`.
Candidate `4f0288b4afb608412f984fa9078b7b0692fa0e6f` repairs only the
two admitted test fixture files. Production storage, Policy, environment
whitelist, original test assertions and command budgets remain unchanged.

Test-owned Win32 physical file names now support historical record copies
and corruption writes while logical fixture roots and service arguments
retain their ordinary paths. The shared Git helper retains checked UTF-8
capture and its original ten-second command deadline. After a timeout it
terminates the owned running Windows process tree or POSIX process group
and bounds the subsequent pipe drain to five seconds. A direct parent that
has already exited receives only bounded draining; no complete orphan-tree
cleanup is claimed. The initial cause of the earlier Git timeout remains
unknown. Failed cleanup still raises a command timeout.

Independent complete bounded runs on the fixed candidate inputs returned:

- Shared Git helper module: 34 passed in 55.02 seconds, actual exit 0.
- Verification command module: 81 passed in 189.63 seconds, actual exit 0.
- External review command module: 187 passed, 1 skipped in 225.66 seconds,
  actual exit 0. The skip is the existing POSIX FIFO restriction.
- Complete E2E collection: 28 passed in 144.78 seconds, actual exit 0.

All four runs had no diagnostic outer timeout. Before/after source HEAD
and the two file hashes matched. The real inherited-pipe Windows child
case separately passed in 11.04 seconds; its command timed out at the
original ten-second deadline and its exact owned child PID had exited.
No production code, refs or runtime configuration changed during these
runs. The first external-review diagnostic reached 93 percent before its
210-second diagnostic outer limit and had no terminal summary; that
incomplete result remains preserved and is not a completed test failure
or pass. The complete rerun used a separately recorded 300-second
diagnostic limit without changing any native Policy budget.

The private amended-module summary SHA-256 is
`d1b12e25202134ece73be47240a7cf0559f4e467347e28b0594cc270aadcc6be`.
The independent helper preview report SHA-256 is
`08b5eff9739c43a776ebdcbab6a12675524d38bd9aad2e8e2a12926149e1e825`;
the independent E2E preview report SHA-256 is
`1b3231e368db89e030f40af6b2d9e9d94dcc8a998487f6349f1790de56033d15`.
Their original commands, output and PID handbacks remain private runtime
materials. An AST comparison retained all 247 original logical assertions
in 85 existing test functions; this comparison is structural evidence,
not a replacement for runtime validation.

These previews permit a fresh complete native V2 attempt and do not
establish full-suite success, coverage or Gate approval. The candidate
must receive independent current preflight and a fresh exact-subject
single-use action003 before execution. The complete default fourteen-check
plan and fixed five-mutation manifest remain required. The short ordinary
`${PYTEST_TEMP_ROOT}` parent and isolated locked `${VERIFIER_PYTHON}`
runtime inherit the real profile and retain native MINENV. Formal
implementation Review, same-verifier finalization, current code approval
and Gate are still pending. No publication is authorized by this preview
record alone; publication uses the owner's separate authorization and
fresh action bindings after implementation completion.
