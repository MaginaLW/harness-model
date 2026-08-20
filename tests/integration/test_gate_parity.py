from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aiflow import cli
from aiflow.gate import GateFacts, evaluate_gate_facts
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
    monkeypatch.chdir(tmp_path)

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
