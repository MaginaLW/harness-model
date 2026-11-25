from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from aiflow.evidence import verification_snapshot_sha256
from tools.ci import verify_private_replay_receipt as verifier

ROOT = Path(__file__).resolve().parents[2]
REPO = "MaginaLW/harness-model"
ORDINARY = ".github/workflows/ai-quality-gate.yml"
PROTECTED = ".github/workflows/private-replay-receipt.yml"
PROTECTED_REF = f"{REPO}/{PROTECTED}@refs/heads/main"
DOMAIN = "aiflow-private-v2-receipt-v1"
BASE, SUBJECT, HEAD, WORKFLOW_BLOB = (digit * 40 for digit in "1234")
TASK = "TASK-9999"
BRANCH = "codex/synthetic-verification"
MUTATION = "a" * 64
ENGINE, VERIFIER = "b" * 64, "c" * 64
MAIN = "git/ref/heads/main"
PR = "pulls/71"
RUN = "actions/runs/83"
CHECK = "check-runs/97"
WORKFLOW = "actions/workflows/ai-quality-gate.yml"
EVIDENCE = f"contents/.ai/tasks/{TASK}/evidence.json?ref={HEAD}"
MISSING = object()
Json = dict[str, Any]


@pytest.fixture(scope="module")
def keys() -> Iterator[tuple[Path, Path]]:
    with tempfile.TemporaryDirectory() as directory:
        trusted, other = (Path(directory, name) for name in ("trusted", "other"))
        for path in (trusted, other):
            subprocess.run(
                ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "synthetic", "-f", str(path)],
                check=True,
                capture_output=True,
                timeout=10,
            )
        yield trusted, other


_SIGNATURE_CACHE: dict[tuple[Path, bytes, str], str] = {}


def _key_digests(keys: tuple[Path, Path]) -> dict[Path, str]:
    paths = (
        keys[0],
        keys[0].with_suffix(".pub"),
        keys[1],
        keys[1].with_suffix(".pub"),
    )
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


@pytest.fixture(scope="module", autouse=True)
def _keys_guard(keys: tuple[Path, Path]) -> Iterator[None]:
    before = _key_digests(keys)
    _SIGNATURE_CACHE.clear()
    try:
        yield
        assert _key_digests(keys) == before, "Module SSH keys were mutated during test execution"
    finally:
        _SIGNATURE_CACHE.clear()


def _sign(key: Path, body: bytes, namespace: str = DOMAIN) -> str:
    cache_key = (key.resolve(), body, namespace)
    cached = _SIGNATURE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    result = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", namespace],
        input=body,
        check=True,
        capture_output=True,
        timeout=10,
    )
    signature = result.stdout.decode("ascii")
    _SIGNATURE_CACHE[cache_key] = signature
    return signature


@pytest.fixture
def env(keys: tuple[Path, Path]) -> dict[str, str]:
    key = keys[0].with_suffix(".pub").read_text(encoding="ascii").split()
    return {
        "GITHUB_REPOSITORY": REPO,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_WORKFLOW_REF": PROTECTED_REF,
        "GITHUB_SHA": BASE,
        "GITHUB_WORKFLOW_SHA": BASE,
        "TRUSTED_WORKFLOW_SHA": BASE,
        "PR_NUMBER": "71",
        "TASK_ID": TASK,
        "ORDINARY_RUN_ID": "83",
        "GITHUB_RUN_ID": "89",
        "GITHUB_RUN_ATTEMPT": "3",
        "RECEIPT_APP_ID": "91",
        "CHECK_RUN_ID": "97",
        "ENGINE_SHA256": ENGINE,
        "VERIFIER_SHA256": VERIFIER,
        "RECEIPT_PUBLIC_KEY": " ".join(key[:2]),
    }


@pytest.fixture
def evidence() -> Json:
    # Start from the public synthetic contract template and populate this test's identities.
    template = ROOT / "tests/fixtures/contracts/valid/evidence-v2.json"
    value = json.loads(template.read_bytes())
    value.update(
        repository_id="b85e5a53-4935-4436-bdbc-c26a241bfae8",
        task_id=TASK,
        branch=BRANCH,
        base_commit=BASE,
        subject_commit=SUBJECT,
        reproduce_command=["synthetic", "合成"],
    )
    mutation = value["targeted_mutation"]
    mutation["evidence_ref"] = mutation["evidence_ref"].replace("TASK-0001", TASK)
    mutation["mutation_evidence_sha256"] = MUTATION
    value["verification_snapshot_sha256"] = verification_snapshot_sha256(value)
    return value


def _contents(value: Json) -> Json:
    raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
    return {"encoding": "base64", "content": base64.encodebytes(raw).decode("ascii")}


def _signed_bytes(snapshot: str) -> bytes:
    # Independent wire vector, including key order, integer types, punctuation and no newline.
    return (
        f'{{"app_id":91,"base":"{BASE}","check_run":97,"engine_sha256":"{ENGINE}",'
        f'"head":"{HEAD}","mutation_evidence_sha256":"{MUTATION}","ordinary_attempt":2,'
        f'"ordinary_run":83,"ordinary_workflow":"{ORDINARY}","ordinary_workflow_blob":'
        f'"{WORKFLOW_BLOB}","pr":71,"protected_attempt":3,"protected_run":89,'
        f'"protected_workflow":"{PROTECTED_REF}","protected_workflow_sha":"{BASE}",'
        f'"protocol":"{DOMAIN}","repository":"{REPO}","result":"private-v2-gates-passed",'
        f'"subject":"{SUBJECT}","task":"{TASK}","verification_snapshot_sha256":"{snapshot}",'
        f'"verifier_sha256":"{VERIFIER}"}}'
    ).encode("ascii")


@pytest.fixture
def api(evidence: Json, keys: tuple[Path, Path]) -> dict[str, Json]:
    repo = {"full_name": REPO}
    return {
        MAIN: {"object": {"sha": BASE}},
        PR: {
            "number": 71,
            "state": "open",
            "base": {"repo": dict(repo), "ref": "main", "sha": BASE},
            "head": {"repo": dict(repo), "ref": BRANCH, "sha": HEAD},
        },
        RUN: {
            "repository": dict(repo),
            "head_repository": dict(repo),
            "id": 83,
            "event": "pull_request",
            "workflow_id": 79,
            "head_branch": BRANCH,
            "head_sha": HEAD,
            "run_attempt": 2,
            "pull_requests": [{"number": 71, "base": {"sha": BASE}, "head": {"sha": HEAD}}],
        },
        WORKFLOW: {"id": 79, "path": ORDINARY},
        f"contents/{ORDINARY}?ref={BASE}": {"sha": WORKFLOW_BLOB},
        f"contents/{ORDINARY}?ref={HEAD}": {"sha": WORKFLOW_BLOB},
        EVIDENCE: _contents(evidence),
        f"compare/{BASE}...{SUBJECT}?per_page=1": {"merge_base_commit": {"sha": BASE}},
        f"compare/{SUBJECT}...{HEAD}?per_page=1": {"merge_base_commit": {"sha": SUBJECT}},
        CHECK: {
            "id": 97,
            "app": {"id": 91},
            "name": "private-v2-receipt/staged",
            "head_sha": HEAD,
            "status": "completed",
            "conclusion": "success",
            "output": {
                "summary": _sign(keys[0], _signed_bytes(evidence["verification_snapshot_sha256"]))
            },
        },
    }


def test_accepts_independently_signed_wire_bytes(env: dict, api: dict, evidence: Json) -> None:
    expected = _signed_bytes(evidence["verification_snapshot_sha256"])
    assert verifier.canonical(verifier.statement_for(env, api.__getitem__)) == expected
    verifier.verify(env, api.__getitem__)


def _stage_signed_evidence(api: dict, evidence: Json, key: Path) -> None:
    snapshot = verification_snapshot_sha256(evidence)
    evidence["verification_snapshot_sha256"] = snapshot
    api[EVIDENCE] = _contents(evidence)
    api[CHECK]["output"]["summary"] = _sign(key, _signed_bytes(snapshot))


def test_accepts_multiple_and_extended_decision_unit_ids(
    env: dict, api: dict, evidence: Json, keys: tuple[Path, Path]
) -> None:
    evidence["decision_unit_ids"] = ["DU-1000", "DU-001"]
    _stage_signed_evidence(api, evidence, keys[0])
    verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("spec_sha256", MISSING),
        ("spec_sha256", "A" * 64),
        ("policy_sha256", MISSING),
        ("policy_sha256", "a" * 63),
        ("classification_input_sha256", MISSING),
        ("classification_input_sha256", 42),
        ("decision_unit_ids", MISSING),
        ("decision_unit_ids", "DU-001"),
        ("decision_unit_ids", []),
        ("decision_unit_ids", ["DU-001", "DU-001"]),
        ("decision_unit_ids", ["DU-001", {}]),
        ("decision_unit_ids", ["DU-01"]),
        ("decision_unit_ids", ["DU-１２３"]),
        ("decision_unit_ids", ["DU-001\n"]),
    ],
)
def test_requires_valid_signed_evidence_version_fields(
    env: dict, api: dict, evidence: Json, keys: tuple[Path, Path], name: str, value: object
) -> None:
    if value is MISSING:
        del evidence[name]
    else:
        evidence[name] = value
    _stage_signed_evidence(api, evidence, keys[0])
    with pytest.raises(ValueError, match=name):
        verifier.verify(env, api.__getitem__)


def test_github_reader_uses_a_read_only_repository_scoped_request(monkeypatch) -> None:
    seen = []

    def gh(args, **kwargs):
        seen.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=b'{"number":71}')

    monkeypatch.setattr(subprocess, "run", gh)
    assert verifier.github_read(PR) == {"number": 71}
    assert seen == [
        ["gh", "api", "--hostname", "github.com", "--method", "GET", f"repos/{REPO}/{PR}"]
    ]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("GITHUB_REPOSITORY", "example/other"),
        ("GITHUB_REF", "refs/heads/other"),
        ("GITHUB_EVENT_NAME", "pull_request"),
        ("GITHUB_WORKFLOW_REF", f"{REPO}/{ORDINARY}@refs/heads/main"),
        ("GITHUB_WORKFLOW_SHA", HEAD),
        ("GITHUB_RUN_ID", "90"),
        ("GITHUB_RUN_ATTEMPT", "4"),
        ("ENGINE_SHA256", "d" * 64),
        ("VERIFIER_SHA256", "e" * 64),
        ("RECEIPT_PUBLIC_KEY", ""),
        ("RECEIPT_APP_ID", "15368"),
    ],
)
def test_rejects_changed_run_or_trust_configuration(env: dict, api: dict, key, value) -> None:
    env[key] = value
    with pytest.raises(ValueError):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize(
    ("path", "field", "value"),
    [
        (MAIN, "object.sha", SUBJECT),
        (PR, "state", "closed"),
        (PR, "head.repo.full_name", "example/fork"),
        (PR, "base.ref", "other"),
        (RUN, "run_attempt", 3),
        (RUN, "run_attempt", True),
        (RUN, "head_sha", SUBJECT),
        (RUN, "event", "workflow_dispatch"),
        (RUN, "pull_requests", []),
        (RUN, "workflow_id", 80),
        (WORKFLOW, "path", PROTECTED),
        (f"contents/{ORDINARY}?ref={HEAD}", "sha", SUBJECT),
        (f"compare/{BASE}...{SUBJECT}?per_page=1", "merge_base_commit.sha", HEAD),
        (f"compare/{SUBJECT}...{HEAD}?per_page=1", "merge_base_commit.sha", BASE),
        (CHECK, "name", "other/check"),
        (CHECK, "id", 98),
        (CHECK, "app.id", 92),
        (CHECK, "head_sha", SUBJECT),
        (CHECK, "status", "in_progress"),
        (CHECK, "conclusion", "failure"),
        (CHECK, "output.summary", "unsigned summary"),
        (EVIDENCE, "encoding", "utf-8"),
        (EVIDENCE, "content", "???"),
    ],
)
def test_rejects_mismatched_api_observation(env: dict, api: dict, path, field, value) -> None:
    target = api[path]
    parts = field.split(".")
    for key in parts[:-1]:
        target = target[key]
    target[parts[-1]] = value
    with pytest.raises(ValueError):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("schema_version", "3.2", "Invalid public final evidence"),
        ("task_id", "TASK-9998", "Invalid public final evidence"),
        ("phase", "pre_implementation_review", "Invalid public final evidence"),
        ("branch", "codex/other", "Invalid public final evidence"),
        ("repository_id", "cf3ff293-1db4-4fe9-914a-b645a6a24bb0", "Invalid public final evidence"),
        ("base_commit", SUBJECT, "Invalid public final evidence"),
        ("verification_level", "V1", "Invalid public final evidence"),
        ("mode", "ci", "Invalid public final evidence"),
        ("conclusion", "failed", "Invalid public final evidence"),
        ("verification_snapshot_sha256", "f" * 64, "Stale snapshot"),
        ("reproduce_command", ["different", "facts"], "Stale snapshot"),
    ],
)
def test_rejects_changed_public_evidence(
    env: dict, api: dict, evidence: Json, field, value, reason
) -> None:
    evidence[field] = value
    api[EVIDENCE] = _contents(evidence)
    with pytest.raises(ValueError, match=reason):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize(
    "invalid",
    [
        "missing implementation",
        "bad reference type",
        "missing checks",
        "failed check",
        "missing verifier",
        "survived mutation",
        "missing mutation digest",
    ],
)
def test_even_a_fresh_signature_requires_complete_final_evidence(
    env: dict, api: dict, evidence: Json, keys: tuple[Path, Path], invalid: str
) -> None:
    if invalid == "missing implementation":
        del evidence["review_refs"]["implementation"]
    elif invalid == "bad reference type":
        evidence["review_refs"]["implementation"] = ["REV-0002", "e" * 64]
    elif invalid == "missing checks":
        evidence["checks"] = []
    elif invalid == "failed check":
        evidence["checks"][0]["status"] = "failed"
    elif invalid == "missing verifier":
        del evidence["verifier_context_sha256"]
    elif invalid == "survived mutation":
        evidence["targeted_mutation"]["results"][0]["outcome"] = "survived"
    else:
        del evidence["targeted_mutation"]["mutation_evidence_sha256"]
    _stage_signed_evidence(api, evidence, keys[0])
    with pytest.raises(ValueError):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize("different", ["key", "namespace", "mutation", "snapshot"])
def test_rejects_other_authentic_signatures(
    env: dict, api: dict, evidence: Json, keys: tuple[Path, Path], different: str
) -> None:
    body = _signed_bytes(evidence["verification_snapshot_sha256"])
    if different == "mutation":
        body = body.replace(MUTATION.encode(), b"f" * 64)
    elif different == "snapshot":
        body = _signed_bytes("f" * 64)
    key = keys[1] if different == "key" else keys[0]
    namespace = "synthetic-other-domain" if different == "namespace" else DOMAIN
    api[CHECK]["output"]["summary"] = _sign(key, body, namespace)
    with pytest.raises(ValueError, match="signature rejected"):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize("path", [PR, RUN, MAIN, CHECK])
def test_rechecks_mutable_references_before_returning(env: dict, api: dict, path: str) -> None:
    reads = 0

    def read(request: str) -> Json:
        nonlocal reads
        if request == path:
            reads += 1
            if reads == 2:
                if path == PR:
                    api[PR]["head"]["sha"] = SUBJECT
                elif path == RUN:
                    api[RUN]["run_attempt"] += 1
                elif path == CHECK:
                    api[CHECK]["output"]["summary"] = "replaced"
                else:
                    api[MAIN]["object"]["sha"] = SUBJECT
        return api[request]

    with pytest.raises(ValueError, match="changed during verification"):
        verifier.verify(env, read)


def test_workflow_is_opt_in_read_only_and_executes_only_pinned_code() -> None:
    workflow = yaml.load((ROOT / PROTECTED).read_bytes(), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == dict.fromkeys(
        ("actions", "contents", "pull-requests", "checks"), "read"
    )
    (job,) = workflow["jobs"].values()
    assert "permissions" not in job
    assert job["environment"] == "private-replay-verification"
    assert set(job["if"].split(" && ")) == {
        f"github.repository == '{REPO}'",
        "github.ref == 'refs/heads/main'",
        "vars.PRIVATE_REPLAY_ENABLED == 'true'",
    }
    (step,) = job["steps"]
    assert "uses" not in step
    bootstrap = step["run"]
    assert "checkout" not in bootstrap and "${{" not in bootstrap
    assert step["env"]["TRUSTED_WORKFLOW_SHA"] == "${{ vars.PRIVATE_REPLAY_WORKFLOW_SHA }}"
    assert step["env"]["VERIFIER_SHA256"] == "${{ vars.PRIVATE_REPLAY_VERIFIER_SHA256 }}"
    assert (
        step["env"]["V2_APPROVAL_COMMITMENT"] == "${{ vars.PRIVATE_REPLAY_V2_APPROVAL_COMMITMENT }}"
    )
    required_order = [
        '"$GITHUB_WORKFLOW_SHA" == "$TRUSTED_WORKFLOW_SHA"',
        "contents/tools/ci/verify_private_replay_receipt.py?ref=$TRUSTED_WORKFLOW_SHA",
        "sha256sum --check --status",
        'python -I "$verifier"',
    ]
    positions = [bootstrap.index(part) for part in required_order]
    assert positions == sorted(positions)


V2 = "aiflow-private-v2-receipt-v2"
V3 = "aiflow-private-v2-receipt-v3"
MERGE = "5" * 40
CHECKS = (
    "contract scope ruff_check ruff_format_check smoke unit_tests regression_tests mypy "
    "coverage_xml diff_coverage acceptance integration targeted_mutation independent_verifier"
).split()
JOBS = "actions/runs/83/attempts/2/jobs?per_page=100"
PROTECTED_RUN = "actions/runs/89"
ORDINARY_CHECK = "check-runs/101"
POLICY = ".ai/policy/verification-levels.yaml"


def _git_contents(raw: bytes) -> Json:
    oid = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    return {"sha": oid, "encoding": "base64", "content": base64.encodebytes(raw).decode("ascii")}


def _attempt_steps() -> list[Json]:
    rows = [
        (1, "Set up job", "success"),
        (2, f"Replay request merge={MERGE} workflow={MERGE}", "success"),
        (3, "Run actions/checkout@v7", "success"),
        (4, "Run actions/setup-python@v7", "success"),
        (5, "Run astral-sh/setup-uv@v10.0.1", "success"),
        (6, "Install locked project environment", "success"),
        (7, "Resolve PR governance", "success"),
        (8, "Attach exact PR head branch", "success"),
        (9, "Read repository identity", "success"),
        (10, "Validate contracts", "success"),
        (11, "Validate retained task records", "skipped"),
        (12, "Verify and Gate", "failure"),
        (13, "Maintenance quality checks", "skipped"),
        (14, "Upload AI Flow diagnostics", "success"),
        (26, "Post Run astral-sh/setup-uv@v10.0.1", "skipped"),
        (27, "Post Run actions/setup-python@v7", "skipped"),
        (28, "Post Run actions/checkout@v7", "success"),
        (29, "Complete job", "success"),
    ]
    return [
        dict(number=n, name=name, status="completed", conclusion=result) for n, name, result in rows
    ]


@pytest.fixture
def synthetic_fields(api: dict, evidence: Json) -> Json:
    # Use synthetic bytes so a later checkout or a shallow clone does not alter the fixture.
    checkout = b"      - uses: actions/checkout@v7\n"
    before = b"jobs:\n  synthetic:\n    steps:\n" + checkout
    insertion = (
        b"      - name: Replay request merge=${{ github.sha }} "
        b"workflow=${{ github.workflow_sha }}\n"
        b"        run: ':'\n"
    )
    after = before.replace(checkout, insertion + checkout, 1)
    for ref, raw in [(BASE, before), (HEAD, after), (MERGE, after)]:
        api[f"contents/{ORDINARY}?ref={ref}"] = _git_contents(raw)
    api[f"contents/{POLICY}?ref={BASE}"] = {"sha": "ec1511b24896fe5c7c169ec4c397c07eaa406ca8"}
    for branch in ("base", "head"):
        api[PR][branch]["repo"]["id"] = 73
    for name in ("repository", "head_repository"):
        api[RUN][name]["id"] = 73
    api[RUN].update(
        name="ai-quality-gate",
        path=ORDINARY,
        status="completed",
        conclusion="failure",
        check_suite_id=103,
        referenced_workflows=[],
    )
    job = {
        "id": 101,
        "run_id": 83,
        "run_attempt": 2,
        "head_sha": HEAD,
        "name": "ai-quality-gate",
        "workflow_name": "ai-quality-gate",
        "status": "completed",
        "conclusion": "failure",
        "steps": _attempt_steps(),
        "check_run_url": f"https://api.github.com/repos/{REPO}/check-runs/101",
    }
    api[JOBS] = {"total_count": 1, "jobs": [job]}
    api[ORDINARY_CHECK] = {
        "id": 101,
        "name": "ai-quality-gate",
        "head_sha": HEAD,
        "status": "completed",
        "conclusion": "failure",
        "check_suite": {"id": 103},
        "app": {"id": 15368},
        "details_url": f"https://github.com/{REPO}/actions/runs/83/job/101",
    }
    api[f"git/commits/{MERGE}"] = {"sha": MERGE, "parents": [{"sha": BASE}, {"sha": HEAD}]}
    api[PROTECTED_RUN] = {
        "id": 89,
        "run_attempt": 3,
        "head_sha": BASE,
        "head_branch": "main",
        "event": "workflow_dispatch",
        "path": PROTECTED,
        "repository": {"full_name": REPO},
    }
    api[f"compare/{BASE}...{SUBJECT}?per_page=1"]["files"] = [
        {"filename": ORDINARY, "status": "modified"}
    ]
    api[f"compare/{SUBJECT}...{HEAD}?per_page=1"]["files"] = [
        {"filename": f".ai/tasks/{TASK}/approvals.json", "status": "modified"}
    ]
    evidence["checks"] = [dict(evidence["checks"][0], check_id=name) for name in CHECKS]
    evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
    api[EVIDENCE] = _contents(evidence)
    return {
        "repository": REPO,
        "github_repository_id": 73,
        "pr": 71,
        "task_id": TASK,
        "decision_unit_ids": evidence["decision_unit_ids"],
        "head_ref": BRANCH,
        "base": BASE,
        "subject": SUBJECT,
        "head": HEAD,
        "ordinary": {
            "workflow_path": ORDINARY,
            "workflow_id": 79,
            "event": "pull_request",
            "run_id": 83,
            "run_attempt": 2,
            "check_run_id": 101,
            "app_id": 15368,
            "conclusion": "failure",
            "merge_sha": MERGE,
            "merge_parents": [BASE, HEAD],
            "workflow_sha": MERGE,
            "base_workflow_blob": _git_contents(before)["sha"],
            "head_workflow_blob": _git_contents(after)["sha"],
            "executed_workflow_blob": _git_contents(after)["sha"],
        },
        "replay": {
            "round": "R2",
            "attestation": {
                "mode": "ci",
                "verification_level": "V2",
                "phase": "pre_implementation_review",
                "conclusion": "passed",
                "attestation_head": HEAD,
                "attestation_governance_only": True,
            },
            "checks_passed": list(CHECKS),
            "existing_mutations_killed": 5,
            "new_mutation_actions": 0,
            "pytest_passed": 37,
            "pytest_skipped": 2,
            "core_coverage": {
                "lines-covered": 97,
                "lines-valid": 100,
                "branches-covered": 19,
                "branches-valid": 20,
            },
            "no_mapped_core_diff": True,
            "maintenance_exit_codes": dict.fromkeys(
                [
                    "maintenance_coverage",
                    "whitespace",
                    "maintenance_lint",
                    "maintenance_format",
                    "maintenance_mypy",
                ],
                0,
            ),
            "gate": {
                "route": "REVIEW",
                "verification_level": "V2",
                "passed": True,
                "reason_codes": [],
                "exit_code": 0,
            },
        },
        "evidence": {
            "spec_sha256": evidence["spec_sha256"],
            "policy_sha256": evidence["policy_sha256"],
            "classification_input_sha256": evidence["classification_input_sha256"],
            "local_final_snapshot": evidence["verification_snapshot_sha256"],
            "mutation_evidence_sha256": MUTATION,
            **{
                name: hashlib.sha256(("synthetic/" + name).encode()).hexdigest()
                for name in ["redacted_receipt_sha256", "ci_sha256", "ci_snapshot", "gate_sha256"]
            },
        },
    }


@pytest.fixture
def v2_fields(synthetic_fields: Json, monkeypatch: pytest.MonkeyPatch) -> Json:
    ordinary = synthetic_fields["ordinary"]
    monkeypatch.setattr(verifier, "_BASE_WORKFLOW_BLOB", ordinary["base_workflow_blob"])
    monkeypatch.setattr(verifier, "_MARKED_WORKFLOW_BLOB", ordinary["head_workflow_blob"])
    return synthetic_fields


@pytest.fixture(params=[V2, V3], ids=["v2", "v3"])
def versioned_fields(request, v2_fields: Json) -> tuple[str, Json]:
    if request.param == V3:
        del v2_fields["replay"]["round"]
    return request.param, v2_fields


def _stage_receipt(
    env: dict,
    api: dict,
    body: str,
    key: Path,
    *,
    protocol: str = V2,
    namespace: str | None = None,
    commitment_domain: str | None = None,
) -> None:
    raw_digest = hashlib.sha256(body.encode("utf-8")).digest()
    env["V2_APPROVAL_COMMITMENT"] = hashlib.sha256(
        (commitment_domain or protocol).encode("ascii") + b"\0" + raw_digest
    ).hexdigest()
    key_blob = base64.b64decode(env["RECEIPT_PUBLIC_KEY"].split()[1])
    fingerprint = base64.b64encode(hashlib.sha256(key_blob).digest()).decode("ascii").rstrip("=")
    statement = {
        "protocol": protocol,
        "algorithm": "ssh-ed25519",
        "signer_fingerprint": f"SHA256:{fingerprint}",
        "protected_workflow_ref": PROTECTED_REF,
        "protected_workflow_sha": env["TRUSTED_WORKFLOW_SHA"],
        "verifier_sha256": VERIFIER,
        "engine_sha256": ENGINE,
        "protected_run": 89,
        "protected_attempt": 3,
        "app_id": 91,
        "staging_check_id": 97,
        "final_check_name": "private-v2-receipt/verified",
        "fixed_fields_sha256": raw_digest.hex(),
    }
    wire = json.dumps(statement, separators=(",", ":"), sort_keys=True).encode("ascii")
    api[CHECK]["output"] = {"summary": _sign(key, wire, namespace or protocol), "text": body}


def _document(fields: Json) -> str:
    return json.dumps(fields, indent=2) + "\n"


def test_accepts_independent_sshsig_on_versioned_fields(env, api, versioned_fields, keys) -> None:
    protocol, fields = versioned_fields
    _stage_receipt(env, api, _document(fields), keys[0], protocol=protocol)
    verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize(
    ("protocol", "round_value"),
    [(V2, MISSING), (V2, "R1"), (V2, None), (V3, "R2"), (V3, "R1"), (V3, None), (V3, 2)],
)
def test_round_shape_is_enforced_even_when_approved_and_signed(
    env, api, v2_fields, keys, protocol, round_value
) -> None:
    if round_value is MISSING:
        del v2_fields["replay"]["round"]
    else:
        v2_fields["replay"]["round"] = round_value
    _stage_receipt(env, api, _document(v2_fields), keys[0], protocol=protocol)
    with pytest.raises(ValueError, match="Fixed receipt fields differ"):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize("mismatch", ["commitment", "statement", "sshsig"])
def test_versioned_domains_must_agree(env, api, versioned_fields, keys, mismatch) -> None:
    protocol, fields = versioned_fields
    other = V3 if protocol == V2 else V2
    _stage_receipt(
        env,
        api,
        _document(fields),
        keys[0],
        protocol=other if mismatch == "statement" else protocol,
        namespace=other if mismatch == "sshsig" else protocol,
        commitment_domain=other if mismatch == "commitment" else protocol,
    )
    reason = "Fixed receipt fields differ" if mismatch == "commitment" else "signature rejected"
    with pytest.raises(ValueError, match=reason):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize("wrong_input", ["no delimiter", "hex digest", "unknown namespace"])
def test_rejects_other_commitment_preimages(env, api, v2_fields, keys, wrong_input) -> None:
    del v2_fields["replay"]["round"]
    body = _document(v2_fields)
    _stage_receipt(env, api, body, keys[0], protocol=V3)
    digest = hashlib.sha256(body.encode("utf-8"))
    preimage = {
        "no delimiter": V3.encode("ascii") + digest.digest(),
        "hex digest": V3.encode("ascii") + b"\0" + digest.hexdigest().encode("ascii"),
        "unknown namespace": b"synthetic-unknown\0" + digest.digest(),
    }[wrong_input]
    env["V2_APPROVAL_COMMITMENT"] = hashlib.sha256(preimage).hexdigest()
    with pytest.raises(ValueError, match="Unapproved or ambiguous fixed fields"):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize(
    ("field", "refresh_commitment", "reason"),
    [
        ("ci_sha256", False, "Unapproved or ambiguous fixed fields"),
        ("gate_sha256", True, "Receipt signature rejected"),
    ],
)
def test_v3_stale_approval_or_signature_rejects_changed_evidence_digest(
    env, api, v2_fields, keys, field, refresh_commitment, reason
) -> None:
    del v2_fields["replay"]["round"]
    _stage_receipt(env, api, _document(v2_fields), keys[0], protocol=V3)
    v2_fields["evidence"][field] = hashlib.sha256(b"changed synthetic evidence").hexdigest()
    changed = _document(v2_fields)
    api[CHECK]["output"]["text"] = changed
    if refresh_commitment:
        digest = hashlib.sha256(changed.encode("utf-8")).digest()
        env["V2_APPROVAL_COMMITMENT"] = hashlib.sha256(
            V3.encode("ascii") + b"\0" + digest
        ).hexdigest()
    with pytest.raises(ValueError, match=reason):
        verifier.verify(env, api.__getitem__)


def test_v2_production_pins_reject_synthetic_workflows(env, api, synthetic_fields, keys) -> None:
    # These two Git blob IDs were independently reviewed for the historical marker change.
    assert verifier._BASE_WORKFLOW_BLOB == "e8f71c6a189446b0ba8f5b61e22cbd8ea9b7c2d9"
    assert verifier._MARKED_WORKFLOW_BLOB == "5027a41d3fbc9b64e189b6d6c337636a4b5c4e37"
    _stage_receipt(env, api, _document(synthetic_fields), keys[0])
    with pytest.raises(ValueError, match="Unreviewed ordinary workflow"):
        verifier.verify(env, api.__getitem__)


def test_v2_rejects_optional_duplicate_of_required_local_final_check(
    env, api, evidence, v2_fields, keys
) -> None:
    evidence["checks"].append(dict(evidence["checks"][0], required=False))
    snapshot = verification_snapshot_sha256(evidence)
    evidence["verification_snapshot_sha256"] = snapshot
    api[EVIDENCE] = _contents(evidence)
    v2_fields["evidence"]["local_final_snapshot"] = snapshot
    _stage_receipt(env, api, _document(v2_fields), keys[0])
    with pytest.raises(ValueError, match="Duplicate final check ID"):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("ordinary", "conclusion", "success"),
        ("ordinary", "run_attempt", 1),
        ("ordinary", "merge_parents", [HEAD, BASE]),
        ("ordinary", "workflow_sha", HEAD),
        ("ordinary", "executed_workflow_blob", WORKFLOW_BLOB),
        ("replay", "checks_passed", CHECKS[:-1]),
        ("replay", "checks_passed", CHECKS[:-1] + [CHECKS[0]]),
        ("replay", "existing_mutations_killed", 4),
        ("replay", "new_mutation_actions", False),
        ("replay", "no_mapped_core_diff", False),
        ("attestation", "attestation_head", SUBJECT),
        ("gate", "exit_code", False),
        ("maintenance_exit_codes", "maintenance_lint", 1),
        ("core_coverage", "lines-covered", 10),
        ("evidence", "spec_sha256", "f" * 64),
        ("evidence", "ci_sha256", "z" * 64),
        ("evidence", "local_final_snapshot", "0" * 64),
    ],
)
def test_even_authorized_and_signed_versioned_fields_require_semantics(
    env, api, versioned_fields, keys, section, field, value
) -> None:
    protocol, fields = versioned_fields
    parent = fields if section in fields else fields["replay"]
    parent[section][field] = value
    _stage_receipt(env, api, _document(fields), keys[0], protocol=protocol)
    with pytest.raises(ValueError):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize(
    "case",
    [
        "missing pin",
        "wrong pin",
        "changed text",
        "changed signature",
        "runtime",
        "key",
        "v1 domain",
    ],
)
def test_v2_requires_independent_approval_and_authentic_sshsig(
    env, api, v2_fields, keys, case
) -> None:
    key = keys[1] if case == "key" else keys[0]
    _stage_receipt(
        env, api, _document(v2_fields), key, namespace=DOMAIN if case == "v1 domain" else V2
    )
    if case == "missing pin":
        del env["V2_APPROVAL_COMMITMENT"]
    elif case == "wrong pin":
        env["V2_APPROVAL_COMMITMENT"] = "a" * 64
    elif case == "changed text":
        api[CHECK]["output"]["text"] = _document(
            dict(v2_fields, replay=dict(v2_fields["replay"], pytest_passed=38))
        )
    elif case == "changed signature":
        armor = api[CHECK]["output"]["summary"].splitlines()
        raw = bytearray(base64.b64decode("".join(armor[1:-1])))
        raw[-1] ^= 1
        api[CHECK]["output"]["summary"] = "\n".join(
            [armor[0], base64.encodebytes(raw).decode("ascii").rstrip(), armor[-1], ""]
        )
    elif case == "runtime":
        env["ENGINE_SHA256"] = "d" * 64
    with pytest.raises(ValueError):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize("raw_edit", ["unknown field", "duplicate key", "no final LF"])
def test_v2_rejects_approved_malformed_documents(env, api, v2_fields, keys, raw_edit) -> None:
    body = _document(v2_fields)
    if raw_edit == "unknown field":
        body = _document(dict(v2_fields, extra="unapproved shape"))
    elif raw_edit == "duplicate key":
        body = body.replace('"pr": 71', '"pr": 71, "pr": 71')
    else:
        body = body.rstrip("\n")
    _stage_receipt(env, api, body, keys[0])
    with pytest.raises(ValueError):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize(
    "drift", ["protected attempt", "ordinary attempt", "staging text", "PR head"]
)
def test_versioned_rechecks_after_signature_verification(
    env, api, versioned_fields, keys, drift
) -> None:
    protocol, fields = versioned_fields
    _stage_receipt(env, api, _document(fields), keys[0], protocol=protocol)
    target = {
        "protected attempt": PROTECTED_RUN,
        "ordinary attempt": RUN,
        "staging text": CHECK,
        "PR head": PR,
    }[drift]
    observations = 0

    def read(path: str) -> Json:
        nonlocal observations
        if path == target:
            observations += 1
            if observations == 2:
                if target == CHECK:
                    api[target]["output"]["text"] += "\n"
                elif target == PR:
                    api[target]["head"]["sha"] = SUBJECT
                else:
                    api[target]["run_attempt"] += 1
        return api[path]

    with pytest.raises(ValueError):
        verifier.verify(env, read)
    assert observations == 2


@pytest.mark.parametrize(
    ("path", "fields", "value"),
    [
        (JOBS, ("total_count",), 2),
        (JOBS, ("jobs", 0, "steps", 2, "conclusion"), "skipped"),
        (JOBS, ("jobs", 0, "steps", 1, "name"), f"Replay request merge={MERGE} workflow={HEAD}"),
        (RUN, ("referenced_workflows",), [{"path": "other/workflow.yml", "sha": BASE}]),
        (ORDINARY_CHECK, ("check_suite", "id"), 111),
        (ORDINARY_CHECK, ("app", "id"), 92),
        (CHECK, ("app", "id"), 92),
        (f"git/commits/{MERGE}", ("parents",), [{"sha": HEAD}, {"sha": BASE}]),
        (f"contents/{ORDINARY}?ref={HEAD}", ("content",), base64.b64encode(b"unreviewed").decode()),
        (
            f"compare/{BASE}...{SUBJECT}?per_page=1",
            ("files",),
            [
                {"filename": ORDINARY, "status": "modified"},
                {"filename": "src/aiflow/gate.py", "status": "modified"},
            ],
        ),
        (
            f"compare/{SUBJECT}...{HEAD}?per_page=1",
            ("files",),
            [
                {"filename": "src/aiflow/gate.py", "status": "modified"},
            ],
        ),
    ],
)
def test_v2_binds_signed_results_to_independent_github_facts(
    env, api, v2_fields, keys, path, fields, value
) -> None:
    _stage_receipt(env, api, _document(v2_fields), keys[0])
    target = api[path]
    for field in fields[:-1]:
        target = target[field]
    target[fields[-1]] = value
    with pytest.raises(ValueError):
        verifier.verify(env, api.__getitem__)


@pytest.mark.parametrize(
    ("refresh_local_final", "reason"),
    [(False, "Invalid public final evidence"), (True, "Fixed receipt fields differ")],
)
def test_rejects_old_versioned_fields_on_consistent_new_protected_main(
    env, api, evidence, versioned_fields, keys, refresh_local_final, reason
) -> None:
    # A real main advance changes every live main pointer, not just the launch environment.
    new_base, new_merge = "6" * 40, "7" * 40
    for name in ("TRUSTED_WORKFLOW_SHA", "GITHUB_SHA", "GITHUB_WORKFLOW_SHA"):
        env[name] = new_base
    api[MAIN]["object"]["sha"] = new_base
    api[PR]["base"]["sha"] = new_base
    new_run_id = 84
    env["ORDINARY_RUN_ID"] = str(new_run_id)
    new_run = dict(api[RUN], id=new_run_id, check_suite_id=104)
    new_run["pull_requests"] = [{"number": 71, "base": {"sha": new_base}, "head": {"sha": HEAD}}]
    api[f"actions/runs/{new_run_id}"] = new_run
    job = dict(
        api[JOBS]["jobs"][0],
        id=102,
        run_id=new_run_id,
        steps=_attempt_steps(),
        check_run_url=f"https://api.github.com/repos/{REPO}/check-runs/102",
    )
    job["steps"][1]["name"] = f"Replay request merge={new_merge} workflow={new_merge}"
    api[f"actions/runs/{new_run_id}/attempts/2/jobs?per_page=100"] = {
        "total_count": 1,
        "jobs": [job],
    }
    api["check-runs/102"] = dict(
        api[ORDINARY_CHECK],
        id=102,
        check_suite={"id": 104},
        details_url=f"https://github.com/{REPO}/actions/runs/{new_run_id}/job/102",
    )
    api[PROTECTED_RUN]["head_sha"] = new_base
    api[f"git/commits/{new_merge}"] = {
        "sha": new_merge,
        "parents": [{"sha": new_base}, {"sha": HEAD}],
    }
    api[f"contents/{ORDINARY}?ref={new_merge}"] = api[f"contents/{ORDINARY}?ref={MERGE}"]
    for path in (ORDINARY, POLICY):
        api[f"contents/{path}?ref={new_base}"] = api[f"contents/{path}?ref={BASE}"]
    old_compare = api[f"compare/{BASE}...{SUBJECT}?per_page=1"]
    api[f"compare/{new_base}...{SUBJECT}?per_page=1"] = {
        **old_compare,
        "merge_base_commit": {"sha": new_base},
    }
    if refresh_local_final:
        evidence["base_commit"] = new_base
        evidence["verification_snapshot_sha256"] = verification_snapshot_sha256(evidence)
        api[EVIDENCE] = _contents(evidence)
    protocol, fields = versioned_fields
    _stage_receipt(env, api, _document(fields), keys[0], protocol=protocol)
    with pytest.raises(ValueError, match=reason):
        verifier.verify(env, api.__getitem__)


def test_v2_pin_disallows_v1_fallback_even_for_valid_v1_signature(env, api) -> None:
    env["V2_APPROVAL_COMMITMENT"] = "d" * 64
    with pytest.raises(ValueError):
        verifier.verify(env, api.__getitem__)
