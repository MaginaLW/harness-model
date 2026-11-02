# Node CI 3.3 contract

## 1. Outcome and trust boundary

Node CI3.3 for `agent-bridge-node@2` / Policy3.2 combines an **attested committed LOCAL approval tuple**, complete fresh CI originals, authenticated completed exact-head Check/artifact, and an **external Gate on the original local host** using unchanged live local3.2 readers. Missing/stale/damaged LOCAL originals reject even when CI is green. No imported filesystem is LOCAL Current or remote-only merge readiness.

Native, Node@1, Policy3.2/profile2, local evidence3.2, approval1.0/review-context2.0 and the existing Ubuntu quality workflow remain unchanged. V0/V1 acquire no V2 verifier/review/pair requirements beyond their existing route rules. Existing local action/recorder restrictions, state transitions, quality thresholds and budgets are not relaxed.

The unchanged local formats/methods are specified in [Local Node2](node-v2-installed-lifecycle.md) and its package-owned schemas/constants.

The fixed logical checks, in order, are:

- V0: `contract,scope,smoke,node_build,node_check,diff_whitespace`.
- V1: V0 plus `ts_coverage,ts_total_lines,ts_diff_lines`.
- V2: V1 plus `acceptance,integration,targeted_mutation,independent_verifier`.

V2 requires five **fresh** actual baseline/mutant pairs. Coverage/product checks reuse the complete fixed shared suite, exact Istanbul/AST-zero/config/product declaration and85% total/90% applicable changed-line thresholds of the local Node2 contract. No npm-only substitute, discovery fallback, old killed projection or arbitrary commands. Native-ownership applicability, successful node-check first seal, subsequent stability and complete original retention remain mandatory. The generated helper PE is host output, not a cross-host byte-identical input or Node's x64 executable role; no PE normalization, extra compilation or compiler-trace framework.

No deployment/settings/credential/paid/model/SDK/WeChat/publication permission is created. Public source scope and private target material/recipient/access/retention require separate actual authorization.

## 2. Fixed producer and source package

| Constant | Value |
|---|---|
| Public engine source | `MaginaLW/harness-model`, provider repository ID`1319293089` |
| Source workflow | `.github/workflows/node-engine-artifacts.yml`; `pull_request`, same-repository PR only |
| Source job / Check / app | `node-engine-artifacts` / `node-engine-artifacts` / `15368` |
| Source job limit | `timeout-minutes:15`, only the new package-build job |
| Target workflow | `.github/workflows/aiflow-node-ci.yml`; `pull_request`, same-repository PR only |
| Target job / Check / app | `aiflow-node-ci` / `aiflow-node-ci` / `15368` |
| Static target declaration | `.ai/node-ci-producer.json` |
| New Windows label | `windows-2025`, with actual host-role verification still required |
| Permissions / checkout | explicit `contents:read,actions:read`; `persist-credentials:false,set-safe-directory:false,fetch-depth:0` |
| Source artifact | exactly `aiflow-node-engine-<run_id>-<run_attempt>` |
| Private CI artifact | exactly `aiflow-node-ci-<run_id>-<run_attempt>` |

Actual private target repository UUID/provider identity/full name are read from the target-owned declaration and authenticated API, not embedded in public code or this contract. An example identity is provider ID`42`, full name`example/synthetic-target`; examples confer no authority. Source authorization/account access does not transfer to that target.

The source artifact has exactly four regular members:

```text
direct/aiflow-0.2.0-py3-none-any.whl
sdist/aiflow-0.2.0.tar.gz
sdist-rebuilt/aiflow-0.2.0-py3-none-any.whl
build-manifest.json
```

Use existing setuptools wheel/sdist/rebuild. Keep source-owned package allowlists, registering only necessary schemas/build entries; never add tasks/private payload/runtime/whole `.ai`. No machine/user/absolute local path/credential in public metadata. Public visibility does not prove target download access.

The closed build manifest is:

```text
{kind:"aiflow-node-engine-build",schema_version:"1.0",repository_id,
 source_head,workflow_path,workflow_blob_sha256,job_key,run_id,run_attempt,
 python_version,setuptools_version,members,package_payload_sha256,resource_manifest_sha256}
```

`members` is the three ordered payloads, each `{path,origin,size,sha256}`, origin`direct/source/sdist_rebuilt`; no manifest self-hash. Authenticate actual archive/manifest bytes. Release requires reviewed source quality/code/Gate, required exact-head checks and publication scope. Packaging/15-minute job success replaces no native/proof gate.

Manifest types: repository_id=`1319293089`; source_head is40-hex and equals authenticated run/checkout PR head; path/job equal section2; run_id/attempt are positive integers; python_version is exactly three integers beginning3,11; setuptools_version is a bounded version string from the approved source lock. All SHA fields are64 lower hex; member sizes are bounded integers. Verify each of the three actual raw members against its exact ordered path/origin/size/SHA, then payload/resource digests against actual distributions. Selection validates the **complete authenticated four-member archive**, including build-manifest raw Ref, before choosing direct or rebuilt wheel; no same-version replacement.

The package payload digest is SHA256 of the canonical UTF-8-path-sorted list of `{path,size,sha256}` for every validated regular wheel member, including dist-info/RECORD. It is an extracted-content projection; the independent raw wheel SHA remains mandatory and binds the whole container. Source direct and rebuilt wheels must have the same declared package/resource content; each origin still binds its own raw wheel.

Provisioning reuses approved public locked installation. If Python dependencies require uv.lock, read its trusted Git blob at the selected public source_head and bind raw blob SHA in control/provision inputs and admission input_materials_sha256. Node dependencies use the approved subject-bound package-lock. Neither lock, wheelhouse nor dependency payload becomes a fifth public artifact member; no lock service or package registry publication.

Select/download the actual immutable artifact **before target LOCAL acceptance**. Both hosts install the same raw wheel with independent checks. Version/commit/equal payload/rebuild/normalization cannot substitute; direct/rebuilt origins remain distinct. Prove authorized download from both hosts; no credential export or new release/mirror/storage workaround.

## 3. Closed data model

Reject unknown/duplicate fields, wrong types, missing/extra members and aliases. SHA256 is64 lowercase hex; bounded counts/sizes are nonnegative integers, IDs positive, never bool. Reuse UUID/Git-ID/safe relative-path validators and existing JSON/physical limits.

Object digests use UTF-8 canonical JSON: sorted keys, compact separators, ensure_ascii=false, allow_nan=false, no trailing LF.

Common objects:

```text
Ref={ref,size,sha256}
ReviewRef={record:Ref,context:Ref,review_id,revision,context_sha256}
SpecApprovalRef={record_sha256,decision_unit_id,approval_type:"spec"}
CodeApprovalRef={record_sha256,decision_unit_id,approval_type:"code",evidence_sha256}
GitBinding={repository_id,task_id,branch,base_commit,subject_commit,subject_tree,
 policy_sha256,spec_sha256,classification_input_sha256,decision_unit_ids,verification_level}
```

GitBinding.repository_id and declaration.repository.repository_id are UUIDs; platform/source repository IDs are provider integers. Approval refs name canonical committed records, not a new schema. Spec is not final/subject-bound; code evidence_sha256 is the canonical **full-final** digest, not snapshot. DU coverage derives from actual Policy.

StaticDeclaration is present in the approved target subject before new LOCAL acceptance/final:

```text
{kind:"aiflow-node-ci-producer",schema_version:"1.0",
 repository:{repository_id,provider_repository_id,full_name},
 profile:{id:"agent-bridge-node",revision:2},policy_version:"3.2.0",
 workflow:{path,ref,sha256},
 producer:{job_key,check_name,app_id,event:"pull_request"},
 tier_contracts:{V0:execution_contract_sha256,V1:execution_contract_sha256,V2:execution_contract_sha256},
 engine_source:{repository_id,full_name,workflow_path,workflow_ref,workflow_sha256,job_key,artifact_name},
 engine_artifact:ChosenEngineArtifact,
 artifact_policy:{ci_artifact_name,retention_days,visibility_scope:"private_target_repository"}}
```

Fixed paths/job/check/app/event/templates must equal section2. Workflow ref is the declared candidate branch ref; authenticate the actual executing workflow reference separately and require its exact blob content SHA to match. The declared file/ref must be present at the approved subject and unchanged through permitted governance descendants. No circular workflow/declaration self-hash. Retention/access constraints are subordinate to real authorization. There are no private declaration limit knobs.

ChosenEngineArtifact is:

```text
{origin:"direct"|"sdist_rebuilt",source_repository_id,source_full_name,
 workflow_id,workflow_path,workflow_ref,workflow_sha256,source_head,
 run_id,run_attempt,job_id,artifact_id,artifact_name,artifact_digest,
 wheel:{member,size,sha256},sdist:{member,size,sha256},
 build_manifest:{member,size,sha256}}
```

Authenticate source records/downloads and exact members; preserve the provider digest response and reject unsupported/missing digest behavior. Existing source runtime IDs are selected inputs; future target IDs are not guessed. The whole object exists in the pre-final declaration. Combined Gate checks raw wheel/install receipt/RECORD/resources/current engine; direct_url or selected module equality alone is insufficient.

AttestedSource is:

```text
{kind:"aiflow-node-ci-attested-source",schema_version:"1.0",
 binding:GitBinding,attestation_head,static_declaration:Ref,engine_artifact:ChosenEngineArtifact,
 source_evidence:{original:Ref,canonical_sha256},
 task:Ref,events:Ref,classification:Ref,spec:Ref,policy_members:[Ref],
 approvals:Ref,applicable_spec_approvals:[SpecApprovalRef],
 applicable_code_approvals:[CodeApprovalRef],
 v2:null|{snapshot_sha256,verifier_actor,verifier_context:Ref,
          design:ReviewRef,implementation:ReviewRef}}
```

V0/V1 `v2=null` and preserve existing route/spec/ASK/code requirements; never invent AUTO approvals. V2 source is passed final local3.2, with snapshot, independent verifier/context, applicable approved reviews and code approvals. This certifies **committed metadata binding only**. No `current` field or claim that the producer read historical LOCAL raw proof.

Descriptor is generated deterministically outside the protected source root and reconstructed by CI:

```text
{kind:"aiflow-node-ci-descriptor",schema_version:"1.0",
 source_tuple_sha256,static_declaration_sha256,engine_artifact_sha256,
 execution_contract_sha256,verification_level,attestation_head}
```

Its digest covers the canonical closed source tuple/artifact/declaration and the cap-bearing package-owned execution contract. No local-to-Actions raw upload or imported descriptor permission is needed. The producer derives it from committed inputs. Future target runtime IDs are not in it.

RuntimePlatform is:

```text
{provider:"github",repository_id,full_name,workflow_id,workflow_path,workflow_ref,
 workflow_sha256,event,head_sha,run_id,run_attempt,job_id,job_key,
 check_run_id,check_name,app_id}
```

`head_sha` is the actual declared PR/checkout/execution head. Authenticate provider run/Check head and workflow-code coordinates separately. `GITHUB_SHA` can identify a synthetic merge and is not assumed equal. Status/conclusion/expiry are live authenticated facts, not fields accepted from caller JSON. The producer can authenticate an in-progress identity but cannot certify its future completed Check.

Admission is:

```text
{kind:"aiflow-node-ci-admission",schema_version:"1.0",
 descriptor_sha256,platform,input_materials_sha256,engine_content_sha256,claimed_at}
```

It is exclusively created before package-owned preflight/pair/Node proof processes. Hash provisioned input inventories, not a future prepared document. Explicit workflow public material provisioning is a separate reviewed prerequisite, with fixed recipe/provenance/receipts; collectors never secretly download/install. Partial/interrupted/reused claims remain spent.

`engine_content_sha256` is the canonical digest of `{wheel_sha256,package_payload_sha256,resource_manifest_sha256,execution_contract_sha256}` from validated selected inputs. Preserve host/install-derived metadata separately; never strip it to force cross-host equality.

Prepared/Run closed objects:

```text
prepared={kind:"aiflow-node-ci-prepared-3.3",schema_version:"1.0",
 descriptor:Ref,source_tuple:Ref,admission:Ref,platform,profile,
 verification_level,execution_contract_sha256,
 manifests:{source:Ref,node:Ref,npm:Ref,dependencies:Ref,engine:Ref,host_tools:Ref,preflight:Ref}}
run={kind:"aiflow-node-ci-run-3.3",schema_version:"1.0",prepared:Ref,
 descriptor_sha256,platform,inputs,environment,roots,executions,coverage,
 product_tests,installed_mutation,outputs,failure}
```

Node input/environment/root/process/coverage/output subobjects use the existing fixed Node2 original contracts with CI-owned role coordinates. Do not reinterpret local3.2 paths or add arbitrary commands. Nonapplicable coverage/products/pairs are null. V2 installed mutation is exactly `{admission_sha256,engine_content_sha256,pairs,failure}`; pairs are ordered MUT-V2-001..005 with the existing exact overlay/baseline/mutant original structures. Failure is null or a bounded existing-style reason code. It is not an action-backed local IMUT run.

Public CI evidence is:

```text
{schema_version:"3.3",kind:"aiflow-node-ci-evidence",mode:"ci",binding:GitBinding,
 generated_at,conclusion,source_binding_kind:"attested_committed_tuple",
 source_tuple:Ref,descriptor:Ref,platform,prepared:Ref,run:Ref,
 checks,node_binding,installed_mutation,reproduce_command,known_limitations}
```

Checks are exactly the tier's ordered existing rows/status rules. Node binding retains fixed source/profile/material/coverage/product projections through CI refs. V2 independent_verifier reflects the validated independent committed source-verifier tuple; actual LOCAL currentness/finality remains external. Producer identity is the platform tuple. `known_limitations` must state original-host LOCAL originals are required. No local phase/review/finalization is synthesized; CI evidence cannot be passed alone to the unchanged local Gate.

The portable package index and each role manifest are:

```text
index={kind:"aiflow-node-ci-originals",schema_version:"1.0",
 evidence:Ref,descriptor:Ref,source_tuple:Ref,roles:[{id,manifest:Ref}]}
manifest={id,root,identity,entries,total_bytes}
```

Inventory identity and file/directory entry shapes are the existing closed originals. Preserve original producing root/identity metadata, but never use it as an extraction instruction or as a consumer inode. Fixed role IDs and membership follow section5; extras/omissions reject.

## 4. Source authority reader

Trusted source Git spools exact attestation-head task/events/approvals/context blobs unchanged into control; Ref hashes name committed bytes. Source separately retains physical checkout raw; LF blobs need not equal CRLF checkout. Consumer compares control refs to trusted reachable original-host Git blobs, never executes imported `.git`, follows old absolute paths or normalizes wheel/content.

The producer reader performs this finite ordered validation without recovery/state writes:

1. Strict task/events/risk/materialized state and Git identity. Require `_ci_git_assessment(...).subject_commit == task.subject_commit`; its helper may propose a newer subject. Preserve ancestry, per-commit same-task governance, cached/worktree and unchanged declaration/workflow/artifact checks; no synchronization.
2. Recompute DU/route/level/ASK via actual Policy, parse_decision_units/current_classification_input_digest/route_task/verification_for_task, frozen spec and ordered subject-sync events. Preserve BLOCK/ASK/completed-unit semantics; reject stale risk/classification or selected easier units.
3. Full ASK options/selection/digest/actor/reason and DU/spec/classification/Policy transaction bindings. Do not fake WAITING_FOR_ASK or rely solely on answered-ID scan. REVIEW spec approvals require existing pure checks plus event/actor/structured design-review correspondence; not final binding.
4. Validate all registered review revisions/contexts, filenames/digests/events/actors/resolutions. Select latest revision per ID then latest registered stage. Rebuild expected committed metadata/diff/evidence; design has no new subject binding, implementation binds subject/snapshot. Reject dangling/stale/nonapprovable/open high-critical records.
5. Require passed final3.2 V2/snapshot/context, latest implementation_started/retried cycle and independent verifier. Relate verification_started/passed, implementation review and code approval to that cycle/context. No invented finalization event or stronger finalizer proof. Pure pre/final reconstruction checks projection, not raw currentness.
6. Code records match code_approved additions/actor/structured review, full-final canonical hash, subject and DU coverage. No synthetic pending marker; approval/freshness semantics unchanged.

Reuse pure validators; extract only missing committed-context/review-resolution/approval-event/ASK/cycle relations. `latest_review_assessment` enters live Node replay: never suppress its failure, force node_policy=false, inject passing V2 facts or construct Current/node_evidence_current. Return explicit attested binding.

Historical committed metadata is authenticated at its execution head. Later permitted append-only governance need not preserve the current events file's raw bytes; the original-host live Gate must still confirm the same subject/declaration/engine/final/snapshot and valid latest review/code authority. An old approved record alone is insufficient.

## 5. Execution roles, reuse and clean boundaries

Fixed common role IDs are exactly:

```text
source artifact engine runtime dependencies host preflight control node
```

Source keeps the complete CI clone/.git/metadata; artifact the exact payload/download/install originals; engine the full ordinary prefix/RECORD/startup/direct_url/pyvenv/launchers/pyc; runtime/dependencies separate inputs; host declared interpreter/OS/Git/compiler/client; preflight node/npm originals; control raw blobs/descriptor/tuple/admission/prepared/run/evidence/provision receipts; node the whole checkout/.git/deps/dist/build-dist/source manifest/diff/home/cache/tmp/raw/reports/coverage/domain/products/fixtures/native.

V2 adds exactly `pair-0-b,pair-0-m,...,pair-4-b,pair-4-m`, hence N=19; V0/V1 N=9 with no pairs. Each phase top level is exactly `i,c,h,t,raw,report.json`; its raw directory is exactly receipt.json/stdout.raw/stderr.raw/stdout.log/stderr.log. Keep empty directories and all ten distinct installed copies. Node raw directories are exactly setup-clone/setup-checkout plus EXEC-001..008 at V0 or EXEC-001..010 at V1/V2, each with the existing five originals. Retain any actual fixed-plan outputs even if not independently required at that tier. Unknown neighbors reject.

Node's internal sealed output inventory excludes only its own run.json. The external manifest still retains/hashes that file. Outer package index/manifests live outside originals; control does not inventory those outer metadata files, preventing self-reference. One physical original with multiple declared uses may be explicitly referenced once; different physical copies are never content-deduplicated or dropped.

Reuse fixed plan/Job runner and `_run_stage/_pair_originals`. Extract actual shared receipt/envelope/pair/coverage/product byte checks. Producer checks live identities/disjointness/unchanged inputs/outputs/native seal. Portable replay checks producing-coordinate argv/cwd/env/origins/raw/log/report/probe/overlay/AST/catalog/coverage/products, opening only package members. No process/import/compile/repair/write in pure replay; trusted Git/client observations are separate.

Local authority/action/material writers/IMUT claim/execute/collect/replay/recheck stay unchanged. New fixed interfaces:

```text
claim_ci_attempt(attempt_root,descriptor,platform,input_inventories) -> Admission
prepare_ci_materials(source_root,payload_root,attempt_root,admission) -> Prepared
record_ci_pairs(attempt_root,admission,prepared) -> CiPairOriginals
execute_ci_node(source_root,task_id,attempt_root,admission,prepared,pairs=None) -> CiRun
validate_ci_originals(package_root,descriptor,source_tuple) -> CiContentFacts
```

CiContentFacts is content validity, not LOCAL Current or platform authentication. No shadow task, force_ci flag, synthetic approval, generic backend or global spent-token service.

GITHUB_WORKSPACE owns protected `source/`, TEMP/TMP/TMPDIR `.tmp/`, run `.tmp/node-ci/<run>-<attempt>/` and sibling HOME/cache/tools, set before Python. Preserve strict temp-descendant/no system Temp/no source exception. Attach check-ref-format-validated PR branch; run.head_sha==PR head==git HEAD, workflow blob checked separately. No token/authheader in.git/logs/package or global trust/config change. Old Ubuntu/native temporary setup stays unchanged.

## 6. Fixed CI-only capacity contract

Existing file128MiB/JSON16MiB/role20,000 entries/512MiB and shared materials/ten-copy budgets stay unchanged. CI transport uses one fixed table in `src/aiflow/node_ci.py`; no registry/private declaration limits/caller knob/env override/public bypass.

Fixed table columns, each tier:

```text
(max_physical_entries,max_original_bytes,max_manifest_bytes,max_index_bytes,max_archive_bytes)
```

Expanded bytes≤original+manifest+index limits. Count role roots/envelopes/members, outer metadata separately, not nested projections twice. Index/each JSON≤16MiB; table values cannot grow role sets.

Unregistered source state is an explicit non-runnable constant, not an unknown accepted configuration:

```text
CI_CAPS_REGISTERED = False
CI_CAPS = {"V0":(0,0,0,0,0),"V1":(0,0,0,0,0),"V2":(0,0,0,0,0)}
```

The table has exactly those three rows/five columns. Registration replaces them with reviewed concrete positive integers and sets the literal flag true; missing/nonpositive/unregistered values reject production admission. There is no automatic registration or runtime lookup service. The exact cap table, registration flag and fixed role/check contracts enter the execution-contract digest and selected cap-bearing engine artifact. All consumers must be complete before public `--node-ci` activation. Static artifact_policy keeps only name/retention/visibility; it never silently acquires limit fields.

Before registration, a controlled Windows **implementation measurement** may directly exercise the fixed fresh physical kernels under an isolated, explicitly labelled fixture platform. It runs complete actual fixed operations/new pairs and retains every physical original. Fixture observations are never authenticated GitHub Current, accepted CI, a passing combined Gate or production admission. No production flag admits fixture credentials/Current, and no remote run must first succeed to measure.

That first measurement has a finite source-owned envelope, only for the controlled measurement: N=9/19, total physical entries≤N×20,000, original bytes≤N×512MiB, index plus N manifests≤(N+1)×16MiB, with all original per-file/JSON/per-role and shared budgets also enforced. This is neither preallocation nor the production cap. Verify exact write/storage/action bounds first. No old historical-LOCAL package size substitutes for fresh measurement.

Independent review inspects actual full-kernel candidate/inputs/roles/members/bytes/index/manifests, ordinary/runtime/Job/original proof and bounded local ZIP measurements. Retain immutable originals/review record; bind concrete code/Norm/frozen-spec values and reserve rationale **before final source verification/packaging and remote acceptance**. No unresolved registered values. Changed candidate bytes require current-candidate proof; over-cap needs measured independent amendment, never automatic growth/drop/retry.

Admission, proof/package writer, download/ZIP/manifest/inventory/content readers enforce the **same installed tier table** before allocation/writes, incrementally and at completion. Bound actual compressed/expanded bytes/entries/metadata; provider size is not actual size. One valid role cannot validate an over-limit package. Missing/over-cap rejects with bounded diagnostics/spent claim; no private knob or remote-first cycle.

## 7. CLI, platform and final consumer

Explicit production opt-in:

```text
python -I -B -m aiflow verify TASK --ci --node-ci
  --ci-run-dir RUN --output RUN/evidence.json --node-ci-payload PAYLOAD
```

The original-host consumer entry point is `python -I -B -m aiflow node-ci gate TASK --run RUN_ID --attempt ATTEMPT --download-dir OWNED`. These IDs are selectors only. It first calls the unchanged local Gate, authenticates the actual fixed artifact with the official client, retains/downloads it under the explicitly owned directory outside the protected source root, validates all originals, and repeats the local decision boundary. It returns the combined result as JSON without source task/approval writes. No caller platform JSON is accepted; the existing local `gate` behavior stays unchanged.

Payload is the fixed owned workflow-provisioned node/dependencies tree, not executable commands or authoritative JSON. Unsupported profile/old bare Node CI/local installed-mutations/finalize/partial/provisional combinations reject before recovery/write/process. New mode also rejects absent registration/incomplete consumers/declaration/real artifact/current committed authority/platform authentication before claiming/running. Source `.ai` stays read-only. New CI evidence uses its disjoint3.3 schema; no mode=ci is legalized in3.2.

Use owned-workspace official gh2.103.3, official-release integrity checked, through a thin fixed GET adapter. No global login/PATH/config change or user token export. Authorized token only in the client subprocess, never proof environments/files. Bound time/response/stream; use explicit repo/IDs and complete exact-attempt pagination, not a new HTTP/auth framework.

Caller IDs select, never authenticate. Fetch actual repo/PR/head/workflow/blob/run/attempt/jobs/Check/artifact. Require fixed event/job/check/app15368, completed/success, exact head/attempt, supported digest, nonexpiry and actual download/member hashes. Latest-first-page/cached JSON/env/label/native Gate is insufficient. Wrong/ambiguous/reused/mixed/inaccessible associations reject; producer cannot authenticate future completion.

An eligible genuinely new workflow run or run_attempt can perform a complete new attempt with new exclusive claim/root/materials/copies/pairs/receipts and exact authenticated association. Preserve previous failed/interrupted originals. No partial resume, claim repair, automatic retry framework, reused local killed projection or old artifact paired with a newer Check.

Actions ZIP only wraps section3's closed directory package. Stdlib bounded reader rejects aliases/traversal/absolute names/links/reparse/unsupported entries or codec/wrong members/hash/overflow before writes. No blind extraction. Keep original bytes under owned download space outside protected source; imported.git is content, never executed authority.

On the **original host**, require unchanged local3.2 live Gate, validate all fresh originals/tuple/declaration/wheel/platform, and read historical blobs from trusted reachable local Git. Compare final canonically under existing text/Git semantics, keeping each raw separately; no wheel normalization. Repeat subject/governance/live Gate at final decision. Existing Gate selects latest valid review/code; stale LOCAL raw/material/snapshot/authority rejects.

Return combined readiness only if local_current, source_tuple_matches, fresh_ci_originals_passed and platform_authenticated all hold. Original-host absence/loss has no portable LOCAL fallback. No second implementation approval or task transition is written. The authenticated Check may attest successful CI execution while the combined local decision rejects later local damage; name/report that distinction truthfully.

## 8. Implementation scope, failure and acceptance

Use node_ci.py, existing Node/installed byte kernels, evidence/schema/CLI/Gate/freshness/resource integration and a thin tools/ci client/build helper. Keep approval schemas and resource builder/allowlist. No service/registry or error/status recovery/marker writes.

Freeze interfaces first; separate file ownership for pair, Node, fixtures/client work; integrator owns shared schema/tuple/CLI/Gate/caps/workflows and integration. Governance and safe test/docs scope obey existing review/task rules.

Missing/stale/unsafe authority/material/process/content/platform/cap fails closed with truthful checks/all originals/spent claims. No fallback, threshold change or repair. Cleanup only exact owned disposable paths after awaited teardown; never protected source/old attempts/evidence/claims/WIP. Rollback only reviewed ordinary reverts, preserving history/tasks/originals and old native/local/unsupported behavior.

Acceptance: actual direct/rebuilt ordinary installs; V0/V1/V2 and old-mode rejection before writes; full fresh Windows operations/pure replay; unchanged native/local regressions; all failures in sections4-7, including forged Current, content/process/cleanup/attempt/platform drift and later LOCAL tamper despite green Check. Require full suite/timeouts, source full tests85/90 complete original-base diff, Ruff/format/mypy/whitespace, native five mutations and exact-head required CI.

The serial completion chain is:

1. Approve source interfaces/scope/staged proof without a future artifact prerequisite.
2. Implement; full bounded fixture-kernel measurement/originals/independent cap review; register concrete constants and complete consumers.
3. Final cap-bearing ordinary/native/quality/code/Gate proof; publish only authorized exact source artifact.
4. Authenticate/download real artifact on both hosts; freeze actual target declaration/workflow at subject before new LOCAL proof. Unknown inputs block, not pass placeholders.
5. Full target LOCAL lifecycle/code/Gate, only permitted governance descendants; descriptor outside protected root.
6. Actual authorized private CI/fresh attempts/all originals; authenticate completed exact-head Check/artifact and original-host combined Gate before delivery.

Target delivery needs authorization/coordination and non-overwriting baseline/WIP checks. Fixtures, metadata or remote green alone complete no capability.
