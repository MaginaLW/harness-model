# Bounded diagnosis and second complete V2 admission

After run001 ended and all verifier handles were handed back, an independent
worker compared the same two original mutation/context test cases with
the original interpreter and native process environment. Both used actual
TASK-0056 run-owned containers, native-format run IDs and EXEC-006 leaves.
Long parent: exit 1, two failed in 1.34 seconds; the two failed atomic
temporary filenames were 272 and 275 characters. Short parent: exit 0,
the same two passed in 0.89 seconds. The short-parent original failure
family then completed with 36 passed in 8.60 seconds, exit 0. The four
original runner deadline failures completed with 4 passed in 26.83
seconds, exit 0. No diagnostic outer execution timed out.

The actual native minimal environment, original assertions and deadlines
were preserved. These results establish the path-length dependence of
the two representative write failures. The earlier PowerShell timeout
causes remain unknown; their limited successful rerun does not establish
full-suite success or performance guarantees. Maximum existing file paths
in the long pair, short pair, short 36-case family and short runner group
were respectively 252, 226, 255 and 136 characters.

The private diagnostic report SHA-256 is
`d0b492e34a449d26e7f27d3fe4abc802b40b5f020ea2fddb589831c27bd976a0`;
its 28-file manifest SHA-256 is
`8039fc21b10542101b9438942c37542e12e3abd7f7fe1b2052fd3baea05c40d4`.
Original stdout/stderr, actual argv bindings and runtime facts remain
under `logs/paired-parent-diagnostic-002/`. Diagnostic001 failed before
pytest or container creation because its Git filename reader mishandled
quoted non-ASCII paths; that auxiliary error and its original materials
remain preserved. Source, original tests, task records and refs were
unchanged by both diagnostic attempts.

Separately, an isolated Python 3.11.9 environment completed the project
`uv lock --check`, `uv sync --locked --all-extras` and `uv pip check`, all
exit 0. Normal-profile actual locator/version probes confirmed pytest
9.1.1, Ruff 0.16.1, mypy 1.20.2, diff-cover 9.7.2 and Git
2.55.0.windows.3 at the intended isolated executable entries. Editable
source import points at this checkout. No lock, original interpreter,
registry or global environment was changed. Runtime facts and raw
installer/probe logs remain private external materials; preparation is
not a test, performance or Gate pass.

The complete retry will use `${PYTEST_TEMP_ROOT}` as the independently
validated short ordinary parent, `${VERIFIER_PYTHON}` as that isolated
interpreter and a process-scoped PATH prefix for its Scripts and Git cmd
directories. It inherits the real profile and temporary environment;
installer isolation and probe flags are not reused. Native `_environment`
remains unchanged and still selects the existing PowerShell 7.6.6 entry.
All original Policy checks, selectors, deadlines and thresholds remain
required. The usage document now describes the observed long-path risk.
The final committed candidate must be synchronized and independently
preflighted before recording a fresh exact-subject action002. Action001
and its receipt remain consumed. Only actual full V2, independent
implementation Review, finalization, code approval and Gate can complete
this implementation task.
