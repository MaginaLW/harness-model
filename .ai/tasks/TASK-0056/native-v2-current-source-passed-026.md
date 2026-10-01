# Current-source native V2 passed — 2026-10-01

This is an append-only portable verification record. Implementation Review,
finalization, code approval and Gate were still pending at this record's creation.
No Task55 admission, remote publication or real-report acceptance follows from it.

## Exact candidate and original execution

- Subject: `9dca04dc18e1551dc86987eb594f84f9d37b47ad`.
- Verification attestation HEAD: `4bb8a60d2d3b67e95789e8fd2ff4b203044ac8aa`.
- Base: `ef92b795da729566870ff4878f100a4ffe319db5`.
- Frozen spec: `992b927ce833a8fa9876c7e278d024eca7903763621ea84391c2ad4c09f6916c`.
- Policy: `d21a386779147dfad962a0fc0656bef61bc581e27f63c4789dcc06520fa10ff1`.
- Classification input: `365b5f52294b6fb528012f3bcff322294933d788d5eb6b35b7df35e5d6f279f6`.
- Native run: `run-20261001T060444519719Z`.
- Verifier: `e4-temp-independent-verifier`; actual native and driver tool exits were 0.
- Original default command: `python -m aiflow verify TASK-0056 --actor e4-temp-independent-verifier --pytest-temp-root ${PYTEST_TEMP_ROOT}`.
- Actual runtime was the locked isolated Python 3.13.15 GIL environment; the
  existing two-key production environment and original selectors were retained.

All 14 required native checks passed with exit 0 and no timeout: contract, scope,
Ruff, format, smoke, unit, regression, mypy, coverage XML, diff coverage,
acceptance, integration, targeted mutation and independent verifier. The original
check budgets remained unchanged, including regression 900 seconds, coverage
1200 seconds and integration 600 seconds; overall outer allowance remained 4410.

| Original check | Actual final result | Pytest seconds |
| --- | --- | --- |
| unit | 1888 passed | 133.17 |
| regression | 2831 passed, 1 original FIFO platform skip | 775.69 |
| coverage | 2831 passed, 1 original FIFO platform skip | 798.85 |
| acceptance | 9 passed | 0.36 |
| integration | 906 passed, 1 original FIFO platform skip | 545.48 |

Integration's native measured duration was 545738 ms, below 600000 ms.
XML line coverage was 91.42 percent (7487/8190); diff coverage was reported as
97 percent, with 304 changed and 9 uncovered lines. The original 85/90 thresholds
were retained. These are local native results, not a required remote CI result.

## Evidence, action and independent handback

Pre-implementation evidence raw SHA256:
`28e9b4dce0f196e385338516371aedcef937af137267a38019b70e7d92408a5d`.
Verification snapshot:
`6a71bbf1c66efcf7c5addf96a0a522e2147c694214f7109d117005044303e046`.
Verifier context:
`bc219ede3636f454d72066ad6f6a7e99fa54af19d63a892c6d03740ff065519c`.
Mutation canonical evidence:
`9121e6ce452825ade6ed3d3ea3915dfd385b34a79f20e101df0bf753ffea7ea4`.
All five original fixed mutations were killed, each with baseline exit 0,
mutant exit 1, original detector/operator and no timeout; the main tree was unchanged.

Action006 canonical digest
`b1e35fc69bd138767e611a67d1334130f96ffa4eebc4caafa38bfe1c938b0c27`
was consumed once by the native recorder at event 107, 2026-10-01T06:42:24Z.
Receipt raw digest:
`96e74c288be5c176a03b5dcd153bcf18cae340801344e1d76f13c215d91c627b`.
It is not reusable. Events 108/109 reached VERIFIED/WAITING_FOR_FINAL_REVIEW.

The independent handback's raw digest is
`60eade39b8bee791c14403d43f73c1c2e2b497d0b6a95a82e01b4a9181c26601`.
Its create-only private `native-archive-006` retains 40 complete originals,
including all 24 non-null native log references, mutation artifacts, context,
coverage, evidence and consumed-action receipt. Root independently recomputed
all archive/current bytes and digests, driver artifacts, all 24 source paths
and nine prior materials with zero mismatch and native schema/snapshot validation.
The full native run did not separately record a per-node collection; the exact
current prerequisite collection remains 907, retaining all original 867 and eight
new helper tests, as proved by the prerequisite record 025.

The original retained native process handle matched actual PID and creation time,
then supplied terminal exit 0 and an exit time; driver tool exit was also 0,
outer timeout was false and cleanup was null. This proves release of that known
scope. Historical engines or unobserved descendants remain UNKNOWN; no global
process-absence claim or unknown-PID cleanup is made.

Old source113's native pass, REV-0009/RF-001 and every prior failed/interrupted
attempt remain preserved. The first integration006 prerequisite's exit remains
UNKNOWN; the separate recovered prerequisite pass did not rewrite it. Current
helper repair and this native pass do not themselves resolve the formal finding.
Task55 requires this task's actual Gate and its own amended admission/verification;
publication and matching real-report acceptance retain their own conditions.
