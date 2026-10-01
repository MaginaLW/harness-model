# Git endpoint comparison and targeted profiling diagnostics

These completed diagnostics concern source e3790a43bf51b976816a8eaf8770789c7f90a1f2
and clean attestation HEAD ba3e9994c571e0c0adf4b9332a589808c395c94f.
They do not pass the canonical integration600 prerequisite, a fifth native V2,
formal implementation Review, code approval, or Gate. All earlier failures remain.

## Paired read-only endpoint observation

The complete owned Git for Windows 2.55.0.3-1 package's cmd and mingw64/bin
executables were compared in twenty alternating AB/BA pairs. The argv was
`--no-optional-locks rev-parse --show-toplevel HEAD --abbrev-ref=loose HEAD`.
Both received exactly the same prior native two-key PATH/SystemRoot environment,
fixed source cwd, inherited stdin and binary raw capture. The selected native
endpoint was not changed by the probe. Two additional untimed read-only clean
status guards were recorded.

All forty identity calls and both guards actually exited zero, with no timeout
or cleanup. All identity stdout bytes agree (136 bytes, SHA256
63a8745af9746db6a32e853a475fb734cdc7ba1a075f1026f3f87506d3de514a),
and stderr is empty. cmd median is 49.69765ms, direct median is 35.71615ms.
Paired cmd-minus-direct median is 13.4795ms, mean 18.424355ms,
p05 5.022155ms and p95 109.365395ms; nineteen of twenty pairs favor direct,
with one opposite observation. These are one-window call latencies including
symmetric recording overhead, not child CPU or complete command/environment
semantics. They cannot predict current full-suite duration or a 600-second pass.

Source24, common refs, worktree registration facts and index bytes/mode agree
before/after. Retained owned driver creation identity remained equal with terminal
exit zero; forty-two retained direct Popen processes had terminal exit zero.
No orphan-tree completion claim is made from parent exit. Resources were RELEASED.
Completed record SHA256: ee1e8a3af5c7411a8b6328bad3b6a4f46694be3f82a21b0ac954183f494982d5.
Summary SHA256: d921fe0952c1f969f93e16e4a936a74d097a22f25d254b670373fb3d63bfe636.
Handback SHA256: 87010b93c761bbc66c1f41ee0e3291ec3aa19f4fef9ba38c59bef692a8767acd.

## Four-complete-module profiling diagnostic

The original classify, gate, observation-escalation and verify modules actually
collected 45/27/41/81 unique cases, total 194. Every case has real passed setup,
call and teardown, total 582 reports; audit issues, hook and export errors are
empty. Actual pytest and wrapper exit are zero, no subset600 or outer720 timeout.
Pytest reports 194 passed in 367.30s; wrapper elapsed is 368.175059s. The actual
run identity is run-20260930T173320880907Z. Source24, selected4, old8 receipts,
HEAD/status and common refs agree before/after. This four-module subset has a
separate startup/order and is not the canonical full integration selector.

Raw getstats export preserves 5421 code entries and 14657 child edges by code
object identity; no identity edge is unresolved/ambiguous or label-overwritten.
However nine entries and forty-nine edges have inline time greater than total
time. For example BufferedReader.read has inline 150.6194s versus total 14.4624s.
No per-thread event chronology is available. All function timing cost attribution,
including apparently normal Git/registry/YAML entries and disjoint timing sums,
is therefore UNKNOWN and is not a production optimization basis. The Python
3.13 monitoring implementation provides a possible interleaving mechanism, not
a verified local binary bug or the canonical timeout's root cause. Raw data and
all failed/unused drafts remain preserved; no profiling rerun is requested.

Counting alone records one create_repository code entry with 175 calls,
_populate_repository 1, populate_or_copy 175, _copy_snapshot 175, _qualify 1,
and qualification.current 177. These are subset calls, not inferred full-suite
hit counts. Observer callback time is not total instrumentation overhead.
Completed SHA256: 56a08dd38dbbf264afcc24cee5305f5a0a30f03f2bbed85439643c4f70ae04ff.
Per-ID phase audit SHA256: cdc8cbc29b6ae8a925b832fc806fcaaa56581f1a5605a785fa99984f670eb5ea.
Raw anomaly audit SHA256: f90fafe9e78720afd7ab3968011626791e941c51789bba452242fa6b94191e1f.
Profile handback SHA256: 394e68fe41540c61af1bc304d2be5b618c5c1871b1d3d6c385ca964eb68596f6.
Seven retained direct handles and the launcher handle had verified actual PID,
creation identity and terminal zero exit. Creation-aware owned-process query
succeeded with no matching known owned process; no cleanup/stop was performed.
One initial builder/publication plus 174 warm copies is consistent with the
counts and static branches; direct owner.hits was not logged and stays distinct.
