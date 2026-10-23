"""Exercise explicit draft risk facts through the real in-process CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_begin_close_commands import create_repository, run_git

from aiflow.cli import main
from aiflow.storage import atomic_write_yaml, read_task_json, resolve_task_path
from aiflow.task_service import load_task_record, transition_task_record

FACTS: dict[str, Any] = {
    "scope": {"clear": True},
    "impact": {"level": "low"},
    "protections": {"verified_backup": True, "dry_run": True},
    "verification": {"automatic": True, "tools_missing": False},
    "impact_categories": [],
    "controlled_actions": [],
    "business_direction_count": 1,
    "change_characteristics": {
        "mechanical": True,
        "behavior_changed": False,
        "code_modified": False,
        "interaction_scope": "local",
        "regression_risk": False,
        "error_detectability": "high",
    },
    "verification_requirements": {
        "acceptance_required": False,
        "integration_required": False,
        "targeted_mutation_required": False,
        "independent_verifier_required": False,
    },
    "reversibility": "reversible",
    "external_side_effects": [],
    "permission_requirements": [],
}


@pytest.fixture
def draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> tuple[Path, Path]:
    repository = create_repository(tmp_path / "repository")
    monkeypatch.chdir(repository)
    assert main(["start", "--objective", "bounded", "--allow", "src/module.py"]) == 0
    source = repository / "facts.json"
    source.write_text(json.dumps(FACTS), encoding="utf-8")
    capsys.readouterr()
    return repository, source


def _task(repository: Path) -> dict[str, Any]:
    path = resolve_task_path(repository, "TASK-0001", "task.yaml")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _save(repository: Path, task: dict[str, Any]) -> None:
    atomic_write_yaml(resolve_task_path(repository, "TASK-0001", "task.yaml"), task)


def _artifacts(repository: Path) -> dict[str, bytes]:
    directory = resolve_task_path(repository, "TASK-0001")
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def _facts(
    source: Path | str, *, unit: str = "DU-001", actor: str = "declarer", preview: bool = False
) -> int:
    arguments = [
        "facts",
        "TASK-0001",
        "--decision-unit",
        unit,
        "--input",
        str(source),
        "--actor",
        actor,
    ]
    if preview:
        arguments.append("--dry-run")
    return main(arguments)


def _report(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    captured = capsys.readouterr()
    assert not captured.err
    value = json.loads(captured.out)
    assert isinstance(value, dict)
    return value


def test_facts_changes_only_selected_unit_and_records_present_projections(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    repository, source = draft
    original = _task(repository)
    second = deepcopy(original["decision_units"][0])
    second["decision_unit_id"] = "DU-002"
    second["goal"] = "independent unit"
    original["decision_units"].append(second)
    _save(repository, original)

    assert _facts(source, unit="DU-002") == 0
    report = _report(capsys)
    before = {
        "reversibility": "reversible",
        "external_side_effects": [],
        "permission_requirements": [],
    }
    assert report == {
        "task_id": "TASK-0001",
        "decision_unit_id": "DU-002",
        "dry_run": False,
        "changed": True,
        "applied": True,
        "recovered": False,
        "before": before,
        "after": FACTS,
    }
    current = _task(repository)
    assert current["decision_units"][0] == original["decision_units"][0]
    expected_second = {**second, **FACTS}
    assert current["decision_units"][1] == expected_second
    assert {k: v for k, v in current.items() if k not in {"decision_units", "updated_at"}} == {
        k: v for k, v in original.items() if k not in {"decision_units", "updated_at"}
    }
    record = load_task_record(repository, "TASK-0001")
    assert len(record.events) == 2
    event = record.events[-1]
    assert event["event_type"] == "risk_facts_recorded"
    assert event["from_state"] == event["to_state"] == "NEW"
    assert event["actor"] == "declarer"
    assert event["payload"]["decision_unit_id"] == "DU-002"
    assert event["payload"]["before"] == before
    assert event["payload"]["after"] == FACTS
    assert current["updated_at"] == event["occurred_at"]
    assert not resolve_task_path(repository, "TASK-0001", "classification.json").exists()
    assert not resolve_task_path(repository, "TASK-0001", "task.yaml.next").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scope", {"clear": False}),
        ("impact", {"level": "high"}),
        ("protections", {"verified_backup": False, "dry_run": False}),
        ("verification", {"automatic": False, "tools_missing": True}),
        ("impact_categories", ["ci"]),
        ("controlled_actions", ["deploy"]),
        ("business_direction_count", 2),
        (
            "change_characteristics",
            {**FACTS["change_characteristics"], "interaction_scope": "cross_module"},
        ),
        ("verification_requirements", {key: True for key in FACTS["verification_requirements"]}),
        ("reversibility", "conditionally_reversible"),
        ("external_side_effects", ["credential_export"]),
        ("permission_requirements", ["spec_approval"]),
    ],
)
def test_every_declared_risk_field_accepts_typed_replacement(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], field: str, value: object
) -> None:
    repository, source = draft
    source.write_text(json.dumps({field: value}), encoding="utf-8")
    assert _facts(source) == 0
    report = _report(capsys)
    assert report["after"][field] == value
    assert _task(repository)["decision_units"][0][field] == value


@pytest.mark.parametrize("preview", [False, True])
def test_omitted_facts_stay_missing_and_classification_still_requires_assessment(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], preview: bool
) -> None:
    repository, source = draft
    source.write_text('{"scope":{"clear":true}}', encoding="utf-8")
    before = _artifacts(repository)
    assert _facts(source, preview=preview) == 0
    report = _report(capsys)
    for field in ("impact_categories", "controlled_actions", "impact", "verification"):
        assert field not in report["after"]
        assert field not in _task(repository)["decision_units"][0]
    if preview:
        assert _artifacts(repository) == before
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 1
    error = capsys.readouterr().err
    assert "impact_categories" in error and "controlled_actions" in error


@pytest.mark.parametrize("changed", [False, True])
def test_preview_and_ordinary_noop_preserve_every_task_artifact(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], changed: bool
) -> None:
    repository, source = draft
    if not changed:
        source.write_text('{"reversibility":"reversible"}', encoding="utf-8")
    before = _artifacts(repository)
    assert _facts(source, preview=True) == 0
    report = _report(capsys)
    assert report["dry_run"] is True and report["changed"] is changed
    assert report["applied"] is report["recovered"] is False
    assert _artifacts(repository) == before
    assert _facts(source) == 0
    _report(capsys)
    applied = _artifacts(repository)
    assert _facts(source) == 0
    report = _report(capsys)
    assert report["before"] == report["after"]
    assert report["changed"] is report["applied"] is report["recovered"] is False
    assert _artifacts(repository) == applied


@pytest.mark.parametrize("subdirectory", [False, True])
def test_explicit_input_path_uses_invocation_directory(
    draft: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    subdirectory: bool,
) -> None:
    repository, source = draft
    if subdirectory:
        directory = repository / "nested"
        directory.mkdir()
        source.write_text("not the selected input", encoding="utf-8")
        source = directory / "facts.json"
        source.write_text('{"impact":{"level":"medium"}}', encoding="utf-8")
        monkeypatch.chdir(directory)
    assert _facts(source.name) == 0
    report = _report(capsys)
    assert report["after"]["impact"]["level"] == ("medium" if subdirectory else "low")


@pytest.mark.parametrize(
    ("changes", "route"),
    [
        ({}, "AUTO"),
        ({"business_direction_count": 2}, "ASK"),
        ({"impact_categories": ["ci"]}, "REVIEW"),
        ({"external_side_effects": ["credential_export"]}, "BLOCK"),
    ],
)
def test_facts_do_not_classify_but_existing_classifier_retains_all_routes(
    draft: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
    changes: dict[str, object],
    route: str,
) -> None:
    repository, source = draft
    source.write_text(json.dumps({**FACTS, **changes}), encoding="utf-8")
    assert _facts(source) == 0
    _report(capsys)
    assert _task(repository)["current_state"] == "NEW"
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    value = read_task_json(repository, "TASK-0001", "classification.json")
    assert isinstance(value, dict) and value["effective_route"] == route


@pytest.mark.parametrize(
    "raw",
    [
        "{",
        "{}",
        "[]",
        "null",
        '"secret-payload"',
        '{"scope":{"clear":true,"clear":false}}',
        '{"impact":{"level":"low"},"impact":{"level":"high"}}',
        '{"business_direction_count":NaN}',
        '{"business_direction_count":Infinity}',
        '{"business_direction_count":-Infinity}',
        '{"business_direction_count":1e9999}',
        r'{"external_side_effects":["\ud800"]}',
        r'{"external_side_effects":["\udfff"]}',
        r'{"\ud800":true}',
    ],
)
def test_invalid_json_is_rejected_without_task_writes_or_payload_echo(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], raw: str
) -> None:
    repository, source = draft
    source.write_text(raw, encoding="utf-8")
    before = _artifacts(repository)
    assert _facts(source) == 1
    output = capsys.readouterr()
    assert not output.out
    assert output.err and "Traceback" not in output.err and "secret-payload" not in output.err
    assert _artifacts(repository) == before


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"business_direction_count":2.0}', {"business_direction_count": 2}),
        ('{"external_side_effects":["测试😀"]}', {"external_side_effects": ["测试😀"]}),
        (r'{"external_side_effects":["\ud83d\ude00"]}', {"external_side_effects": ["😀"]}),
    ],
)
def test_valid_finite_numbers_and_paired_unicode_remain_recordable(
    draft: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
    raw: str,
    expected: dict[str, object],
) -> None:
    repository, source = draft
    source.write_text(raw, encoding="utf-8")
    assert _facts(source) == 0
    report = _report(capsys)
    for field, value in expected.items():
        assert report["after"][field] == value
        assert _task(repository)["decision_units"][0][field] == value


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
def test_unicode_actor_keeps_event_log_readable_and_repeated_apply_is_a_noop(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], separator: str
) -> None:
    repository, source = draft
    actor = f"declarer{separator}suffix"
    assert _facts(source, actor=actor) == 0
    assert _report(capsys)["applied"] is True
    applied = _artifacts(repository)
    record = load_task_record(repository, "TASK-0001")
    assert len(record.events) == 2
    assert record.events[-1]["actor"] == actor
    assert record.events[-1]["payload"]["after"] == FACTS
    assert main(["status", "TASK-0001", "--format", "json"]) == 0
    assert _report(capsys)["current_state"] == "NEW"
    assert _facts(source, actor=actor) == 0
    report = _report(capsys)
    assert report["changed"] is report["applied"] is report["recovered"] is False
    assert _artifacts(repository) == applied


@pytest.mark.parametrize("encoding", ["ascii", "gbk", "utf-8"])
def test_unicode_facts_subprocess_report_survives_stdout_encoding(
    draft: tuple[Path, Path], encoding: str
) -> None:
    repository, source = draft
    facts = {**FACTS, "external_side_effects": ["测试😀"]}
    source.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    environment["PYTHONIOENCODING"] = encoding
    command = [
        sys.executable,
        "-m",
        "aiflow",
        "facts",
        "TASK-0001",
        "--decision-unit",
        "DU-001",
        "--input",
        str(source),
        "--actor",
        "declarer",
    ]
    original = _artifacts(repository)
    before: dict[str, object] = {
        "reversibility": "reversible",
        "external_side_effects": [],
        "permission_requirements": [],
    }
    applied: dict[str, bytes] = {}
    for mode in ("preview", "apply", "noop"):
        result = subprocess.run(
            [*command, *(["--dry-run"] if mode == "preview" else [])],
            cwd=repository,
            env=environment,
            capture_output=True,
            check=False,
            timeout=10,
        )
        assert result.returncode == 0, result.stderr.decode(encoding)
        assert not result.stderr
        assert json.loads(result.stdout.decode(encoding)) == {
            "task_id": "TASK-0001",
            "decision_unit_id": "DU-001",
            "dry_run": mode == "preview",
            "changed": mode != "noop",
            "applied": mode == "apply",
            "recovered": False,
            "before": facts if mode == "noop" else before,
            "after": facts,
        }
        if mode == "preview":
            assert _artifacts(repository) == original
        elif mode == "apply":
            applied = _artifacts(repository)
        else:
            assert _artifacts(repository) == applied
    record = load_task_record(repository, "TASK-0001")
    assert len(record.events) == 2
    assert record.task["decision_units"][0]["external_side_effects"] == ["测试😀"]
    assert record.events[-1]["payload"]["after"] == facts
    assert json.loads(source.read_text(encoding="utf-8")) == facts


@pytest.mark.parametrize(
    "field",
    [
        "goal",
        "task_id",
        "decision_unit_id",
        "schema_version",
        "inputs",
        "planned_actions",
        "impact_scope",
        "verification_methods",
        "allowed_scope",
        "current_state",
        "subject_commit",
        "unknown",
    ],
)
def test_protected_and_unknown_fields_are_rejected(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], field: str
) -> None:
    repository, source = draft
    source.write_text(json.dumps({field: "private-payload"}), encoding="utf-8")
    before = _artifacts(repository)
    assert _facts(source) == 1
    output = capsys.readouterr()
    assert not output.out and "private-payload" not in output.err
    assert _artifacts(repository) == before


@pytest.mark.parametrize(
    "value",
    [
        {"scope": {"clear": 1}},
        {"scope": {"clear": True, "extra": False}},
        {"impact": {"level": "invalid"}},
        {"protections": {"dry_run": True}},
        {"verification": {"automatic": True}},
        {"impact_categories": ["ci", "ci"]},
        {"controlled_actions": ["unknown"]},
        {"business_direction_count": 0},
        {"change_characteristics": {"mechanical": True}},
        {"verification_requirements": {"acceptance_required": True}},
        {"reversibility": "unknown"},
        {"external_side_effects": [""]},
        {"permission_requirements": ["undeclared_permission"]},
    ],
)
def test_invalid_types_nested_replacements_and_semantic_values_preserve_artifacts(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], value: dict[str, object]
) -> None:
    repository, source = draft
    source.write_text(json.dumps(value), encoding="utf-8")
    before = _artifacts(repository)
    assert _facts(source) == 1
    assert not capsys.readouterr().out
    assert _artifacts(repository) == before


@pytest.mark.parametrize(
    "kind", ["missing", "directory", "invalid_utf8", "missing_unit", "blank_actor"]
)
def test_unreadable_input_and_invalid_identity_preserve_artifacts(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    repository, source = draft
    if kind == "missing":
        source = repository / "absent.json"
    elif kind == "directory":
        source = repository
    elif kind == "invalid_utf8":
        source.write_bytes(b"\xff\xfe")
    before = _artifacts(repository)
    assert (
        _facts(
            source,
            unit="DU-999" if kind == "missing_unit" else "DU-001",
            actor=" " if kind == "blank_actor" else "declarer",
        )
        == 1
    )
    output = capsys.readouterr()
    assert not output.out and "Traceback" not in output.err
    assert _artifacts(repository) == before


@pytest.mark.parametrize(
    "kind",
    ["non_new", "frozen", "classification", "classification_pending", "corrupt_events", "staged"],
)
def test_ineligible_and_corrupt_drafts_are_never_repaired_by_facts(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    repository, source = draft
    directory = resolve_task_path(repository, "TASK-0001")
    if kind == "non_new":
        transition_task_record(
            repository,
            "TASK-0001",
            target_state="CLASSIFIED",
            event_type="classification_recorded",
            actor="tester",
            payload={},
            satisfied_preconditions={"classification_available"},
        )
    elif kind == "frozen":
        task = _task(repository)
        task.update(frozen_spec_sha256="a" * 64, spec_frozen_at="2026-10-21T00:00:00Z")
        _save(repository, task)
    elif kind in {"classification", "classification_pending"}:
        (directory / f"{kind}.json").write_text("{}", encoding="utf-8")
    elif kind == "corrupt_events":
        (directory / "events.jsonl").write_text("{broken", encoding="utf-8")
    else:
        atomic_write_yaml(directory / "task.yaml.next", _task(repository))
    before = _artifacts(repository)
    assert _facts(source) == 1
    output = capsys.readouterr()
    assert not output.out and "Traceback" not in output.err
    assert _artifacts(repository) == before


@pytest.mark.parametrize("kind", ["branch", "repository", "head", "base", "subject"])
def test_git_baseline_mismatch_cannot_be_rebased_by_facts(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    repository, source = draft
    if kind == "branch":
        run_git(repository, "switch", "-c", "different")
    elif kind == "repository":
        (repository / ".ai" / "repository-id").write_text(
            "223e4567-e89b-42d3-a456-426614174000\n", encoding="utf-8"
        )
    elif kind == "head":
        (repository / "tracked.txt").write_text("another committed baseline\n", encoding="utf-8")
        run_git(repository, "add", "tracked.txt")
        run_git(
            repository,
            "-c",
            "user.name=AI Flow Tests",
            "-c",
            "user.email=aiflow@example.invalid",
            "commit",
            "-m",
            "new baseline",
        )
    else:
        task = _task(repository)
        task[f"{kind}_commit"] = "2" * 40
        _save(repository, task)
    before = _artifacts(repository)
    assert _facts(source) == 1
    assert not capsys.readouterr().out
    assert _artifacts(repository) == before


@pytest.mark.parametrize("kind", ["other_unit", "duplicate_unit", "task_contract", "task_identity"])
def test_validation_covers_all_units_and_the_complete_resulting_task(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    repository, source = draft
    task = _task(repository)
    if kind == "task_identity":
        task["task_id"] = "TASK-0002"
        for unit in task["decision_units"]:
            unit["task_id"] = "TASK-0002"
    elif kind == "task_contract":
        task["goal"] = ""
    else:
        other = deepcopy(task["decision_units"][0])
        if kind == "other_unit":
            other["decision_unit_id"] = "DU-002"
            other["permission_requirements"] = ["undeclared"]
        task["decision_units"].append(other)
    _save(repository, task)
    before = _artifacts(repository)
    assert _facts(source) == 1
    assert not capsys.readouterr().out
    assert _artifacts(repository) == before


def test_historical_facts_allow_existing_escalation_and_manual_reassessment(
    draft: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    repository, source = draft
    assert _facts(source) == 0
    _report(capsys)
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    assert (
        main(
            [
                "escalate",
                "TASK-0001",
                "--to",
                "REVIEW",
                "--reason-code",
                "spec_changed",
                "--impact",
                "facts reassessed",
                "--next-step",
                "reclassify",
                "--actor",
                "classifier",
            ]
        )
        == 0
    )
    task = _task(repository)
    task["decision_units"][0]["impact_categories"] = ["ci"]
    _save(repository, task)
    resolve_task_path(repository, "TASK-0001", "resolution.md").write_text(
        "facts reassessed against current work\n", encoding="utf-8"
    )
    assert (
        main(
            [
                "resolve",
                "TASK-0001",
                "--condition",
                "spec_changed",
                "--evidence-ref",
                "resolution.md",
                "--reason",
                "facts reassessed",
                "--actor",
                "reviewer",
            ]
        )
        == 0
    )
    assert main(["classify", "TASK-0001", "--actor", "classifier"]) == 0
    classification = read_task_json(repository, "TASK-0001", "classification.json")
    assert isinstance(classification, dict) and classification["effective_route"] == "REVIEW"
    record = load_task_record(repository, "TASK-0001")
    assert record.task["current_state"] == "WAITING_FOR_SPEC_REVIEW"
    capsys.readouterr()
    before = _artifacts(repository)
    assert _facts(source) == 1
    assert not capsys.readouterr().out
    assert _artifacts(repository) == before
