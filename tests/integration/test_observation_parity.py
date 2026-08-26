from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from test_begin_close_commands import commit_all, create_repository, make_ready, start

from aiflow.cli import main as cli_main
from aiflow.observation import parse_observation
from aiflow.observation_decision import (
    DecisionRoute,
    VerificationLevel,
    decide_observation,
)
from aiflow.policy import load_policy_bundle
from aiflow.task_service import load_task_record
from tools.hooks import pre_command, pre_commit

TASK_ID = "TASK-0001"
SOURCES = ("hook_pre_commit", "hook_pre_command", "cli", "ci")
HIGH_RISK_ACTIONS = (
    "push",
    "merge",
    "deploy",
    "delete",
    "secret_export",
    "paid_external_call",
)
SUMMARIES: dict[str, dict[str, object]] = {
    "scope_out_of_bounds": {"paths": ["outside/file.py"]},
    "policy_changed": {"paths": [".ai/policy/routing.yaml"]},
    "controlled_file_changed": {"paths": [".github/workflows/gate.yml"]},
    "high_risk_command": {"action": "push", "target_ref": "origin/main"},
    "evidence_missing": {"artifact": "evidence", "reason_code": "stale"},
}


def _decision_semantics(decision: dict[str, object]) -> tuple[object, ...]:
    return (
        decision["schema_version"],
        decision["disposition"],
        decision["reason_code"],
        decision["current_route"],
        decision["current_verification_level"],
        decision["execution_allowed"],
        tuple(decision["required_conditions"]),
        decision.get("target_route"),
    )


def _tree_digest(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        digest.update(path.relative_to(directory).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _ready_repository(
    path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    route: str = "REVIEW",
) -> Path:
    repository = create_repository(path)
    start(repository, monkeypatch)
    make_ready(repository, route=route, valid_approval=route == "REVIEW")
    if route != "BLOCK":
        assert cli_main(["begin", TASK_ID, "--actor", "implementer"]) == 0
    return repository


def _payload(
    repository: Path,
    *,
    source: str,
    kind: str,
    summary: dict[str, object],
) -> dict[str, object]:
    task = load_task_record(repository, TASK_ID).task
    return {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "base_commit": task["base_commit"],
        "subject_commit": task["subject_commit"],
        "policy_sha256": load_policy_bundle(repository).sha256,
        "source": source,
        "kind": kind,
        "summary": summary,
    }


def _write_payload(repository: Path, name: str, payload: dict[str, object]) -> Path:
    path = repository / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _run_observe(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    mode: str,
    payload: dict[str, object],
    name: str,
) -> dict[str, object]:
    monkeypatch.chdir(repository)
    path = _write_payload(repository, name, payload)
    argv = ["observe", TASK_ID, "--input", str(path), "--mode", mode]
    if mode == "apply":
        argv.extend(["--actor", "cli-observer"])
    assert cli_main(argv) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    result = json.loads(captured.out)
    assert result["mode"] == mode
    assert result["decision"]["execution_allowed"] is False
    return result


def _latest_observation_decision(repository: Path) -> dict[str, object]:
    events = [
        event
        for event in load_task_record(repository, TASK_ID).events
        if event["event_type"] in {"observation_recorded", "observation_refused"}
    ]
    assert len(events) == 1
    payload = events[0]["payload"]
    assert isinstance(payload, dict)
    decision = payload["decision"]
    assert isinstance(decision, dict)
    return decision


@pytest.mark.parametrize("kind", sorted(SUMMARIES))
@pytest.mark.parametrize("route", list(DecisionRoute))
@pytest.mark.parametrize("level", list(VerificationLevel))
def test_all_sources_have_source_sensitive_identity_but_identical_non_authorizing_semantics(
    kind: str,
    route: DecisionRoute,
    level: VerificationLevel,
) -> None:
    decisions = []
    for source in SOURCES:
        observation = parse_observation(
            {
                "schema_version": "1.0",
                "task_id": TASK_ID,
                "base_commit": "a" * 40,
                "subject_commit": "b" * 40,
                "policy_sha256": "c" * 64,
                "source": source,
                "kind": kind,
                "summary": SUMMARIES[kind],
            }
        )
        decision = decide_observation(observation, route, level)
        decisions.append(
            {
                "schema_version": decision.schema_version,
                "observation_sha256": decision.observation_sha256,
                "disposition": decision.disposition.value,
                "reason_code": decision.reason_code.value,
                "current_route": decision.current_route.value,
                "current_verification_level": decision.current_verification_level.value,
                "execution_allowed": decision.execution_allowed,
                "required_conditions": [item.value for item in decision.required_conditions],
                **(
                    {"target_route": decision.target_route.value}
                    if decision.target_route is not None
                    else {}
                ),
            }
        )

    assert len({_decision_semantics(item) for item in decisions}) == 1
    assert len({item["observation_sha256"] for item in decisions}) == len(SOURCES)
    assert all(item["execution_allowed"] is False for item in decisions)
    for item in decisions:
        target = item.get("target_route")
        if target is not None:
            assert list(DecisionRoute).index(DecisionRoute(target)) >= list(DecisionRoute).index(
                route
            )


def test_pre_commit_cli_and_ci_scope_parity_with_read_only_zero_write_and_apply_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    hook_repository = _ready_repository(tmp_path / "hook", monkeypatch)
    capsys.readouterr()
    outside = hook_repository / "outside" / "file.py"
    outside.parent.mkdir(parents=True)
    outside.write_text("outside\n", encoding="utf-8")
    monkeypatch.chdir(hook_repository)

    assert pre_commit.main(["--task", TASK_ID]) == 2
    hook_output = capsys.readouterr()
    assert hook_output.out == ""
    assert hook_output.err.startswith("pre-commit denied:")
    hook_decision = _latest_observation_decision(hook_repository)

    adapter_repository = _ready_repository(tmp_path / "adapter", monkeypatch)
    capsys.readouterr()
    task_directory = adapter_repository / ".ai" / "tasks" / TASK_ID
    before = _tree_digest(task_directory)
    summary = {"paths": ["outside/file.py"]}

    dry_run = _run_observe(
        adapter_repository,
        monkeypatch,
        capsys,
        mode="dry-run",
        payload=_payload(
            adapter_repository,
            source="cli",
            kind="scope_out_of_bounds",
            summary=summary,
        ),
        name="scope-dry-run.json",
    )
    ci = _run_observe(
        adapter_repository,
        monkeypatch,
        capsys,
        mode="ci",
        payload=_payload(
            adapter_repository,
            source="ci",
            kind="scope_out_of_bounds",
            summary=summary,
        ),
        name="scope-ci.json",
    )
    assert _tree_digest(task_directory) == before

    apply = _run_observe(
        adapter_repository,
        monkeypatch,
        capsys,
        mode="apply",
        payload=_payload(
            adapter_repository,
            source="cli",
            kind="scope_out_of_bounds",
            summary=summary,
        ),
        name="scope-apply.json",
    )
    replay = _run_observe(
        adapter_repository,
        monkeypatch,
        capsys,
        mode="apply",
        payload=_payload(
            adapter_repository,
            source="cli",
            kind="scope_out_of_bounds",
            summary=summary,
        ),
        name="scope-apply.json",
    )

    decisions = [hook_decision, dry_run["decision"], ci["decision"], apply["decision"]]
    assert len({_decision_semantics(item) for item in decisions}) == 1
    assert len({item["observation_sha256"] for item in decisions}) == 3
    assert apply["audit_event"] == replay["audit_event"]
    assert apply["escalation_event"] == replay["escalation_event"] is None
    observation_events = [
        event
        for event in load_task_record(adapter_repository, TASK_ID).events
        if event["event_type"] == "observation_refused"
    ]
    assert len(observation_events) == 1


@pytest.mark.parametrize("action", HIGH_RISK_ACTIONS)
def test_pre_command_cli_and_ci_high_risk_parity_for_all_policy_denied_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    action: str,
) -> None:
    hook_repository = _ready_repository(tmp_path / f"hook-{action}", monkeypatch)
    capsys.readouterr()
    monkeypatch.chdir(hook_repository)

    assert pre_command.main(["--action", action, "--target", "origin/main", "--task", TASK_ID]) == 2
    hook_output = capsys.readouterr()
    assert hook_output.out == ""
    assert hook_output.err.startswith("pre-command denied:")
    hook_decision = _latest_observation_decision(hook_repository)

    adapter_repository = _ready_repository(tmp_path / f"adapter-{action}", monkeypatch)
    capsys.readouterr()
    task_directory = adapter_repository / ".ai" / "tasks" / TASK_ID
    before = _tree_digest(task_directory)
    summary = {"action": action, "target_ref": "origin/main"}

    dry_run = _run_observe(
        adapter_repository,
        monkeypatch,
        capsys,
        mode="dry-run",
        payload=_payload(
            adapter_repository,
            source="cli",
            kind="high_risk_command",
            summary=summary,
        ),
        name=f"{action}-dry-run.json",
    )
    ci = _run_observe(
        adapter_repository,
        monkeypatch,
        capsys,
        mode="ci",
        payload=_payload(
            adapter_repository,
            source="ci",
            kind="high_risk_command",
            summary=summary,
        ),
        name=f"{action}-ci.json",
    )
    assert _tree_digest(task_directory) == before
    apply = _run_observe(
        adapter_repository,
        monkeypatch,
        capsys,
        mode="apply",
        payload=_payload(
            adapter_repository,
            source="cli",
            kind="high_risk_command",
            summary=summary,
        ),
        name=f"{action}-apply.json",
    )

    decisions = [hook_decision, dry_run["decision"], ci["decision"], apply["decision"]]
    assert len({_decision_semantics(item) for item in decisions}) == 1
    assert len({item["observation_sha256"] for item in decisions}) == 3
    assert all(item["disposition"] == "refuse" for item in decisions)
    assert all(item["reason_code"] == "action_approval_required" for item in decisions)


def test_in_scope_pre_commit_allows_without_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _ready_repository(tmp_path / "repository", monkeypatch)
    capsys.readouterr()
    source = repository / "src" / "inside.py"
    source.parent.mkdir()
    source.write_text("inside\n", encoding="utf-8")
    monkeypatch.chdir(repository)

    assert pre_commit.main(["--task", TASK_ID]) == 0
    captured = capsys.readouterr()
    assert captured.out == "pre-commit allowed\n"
    assert captured.err == ""
    assert not any(
        event["event_type"] in {"observation_recorded", "observation_refused"}
        for event in load_task_record(repository, TASK_ID).events
    )


@pytest.mark.parametrize("mode,source,actor", [("dry-run", "cli", None), ("ci", "ci", None)])
def test_read_only_mode_binding_drift_fails_without_task_write_or_payload_echo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str,
    source: str,
    actor: str | None,
) -> None:
    repository = _ready_repository(tmp_path / mode, monkeypatch)
    capsys.readouterr()
    payload = _payload(
        repository,
        source=source,
        kind="scope_out_of_bounds",
        summary={"paths": ["outside/SECRET_VALUE.py"]},
    )
    task_directory = repository / ".ai" / "tasks" / TASK_ID
    before = _tree_digest(task_directory)
    (repository / "tracked.txt").write_text("changed\n", encoding="utf-8")
    commit_all(repository, "advance head")
    monkeypatch.chdir(repository)
    path = _write_payload(repository, f"{mode}.json", payload)
    argv = ["observe", TASK_ID, "--input", str(path), "--mode", mode]
    if actor is not None:
        argv.extend(["--actor", actor])

    assert cli_main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "SECRET_VALUE" not in captured.err
    assert _tree_digest(task_directory) == before
