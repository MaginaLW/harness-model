"""Selection checks preserve the distinction between original bytes and CRLF folding."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from tools.evidence import bundle
from tools.evidence import selection_review as subject


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def inputs(tmp_path: Path) -> dict[str, Path]:
    paths = {name: tmp_path / name for name in ("task", "raw", "producer")}
    for path in paths.values():
        path.mkdir()
    paths["selection"] = tmp_path / "selection.json"
    paths["request"] = tmp_path / "request.json"
    (paths["raw"] / "task" / "logs").mkdir(parents=True)
    checks = []
    files = [{"kind": "runtime-original", "path": "task/evidence.json"}]
    for number in range(10):
        check: dict[str, Any] = {"status": "passed", "command_summary": "private ignored data"}
        for stream in ("stdout", "stderr"):
            relative = f"logs/check-{number}.{stream}.log"
            (paths["raw"] / "task" / relative).write_bytes(b"" if stream == "stderr" else b"ok\r\n")
            files.append({"kind": "runtime-original", "path": f"task/{relative}"})
            check[f"{stream}_log_ref"] = relative
        checks.append(check)
    write_json(paths["raw"] / "task/evidence.json", {"schema_version": "1.0", "checks": checks})
    (paths["task"] / "events.jsonl").write_bytes(b'{"state":"done"}\n')
    (paths["producer"] / "events.jsonl").write_bytes(b'{"state":"done"}\r\n')
    (paths["raw"] / "events-original.jsonl").write_bytes(b'{"state":"done"}\r\n')
    files.extend(
        [
            {"kind": "git-text", "path": "events.jsonl"},
            {"kind": "runtime-original", "path": "events-original.jsonl"},
        ]
    )
    write_json(paths["selection"], {"version": 1, "files": files})
    write_json(
        paths["request"],
        {
            "version": 1,
            "evidence": [{"path": "task/evidence.json", "task_root": "task"}],
            "pairs": [
                {
                    "producer_path": "events.jsonl",
                    "staged_path": "events.jsonl",
                    "original_path": "events-original.jsonl",
                }
            ],
        },
    )
    return paths


def review(inputs: dict[str, Path], **kwargs: Any) -> dict[str, Any]:
    return subject.review_selection(
        inputs["task"],
        inputs["raw"],
        inputs["selection"],
        inputs["request"],
        kwargs.get("producer", inputs["producer"]),
    )


def edit_json(path: Path, change: Any) -> None:
    document = json.loads(path.read_bytes())
    change(document)
    write_json(path, document)


def omit(inputs: dict[str, Path], path: str) -> None:
    edit_json(
        inputs["selection"],
        lambda document: document.update(files=[e for e in document["files"] if e["path"] != path]),
    )


def test_actual_shape_twenty_references_and_distinct_crlf_original_are_read_only(
    inputs: dict[str, Path], tmp_path: Path
) -> None:
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    result = review(inputs)
    assert result["status"] == "CONSISTENT"
    assert (result["checks"], result["log_references"], result["selected_files"]) == (10, 20, 23)
    assert result["evidence"] == [{"checks": 10, "log_references": 20, "issues": []}]
    assert result["pairs"] == [{"comparison": "CRLF_ONLY", "original": "MATCHED"}]
    assert result["source_authenticated"] is False
    assert result["governance_effect"] == "none"
    assert str(tmp_path) not in json.dumps(result)
    assert "private ignored data" not in json.dumps(result)
    assert before == {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("task/logs/check-0.stdout.log", "LOG_NOT_SELECTED"),
        ("task/logs/check-9.stderr.log", "LOG_NOT_SELECTED"),
        ("task/evidence.json", "EVIDENCE_NOT_SELECTED"),
        ("events-original.jsonl", "ORIGINAL_NOT_SELECTED"),
        ("events.jsonl", "STAGED_NOT_SELECTED"),
    ],
)
def test_omitted_files_are_not_even_inspected(
    inputs: dict[str, Path], path: str, code: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    omit(inputs, path)
    original = bundle._plain_path

    def guarded(candidate: Path, **kwargs: Any) -> Path:
        assert candidate not in {inputs[root] / path for root in ("raw", "task", "producer")}
        return original(candidate, **kwargs)

    monkeypatch.setattr(bundle, "_plain_path", guarded)
    result = review(inputs)
    assert result["status"] == "INCOMPLETE"
    assert code in json.dumps(result)


@pytest.mark.parametrize(
    ("root", "path", "code"),
    [
        ("raw", "task/evidence.json", "MISSING_EVIDENCE"),
        ("raw", "task/logs/check-2.stderr.log", "MISSING_LOG"),
        ("raw", "events-original.jsonl", "MISSING_ORIGINAL"),
        ("task", "events.jsonl", "MISSING_STAGED"),
        ("producer", "events.jsonl", "MISSING_PRODUCER"),
    ],
)
def test_missing_explicit_files_are_reported(
    inputs: dict[str, Path], root: str, path: str, code: str
) -> None:
    (inputs[root] / path).unlink()
    result = review(inputs)
    assert result["status"] == "INCOMPLETE"
    assert code in json.dumps(result)


@pytest.mark.parametrize(
    ("producer", "staged", "comparison"),
    [
        (b"a\r\nb\r\n", b"a\nb\n", "CRLF_ONLY"),
        (b"a\rb\r", b"a\nb\n", "CONTENT_CONFLICT"),
        (b"a\r\rb", b"a\rb", "CONTENT_CONFLICT"),
        (b"a\r\n", b"changed\n", "CONTENT_CONFLICT"),
        (b"\r\r\n", b"\r\n", "CONTENT_CONFLICT"),
        (b"a\rb\r", b"a\rb\r", "RAW_IDENTICAL"),
        (b"", b"", "RAW_IDENTICAL"),
        (b"\xff\r\n", b"\xff\n", "CRLF_ONLY"),
    ],
)
def test_byte_comparison_handles_split_crlf_and_keeps_bare_cr(
    inputs: dict[str, Path],
    producer: bytes,
    staged: bytes,
    comparison: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bundle, "CHUNK_BYTES", 2)
    (inputs["producer"] / "events.jsonl").write_bytes(producer)
    (inputs["raw"] / "events-original.jsonl").write_bytes(producer)
    (inputs["task"] / "events.jsonl").write_bytes(staged)
    result = review(inputs)
    assert result["pairs"] == [{"comparison": comparison, "original": "MATCHED"}]
    assert result["status"] == ("INCOMPLETE" if comparison == "CONTENT_CONFLICT" else "CONSISTENT")


@pytest.mark.parametrize(
    ("same", "original"), [(True, "NOT_REQUIRED"), (False, "ORIGINAL_NOT_MAPPED")]
)
def test_only_identical_bytes_can_omit_original_mapping(
    inputs: dict[str, Path], same: bool, original: str
) -> None:
    if same:
        (inputs["producer"] / "events.jsonl").write_bytes(
            (inputs["task"] / "events.jsonl").read_bytes()
        )
    edit_json(inputs["request"], lambda d: d["pairs"][0].update(original_path=None))
    result = review(inputs)
    assert result["pairs"][0]["original"] == original
    assert result["status"] == ("CONSISTENT" if same else "INCOMPLETE")


def test_folded_original_cannot_replace_exact_producer_bytes(inputs: dict[str, Path]) -> None:
    (inputs["raw"] / "events-original.jsonl").write_bytes(
        (inputs["task"] / "events.jsonl").read_bytes()
    )
    result = review(inputs)
    assert result["status"] == "INCOMPLETE"
    assert result["pairs"] == [{"comparison": "CRLF_ONLY", "original": "ORIGINAL_MISMATCH"}]


def test_no_pairs_needs_no_producer_and_raw_root_can_be_task_root(inputs: dict[str, Path]) -> None:
    edit_json(
        inputs["request"],
        lambda d: d.update(pairs=[], evidence=[{"path": "evidence.json", "task_root": ""}]),
    )
    evidence = inputs["raw"] / "task/evidence.json"
    write_json(inputs["raw"] / "evidence.json", json.loads(evidence.read_bytes()))
    edit_json(inputs["selection"], lambda d: d["files"][0].update(path="evidence.json"))
    result = review(inputs, producer=None)
    assert result["checks"] == 10
    assert result["pairs"] == []
    assert all(item["code"] == "LOG_NOT_SELECTED" for item in result["evidence"][0]["issues"])


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (lambda d: d.update(version=True), "UNSUPPORTED_VERSION"),
        (lambda d: d.update(version=2), "UNSUPPORTED_VERSION"),
        (lambda d: d.update(extra="ignored?"), "INVALID_FIELDS"),
        (lambda d: d.update(evidence=[], pairs=[]), "INVALID_MAPPING_COUNT"),
        (lambda d: d.update(pairs={}), "INVALID_MAPPING_COUNT"),
        (lambda d: d.update(evidence=None), "INVALID_MAPPING_COUNT"),
        (lambda d: d["evidence"][0].update(task_root="wrong"), "EVIDENCE_ROOT_MISMATCH"),
        (lambda d: d["evidence"].append(d["evidence"][0]), "DUPLICATE_MAPPING"),
        (lambda d: d["pairs"].append(d["pairs"][0]), "DUPLICATE_MAPPING"),
        (lambda d: d["pairs"][0].update(producer_path="../secret"), "UNSAFE_PATH"),
        (lambda d: d["pairs"][0].update(original_path="secret:stream"), "UNSAFE_PATH"),
        (lambda d: d["pairs"][0].update(staged_path="CON"), "UNSAFE_PATH"),
    ],
)
def test_request_rejects_ambiguous_or_unsafe_mappings(
    inputs: dict[str, Path], change: Any, code: str
) -> None:
    edit_json(inputs["request"], change)
    with pytest.raises(bundle.BundleError, match=f"^{code}$"):
        review(inputs)


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (lambda d: d.update(schema_version="2.0"), "UNSUPPORTED_EVIDENCE"),
        (lambda d: d.update(checks=[]), "INVALID_CHECK_COUNT"),
        (lambda d: d.update(checks=[None]), "INVALID_CHECK"),
        (lambda d: d["checks"][0].update(stdout_log_ref="../secret"), "UNSAFE_PATH"),
        (lambda d: d["checks"][0].update(stderr_log_ref="secret.log"), "INVALID_LOG_REFERENCE"),
    ],
)
def test_bad_evidence_references_fail_closed(
    inputs: dict[str, Path], change: Any, code: str
) -> None:
    edit_json(inputs["raw"] / "task/evidence.json", change)
    with pytest.raises(bundle.BundleError, match=f"^{code}$"):
        review(inputs)


def test_null_or_absent_reference_is_not_silently_complete(inputs: dict[str, Path]) -> None:
    edit_json(inputs["raw"] / "task/evidence.json", lambda d: d["checks"][0].pop("stdout_log_ref"))
    edit_json(
        inputs["raw"] / "task/evidence.json", lambda d: d["checks"][0].update(stderr_log_ref=None)
    )
    result = review(inputs)
    assert result["status"] == "INCOMPLETE"
    assert result["log_references"] == 18
    assert [issue["code"] for issue in result["evidence"][0]["issues"]] == [
        "MISSING_LOG_REFERENCE"
    ] * 2


def test_producer_root_is_required_for_pairs(inputs: dict[str, Path]) -> None:
    with pytest.raises(bundle.BundleError, match="^PRODUCER_DIR_REQUIRED$"):
        review(inputs, producer=None)


def test_selection_case_collision_is_rejected(inputs: dict[str, Path]) -> None:
    edit_json(
        inputs["selection"],
        lambda d: d["files"].append({"kind": "git-text", "path": "EVENTS.jsonl"}),
    )
    with pytest.raises(bundle.BundleError, match="^DUPLICATE_PATH$"):
        review(inputs)


def test_selected_link_is_rejected_without_reading_target(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    target = inputs["raw"] / "task/logs/check-0.stdout.log"
    original = Path.lstat

    def reparse(path: Path, *args: Any, **kwargs: Any) -> Any:
        info = original(path, *args, **kwargs)
        if path == target:
            return type("Reparse", (), {"st_mode": info.st_mode, "st_file_attributes": 0x400})()
        return info

    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(bundle.BundleError, match="^LINK_NOT_ALLOWED$"):
        review(inputs)


def test_reader_detects_atomic_replacement_before_final_identity_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, replacement = tmp_path / "source", tmp_path / "replacement"
    source.write_bytes(b"one")
    replacement.write_bytes(b"two")
    original = Path.open

    class ReplacingStream:
        def __enter__(self) -> Any:
            self.stream = original(source, "rb")
            return self

        def __exit__(self, *args: Any) -> None:
            self.stream.close()
            os.replace(replacement, source)

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, count: int) -> bytes:
            return self.stream.read(count)

    monkeypatch.setattr(
        Path,
        "open",
        lambda path, *a, **kw: ReplacingStream() if path == source else original(path, *a, **kw),
    )
    with pytest.raises(bundle.BundleError, match="^SOURCE_CHANGED$"):
        subject.Reader().read(source)


def test_cached_reads_still_detect_file_changes(tmp_path: Path) -> None:
    path = tmp_path / "file"
    path.write_bytes(b"a")
    reader = subject.Reader()
    first, _ = reader.read(path)
    assert reader.read(path)[0] == first
    assert reader.total == 1
    path.write_bytes(b"changed")
    with pytest.raises(bundle.BundleError, match="^SOURCE_CHANGED$"):
        reader.read(path)


def test_reader_size_and_total_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "file"
    path.write_bytes(b"12345")
    monkeypatch.setattr(bundle, "MAX_FILE_BYTES", 4)
    with pytest.raises(bundle.BundleError, match="^CONTENT_TOO_LARGE$"):
        subject.Reader().read(path)
    monkeypatch.setattr(bundle, "MAX_FILE_BYTES", 8)
    monkeypatch.setattr(bundle, "MAX_TOTAL_BYTES", 4)
    with pytest.raises(bundle.BundleError, match="^TOTAL_TOO_LARGE$"):
        subject.Reader().read(path)


def test_total_checks_are_bounded_across_evidence_documents(
    inputs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = subject.Reader()
    monkeypatch.setattr(bundle, "MAX_FILES", 15)
    item = {"path": "task/evidence.json", "task_root": "task"}
    selected = {("runtime-original", "task/evidence.json")}
    subject._evidence(item, selected, inputs["raw"], reader)
    with pytest.raises(bundle.BundleError, match="^TOO_MANY_CHECKS$"):
        subject._evidence(item, selected, inputs["raw"], reader)


def test_read_growth_cannot_evade_file_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "growing"
    path.write_bytes(b"123")
    original = Path.open

    class GrowingStream:
        def __enter__(self) -> Any:
            self.stream = original(path, "rb")
            self.grown = False
            return self

        def __exit__(self, *args: Any) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, count: int) -> bytes:
            if not self.grown:
                with original(path, "ab") as writer:
                    writer.write(b"456")
                self.grown = True
            return self.stream.read(count)

    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: GrowingStream())
    monkeypatch.setattr(bundle, "MAX_FILE_BYTES", 4)
    monkeypatch.setattr(bundle, "CHUNK_BYTES", 2)
    with pytest.raises(bundle.BundleError, match="^CONTENT_TOO_LARGE$"):
        subject.Reader().read(path)


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"\xff", "INVALID_JSON"),
        (b'{"version":1,"version":1}', "DUPLICATE_JSON_KEY"),
        (b"[" * 5000 + b"]" * 5000, "INVALID_JSON"),
        (b'{"version":' + b"1" * 5000 + b"}", "INVALID_JSON"),
    ],
)
def test_untrusted_request_json_is_bounded_and_parse_errors_are_stable(
    inputs: dict[str, Path], content: bytes, code: str
) -> None:
    inputs["request"].write_bytes(content)
    with pytest.raises(bundle.BundleError, match=f"^{code}$"):
        review(inputs)


def arguments(inputs: dict[str, Path]) -> list[str]:
    return [
        part
        for name in ("task", "raw", "selection", "request", "producer")
        for part in (
            f"--{name}-dir" if name in {"task", "raw", "producer"} else f"--{name}",
            str(inputs[name]),
        )
    ]


def test_cli_success_and_incomplete(
    inputs: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    assert subject.main(arguments(inputs)) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "CONSISTENT"
    omit(inputs, "events-original.jsonl")
    assert subject.main(arguments(inputs)) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "INCOMPLETE"


def test_cli_errors_never_print_private_paths(
    inputs: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    inputs["request"].write_bytes(b'{"version":1,"version":1}')
    assert subject.main(arguments(inputs)) == 1
    output = capsys.readouterr()
    assert not output.out
    assert json.loads(output.err) == {"status": "ERROR", "code": "DUPLICATE_JSON_KEY"}
    inputs["request"].unlink()
    assert subject.main(arguments(inputs)) == 1
    assert json.loads(capsys.readouterr().err) == {"status": "ERROR", "code": "IO_ERROR"}
