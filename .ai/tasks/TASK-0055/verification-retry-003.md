# Third fixed-candidate V2 retry

Source subject `28d5184e02dc9b4dee0cc6df942000ad34f8b611` batches the
three Git identity subprocesses into one `rev-parse` call using explicit
`--abbrev-ref=loose`; the existing NUL-delimited dirty query remains separate.
Each required observation, ancestry check, strict task/Policy/input reread,
byte binding and publication guard remains. Raw refs named HEAD use the
original symbolic-ref fallback; detached and unborn checkouts still fail.

Real Git checks cover Unicode internal whitespace, branch/tag collisions,
deep ref ambiguity with both core.warnAmbiguousRefs values, raw HEAD refs,
detached refusal, and unchanged full task tree/Git index. This subset passed
19 cases. Pure unit and the unchanged legacy CLI regression passed 59 cases;
Ruff, format, mypy and whitespace checks passed.

An independent synthetic Git microbenchmark observed equivalent identities
in 60 rounds and lower identity-query cost. The two representative integration
cases passed in 22.26 seconds versus an earlier 18.79 seconds; those runs were
not simultaneous controlled comparisons. No end-to-end speedup, past host
cause or passing complete V2 is inferred from the preparation measurements.

The complete new native V2 must use all original checks and deadlines.
The two prior failed/interrupted runs, original actions and native events are
retained. Native sync reports current classification/spec approval, and the
third single-use canonical mutation action binds this exact source subject.
No Policy, CI, threshold, timeout, external action or frozen scope changes.
