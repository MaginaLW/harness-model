# Evidence expiry example

An AI Flow evidence record is usable only while its version bindings still match the task.

## Frozen specification changes

If `spec.md` changes after it was frozen, the recorded specification digest no longer matches.
Freeze the revised specification, obtain any required approval again, and rerun verification.

## Policy changes

If an applicable file under `.ai/policy/` changes, the Policy digest changes. Reclassify under the
new Policy and regenerate any approval or evidence that was bound to the previous digest.

## Subject changes

If the governed business commit changes, previous evidence no longer describes the current
`subject_commit`. Run final verification again at the new subject and use only its evidence at Gate.

Current-task governance-only attestation commits may advance HEAD without changing the governed
subject, but CI evidence must still bind the attestation HEAD used by Gate.
