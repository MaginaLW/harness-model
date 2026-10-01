# Windows creation identity and controlled runtime comparison

The previous frozen specification is preserved byte-for-byte as
spec-design-005.md, SHA256
3a782321645c40b71cf4921a7322872bf45285bf009218edb3e1d4d9310c53ce.
The committed fixture prerequisite failure and four native failures remain.
No fifth full V2, action005 or formal implementation approval has occurred.

Real standard-library probes read the same ordinary 127-character, 1305-byte
input, SHA256 1c888d9c0c752c6b9fcf79169a406bfd73faef36fb4cc3267e553ce4e5b421dd.
Python 3.11.9 path and handle identities agree. In locked 3.13.15, path ctime
is 1790763800488195400 and handle ctime is 1790763800490192800; birthtime
agrees at the former value. The earlier 3.14.7 observation has the same mismatch.
This is one concrete compatibility refusal, not a full-suite cause or pass.

Isolated 3.13 installation, locked all-extra sync, dependency check, import
binding and standard-library probes actually exited zero. Source, refs and
original 3.11 bindings stayed unchanged. The normal editable backend refreshed
only ignored SOURCES.txt; this is not filesystem zero writes. The vendor archive
checksum is not independently verified. Runtime handback SHA256 is
c0640aac389a5e6e8302e2042bae82909827e86b6d0ee09af388273f03424ab5.

The proposed production change is only Windows creation-time selection: use
available birthtime_ns, including zero, with legacy attribute-absence fallback.
POSIX ctime, the other fields, current repeated reads, raw-byte comparisons and
all path/budget/refusal guards remain. Git transport, Schema and transactions
are excluded. See the official
[Python field documentation](https://docs.python.org/3.13/library/os.html#os.stat_result.st_birthtime_ns).

Rule 8 ownership: the new metadata tests and operating documentation form a
separate task-free safety maintenance unit, with separate commits under the
active bootstrap marker. Production belongs to Task56. Cumulative validation
scope includes safety artifacts without merging governance approval or reducing
any check. This statement applies to the new work, not a rewrite of prior records.

Exact 3.13.15 may be selected for new complete default V2 only after the current
fixed candidate's full original external-review module and original integration600
actually pass. The identity module also runs on original 3.11 and prepared 3.14.
CI 3.11, MINENV, all fourteen checks/five mutations and deadlines remain unchanged.
No performance, implementation or complete validation success is claimed here.
