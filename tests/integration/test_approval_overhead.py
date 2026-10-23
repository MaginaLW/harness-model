"""Integration coverage for the standalone read-only approval-overhead report."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = PROJECT_ROOT / "tools" / "analysis" / "approval_overhead.py"


@pytest.fixture(scope="module")
def overhead_module() -> Any:
    spec = importlib.util.spec_from_file_location("approval_overhead", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _approval(
    kind: str, *, actor: str = "owner", approved_at: str = "2026-09-01T00:00:00Z"
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "decision_unit_id": "DU-001",
        "approval_type": kind,
        "actor": actor,
        "reason": "recorded approval",
        "spec_sha256": "a" * 64,
        "policy_sha256": "b" * 64,
        "subject_commit": "c" * 40,
        "approved_at": approved_at,
    }
    if kind == "action":
        value.update(
            {"action_sha256": "d" * 64, "expires_at": "2026-10-01T00:00:00Z", "single_use": True}
        )
    return value


def _event(kind: str, *, sequence: int, state: str = "CLASSIFIED") -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": "TASK-0001",
        "sequence": sequence,
        "from_state": "NEW",
        "to_state": state,
        "event_type": kind,
        "actor": "owner",
        "occurred_at": "2026-09-01T00:00:00Z",
        "payload": {},
    }


def _ledger(root: Path) -> Path:
    directory = root / ".ai" / "tasks" / "TASK-0001"
    directory.mkdir(parents=True)
    (directory / "task.yaml").write_text(
        "task_id: TASK-0001\ncurrent_state: IMPLEMENTING\n", encoding="utf-8"
    )
    (directory / "classification.json").write_text(
        json.dumps({"task_id": "TASK-0001", "effective_route": "REVIEW"}), encoding="utf-8"
    )
    return directory


def test_report_counts_record_proxies_and_leaves_ledger_unchanged(
    tmp_path: Path, overhead_module: Any
) -> None:
    directory = _ledger(tmp_path)
    approvals = [
        _approval("spec"),
        _approval("action"),
        _approval("action", actor="another-owner", approved_at="2026-09-01T01:00:00Z"),
    ]
    (directory / "approvals.json").write_text(json.dumps(approvals), encoding="utf-8")
    events = [
        _event("task_created", sequence=1),
        _event("task_escalated", sequence=2, state="ESCALATED"),
        _event("verification_failed", sequence=3, state="FAILED"),
    ]
    (directory / "events.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    report = overhead_module.build_report(tmp_path)

    assert report["tasks"] == {
        "total": 1,
        "by_state": {"IMPLEMENTING": 1},
        "by_route": {"REVIEW": 1},
    }
    assert report["approvals"]["by_type"] == {"action": 2, "spec": 1}
    assert report["approvals"]["first_records"] == 2
    assert report["approvals"]["subsequent_records"] == 1
    assert report["approvals"]["same_binding_subsequent_records_by_type"] == {
        "action": 1,
        "spec": 0,
    }
    assert (
        report["approvals"]["by_task_decision_unit_type"][0]["same_binding_subsequent_records"] == 1
    )
    assert report["events"] == {
        "total": 3,
        "by_type": {"task_created": 1, "task_escalated": 1, "verification_failed": 1},
        "escalation_events": 1,
        "verification_failed_events": 1,
    }
    assert report["unavailable"] == {
        "human_interruptions": "unavailable",
        "human_review_time": "unavailable",
        "defect_escape_rate": "unavailable",
    }
    assert "do not prove redundant authorization" in report["limitations"][2]
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_report_rejects_corrupt_ledger_data(
    tmp_path: Path, overhead_module: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = _ledger(tmp_path)
    (directory / "approvals.json").write_text("[]", encoding="utf-8")
    (directory / "events.jsonl").write_text("not-json\n", encoding="utf-8")

    assert overhead_module.main([str(tmp_path), "--format", "json"]) == 2
    assert "TASK-0001/events.jsonl: invalid JSON at line 1" in capsys.readouterr().err


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("terminated", [False, True])
def test_report_keeps_unicode_string_separators_inside_jsonl_records(
    tmp_path: Path,
    overhead_module: Any,
    capsys: pytest.CaptureFixture[str],
    separator: str,
    newline: str,
    terminated: bool,
) -> None:
    directory = _ledger(tmp_path)
    (directory / "approvals.json").write_text("[]", encoding="utf-8")
    events = [_event("task_created", sequence=1), _event("verification_failed", sequence=2)]
    events[0]["payload"] = {"reason": f"private-jsonl-before{separator}private-jsonl-after"}
    text = newline.join(json.dumps(event, ensure_ascii=False) for event in events)
    (directory / "events.jsonl").write_bytes((text + newline * terminated).encode("utf-8"))
    before = _tree_bytes(tmp_path)

    assert overhead_module.main([str(tmp_path), "--format", "json"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["events"] == {
        "total": 2,
        "by_type": {"task_created": 1, "verification_failed": 1},
        "escalation_events": 0,
        "verification_failed_events": 1,
    }
    assert "private-jsonl" not in captured.out
    assert _tree_bytes(tmp_path) == before


def test_report_accepts_cr_delimited_event_records(tmp_path: Path, overhead_module: Any) -> None:
    directory = _ledger(tmp_path)
    (directory / "approvals.json").write_text("[]", encoding="utf-8")
    events = [_event("task_created", sequence=1), _event("verification_failed", sequence=2)]
    events[0]["payload"] = {"reason": "private-jsonl-before\u2028private-jsonl-after"}
    text = "\r".join(json.dumps(event, ensure_ascii=False) for event in events)
    (directory / "events.jsonl").write_bytes(text.encode("utf-8"))

    report = overhead_module.build_report(tmp_path)

    assert report["events"]["total"] == 2
    assert "private-jsonl" not in json.dumps(report, ensure_ascii=False)


@pytest.mark.parametrize("invalid_line", ["", " \t", "private-jsonl-invalid"])
def test_report_still_rejects_invalid_physical_jsonl_records(
    tmp_path: Path,
    overhead_module: Any,
    capsys: pytest.CaptureFixture[str],
    invalid_line: str,
) -> None:
    directory = _ledger(tmp_path)
    (directory / "approvals.json").write_text("[]", encoding="utf-8")
    event = _event("task_created", sequence=1)
    event["payload"] = {"reason": "private-jsonl-before\u2028private-jsonl-after"}
    text = json.dumps(event, ensure_ascii=False) + "\n" + invalid_line + "\n"
    (directory / "events.jsonl").write_bytes(text.encode("utf-8"))
    before = _tree_bytes(tmp_path)

    assert overhead_module.main([str(tmp_path), "--format", "json"]) == 2

    captured = capsys.readouterr()
    reason = "invalid JSON at line 2" if invalid_line.strip() else "blank line at 2"
    assert captured.out == ""
    assert captured.err == f"approval-overhead: TASK-0001/events.jsonl: {reason}\n"
    assert "private-jsonl" not in captured.err
    assert _tree_bytes(tmp_path) == before


def test_report_accepts_unclassified_new_task(tmp_path: Path, overhead_module: Any) -> None:
    directory = _ledger(tmp_path)
    (directory / "classification.json").unlink()
    (directory / "approvals.json").write_text("[]", encoding="utf-8")
    (directory / "events.jsonl").write_text(
        json.dumps(_event("task_created", sequence=1)) + "\n", encoding="utf-8"
    )

    assert overhead_module.build_report(tmp_path)["tasks"]["by_route"] == {"not_available": 1}


@pytest.mark.parametrize("field", ["effective_route", "approval_type"])
def test_report_rejects_non_string_categories_without_traceback(
    tmp_path: Path,
    overhead_module: Any,
    capsys: pytest.CaptureFixture[str],
    field: str,
) -> None:
    directory = _ledger(tmp_path)
    approval = _approval("spec")
    if field == "effective_route":
        (directory / "classification.json").write_text(
            json.dumps({"task_id": "TASK-0001", "effective_route": []}), encoding="utf-8"
        )
    else:
        approval[field] = {}
    (directory / "approvals.json").write_text(json.dumps([approval]), encoding="utf-8")

    assert overhead_module.main([str(tmp_path)]) == 2
    assert f"{field} is invalid" in capsys.readouterr().err


def test_binding_counts_follow_approval_type_and_keep_action_limits(
    tmp_path: Path, overhead_module: Any
) -> None:
    directory = _ledger(tmp_path)
    spec = _approval("spec")
    code = {**_approval("code"), "evidence_sha256": "e" * 64}
    action = _approval("action")
    approvals = [
        spec,
        {**spec, "subject_commit": "f" * 40},
        code,
        {**code, "evidence_sha256": "f" * 64},
        action,
        {**action, "expires_at": "2026-11-01T00:00:00Z"},
    ]
    (directory / "approvals.json").write_text(json.dumps(approvals), encoding="utf-8")
    (directory / "events.jsonl").write_text(
        json.dumps(_event("task_created", sequence=1)) + "\n", encoding="utf-8"
    )

    assert overhead_module.build_report(tmp_path)["approvals"][
        "same_binding_subsequent_records_by_type"
    ] == {"action": 0, "code": 0, "spec": 1}


def _run_overhead(
    repository: Path, *arguments: str, encoding: str = "utf-8"
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-B", str(TOOL_PATH), str(repository), *arguments],
        capture_output=True,
        env={**os.environ, "PYTHONINTMAXSTRDIGITS": "4300", "PYTHONIOENCODING": encoding},
        check=False,
        timeout=15,
    )


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _malformed_ledger(root: Path, filename: str, malformed: str) -> None:
    directory = _ledger(root)
    (directory / "approvals.json").write_text("[]", encoding="utf-8")
    event = json.dumps(_event("task_created", sequence=1)) + "\n"
    (directory / "events.jsonl").write_text(event, encoding="utf-8")
    value = "9" * 4500 if malformed == "integer" else "[" * 1500 + "null" + "]" * 1500
    payload = (
        "private-probe: " + value if filename == "task.yaml" else '{"private-probe":' + value + "}"
    )
    if filename == "events.jsonl":
        payload = event + payload + "\n"
    (directory / filename).write_text(payload, encoding="utf-8")


@pytest.fixture
def fixed_integer_limit() -> Any:
    original = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    try:
        yield
    finally:
        sys.set_int_max_str_digits(original)


@pytest.mark.parametrize(
    "filename", ["task.yaml", "classification.json", "approvals.json", "events.jsonl"]
)
@pytest.mark.parametrize("malformed", ["integer", "deep"])
def test_legacy_parser_limits_are_safe_cli_errors(
    tmp_path: Path,
    overhead_module: Any,
    capsys: pytest.CaptureFixture[str],
    fixed_integer_limit: Any,
    filename: str,
    malformed: str,
) -> None:
    _malformed_ledger(tmp_path, filename, malformed)
    before = _tree_bytes(tmp_path)
    message = {
        "task.yaml": "invalid YAML",
        "classification.json": "invalid JSON",
        "approvals.json": "invalid JSON",
        "events.jsonl": "invalid JSON at line 2",
    }[filename]
    expected = f"approval-overhead: TASK-0001/{filename}: {message}\n"

    assert overhead_module.main([str(tmp_path), "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == expected
    result = _run_overhead(tmp_path, "--format", "json")
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.decode("ascii").replace("\r\n", "\n") == expected
    assert _tree_bytes(tmp_path) == before


def _commit_fixture(root: Path) -> None:
    environment = {
        key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ALLOW_PROTOCOL": "",
        }
    )
    for arguments in (
        ("-c", "init.templateDir=", "init", "--quiet"),
        ("add", ".ai/tasks"),
        (
            "-c",
            "user.name=Synthetic Fixture",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "synthetic parser boundary",
        ),
    ):
        subprocess.run(
            ["git", "-c", f"core.hooksPath={root / '.git/no-hooks'}", *arguments],
            cwd=root,
            env=environment,
            capture_output=True,
            check=True,
            timeout=15,
        )


@pytest.mark.parametrize("mode", ["--snapshot", "--availability"])
@pytest.mark.parametrize("filename", ["task.yaml", "classification.json", "events.jsonl"])
@pytest.mark.parametrize("malformed", ["integer", "deep"])
def test_committed_parser_limits_are_safe_cli_errors(
    tmp_path: Path,
    overhead_module: Any,
    capsys: pytest.CaptureFixture[str],
    fixed_integer_limit: Any,
    mode: str,
    filename: str,
    malformed: str,
) -> None:
    _malformed_ledger(tmp_path, filename, malformed)
    _commit_fixture(tmp_path)
    before = _tree_bytes(tmp_path)
    expected = f"approval-overhead: TASK-0001/{filename}: invalid document\n"

    assert overhead_module.main([str(tmp_path), mode, "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == expected
    result = _run_overhead(tmp_path, mode, "--format", "json")
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.decode("ascii").replace("\r\n", "\n") == expected
    assert _tree_bytes(tmp_path) == before


@pytest.mark.parametrize("mode", [None, "--snapshot", "--availability"])
@pytest.mark.parametrize("failure", [RuntimeError, OSError, ValueError])
def test_root_resolution_errors_stop_before_any_ledger_read(
    tmp_path: Path,
    overhead_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str | None,
    failure: type[Exception],
) -> None:
    native_resolve = Path.resolve
    calls = 0

    def failed_resolve(path: Path, *args: Any, **kwargs: Any) -> Path:
        nonlocal calls
        if path == tmp_path:
            calls += 1
            raise failure("private-root-probe")
        return native_resolve(path, *args, **kwargs)

    def forbidden_read(*args: Any, **kwargs: Any) -> None:
        pytest.fail("root resolution failure must stop before ledger/Git reads")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "resolve", failed_resolve)
        for name in ("build_report", "build_snapshot", "build_availability", "_snapshot_git"):
            patch.setattr(overhead_module, name, forbidden_read)
        arguments = [str(tmp_path), "--format", "json"]
        if mode:
            arguments.append(mode)
        assert overhead_module.main(arguments) == 2
    captured = capsys.readouterr()
    assert calls == 1
    assert captured.out == ""
    assert captured.err == "approval-overhead: repository: root path could not be resolved\n"


@pytest.mark.parametrize("mode", [None, "--snapshot", "--availability"])
def test_cyclic_root_has_only_the_safe_cli_error(tmp_path: Path, mode: str | None) -> None:
    root = tmp_path / "private-root-probe"
    try:
        root.symlink_to(root.name, target_is_directory=True)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"directory symlinks are unavailable: {type(error).__name__}")
    arguments = ["--format", "json"]
    if mode:
        arguments.append(mode)
    result = _run_overhead(root, *arguments)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.replace(b"\r\n", b"\n") == (
        b"approval-overhead: repository: root path could not be resolved\n"
    )


@pytest.mark.parametrize("failure", [RuntimeError, OSError, ValueError, RecursionError])
def test_internal_build_errors_are_not_reclassified_as_root_input_errors(
    tmp_path: Path,
    overhead_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    failure: type[Exception],
) -> None:
    def failed_build(*args: Any, **kwargs: Any) -> None:
        raise failure("internal-build-probe")

    monkeypatch.setattr(overhead_module, "build_report", failed_build)
    with pytest.raises(failure, match="internal-build-probe"):
        overhead_module.main([str(tmp_path)])


@pytest.mark.parametrize("field", ["decision_unit_id", "current_state"])
@pytest.mark.parametrize("encoding", ["utf-8", "ascii", "gbk"])
@pytest.mark.parametrize("output_format", ["json", "text"])
def test_unicode_legacy_projection_survives_stdout_encoding_without_changing_values(
    tmp_path: Path,
    overhead_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    encoding: str,
    output_format: str,
) -> None:
    directory = _ledger(tmp_path)
    label = "synthetic_\u4e2d\U0001f9ea"
    approval = _approval("spec", actor=label)
    if field == "decision_unit_id":
        approval[field] = label
    else:
        (directory / "task.yaml").write_text(
            f"task_id: TASK-0001\ncurrent_state: {label}\n", encoding="utf-8"
        )
    (directory / "approvals.json").write_text(
        json.dumps([approval], ensure_ascii=False), encoding="utf-8"
    )
    (directory / "events.jsonl").write_text(
        json.dumps(_event("task_created", sequence=1)) + "\n", encoding="utf-8"
    )
    expected = overhead_module.build_report(tmp_path)
    before = _tree_bytes(tmp_path)

    with (
        io.BytesIO() as buffer,
        io.TextIOWrapper(buffer, encoding=encoding, newline="\n") as output,
    ):
        with monkeypatch.context() as patch:
            patch.setattr(sys, "stdout", output)
            assert overhead_module.main([str(tmp_path), "--format", output_format]) == 0
        output.flush()
        in_process = buffer.getvalue()
    result = _run_overhead(tmp_path, "--format", output_format, encoding=encoding)

    assert result.returncode == 0
    assert result.stderr == b""
    assert result.stdout.replace(b"\r\n", b"\n") == in_process
    if output_format == "json":
        assert json.loads(result.stdout.decode("ascii")) == expected
    else:
        text = overhead_module._text(expected) + "\n"
        assert result.stdout.replace(b"\r\n", b"\n") == text.encode(
            encoding, errors="backslashreplace"
        )
    assert _tree_bytes(tmp_path) == before


def test_text_main_accepts_a_string_stream_without_an_encoding(
    tmp_path: Path, overhead_module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = _ledger(tmp_path)
    (directory / "approvals.json").write_text("[]", encoding="utf-8")
    (directory / "events.jsonl").write_text(
        json.dumps(_event("task_created", sequence=1)) + "\n", encoding="utf-8"
    )
    expected = overhead_module._text(overhead_module.build_report(tmp_path)) + "\n"
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)

    assert overhead_module.main([str(tmp_path), "--format", "text"]) == 0

    assert output.getvalue() == expected
