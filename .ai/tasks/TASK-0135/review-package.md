# Review Package

## 审核目标

Approve the reviewed native installed-engine primitive for TASK-0135, subject `84aaf4059da6506e793b83be24ceed7350376dc6`, under its frozen specification and existing delivery gates.

## 背景

This slice adds closed ordinary-installed mutation execution and exact-reference replay. Node revision 2, Node CI and real-target adoption are separate work and are outside this package.

## 代码地图

`src/aiflow/installed_mutations.py` owns prepare, record, current-authority collection and pure replay. `src/aiflow/installed_probe.py` defines five fixed controls and assertion anchors. Existing inventory, action-lock, native operators, Windows Job and review helpers are reused; native lifecycle consumers remain unchanged.

## 语义变更

Stable inputs bind task/version/context and installed bytes; live Current binds one exact ref/size/SHA and complete root facts. Only preparation/recording require IMPLEMENTING and a fresh single-use action. Pure replay checks retained originals without processes, writes, recovery or repair; only the exact owned run is excluded.

## 风险

The supported interpreter, standard library, loader and OS remain trusted. Malformed, stale, substituted or incomplete materials and unrelated failures reject. Interrupted or failed actions remain spent. No open findings remain; original coverage thresholds and native safeguards are retained.

## 证据

已验证: 5926 tests passed, 9 declared skips; 14/14 required native checks passed; core total branch coverage 89.3658%, analysis 97.5039%, complete diff coverage 949/1039 = 91.3378%; five fresh native mutations killed. Both direct and rebuilt IQ origins retain five actual killed pairs each with current independently checked originals and pure-replay facts. Independent review: `reviews/REV-0006-r0001.json`; context `3c9e9ba5a79ceb0675ad52357bf17a79c02f19067a35468c056f81fea86b45c7`; stable snapshot `a0072b346e2682ada2c2bd6133456fb1b91e4179e3ed02a3c4b6bba9c3ca3cef`.

未验证: Current-head required remote CI and merge remain pending. Node revision 2 and real-target acceptance are not established by this native review.

## 审核问题

- No unresolved implementation findings or owner decisions remain. Current-head required remote CI and merge remain delivery prerequisites, not a request for another implementation approval.

## 推荐结论

APPROVE. The independent REV-0006 review found no issues in the fixed native implementation. Same-verifier finalization, current code approval, Gate and current-head required remote CI must still be satisfied before merge.
