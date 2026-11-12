# TASK-0143 implementation review package

## 审核目标

Review the bounded workflow-authentication repair at subject `84a32cf4c526b69de2a1399ded6917e5a11c8175`, base `f4a9844bb3ba53c0c0e058e08374d98ff696ddf9`, and frozen specification `e6542851d716948b3dd13732acb2b1b8071c5c0b497cbeb9a5d68490a49a81c8`. This is the implementation review of the source unit under the explicit owner A38 scope.

## 背景

The PR and workflow-run base snapshots can agree with each other while the current synthetic merge commit uses a newer base-branch tip. Requiring the historical snapshot itself as the current merge parent rejects that valid association. The safe synthetic tests and enduring Norm were committed separately before this governed implementation. All earlier successful or failed proof remains historical and retained.

## 代码地图

- `src/aiflow/node_ci.py`: only `authenticate_workflow` changes product behavior, using the existing bounded API reader and valid-branch checks.
- `tests/unit/test_node_ci_platform.py`: synthetic regressions cover historical snapshots, the actual base tip, invalid or changed refs, and merge-parent association.
- `docs/superpowers/specs/node-ci.md`: describes the retained snapshot checks and actual base/merge authentication.

## 语义变更

Keep the PR/run historical base snapshot association and every existing repository, head, attempt, workflow, job, Check and App constraint. Validate the common base branch, read its actual repository `git/ref/heads` tip, and require the two merge parents to be exactly that tip and the selected head. Read the base and merge refs again before returning and reject observed drift. The three extra GETs use the existing time, response-size and aggregate-byte bounds and retained raw-response contract. No wire field, role, cap, Policy, permission, dependency, quality threshold or Node execution-contract declaration changes.

## 风险

This authenticates the observed current association, which must be checked again when consumed. Synthetic API regressions do not establish a successful real source publication or consumer Gate. The generic Native suite has nine explicit platform/material skips; it does not claim to run those conditional scenarios. Ordinary installed-package provenance and new CI artifacts remain subsequent requirements even when package versions or logical tier digests match old values.

## 证据

已验证: Actual source5 Native evidence `b17efd897f84c3eb0e1892b346e72c2e22727492b15b485387eb8052f83c0f2b` is passed at `pre_implementation_review`. All fourteen required checks passed. One shared full pytest execution produced 7353 passed and 9 skipped in 3434.06 seconds, with a 3435.500-second shared receipt. Core coverage is 90%, core diff coverage is 100% (13/13 applicable lines), and analysis coverage is 98%; the unchanged required thresholds are 85/90. All five fresh targeted mutation outcomes are killed, with mutation evidence `3d936b531143f8c5bd60179c3a538864dd1a589afc3ea6b9fc0382b5ab2db78a`. The original plan took 3444.297 seconds, the single actual record API call 18.813 seconds, and the complete CLI 3464.312 seconds. The external supervisor receipt reports 3464.594 seconds, return0, confirmed cleanup, all eight lifecycle facts true, and no timeout, overflow or execution error. Current verification snapshot is `604d5c4e0cb64e91a0c2710d8aa468c1fdf8626412cb442897a3bb4bda352c88`; independently saved verifier context is `632d8cbca67c286342425bb66522ba888f41aacd018078023b01d28572df8c25`. The separate focused platform regression run passed 241 tests and is supplementary preparation evidence.

未验证: Formal implementation review, same-verifier finalization, owner code approval and current source Gates are subsequent required steps. The new published source head, both successful exact-head source workflows, usable authenticated archive/direct wheel/sdist/rebuilt wheel and all three actual installed tier digests remain pending. Fresh target LOCAL, private originals and the original-host combined Gate remain pending. No current Native result is presented as those outcomes or completion of the overall bridge integration.

## 审核问题

- Does the repair preserve historical snapshot association while authenticating the actual merge-parent base and rejecting observed ref drift?
- Do the added reads retain existing resource and identity constraints without expanding the closed wire or execution contract?
- Are real publication, ordinary installation, target lifecycle and combined acceptance still clearly pending?

## 推荐结论

APPROVE if the independent implementation review confirms this bounded change has no unresolved blocking findings. The actual review record and same-verifier final evidence remain authoritative. This package does not itself establish publication, merge, consumer acceptance or overall completion.
