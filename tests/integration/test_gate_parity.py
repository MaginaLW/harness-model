from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from test_approve_command import _record_review, review_package
from test_gate_command import _prepare_gate
from test_start_command import create_repository
from test_status_command import _approve_current_review_implementation, _prepare_native_v2

from aiflow import approval as approval_service
from aiflow import cli, verification_service
from aiflow import gate as gate_service
from aiflow.gate import GateFacts, evaluate_gate, evaluate_gate_facts
from aiflow.mutation_evidence import TargetedMutationFacts
from aiflow.status_service import summarize_task
from aiflow.storage import atomic_write_json, read_task_json, resolve_task_path
from tools.ci import resolve_task

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "tests" / "fixtures" / "parity" / "decision-table.json"


def _rows() -> list[dict[str, object]]:
    value = json.loads(TABLE.read_text(encoding="utf-8"))
    assert isinstance(value, list)
    return value


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "row", [row for row in _rows() if "facts" in row], ids=lambda row: str(row["id"])
)
def test_package_local_and_ci_gate_have_identical_machine_decisions(
    row: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    before = _digest(TABLE)
    facts = row["facts"]
    assert isinstance(facts, dict)
    package = evaluate_gate_facts(GateFacts(**facts))  # type: ignore[arg-type]
    monkeypatch.setattr(cli, "evaluate_gate", lambda *args, **kwargs: package)
    repository = create_repository(tmp_path / "repository")
    monkeypatch.chdir(repository)

    local_exit = cli.main(["gate", "TASK-0001", "--format", "json"])
    local = json.loads(capsys.readouterr().out)
    evidence = tmp_path / "ci-evidence.json"
    evidence.write_text("{}\n", encoding="utf-8")
    ci_exit = cli.main(["gate", "TASK-0001", "--evidence", str(evidence), "--format", "json"])
    ci = json.loads(capsys.readouterr().out)

    assert package.passed is row["passed"]
    assert list(package.reason_codes) == row["reasons"]
    assert local == package.to_dict() == ci
    assert local_exit == ci_exit == (0 if package.passed else 2)
    assert _digest(TABLE) == before


def test_ambiguous_task_fixture_fails_without_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    row = next(item for item in _rows() if item["id"] == "ambiguous-task")
    paths = row["resolver_candidates"]
    assert isinstance(paths, list)
    identity = tmp_path / ".ai" / "repository-id"
    identity.parent.mkdir(parents=True)
    identity.write_text("shared-repository\n", encoding="utf-8")
    before = _digest(identity)
    monkeypatch.setattr(resolve_task, "_git_paths", lambda root, base, head: tuple(paths))

    with pytest.raises(ValueError, match=str(row["resolver_error"])):
        resolve_task.resolve_task_id(tmp_path, "a" * 40, "b" * 40)

    assert _digest(identity) == before


def test_repository_identity_is_checkout_path_independent(tmp_path: Path) -> None:
    roots = (tmp_path / "one", tmp_path / "two")
    for root in roots:
        (root / ".ai" / "tasks" / "TASK-0001").mkdir(parents=True)
        (root / ".ai" / "repository-id").write_text("shared-repository\n", encoding="utf-8")

    resolved = [
        resolve_task.resolve_task_id(root, "a" * 40, "b" * 40, "TASK-0001") for root in roots
    ]
    assert resolved == ["TASK-0001", "TASK-0001"]
    assert roots[0].resolve() != roots[1].resolve()


def test_status_merge_readiness_matches_evaluate_gate_across_drift_and_native_v2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def assert_parity(repository: Path, *, expected: bool) -> None:
        summary = summarize_task(repository, "TASK-0001")
        decision = evaluate_gate(repository, "TASK-0001")
        assert (summary.merge_readiness == "gate_required") is decision.passed is expected

    review_repo = _prepare_gate(tmp_path / "review", monkeypatch, review=True)
    _approve_current_review_implementation(review_repo, tmp_path / "review")
    assert_parity(review_repo, expected=True)

    dirty_path = review_repo / "outside.txt"
    dirty_path.write_text("out-of-scope\n", encoding="utf-8")
    assert_parity(review_repo, expected=False)
    dirty_path.unlink()
    assert_parity(review_repo, expected=True)

    classification_path = resolve_task_path(review_repo, "TASK-0001", "classification.json")
    classification = read_task_json(review_repo, "TASK-0001", "classification.json")
    assert isinstance(classification, dict)
    classification["effective_route"] = "BLOCK"
    classification["classifications"][0]["route"] = "BLOCK"
    atomic_write_json(classification_path, classification)
    assert_parity(review_repo, expected=False)

    v2_tmp = tmp_path / "v2"
    v2_tmp.mkdir()
    v2_repo = _prepare_native_v2(v2_tmp, monkeypatch)
    resolve_task_path(v2_repo, "TASK-0001", "review-package.md").write_text(
        review_package(), encoding="utf-8"
    )
    _record_review(v2_repo, v2_tmp, stage="implementation", review_id="REV-1002")
    verification_service.verify_task(v2_repo, "TASK-0001", actor="verifier", finalize=True)
    final_evidence = read_task_json(v2_repo, "TASK-0001", "evidence.json")
    assert isinstance(final_evidence, dict)
    mutation = final_evidence["targeted_mutation"]
    assert isinstance(mutation, dict)
    passing_facts = TargetedMutationFacts(
        True,
        None,
        str(mutation["evidence_ref"]),
        str(mutation["mutation_evidence_sha256"]),
        str(mutation["manifest_ref"]),
        tuple(mutation["results"]),
    )
    monkeypatch.setattr(
        approval_service, "consume_targeted_mutation_evidence", lambda *_args: passing_facts
    )
    monkeypatch.setattr(
        gate_service, "consume_targeted_mutation_evidence", lambda *_args: passing_facts
    )
    assert (
        cli.main(
            [
                "approve",
                "TASK-0001",
                "--type",
                "code",
                "--actor",
                "reviewer",
                "--reason",
                "V2 parity check",
            ]
        )
        == 0
    )
    assert_parity(v2_repo, expected=True)

    failed_facts = TargetedMutationFacts(
        False,
        "MUTATION_NOT_KILLED",
        str(mutation["evidence_ref"]),
        str(mutation["mutation_evidence_sha256"]),
        str(mutation["manifest_ref"]),
        tuple(mutation["results"]),
    )
    monkeypatch.setattr(
        gate_service, "consume_targeted_mutation_evidence", lambda *_args: failed_facts
    )
    assert_parity(v2_repo, expected=False)

    monkeypatch.setattr(
        gate_service, "consume_targeted_mutation_evidence", lambda *_args: passing_facts
    )
    tampered = dict(final_evidence)
    tampered["generated_at"] = "2026-08-24T00:00:00Z"
    atomic_write_json(resolve_task_path(v2_repo, "TASK-0001", "evidence.json"), tampered)
    assert_parity(v2_repo, expected=False)
