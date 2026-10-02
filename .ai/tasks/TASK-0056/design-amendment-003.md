# TASK-0056 design amendment 003

Prior frozen specification `0a2f502b9310411d71e6502e871a00e5d1cf600dca7b4ebcbb27f414a4ff1751`
is preserved verbatim in `spec-design-003.md`. Original full run003 remains FAILED:
regression and integration reached their unchanged 900/600-second deadlines.
The complete coverage execution and all old receipts remain independent facts.

An isolated full Python 3.11 module profile completed 187 tests with one original
FIFO skip in 200.15 seconds. It measured 3586 safe YAML decodes with 36.92 seconds
cumulative time. These overlapping measurements do not establish timeout cause.
The isolated Python 3.14 comparison failed and is not used for formal V2.

The expanded dependency scope adds document_parsing.py and the existing policy.py
and storage.py callers, plus three corresponding unit-test files. The sole new
behavior reuses pure text decoding within explicit bounded process memory.
Every path guard, actual current read, schema validation, Policy cross validation,
canonical hash, state/freshness/approval check remains live. Complete text is the
key; independent returned copies prevent mutable leakage. Errors are not cached,
and unsupported parser/configuration/value cases retain original parsing.

Owner authorization covers necessary TODO fixes and concrete approval records.
REVIEW/V2 remains required. No implementation precedes native reclassification,
freeze, independent design Review, specification approval and begin. No Policy,
Schema, workflow, default command, selector, timeout, MINENV or threshold changes.
Publication remains a separate task with actual candidate and CI bindings.
