# Parallel-copy test input stabilization 021

New source subject: `113ecddd90a4c0e4f51cd7d7cea64700cf12736c`.
Frozen spec remains `992b927ce833a8fa9876c7e278d024eca7903763621ea84391c2ad4c09f6916c`.
Native sync/status/scope/validate actually exited 0. State remains IMPLEMENTING,
REVIEW / V2, classification fresh and approvals current; implementation_result
is missing. Source and governance changes remain separately committed.

The previous fixture run remains 96 passed / 1 failed, 51.32s, no timeout.
The new 256-copy case failed exact child-directory mtime equality after its
four-worker / active-zero / 256-copy assertions. Its later pool-ended assertion
was not reached. Failure record 020 and all original artifacts are preserved.

A single default, unwrapped stdlib copytree observation on the original aged
input actually exited 0 in 0.438s. All 258 source/serial-target metadata entries
matched; original source and failed target before/after records were unchanged.
The old target retained its 19,998,800ns difference. New DirEntry objects cannot
recover the old failed-process cache or chronology: the transient was not
reproduced and its cause remains UNKNOWN, including any filesystem attribution.
Observation SHA: `d697102df7bc406b5b386ec826be7d5c054d1495f4d9fef317ecd42ce5f7650b`.
Actual execution receipt SHA: `0b9051cca93b0cf602b7d3b1cfe30160d8ced18bae3a822c5b45b88406623632`.

Only nine lines in this new test changed: after file creation, set two distinct
exact 100ns-aligned directory times, strictly read them back, capture metadata,
and assert source metadata remains unchanged after copying. Original exact
source/target comparison, worker/count assertions and pool-ended assertion stay.
No tolerance, sleep, skip, budget, selector, environment or helper change.
Helper SHA: `26af47db7d7c7caae0a04da63541b5e37e00282593364ac505c04e115633c7cb`.
Test SHA: `5d20932bfb7b8a62d2ebeb620570980672b9b45c5d7822f258073cfc889be8dc`.
Author static report SHA: `acef18f0a6948b19e47a57f571884a5a3bae0a65ab0c28ec795d5dbb335ca847`.
Independent static pre-review SHA: `154314f388af7cd796d648820daf8d469e42d3f885b2e1feb29b0b163d34a7a5`.
Root reviewed both reports and the complete staged diff. All other test bytes
and the preserved old 65-case prefix are unchanged. No static blocker remains.

The new assertions have not run. Static acceptance is not native Review, fixture
PASS, integration600 PASS, full V2 or Gate. Bind the new S/H, measure its complete
warm cost, then run original prerequisites serially with resource handbacks.
Fresh action005/full V2, TASK-0055 readmission and publication retain their
original entry conditions. Matching authentic report input for F is still absent
within the bounded local search; no provider or F import was started.
