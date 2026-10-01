# Parallel-copy original prerequisites passed 022

Measured source: `113ecddd90a4c0e4f51cd7d7cea64700cf12736c`.
Measured attestation HEAD: `1158a0869f480450b4efdf2b04bd4aa8a955b404`.
Frozen spec remains `992b927ce833a8fa9876c7e278d024eca7903763621ea84391c2ad4c09f6916c`.
Helper remains 26af47db; test input stabilization remains 5d20932b.

The new fixed candidate actually completed D cold1 / warm10, median complete
warm cost 73.8351ms, actual driver/launcher exits 0. All ten physical/content/
mode/mtime/source-pristine/thread proofs passed. This is a current single-arm
measurement, without a causal speed or future whole-suite claim.
D handback SHA: `3a95ea467cc150d0c8dd280504626f7a30cd7870086cbdcaebc0026e5e6310b1`.

The four prerequisites then actually ran serially with unchanged selectors,
assertions, MINENV and deadlines, and a resource handback between stages:

| Stage | Actual result | Raw pytest duration |
| --- | --- | --- |
| Narrow | 12 passed | 1.14s |
| Complete fixture | 97 passed, zero skips; all old65 included | 50.51s |
| Complete external-review | 187 passed, one original FIFO skip | 129.37s |
| Original integration600 | 898 passed, one original FIFO skip | 576.91s |

Integration collected 899 unique nodes and included all old867, missing zero.
Its real runner duration was 577173ms, below the original 600000ms deadline;
pytest/owned process/driver/launcher all exited 0, without timeout or cleanup.
Original -q observed the FIFO skip location/reason, not its complete node ID.
Narrow handback SHA: `98fc4cf6e49c59f14fc0d29aa988f643693550836eb6fb75ce2b62e6591672ec`.
Fixture handback SHA: `cd550b882cc185e1bdd12623de3a713183a41570291624064b6fbafd73e04e0a`.
External handback SHA: `f93b62460ca7dbc537c3c2a446801f827eb21b1d30576a14ccd7813c3c25805c`.
Integration handback SHA: `79d734d3d6622e5988c7f62e76899287584ec85b57de9707efdf85a03671ceec`.
Integration result SHA: `823b9d0c22acb525f7bc92031718026a5091665d3c34f6310be796ae7fbe04ba`.
Root read raw results and independently checked artifact hashes, complete
source-before/after equality, unique collections and old node subsets. Each
stage's 87 retained Popen identities and retained venv root actually exited 0.
Known resources were RELEASED; unretained engine/history descendants remain
UNKNOWN. No global absence or complete historical process-tree claim is made.

Old native/600 failures, fixture96/1 and the single aged-input stdlib observation
remain unchanged. The old metadata transient's cause remains UNKNOWN.
These are prerequisite passes, not full native V2, implementation Review or
Gate. A new single-use action005 can now be separately bound to the unchanged
source and current approvals; default V2 still needs actual fresh preflight,
all 14 checks / 5 mutations, independent Review, finalize and code approval.
TASK-0055 readmission, publication and real matching-report F retain their entry
conditions. No provider, push or merge was performed in this implementation task.
