# Private parallel-copy success comparison motivates a proper design

One attempt bound source98b5db7c7643f579619fcc00703e3a5f9044f1b3,
HEADcb03dc1b9a21b190e875dca38a547ef0f39fcd7e, B589/A4/D21 and the existing
locked standard-GIL Python3.13.15/full core Git/original MINENV.
Ten alternating pairs compared the untouched isolated _copy_snapshot against
the private four-worker prototype on a truly qualified initial snapshot.
The original successful builder ran once; owner cold1/hits0/not-disabled.
These twenty isolated calls were not full warm hits or pytest/native execution.

Original median47.12235ms [42.04060,52.97680]; prototype median34.77265ms
[30.71990,48.87370]. Paired A-B median11.44385ms,mean10.73726ms; all ten faster.
Each prototype interval included startup, real copy2, drain/shutdown and final
bottom-up directory copystat. Target mkdir/current qualification/proof scans
and one observer setup were outside those intervals. Observation/future
compatibility overhead and complete warm/suite benefit remain unknown.

All101 ordinary files per pair matched bytes,size,mode,mtime and distinct
source/A/B physical identities; directory modes/mtime matched too. Stable
writable source directories and the256-file ceiling were enforced. Source
remained pristine, targets task-free, all submitted threads ended. Source24,
old8/task/spec/locks/runtime/Git pair/commonrefs/index/topology matched before
and after. Shell/driver exited0, no timeout/interruption. Driver5.0360203s;
launcher5.5410871s. Three retained owned processes matched actual PID/creation
and exited0. Preserve actual taskkill helper38924 exit128 targeting26988;
the target exit preceded helper creation, and cleanup is not called successful.
One bounded five-known-ID query exited0/no timeout/zero rows; its retained
helper also exited0. Historical unobserved descendants/launcher creation are
unknown. Known resources and the source/ref/index/ledger freeze are released.

Only a proper bounded physical-copy design is selected for preparation. This
prototype is not an admitted replacement: DirEntry selection, early readonly
directory metadata and failure/partial sequencing remain unresolved. Future
design must retain current guards, actual copy2, physical isolation, originals,
drained submitted work, actual failures/partials and no builder retry. It needs
spec_changed admission and independent DesignReview before implementation.
No native600 PASS, V2/action005/Review/finalize/Gate or downstream entry follows.

Private evidence:${RUNTIME_ROOT}/e4-tools-20260930-001/parallel-copy-cost-draft-001.
Handback SHA256:fd3141e09b4720ff4250a19162a8749107e7f20233a1754a7ff92390efea3085.
Completed SHA256:c79aeb5baab9e632e265d953c4065feb5f4724b3490ead3e89d931ca26235a9a.
Launcher SHA256:d2b063603aa14fad6a14ad150d35ed08deecb18c044501960f741161633e8867.
Terminal SHA256:10728ab75ff4e510fab09c388506b153b2b66f334bde33e688711d5a329f0da2.
