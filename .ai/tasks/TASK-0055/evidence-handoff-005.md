# Fifth V2 private evidence handoff

The private fifth-run handoff was exported using the existing
`tools/evidence/bundle.py` and independently verified with the separately
recorded expected ZIP SHA-256. Export and independent verify both exited 0.
Verify reported `VERIFIED`, `expected_digest_matched: true`, 100 files and
978718 selected uncompressed bytes. The ZIP is 283734 bytes; its SHA-256 is
`e8e6f3d266959693c2633c357865a831b43133b848694a97b6775ca57f6908b9`.

The private artifact leaf is `harness-model-e4-v2-005-20260930-001`, under the
existing tree-external archived-run convention. The ZIP is
`TASK-0055-v2-005-handoff.zip`. The explicit final selection, environment,
reproduction instructions, Git provenance and independent audit remain with
that artifact. The material contains original private runtime paths; it is
not a public repository deliverable and was not remotely transferred.

## Selected bytes and boundaries

The package includes 26 exact Git blobs: 23 from source commit
`4724c708fc1ff939ef20ab03846d549915a9f811` and three existing tool/document
blobs from `f855ddf551aed343de834608cc707422329e10d2`. Provenance records each
commit, path, Git blob OID and byte SHA-256. Source producer originals are
selected separately. All 23 mapped producer originals match their current
source bytes; 13 staged comparisons are RAW_IDENTICAL and 10 are CRLF_ONLY.
The Git LF blobs do not replace the producer originals or their raw hashes.

The 100-entry final selection retains the earlier explicit 98-entry selection
and adds two audit records. Selected native artifacts include the three
byte-identical formal evidence copies, all 24 non-null check log references,
five mutation logs and mutation evidence, launcher records, bounded unit
diagnostic originals, locked environment information and reproduction notes.
Four native stdout/stderr references are null; they are not invented logs.
Earlier raw runs and missing TASK-0054 logs were not selected and their
availability is not inferred. This is an evidence package, not a complete
source repository or environment backup.

All 100 manifest entries were independently checked against their size and
SHA-256. Package formal evidence remains schema 2.0 and matches the current
native task evidence and fifth-run archive exactly, with raw SHA-256
`59997434080ad6dc95d602a23043e184d765dc20ae221160419a7e6504971726`.
The existing optional selection precheck supports evidence 1.0 only: its
schema 2.0 invocation actually exited 1 with UNSUPPORTED_EVIDENCE. That
limitation is retained in the package. Its successful pairs-only invocation
does not check evidence or log references. A separate explicit selection audit
checked all 24 native references; this is not a substitute Schema validation.

The pre-export credential-pattern check initially matched two substrings
inside pytest parameter names. Review identified those lexical false
positives, and the token-boundary check found zero known-pattern matches.
No original content was changed. This limited check is not authentication
or a claim that arbitrary secret formats are detectable.

## Receiver and current verification state

Using an independently obtained trusted tool copy and separately communicated
digest, the receiver can run:

```text
python tools/evidence/bundle.py verify <HANDOFF_ROOT>/TASK-0055-v2-005-handoff.zip --expected-sha256 e8e6f3d266959693c2633c357865a831b43133b848694a97b6775ca57f6908b9
```

Verification reads the ZIP without extracting or executing its contents. It
reports `source_authenticated: false` and `governance_effect: none`. Byte
consistency does not restore source, an environment, approval or a passing
Gate. Action005 remains consumed and cannot authorize a new checkout or retry.

TASK-0055 remains FAILED on fixed subject
`eb4c49a4ff77ca07f210fceae707495c8dece8be`. The full fifth V2 has four actual
timeouts and missing coverage XML; its original causes remain unknown.
A later read-only host observation found approximately 135 MiB available
physical memory and system-disk queue length 80, while the other disk was 0.
This is prospective resource evidence, not proof of a past test failure cause.
No process or system setting was changed, and no sixth invocation was started.

The next complete attempt requires an adequate ordinary environment, a native
recorded retry reason and a new exact-subject single-use mutation action;
all original checks and deadlines remain mandatory. Failed evidence is not
finalized. The existing push/merge authorization remains unused and valid;
implementation review, final verification, owner code decision and passing
source/publisher Gates still precede publication.
