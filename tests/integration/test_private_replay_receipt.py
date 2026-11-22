from __future__ import annotations

import base64
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


def _sign(key: Path, body: bytes, namespace: str = DOMAIN) -> str:
    result = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", namespace],
        input=body,
        check=True,
        capture_output=True,
        timeout=10,
    )
    return result.stdout.decode("ascii")


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
    required_order = [
        '"$GITHUB_WORKFLOW_SHA" == "$TRUSTED_WORKFLOW_SHA"',
        "contents/tools/ci/verify_private_replay_receipt.py?ref=$TRUSTED_WORKFLOW_SHA",
        "sha256sum --check --status",
        'python -I "$verifier"',
    ]
    positions = [bootstrap.index(part) for part in required_order]
    assert positions == sorted(positions)
