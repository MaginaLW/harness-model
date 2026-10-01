# Parallel-copy fixed-candidate prerequisite failure 020

Source subject: `4c8952b9cb19e4c2487189ed3a3cf4268aca2e82`.
Measured attestation HEAD: `949c53e949dcb5debbc104cecc8b8b39c20477a0`.
Frozen specification: `992b927ce833a8fa9876c7e278d024eca7903763621ea84391c2ad4c09f6916c`.

D and C each actually completed one cold builder and ten complete warm calls,
with unchanged source guards and known-owned resource handback. Observed warm
medians were 73.61235 ms and 102.2351 ms respectively; D was selected for the
prerequisites. These separate observations do not prove causality or predict600.
D handback SHA: `b2c37f4eea208d304a79d85f0284c37b7807b6d94f7bb7c5305f880c9dd60bcc`.
C handback SHA: `2d1a4d68027f351006ff323e7de5764f7958a87f8d0dedf4a98103e3634686c2`.

The narrow selection actually collected12 unique nodes and passed12 in1.14s,
pytest/launcher exit0, no timeout. Complete fixture collection actually had97
unique nodes, including every preserved old65. Its unchanged240s execution
finished with96 passed and1 failed in51.32s; pytest/launcher exit1, no timeout.
The new256-file test passed maximum4/active0/copies256 before exact metadata
comparison failed: child directory mode511 matched, but source mtime was
1790819325200590800 ns and target1790819325180592000 ns. Other257 items matched.
The cause is unconfirmed; no assertion tolerance or copy semantics changed.

Root inspected raw failure, computed complete source-before/after equality,
verified old65 membership and all artifact hashes. Fixture handback SHA:
`595a3ef5dd4bf2bc2be3fa2a6c4659f8a11d22d0e0e23b61cc5a9cbb49c7467b`.
Fixture result SHA: `e2789f3dc5ec7439471b2584d3616f694bf854a7ea596d778ac646494df6fcb5`.
Raw stdout SHA: `27d27a4fa7f84a396aa3bb64effae8b5a6193d7d708226f4e3df7276d24dcdfb`.
All87 retained Popen identities had real terminal exits (86 exit0, pytest exit1).
Venv root and actual engine identities are separate; a single known-engine
read-only query returned error87. No retained engine terminal or complete
historical descendant termination is claimed. Historical unseen children remain
UNKNOWN. Known resources were RELEASED; all raw files remain unchanged.

External, original integration600, fresh action005 and native V2 did not run.
This private prerequisite failure does not fabricate a native FAILED event or
implementation Review. TASK-0056 remains IMPLEMENTING with implementation_result
pending. TASK-0055, publication and real-report F entry conditions remain pending.
Next: diagnose original DirEntry/copytree metadata semantics and new test input,
then make only an evidenced repair, preserve this failed run, and rebind all
subsequent checks to any new candidate. No automatic retry or widened budget.
