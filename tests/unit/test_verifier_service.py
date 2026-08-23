"""Verifier-context service regression tests."""

from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from aiflow.errors import ContractError
from aiflow.verifier_service import (
    _acceptance_conditions,
    _diff_summary,
    canonical_json,
    context_sha256,
    current_implementer_actor,
    load_verifier_context,
    save_verifier_context,
    validate_verifier_actor,
    validate_verifier_context,
    validate_verifier_context_current,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _context() -> dict[str, object]:
    path = REPOSITORY_ROOT / "tests" / "fixtures" / "contracts" / "valid" / "verifier-context.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    value["context_sha256"] = context_sha256(value)
    return value


def test_canonical_json_and_hash_are_stable_and_tampering_is_rejected() -> None:
    context = _context()
    reordered = {key: context[key] for key in reversed(context)}

    assert canonical_json(context) == canonical_json(reordered)
    validate_verifier_context(context)

    context["content"] = {**context["content"], "goal": "tampered"}  # type: ignore[arg-type]
    with pytest.raises(ContractError) as caught:
        validate_verifier_context(context)
    assert caught.value.code == "VERIFIER_CONTEXT_HASH_INVALID"


def test_current_implementer_actor_uses_latest_implementation_cycle() -> None:
    events = (
        {"event_type": "implementation_started", "actor": " first "},
        {"event_type": "implementation_retried", "actor": " second "},
    )

    assert current_implementer_actor(events) == "second"


@pytest.mark.parametrize(
    "events",
    [(), ({"event_type": "implementation_started", "actor": "  "},)],
)
def test_current_implementer_actor_requires_a_nonempty_actor(
    events: tuple[dict[str, str], ...],
) -> None:
    with pytest.raises(ContractError) as caught:
        current_implementer_actor(events)
    assert caught.value.code == "VERIFIER_IMPLEMENTER_MISSING"


@pytest.mark.parametrize(
    ("implementer", "verifier", "code"),
    [
        (" ", "verifier", "VERIFIER_IMPLEMENTER_MISSING"),
        ("implementer", " ", "VERIFIER_ACTOR_REQUIRED"),
        ("same", " same ", "VERIFIER_ACTOR_NOT_INDEPENDENT"),
    ],
)
def test_verifier_actor_must_be_trimmed_nonempty_and_independent(
    implementer: str, verifier: str, code: str
) -> None:
    with pytest.raises(ContractError) as caught:
        validate_verifier_actor(implementer, verifier)
    assert caught.value.code == code


def test_verifier_context_is_immutable_and_filename_bound(tmp_path: Path) -> None:
    context = _context()
    (tmp_path / ".ai" / "tasks" / "TASK-0001").mkdir(parents=True)

    path = save_verifier_context(tmp_path, "TASK-0001", context)
    assert path.name == f"{context['context_sha256']}.json"
    assert load_verifier_context(tmp_path, "TASK-0001", str(context["context_sha256"])) == context

    stored = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(stored, dict)
    stored["content"] = {**stored["content"], "goal": "different"}
    path.write_text(json.dumps(stored), encoding="utf-8")
    with pytest.raises(ContractError) as caught:
        save_verifier_context(tmp_path, "TASK-0001", context)
    assert caught.value.code == "VERIFIER_CONTEXT_IMMUTABLE"


def test_verifier_context_current_rejects_any_bound_fact_change() -> None:
    context = _context()
    current = deepcopy(context)
    validate_verifier_context_current(context, current)

    current["subject_commit"] = "3" * 40
    current["context_sha256"] = context_sha256(current)
    with pytest.raises(ContractError) as caught:
        validate_verifier_context_current(context, current)
    assert caught.value.code == "VERIFIER_CONTEXT_STALE"


def test_acceptance_conditions_come_from_the_frozen_specification() -> None:
    specification = (
        "# Task\n\n## 验收条件\n\n- first condition\n- second condition\n\n## 禁止动作\n\n- none\n"
    )

    assert _acceptance_conditions(specification, {}) == ["first condition", "second condition"]


def test_diff_summary_preserves_binary_paths_without_inventing_numstat(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout=b"2\t1\tsrc/text.py\n-\t-\tassets/blob.bin\n")

    monkeypatch.setattr("aiflow.verifier_service.subprocess.run", fake_run)

    paths, summary = _diff_summary(tmp_path, "1" * 40, "2" * 40)

    assert paths == ["assets/blob.bin", "src/text.py"]
    assert summary == {"files": 2, "additions": 2, "deletions": 1, "binary_files": 1}


@pytest.mark.parametrize(
    ("failure", "code"),
    [
        (subprocess.TimeoutExpired(["git"], 1), "VERIFIER_CONTEXT_DIFF_TIMEOUT"),
        (OSError("git unavailable"), "VERIFIER_CONTEXT_DIFF_FAILED"),
    ],
)
def test_diff_summary_reports_runner_failures_with_stable_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: BaseException,
    code: str,
) -> None:
    def fail_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise failure

    monkeypatch.setattr("aiflow.verifier_service.subprocess.run", fail_run)

    with pytest.raises(ContractError) as caught:
        _diff_summary(tmp_path, "1" * 40, "2" * 40)

    assert caught.value.code == code


@pytest.mark.parametrize(
    ("result", "code"),
    [
        (SimpleNamespace(returncode=1, stdout=b""), "VERIFIER_CONTEXT_DIFF_FAILED"),
        (SimpleNamespace(returncode=0, stdout=b"\xff"), "VERIFIER_CONTEXT_DIFF_INVALID"),
        (SimpleNamespace(returncode=0, stdout=b"1\t2\n"), "VERIFIER_CONTEXT_DIFF_INVALID"),
        (
            SimpleNamespace(returncode=0, stdout=b"not-a-number\t2\tfile.py\n"),
            "VERIFIER_CONTEXT_DIFF_INVALID",
        ),
    ],
)
def test_diff_summary_rejects_invalid_git_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    result: SimpleNamespace,
    code: str,
) -> None:
    monkeypatch.setattr("aiflow.verifier_service.subprocess.run", lambda *_args, **_kwargs: result)

    with pytest.raises(ContractError) as caught:
        _diff_summary(tmp_path, "1" * 40, "2" * 40)

    assert caught.value.code == code


def test_acceptance_conditions_fall_back_to_unit_methods_then_default() -> None:
    task = {
        "decision_units": [
            {"verification_methods": [" first method ", "", 3]},
            {"verification_methods": ["second method", "first method"]},
            "invalid-unit",
        ]
    }

    assert _acceptance_conditions("# no acceptance heading\n", task) == [
        "first method",
        "second method",
    ]
    assert _acceptance_conditions("# no acceptance heading\n", {}) == [
        "Meet the frozen task specification acceptance conditions"
    ]
