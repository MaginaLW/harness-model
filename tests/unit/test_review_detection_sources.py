"""Check explicit documentation references against real, local Git objects."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "tools/analysis/review_detection_sources.py"
PRIVATE = "PRIVATE_SOURCE_CONTENT_DO_NOT_ECHO"
ERROR = "review-detection-sources: supplied declarations or repository are invalid"
CONTENT = ("# Contract\n\n" + PRIVATE + "\n").encode()


def _git(root: Path, *arguments: str, data: bytes | None = None) -> bytes:
    environment = {
        key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")
    }
    environment.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_OPTIONAL_LOCKS="0",
        GIT_AUTHOR_NAME="Synthetic Fixture",
        GIT_AUTHOR_EMAIL="fixture@example.invalid",
        GIT_COMMITTER_NAME="Synthetic Fixture",
        GIT_COMMITTER_EMAIL="fixture@example.invalid",
    )
    return subprocess.run(
        ["git", "--no-pager", "-C", str(root), *arguments],
        input=data,
        capture_output=True,
        check=True,
        env=environment,
        timeout=10,
    ).stdout


def _blob(root: Path, contents: bytes) -> str:
    return _git(root, "hash-object", "-w", "--stdin", data=contents).decode().strip()


def _tree(root: Path, entries: list[tuple[str, str, str, str]]) -> str:
    data = b"".join(
        f"{mode} {kind} {oid}\t{name}".encode() + b"\0" for mode, kind, oid, name in entries
    )
    return _git(root, "mktree", "-z", data=data).decode().strip()


def _commit(root: Path, entries: list[tuple[str, str, str, str]], parent: str | None = None) -> str:
    docs = _tree(root, entries)
    tree = _tree(root, [("040000", "tree", docs, "docs")])
    arguments = ["commit-tree", tree]
    if parent is not None:
        arguments.extend(["-p", parent])
    return _git(root, *arguments, data=b"synthetic documentation fixture\n").decode().strip()


@pytest.fixture
def repository(tmp_path: Path) -> dict[str, Any]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "--quiet")
    blob = _blob(root, CONTENT)
    commit = _commit(root, [("100644", "blob", blob, "contract.md")])
    _git(root, "update-ref", "refs/heads/main", commit)
    _git(root, "symbolic-ref", "HEAD", "refs/heads/main")
    return {"root": root, "commit": commit, "blob": blob}


@pytest.fixture
def checker(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("review_detection_sources", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reference(repository: dict[str, Any], **changes: Any) -> dict[str, Any]:
    reference = {
        "kind": "git",
        "source_commit": repository["commit"],
        "path": "docs/contract.md",
        "git_blob": repository["blob"],
        "locator": "opaque-semantic-location-that-is-not-evaluated",
    }
    reference.update(changes)
    return reference


def _document(reference: Any) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "repository": "synthetic/project",
        "admission_package": "review-detection-admission-v0.1",
        "window": {"t0": None, "t1": None},
        "candidates": [
            {
                "candidate_id": "candidate-a",
                "related_group": None,
                "candidate_commit": None,
                "declared_at": None,
                "entered_at": None,
                "report_fixed_at": None,
                "closed_at": None,
                "refs": dict.fromkeys(
                    (
                        "candidate",
                        "declaration",
                        "related_group",
                        "conditions",
                        "roles",
                        "budget",
                        "report",
                        "closure",
                    )
                )
                | {"candidate": reference},
                "opportunities": [],
            }
        ],
    }


def _candidate_check(report: dict[str, Any]) -> dict[str, Any]:
    return next(
        item
        for item in report["source_checks"]
        if item["input_locator"] == "$.candidates[0].refs.candidate"
    )


def test_real_git_binding_reads_exact_bytes_without_authenticating_locator(
    checker: Any, repository: dict[str, Any]
) -> None:
    reference = _reference(repository)
    report = checker.build_source_checks(repository["root"], _document(reference))
    item = _candidate_check(report)
    assert item == {
        "input_locator": "$.candidates[0].refs.candidate",
        "reported_reference": reference,
        "status": "matched_git_object",
        "reason": "MATCHED_GIT_OBJECT",
        "observed": {
            "git_blob": repository["blob"],
            "mode": "100644",
            "bytes_read": len(CONTENT),
            "content_sha256": hashlib.sha256(CONTENT).hexdigest(),
        },
        "locator_resolution": "not_evaluated",
    }
    assert report["observation_admission"] == "unknown"
    assert report["probability_status"] == "unestimated"
    assert report["execution_allowed"] is False
    assert PRIVATE not in json.dumps(report)


def _opportunity(reference: Any) -> dict[str, Any]:
    return {
        "opportunity_id": "op-a",
        "contract_ref": reference,
        "object_ref": reference,
        "instance_ref": reference,
        "defect_class": "direct_contradiction",
        "truth": "unknown",
        "adjudication_ref": reference,
        "adjudication_fixed_at": None,
        "match": "unknown",
        "matching_ref": reference,
        "matched_at": None,
    }


def _body_command(command: list[str]) -> bool:
    if "cat-file" not in command:
        return False
    arguments = command[command.index("cat-file") + 1 :]
    return not any(item in arguments for item in ("-t", "-s", "--batch-check"))


def _state(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def _cli(
    root: Path, payload: bytes, cwd: Path | None = None, *, resolve_locators: bool = False
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "ascii"
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), str(root)]
        + (["--resolve-locators"] if resolve_locators else []),
        input=payload,
        capture_output=True,
        check=False,
        env=environment,
        cwd=cwd,
        timeout=15,
    )


@pytest.mark.parametrize(
    "changes,reason,status",
    [
        ({"source_commit": "0" * 40}, "GIT_READ_UNAVAILABLE", "unavailable"),
        ({"path": "docs/absent.md"}, "PATH_NOT_IN_TREE", "unavailable"),
        ({"git_blob": "0" * 40}, "GIT_BLOB_MISMATCH", "conflict"),
    ],
)
def test_missing_objects_paths_and_wrong_blobs_preserve_reported_reference(
    checker: Any, repository: dict[str, Any], changes: dict[str, Any], reason: str, status: str
) -> None:
    reference = _reference(repository, **changes)
    item = _candidate_check(checker.build_source_checks(repository["root"], _document(reference)))
    assert (item["reason"], item["status"]) == (reason, status)
    assert item["reported_reference"] == reference
    assert item["observed"]["bytes_read"] is None
    assert item["observed"]["content_sha256"] is None


def test_blob_sha_cannot_be_used_as_source_commit(checker: Any, repository: dict[str, Any]) -> None:
    reference = _reference(repository, source_commit=repository["blob"])
    item = _candidate_check(checker.build_source_checks(repository["root"], _document(reference)))
    assert (item["status"], item["reason"]) == ("conflict", "COMMIT_TYPE_MISMATCH")


def test_wrong_blob_never_reads_either_blob_body(
    checker: Any, repository: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    other = _blob(repository["root"], b"another private blob\n")
    commands: list[list[str]] = []
    native_run = subprocess.run

    def observed_run(command: list[str], **options: Any) -> Any:
        commands.append(command)
        return native_run(command, **options)

    monkeypatch.setattr(subprocess, "run", observed_run)
    reference = _reference(repository, git_blob=other)
    item = _candidate_check(checker.build_source_checks(repository["root"], _document(reference)))
    assert item["reason"] == "GIT_BLOB_MISMATCH"
    assert item["observed"]["git_blob"] == repository["blob"]
    assert not any(_body_command(command) for command in commands)


def test_each_reference_uses_its_own_commit_despite_current_head_and_dirty_worktree(
    checker: Any, repository: dict[str, Any]
) -> None:
    root = repository["root"]
    newer_bytes = b"# Changed contract\n"
    newer_blob = _blob(root, newer_bytes)
    newer_commit = _commit(
        root, [("100644", "blob", newer_blob, "contract.md")], repository["commit"]
    )
    _git(root, "update-ref", "refs/heads/main", newer_commit)
    (root / "docs").mkdir()
    (root / "docs/contract.md").write_bytes(b"uncommitted and different\n")
    old_reference = _reference(repository)
    new_reference = _reference(repository, source_commit=newer_commit, git_blob=newer_blob)
    document = _document(new_reference)
    opportunity = _opportunity(new_reference)
    opportunity["contract_ref"] = old_reference
    document["candidates"][0]["opportunities"] = [opportunity]
    before = _state(root)
    report = checker.build_source_checks(root, document)
    by_location = {item["input_locator"]: item for item in report["source_checks"]}
    contract = by_location["$.candidates[0].opportunities[0].contract_ref"]
    assert contract["status"] == "matched_git_object"
    assert contract["observed"]["content_sha256"] == hashlib.sha256(CONTENT).hexdigest()
    assert (
        _candidate_check(report)["observed"]["content_sha256"]
        == hashlib.sha256(newer_bytes).hexdigest()
    )
    assert _state(root) == before


@pytest.mark.parametrize(
    "mode,kind", [("040000", "tree"), ("120000", "blob"), ("160000", "commit")]
)
def test_nonregular_git_tree_entries_are_not_read_as_documentation(
    checker: Any, repository: dict[str, Any], mode: str, kind: str
) -> None:
    root = repository["root"]
    oid = repository["blob"]
    if kind == "tree":
        oid = _tree(root, [("100644", "blob", oid, "inside.md")])
    elif kind == "commit":
        oid = repository["commit"]
    commit = _commit(root, [(mode, kind, oid, "entry.md")])
    reference = _reference(repository, source_commit=commit, path="docs/entry.md", git_blob=oid)
    item = _candidate_check(checker.build_source_checks(root, _document(reference)))
    assert (item["status"], item["reason"]) == ("not_checked", "NON_REGULAR_GIT_ENTRY")
    assert item["observed"]["mode"] == mode
    assert item["observed"]["bytes_read"] is None


@pytest.mark.parametrize("filename", ["literal*.md", "literal[1].md", ":(glob)*.md", "契约.md"])
def test_literal_special_and_unicode_git_filenames_match_only_the_exact_name(
    checker: Any, repository: dict[str, Any], filename: str
) -> None:
    root = repository["root"]
    commit = _commit(root, [("100755", "blob", repository["blob"], filename)])
    reference = _reference(repository, source_commit=commit, path=f"docs/{filename}")
    item = _candidate_check(checker.build_source_checks(root, _document(reference)))
    assert item["status"] == "matched_git_object"
    assert item["observed"]["mode"] == "100755"


@pytest.mark.parametrize("path", ["docs/*.md", "docs/[c]ontract.md", "docs/:(glob)*.md"])
def test_pathspec_patterns_cannot_select_a_different_existing_file(
    checker: Any, repository: dict[str, Any], path: str
) -> None:
    reference = _reference(repository, path=path)
    item = _candidate_check(checker.build_source_checks(repository["root"], _document(reference)))
    assert item["reason"] == "PATH_NOT_IN_TREE"


@pytest.mark.parametrize("kind", ["null", "pr", "outside"])
def test_null_pr_and_out_of_scope_references_remain_unread(
    checker: Any, repository: dict[str, Any], monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    reference: Any = None
    reason = "REFERENCE_NOT_PROVIDED"
    if kind == "pr":
        reference = {
            "kind": "pr",
            "url": "https://github.com/synthetic/project/pull/3",
            "locator": "opaque",
        }
        reason = "PR_REFERENCE_NOT_READ"
    elif kind == "outside":
        reference = _reference(repository, path="src/private.md")
        reason = "PATH_OUTSIDE_DOCS_SCOPE"
    native_run = subprocess.run
    commands: list[list[str]] = []

    def observed_run(command: list[str], **options: Any) -> Any:
        commands.append(command)
        return native_run(command, **options)

    monkeypatch.setattr(subprocess, "run", observed_run)
    item = _candidate_check(checker.build_source_checks(repository["root"], _document(reference)))
    assert (item["status"], item["reason"]) == ("not_checked", reason)
    assert item["reported_reference"] == reference
    assert not any("cat-file" in command or "ls-tree" in command for command in commands)


@pytest.mark.parametrize("size", [1024 * 1024, 1024 * 1024 + 1])
def test_blob_resource_limit_is_checked_before_any_body_read(
    checker: Any, repository: dict[str, Any], monkeypatch: pytest.MonkeyPatch, size: int
) -> None:
    root = repository["root"]
    contents = b"x" * size
    blob = _blob(root, contents)
    commit = _commit(root, [("100644", "blob", blob, "large.md")])
    commands: list[list[str]] = []
    native_run = subprocess.run

    def observed_run(command: list[str], **options: Any) -> Any:
        commands.append(command)
        return native_run(command, **options)

    monkeypatch.setattr(subprocess, "run", observed_run)
    reference = _reference(repository, source_commit=commit, path="docs/large.md", git_blob=blob)
    item = _candidate_check(checker.build_source_checks(root, _document(reference)))
    if size > 1024 * 1024:
        assert (item["status"], item["reason"]) == ("not_checked", "BLOB_SIZE_LIMIT")
        assert item["observed"]["bytes_read"] is None
        assert not any(_body_command(command) for command in commands)
    else:
        assert item["status"] == "matched_git_object"
        assert item["observed"]["bytes_read"] == size
        assert item["observed"]["content_sha256"] == hashlib.sha256(contents).hexdigest()


def test_inherited_git_redirection_and_replace_refs_cannot_change_original_objects(
    checker: Any, repository: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository["root"]
    other_blob = _blob(root, b"replaced document\n")
    replacement = _commit(root, [("100644", "blob", other_blob, "contract.md")])
    _git(root, "replace", repository["commit"], replacement)
    _git(root, "replace", repository["blob"], other_blob)
    before = _state(root)
    for name in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_COUNT",
        "GIT_INDEX_FILE",
    ):
        monkeypatch.setenv(name, "invalid-private-redirection")
    item = _candidate_check(checker.build_source_checks(root, _document(_reference(repository))))
    assert item["status"] == "matched_git_object"
    assert item["observed"]["content_sha256"] == hashlib.sha256(CONTENT).hexdigest()
    assert _state(root) == before


def test_all_reference_fields_are_returned_and_result_does_not_alias_or_admit_input(
    checker: Any, repository: dict[str, Any]
) -> None:
    reference = _reference(repository)
    document = _document(reference)
    document["candidates"][0]["refs"] = dict.fromkeys(document["candidates"][0]["refs"], reference)
    document["candidates"][0]["opportunities"] = [_opportunity(reference)]
    original = copy.deepcopy(document)
    before = _state(repository["root"])
    report = checker.build_source_checks(repository["root"], document)
    assert document == original
    assert len(report["source_checks"]) == 13
    assert len({item["input_locator"] for item in report["source_checks"]}) == 13
    assert all(item["status"] == "matched_git_object" for item in report["source_checks"])
    assert all(item["locator_resolution"] == "not_evaluated" for item in report["source_checks"])
    assert {item["code"] for item in report["next_source_checks"]} == {
        "VERIFY_ORIGINALS",
        "VERIFY_NATURAL_DOCS_SCOPE",
        "VERIFY_PRIOR_DECLARATION",
        "VERIFY_ROLES_AND_INPUTS",
        "VERIFY_TRUTH_AND_MATCH",
        "VERIFY_BUDGET_AND_CLOSURE",
        "VERIFY_GROUP_CONDITIONS",
    }
    for field in (
        "repository_identity",
        "source_atomicity",
        "source_authenticity",
        "history_completeness",
        "observation_admission",
        "statistical_independence",
        "actual_model_identity",
    ):
        assert report[field] == "unknown"
    assert report["source_assurance"] == "local_git_object_checks"
    assert report["method_status"] == "design_pending"
    assert report["model_score_update_status"] == "not_implemented"
    assert report["permission_effect"] == report["ledger_effect"] == "none"
    assert not {"ready", "n", "k", "score", "detected_rate"}.intersection(report)
    report["source_checks"][0]["reported_reference"]["path"] = "modified"
    report["window"]["t0"] = "modified"
    assert report["source_checks"][1]["reported_reference"] == reference
    assert document == original
    assert _state(repository["root"]) == before


def test_empty_package_creates_no_candidate_or_window(
    checker: Any, repository: dict[str, Any]
) -> None:
    document = _document(None)
    document["candidates"] = []
    report = checker.build_source_checks(repository["root"], document)
    assert report["source_checks"] == []
    assert report["window"] == {"t0": None, "t1": None}
    assert report["next_source_checks"] == [
        {"code": "LOCATE_NATURAL_CANDIDATE", "locator": "$.candidates"}
    ]


@pytest.mark.parametrize("issue", ["body", "size", "read_error"])
def test_reference_level_read_faults_preserve_input_without_partial_authentication(
    checker: Any, repository: dict[str, Any], monkeypatch: pytest.MonkeyPatch, issue: str
) -> None:
    native_run = subprocess.run

    def altered_run(command: list[str], **options: Any) -> Any:
        result = native_run(command, **options)
        if "cat-file" not in command:
            return result
        if issue == "read_error" and "-s" in command:
            raise OSError(PRIVATE)
        if issue == "size" and "-s" in command:
            return subprocess.CompletedProcess(command, 0, stdout=b"999\n", stderr=b"")
        if issue == "body" and _body_command(command):
            return subprocess.CompletedProcess(command, 0, stdout=b"x" * len(CONTENT), stderr=b"")
        return result

    monkeypatch.setattr(subprocess, "run", altered_run)
    reference = _reference(repository)
    item = _candidate_check(checker.build_source_checks(repository["root"], _document(reference)))
    assert item["status"] in {"conflict", "unavailable"}
    assert item["reason"] in {"GIT_OBJECT_HASH_MISMATCH", "GIT_READ_UNAVAILABLE"}
    if issue == "body":
        assert item["reason"] == "GIT_OBJECT_HASH_MISMATCH"
    assert item["reported_reference"] == reference
    assert PRIVATE not in json.dumps(item)


def test_cli_and_real_inprocess_main_bind_bytes_without_writing_or_disclosing_sources(
    checker: Any,
    repository: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    document = _document(_reference(repository))
    payload = (" \n" + json.dumps(document) + "\n").encode()
    expected = checker.build_source_checks(repository["root"], document)
    before = _state(repository["root"])
    result = _cli(repository["root"], payload, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert result.stdout.isascii()
    report = json.loads(result.stdout)
    assert report.pop("input_sha256") == hashlib.sha256(payload).hexdigest()
    assert report.pop("executed_tool_sha256") == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert report == expected
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"))
    assert checker.main([str(repository["root"])]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["source_checks"] == expected["source_checks"]
    assert PRIVATE not in captured.out
    assert _state(repository["root"]) == before
    assert {path.name for path in tmp_path.iterdir()} == {"repository"}


@pytest.mark.parametrize(
    "suffix", ["\u00a0", "\u2003", "\u3000"], ids=["nbsp", "em-space", "ideographic-space"]
)
@pytest.mark.parametrize("resolve_locators", [False, True])
def test_real_git_root_preserves_trailing_unicode_whitespace_at_all_entrypoints(
    checker: Any,
    repository: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    suffix: str,
    resolve_locators: bool,
) -> None:
    root = tmp_path / ("repository" + suffix)
    assert root.parent.resolve() == tmp_path.resolve()
    repository["root"].rename(root)
    repository["root"] = root
    span = b"# Contract\n"
    document = _document(_reference(repository, locator=_line_selector(1, 1, span)))
    original = copy.deepcopy(document)
    payload = (" \n" + json.dumps(document) + "\n").encode()
    before = _state(root)

    expected = checker.build_source_checks(root, document, resolve_locators=resolve_locators)
    item = _candidate_check(expected)
    assert item["status"] == "matched_git_object"
    assert item["observed"] == {
        "git_blob": repository["blob"],
        "mode": "100644",
        "bytes_read": len(CONTENT),
        "content_sha256": hashlib.sha256(CONTENT).hexdigest(),
    }
    assert item["locator_resolution"] == ("matched_span" if resolve_locators else "not_evaluated")
    if resolve_locators:
        assert item["locator_check"] == {
            "status": "matched_span",
            "reason": "MATCHED_LINE_SPAN",
            "observed": {
                "start_line": 1,
                "end_line": 1,
                "byte_start": 0,
                "byte_end": len(span),
                "span_sha256": hashlib.sha256(span).hexdigest(),
            },
        }
    assert expected["window"] == {"t0": None, "t1": None}
    assert expected["observation_admission"] == "unknown"
    assert expected["source_authenticity"] == "unknown"
    assert expected["probability_status"] == "unestimated"
    assert expected["execution_allowed"] is False

    result = _cli(root, payload, cwd=tmp_path, resolve_locators=resolve_locators)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert result.stdout.isascii()
    report = json.loads(result.stdout)
    assert report.pop("input_sha256") == hashlib.sha256(payload).hexdigest()
    assert report.pop("executed_tool_sha256") == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert report == expected

    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"))
    flags = [str(root)] + (["--resolve-locators"] if resolve_locators else [])
    assert checker.main(flags) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == json.loads(result.stdout)
    assert PRIVATE not in captured.out
    assert document == original
    assert _state(root) == before
    assert {path.name for path in tmp_path.iterdir()} == {root.name}


@pytest.mark.parametrize(
    "payload",
    [
        b"\xffprivate",
        b"not JSON",
        b"null",
        b"[]",
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"schema_version":"1.0","schema_version":"1.0"}',
    ],
)
def test_invalid_cli_input_has_one_safe_error_and_no_partial_report(
    repository: dict[str, Any], payload: bytes
) -> None:
    result = _cli(repository["root"], payload)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.decode().strip() == ERROR


@pytest.mark.parametrize("issue", ["extra", "escape", "unknown_kind", "duplicate_key"])
def test_invalid_nested_declarations_are_not_accepted_by_source_checker(
    repository: dict[str, Any], issue: str
) -> None:
    document = _document(_reference(repository))
    reference = document["candidates"][0]["refs"]["candidate"]
    if issue == "extra":
        reference["extra"] = PRIVATE
    elif issue == "escape":
        reference["path"] = "docs/../private.md"
    elif issue == "unknown_kind":
        reference["kind"] = "file"
    payload = json.dumps(document).encode()
    if issue == "duplicate_key":
        payload = payload.replace(
            b'"git_blob": ', b'"git_blob": "' + b"0" * 40 + b'", "git_blob": ', 1
        )
    result = _cli(repository["root"], payload)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.decode().strip() == ERROR


@pytest.mark.parametrize("kind", ["nested", "missing", "file", "bare"])
def test_invalid_repository_roots_are_rejected_without_path_or_error_disclosure(
    repository: dict[str, Any], tmp_path: Path, kind: str
) -> None:
    target = repository["root"] / PRIVATE
    if kind == "nested":
        target.mkdir()
    elif kind == "file":
        target.write_bytes(b"not a repository")
    elif kind == "bare":
        target = tmp_path / PRIVATE
        target.mkdir()
        _git(target, "init", "--bare", "--quiet")
    result = _cli(target, json.dumps(_document(None)).encode())
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.decode().strip() == ERROR


@pytest.mark.parametrize("resolve_locators", [False, True])
def test_cyclic_repository_root_has_only_the_safe_cli_error(
    tmp_path: Path, resolve_locators: bool
) -> None:
    root = tmp_path / PRIVATE
    try:
        root.symlink_to(root.name, target_is_directory=True)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"directory symlinks are unavailable: {type(error).__name__}")
    try:
        result = _cli(root, json.dumps(_document(None)).encode(), resolve_locators=resolve_locators)
    finally:
        root.unlink()
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.decode().strip() == ERROR
    assert PRIVATE.encode() not in result.stderr
    assert b"Traceback" not in result.stderr


@pytest.mark.parametrize("failed_resolution", [1, 2], ids=["supplied-root", "git-root"])
@pytest.mark.parametrize("resolve_locators", [False, True])
def test_both_repository_resolution_failures_are_safe_at_library_and_cli_boundaries(
    checker: Any,
    repository: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failed_resolution: int,
    resolve_locators: bool,
) -> None:
    root = repository["root"]
    document = _document(None)
    native_resolve = Path.resolve
    resolution_calls = 0

    def failed_resolve(path: Path, *arguments: Any, **options: Any) -> Path:
        nonlocal resolution_calls
        if path == root:
            resolution_calls += 1
            if resolution_calls == failed_resolution:
                raise RuntimeError(PRIVATE)
        return native_resolve(path, *arguments, **options)

    monkeypatch.setattr(Path, "resolve", failed_resolve)
    with pytest.raises(ValueError) as error:
        checker.build_source_checks(root, document, resolve_locators=resolve_locators)
    assert PRIVATE not in str(error.value)
    assert resolution_calls == failed_resolution

    resolution_calls = 0
    monkeypatch.setattr(
        sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(document).encode()), encoding="utf-8")
    )
    flags = [str(root)] + (["--resolve-locators"] if resolve_locators else [])
    assert checker.main(flags) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == ERROR
    assert PRIVATE not in captured.err
    assert "Traceback" not in captured.err
    assert resolution_calls == failed_resolution


def test_actual_git_calls_are_isolated_local_read_only_and_bounded(
    checker: Any, repository: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    native_run = subprocess.run
    commands: list[list[str]] = []
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_CONFIG_COUNT"):
        monkeypatch.setenv(name, PRIVATE)

    def inspected_run(command: list[str], **options: Any) -> Any:
        commands.append(command)
        assert "--no-replace-objects" in command
        assert "--no-pager" in command
        assert options["timeout"] == 30
        environment = options["env"]
        assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
        assert environment["GIT_CONFIG_SYSTEM"] == os.devnull
        assert environment["GIT_NO_LAZY_FETCH"] == "1"
        assert environment["GIT_ALLOW_PROTOCOL"] == ""
        assert environment["GIT_TERMINAL_PROMPT"] == "0"
        assert environment["GIT_OPTIONAL_LOCKS"] == "0"
        assert not any(
            name in environment
            for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_CONFIG_COUNT")
        )
        assert any(name in command for name in ("rev-parse", "cat-file", "ls-tree"))
        return native_run(command, **options)

    monkeypatch.setattr(subprocess, "run", inspected_run)
    document = _document(_reference(repository))
    document["candidates"][0]["refs"]["report"] = _reference(repository, source_commit="0" * 40)
    before = _state(repository["root"])
    report = checker.build_source_checks(repository["root"], document)
    assert _candidate_check(report)["status"] == "matched_git_object"
    missing = next(
        item
        for item in report["source_checks"]
        if item["input_locator"] == "$.candidates[0].refs.report"
    )
    assert missing["reason"] == "GIT_READ_UNAVAILABLE"
    assert _state(repository["root"]) == before
    assert commands


@pytest.mark.parametrize(
    "issue",
    ["multiple_entries", "other_path", "bad_oid", "missing_nul", "bad_size", "negative_size"],
)
def test_malformed_git_metadata_does_not_certify_a_reference(
    checker: Any, repository: dict[str, Any], monkeypatch: pytest.MonkeyPatch, issue: str
) -> None:
    native_run = subprocess.run

    def altered_run(command: list[str], **options: Any) -> Any:
        result = native_run(command, **options)
        output = result.stdout
        if "ls-tree" in command:
            if issue == "multiple_entries":
                output += output
            elif issue == "other_path":
                output = output.replace(b"docs/contract.md", b"docs/other.md")
            elif issue == "bad_oid":
                output = output.replace(repository["blob"].encode(), b"invalid")
            elif issue == "missing_nul":
                output = output.rstrip(b"\0")
        elif "cat-file" in command and "-s" in command:
            if issue == "bad_size":
                output = b"not a number\n"
            elif issue == "negative_size":
                output = b"-1\n"
        return subprocess.CompletedProcess(
            command, result.returncode, stdout=output, stderr=result.stderr
        )

    monkeypatch.setattr(subprocess, "run", altered_run)
    item = _candidate_check(
        checker.build_source_checks(repository["root"], _document(_reference(repository)))
    )
    assert (item["status"], item["reason"]) == ("unavailable", "GIT_READ_UNAVAILABLE")


@pytest.mark.parametrize("issue", ["json", "root", "nested", "stdin", "script"])
def test_real_main_error_path_never_exposes_input_or_underlying_failure(
    checker: Any,
    repository: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    issue: str,
) -> None:
    payload = json.dumps(_document(_reference(repository))).encode()
    root = repository["root"]
    if issue == "json":
        payload = PRIVATE.encode()
    elif issue == "root":
        root = root / PRIVATE
    elif issue == "nested":
        root = root / "nested"
        root.mkdir()
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"))
    if issue == "stdin":

        class BrokenInput:
            @property
            def buffer(self) -> Any:
                raise OSError(PRIVATE)

        monkeypatch.setattr(sys, "stdin", BrokenInput())
    elif issue == "script":
        native_read = Path.read_bytes

        def failed_read(path: Path) -> bytes:
            if path == SCRIPT:
                raise OSError(PRIVATE)
            return native_read(path)

        monkeypatch.setattr(Path, "read_bytes", failed_read)
    assert checker.main([str(root)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == ERROR


def test_script_main_guard_executes_real_cli_entry_in_process(
    checker: Any,
    repository: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = json.dumps(_document(_reference(repository))).encode()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(repository["root"])])
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"))
    with pytest.raises(SystemExit) as exited:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exited.value.code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert _candidate_check(json.loads(captured.out))["status"] == "matched_git_object"


def test_opt_in_locator_matches_real_git_line_bytes(
    checker: Any, repository: dict[str, Any]
) -> None:
    span = b"# Contract\n"
    reference = _reference(
        repository, locator=f"lines-v1:L1-L1:sha256={hashlib.sha256(span).hexdigest()}"
    )
    report = checker.build_source_checks(
        repository["root"], _document(reference), resolve_locators=True
    )
    assert report["schema_version"] == "2.0"
    assert report["measurement"] == "review_detection_git_locator_checks"
    item = _candidate_check(report)
    assert item["locator_resolution"] == "matched_span"
    assert item["locator_check"] == {
        "status": "matched_span",
        "reason": "MATCHED_LINE_SPAN",
        "observed": {
            "start_line": 1,
            "end_line": 1,
            "byte_start": 0,
            "byte_end": len(span),
            "span_sha256": hashlib.sha256(span).hexdigest(),
        },
    }


def _committed_reference(
    repository: dict[str, Any], contents: bytes, locator: str
) -> dict[str, Any]:
    root = repository["root"]
    blob = _blob(root, contents)
    commit = _commit(root, [("100644", "blob", blob, "contract.md")])
    return _reference(repository, source_commit=commit, git_blob=blob, locator=locator)


def _line_selector(start: int, end: int, span: bytes) -> str:
    return f"lines-v1:L{start}-L{end}:sha256={hashlib.sha256(span).hexdigest()}"


def _unlocated(status: str, reason: str) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "observed": dict.fromkeys(
            ("start_line", "end_line", "byte_start", "byte_end", "span_sha256")
        ),
    }


@pytest.mark.parametrize(
    "contents,start,end,byte_start,byte_end,span",
    [
        (b"alpha\nbeta\n", 2, 2, 6, 11, b"beta\n"),
        (b"alpha\nbeta", 2, 2, 6, 10, b"beta"),
        (b"alpha\r\nbeta\r\n", 1, 2, 0, 13, b"alpha\r\nbeta\r\n"),
        (b"alpha\r\nbeta", 2, 2, 7, 11, b"beta"),
        (b"one\rtwo\nlast", 1, 1, 0, 8, b"one\rtwo\n"),
        (b"\n", 1, 1, 0, 1, b"\n"),
        (b"\n\n", 2, 2, 1, 2, b"\n"),
        (b"first\n\nlast\n", 2, 3, 6, 12, b"\nlast\n"),
        (b"same\nsame\nlast", 2, 2, 5, 10, b"same\n"),
        ("契约\n实例".encode(), 2, 2, 7, 13, "实例".encode()),
        (
            "a\u0085b\u2028c\u2029d\ve\ff\r\nlast".encode(),
            2,
            2,
            18,
            22,
            b"last",
        ),
    ],
)
def test_locator_uses_raw_lf_byte_boundaries_only(
    checker: Any,
    repository: dict[str, Any],
    contents: bytes,
    start: int,
    end: int,
    byte_start: int,
    byte_end: int,
    span: bytes,
) -> None:
    reference = _committed_reference(repository, contents, _line_selector(start, end, span))
    item = _candidate_check(
        checker.build_source_checks(repository["root"], _document(reference), resolve_locators=True)
    )
    assert item["status"] == "matched_git_object"
    assert item["locator_resolution"] == "matched_span"
    assert item["locator_check"] == {
        "status": "matched_span",
        "reason": "MATCHED_LINE_SPAN",
        "observed": {
            "start_line": start,
            "end_line": end,
            "byte_start": byte_start,
            "byte_end": byte_end,
            "span_sha256": hashlib.sha256(span).hexdigest(),
        },
    }


@pytest.mark.parametrize(
    "selector",
    [
        "lines-v1:",
        "lines-v1:L0-L1:sha256=" + "0" * 64,
        "lines-v1:L01-L1:sha256=" + "0" * 64,
        "lines-v1:L1-L01:sha256=" + "0" * 64,
        "lines-v1:L2-L1:sha256=" + "0" * 64,
        "lines-v1:L+1-L1:sha256=" + "0" * 64,
        "lines-v1:L-1-L1:sha256=" + "0" * 64,
        "lines-v1:L١-L١:sha256=" + "0" * 64,
        "lines-v1:L１-L１:sha256=" + "0" * 64,
        "lines-v1:L1-L1:SHA256=" + "0" * 64,
        "lines-v1:L1-L1:sha256=" + "A" * 64,
        "lines-v1:L1-L1:sha256=" + "a" * 63,
        "lines-v1:L1-L1:sha256=" + "a" * 65,
        "lines-v1:L1-L1:sha256=" + "a" * 64 + "\n",
        "lines-v1: L1-L1:sha256=" + "0" * 64,
        "lines-v1:L" + "9" * 5000 + "-L" + "9" * 5000 + ":sha256=" + "0" * 64,
    ],
    ids=[
        "empty",
        "zero",
        "leading-zero-start",
        "leading-zero-end",
        "reverse",
        "plus",
        "negative",
        "arabic-digits",
        "fullwidth-digits",
        "hash-key",
        "uppercase-hash",
        "short-hash",
        "long-hash",
        "trailing-newline",
        "space",
        "huge-digits",
    ],
)
def test_recognized_invalid_selector_never_guesses_a_span(
    checker: Any, repository: dict[str, Any], selector: str
) -> None:
    reference = _reference(repository, locator=selector)
    item = _candidate_check(
        checker.build_source_checks(repository["root"], _document(reference), resolve_locators=True)
    )
    assert item["status"] == "matched_git_object"
    assert item["locator_resolution"] == "invalid_selector"
    assert item["locator_check"] == _unlocated("invalid_selector", "INVALID_LINE_SELECTOR")


@pytest.mark.parametrize(
    "contents,start,end,status,reason",
    [
        (b"", 1, 1, "invalid_selector", "INVALID_LINE_SELECTOR"),
        (b"abc", 1, 4, "invalid_selector", "INVALID_LINE_SELECTOR"),
        (b"abc", 4, 4, "invalid_selector", "INVALID_LINE_SELECTOR"),
        (b"abc", 1, 3, "span_unavailable", "LINE_RANGE_NOT_PRESENT"),
        (b"abc", 2, 2, "span_unavailable", "LINE_RANGE_NOT_PRESENT"),
        (b"abc\n", 2, 2, "span_unavailable", "LINE_RANGE_NOT_PRESENT"),
        (b"one\rtwo", 2, 2, "span_unavailable", "LINE_RANGE_NOT_PRESENT"),
    ],
)
def test_locator_distinguishes_byte_bound_from_missing_lines_without_clipping(
    checker: Any,
    repository: dict[str, Any],
    contents: bytes,
    start: int,
    end: int,
    status: str,
    reason: str,
) -> None:
    reference = _committed_reference(repository, contents, _line_selector(start, end, contents))
    item = _candidate_check(
        checker.build_source_checks(repository["root"], _document(reference), resolve_locators=True)
    )
    assert item["status"] == "matched_git_object"
    assert item["locator_resolution"] == status
    assert item["locator_check"] == _unlocated(status, reason)


@pytest.mark.parametrize("contents", [b"safe\n\xff", b"safe\n\xc0\xaf", b"safe\n\x00"])
def test_entire_blob_must_be_strict_utf8_without_nul_before_selecting_valid_ascii_line(
    checker: Any, repository: dict[str, Any], contents: bytes
) -> None:
    reference = _committed_reference(repository, contents, _line_selector(1, 1, b"safe\n"))
    item = _candidate_check(
        checker.build_source_checks(repository["root"], _document(reference), resolve_locators=True)
    )
    assert item["status"] == "matched_git_object"
    assert item["observed"]["content_sha256"] == hashlib.sha256(contents).hexdigest()
    assert item["locator_resolution"] == "not_evaluated"
    assert item["locator_check"] == _unlocated("not_evaluated", "DOCUMENT_ENCODING_UNSUPPORTED")


@pytest.mark.parametrize("locator", ["opaque", "lines-v2:L1-L1:sha256=" + "0" * 64])
def test_unsupported_locator_is_not_interpreted_as_an_anchor(
    checker: Any, repository: dict[str, Any], locator: str
) -> None:
    reference = _reference(repository, locator=locator)
    item = _candidate_check(
        checker.build_source_checks(repository["root"], _document(reference), resolve_locators=True)
    )
    assert item["status"] == "matched_git_object"
    assert item["locator_check"] == _unlocated("not_evaluated", "UNSUPPORTED_LOCATOR")
    assert item["locator_resolution"] == "not_evaluated"


def test_same_git_object_is_read_once_but_each_locator_retains_its_own_result(
    checker: Any, repository: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _reference(repository, locator=_line_selector(1, 1, b"# Contract\n"))
    second = _reference(repository, locator=_line_selector(2, 2, b"\n"))
    conflict = _reference(repository, locator=_line_selector(1, 1, b"other\n"))
    document = _document(first)
    document["candidates"][0]["refs"].update(report=second, closure=conflict)
    document["candidates"][0]["opportunities"] = [_opportunity(first)]
    original = copy.deepcopy(document)
    commands: list[list[str]] = []
    native_run = subprocess.run

    def observed_run(command: list[str], **options: Any) -> Any:
        commands.append(command)
        return native_run(command, **options)

    monkeypatch.setattr(subprocess, "run", observed_run)
    before = _state(repository["root"])
    report = checker.build_source_checks(repository["root"], document, resolve_locators=True)
    by_location = {item["input_locator"]: item for item in report["source_checks"]}
    matched = _candidate_check(report)
    assert matched["locator_check"]["status"] == "matched_span"
    blank = by_location["$.candidates[0].refs.report"]
    assert blank["locator_check"]["observed"] == {
        "start_line": 2,
        "end_line": 2,
        "byte_start": 11,
        "byte_end": 12,
        "span_sha256": hashlib.sha256(b"\n").hexdigest(),
    }
    wrong = by_location["$.candidates[0].refs.closure"]
    assert wrong["locator_check"] == {
        **matched["locator_check"],
        "status": "conflict",
        "reason": "SPAN_HASH_MISMATCH",
    }
    assert wrong["locator_resolution"] == "conflict"
    assert wrong["reported_reference"] == conflict
    assert sum(_body_command(command) for command in commands) == 1
    matched["locator_check"]["observed"]["byte_start"] = 99
    other = by_location["$.candidates[0].opportunities[0].contract_ref"]
    assert other["locator_check"]["observed"]["byte_start"] == 0
    assert document == original
    assert _state(repository["root"]) == before


def test_locator_uses_declared_version_even_when_head_and_worktree_have_matching_other_text(
    checker: Any, repository: dict[str, Any]
) -> None:
    root = repository["root"]
    old_span = b"# Contract\n"
    new_span = b"# Changed\n"
    old_reference = _reference(repository, locator=_line_selector(1, 1, old_span))
    new_reference = _committed_reference(repository, new_span, _line_selector(1, 1, new_span))
    _git(root, "update-ref", "refs/heads/main", new_reference["source_commit"])
    (root / "docs").mkdir()
    (root / "docs/contract.md").write_bytes(b"dirty worktree\n")
    document = _document(new_reference)
    opportunity = _opportunity(old_reference)
    document["candidates"][0]["opportunities"] = [opportunity]
    before = _state(root)
    report = checker.build_source_checks(root, document, resolve_locators=True)
    by_location = {item["input_locator"]: item for item in report["source_checks"]}
    assert (
        _candidate_check(report)["locator_check"]["observed"]["span_sha256"]
        == hashlib.sha256(new_span).hexdigest()
    )
    original = by_location["$.candidates[0].opportunities[0].contract_ref"]
    assert (
        original["locator_check"]["observed"]["span_sha256"] == hashlib.sha256(old_span).hexdigest()
    )
    assert original["locator_resolution"] == "matched_span"
    assert _state(root) == before


@pytest.mark.parametrize(
    "kind", ["null", "pr", "outside", "wrong_blob", "missing_commit", "missing_path", "large"]
)
def test_locator_cannot_bypass_source_gate_or_add_object_reads(
    checker: Any, repository: dict[str, Any], monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    reference: Any = _reference(repository, locator="lines-v1:invalid")
    if kind == "null":
        reference = None
    elif kind == "pr":
        reference = {
            "kind": "pr",
            "url": "https://github.com/synthetic/project/pull/3",
            "locator": "lines-v1:invalid",
        }
    elif kind == "outside":
        reference["path"] = "src/private.md"
    elif kind == "wrong_blob":
        reference["git_blob"] = "0" * 40
    elif kind == "missing_commit":
        reference["source_commit"] = "0" * 40
    elif kind == "missing_path":
        reference["path"] = "docs/absent.md"
    else:
        reference = _committed_reference(repository, b"x" * (1024 * 1024 + 1), "lines-v1:invalid")
    commands: list[list[str]] = []
    native_run = subprocess.run

    def observed_run(command: list[str], **options: Any) -> Any:
        commands.append(command)
        return native_run(command, **options)

    monkeypatch.setattr(subprocess, "run", observed_run)
    document = _document(reference)
    default = checker.build_source_checks(repository["root"], document)
    default_commands = commands.copy()
    commands.clear()
    resolved = checker.build_source_checks(repository["root"], document, resolve_locators=True)
    item = _candidate_check(resolved)
    assert item["locator_check"] == _unlocated("not_evaluated", "SOURCE_NOT_MATCHED")
    assert item["locator_resolution"] == "not_evaluated"
    assert item["status"] != "matched_git_object"
    assert item["reported_reference"] == reference
    assert commands == default_commands
    assert not any(_body_command(command) for command in commands)
    assert {
        key: value for key, value in item.items() if key != "locator_check"
    } == _candidate_check(default)


def test_mismatched_source_bytes_never_resolve_a_locator(
    checker: Any, repository: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    native_run = subprocess.run

    def corrupted_run(command: list[str], **options: Any) -> Any:
        result = native_run(command, **options)
        if _body_command(command):
            return subprocess.CompletedProcess(command, 0, stdout=b"x" * len(CONTENT), stderr=b"")
        return result

    monkeypatch.setattr(subprocess, "run", corrupted_run)
    reference = _reference(repository, locator=_line_selector(1, 1, b"x" * len(CONTENT)))
    item = _candidate_check(
        checker.build_source_checks(repository["root"], _document(reference), resolve_locators=True)
    )
    assert item["reason"] == "GIT_OBJECT_HASH_MISMATCH"
    assert item["locator_check"] == _unlocated("not_evaluated", "SOURCE_NOT_MATCHED")


def test_opt_in_only_adds_locator_evidence_and_does_not_admit_or_mutate_input(
    checker: Any, repository: dict[str, Any]
) -> None:
    reference = _reference(repository, locator=_line_selector(3, 3, (PRIVATE + "\n").encode()))
    document = _document(reference)
    document["candidates"][0]["opportunities"] = [_opportunity(reference)]
    original = copy.deepcopy(document)
    before = _state(repository["root"])
    default = checker.build_source_checks(repository["root"], document)
    assert (
        checker.build_source_checks(repository["root"], document, resolve_locators=False) == default
    )
    resolved = checker.build_source_checks(repository["root"], document, resolve_locators=True)
    assert PRIVATE not in json.dumps(resolved)
    assert resolved["window"] == {"t0": None, "t1": None}
    assert resolved["observation_admission"] == "unknown"
    assert resolved["source_authenticity"] == "unknown"
    assert resolved["execution_allowed"] is False
    assert resolved["next_source_checks"] == default["next_source_checks"]
    assert resolved["schema_version"] == "2.0"
    assert resolved["measurement"] == "review_detection_git_locator_checks"
    resolved["schema_version"] = "1.0"
    resolved["measurement"] = "review_detection_git_source_checks"
    for item in resolved["source_checks"]:
        item.pop("locator_check")
        item["locator_resolution"] = "not_evaluated"
    assert resolved == default
    assert document == original
    assert _state(repository["root"]) == before


@pytest.mark.parametrize("conflict", [False, True])
def test_opt_in_real_cli_and_inprocess_main_keep_conflicts_as_reports(
    checker: Any,
    repository: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    conflict: bool,
) -> None:
    span = b"different\n" if conflict else b"# Contract\n"
    reference = _reference(repository, locator=_line_selector(1, 1, span))
    document = _document(reference)
    payload = (" \n" + json.dumps(document) + "\n").encode()
    expected = checker.build_source_checks(repository["root"], document, resolve_locators=True)
    before = _state(repository["root"])
    result = _cli(repository["root"], payload, cwd=tmp_path, resolve_locators=True)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert result.stdout.isascii()
    report = json.loads(result.stdout)
    assert report.pop("input_sha256") == hashlib.sha256(payload).hexdigest()
    assert report.pop("executed_tool_sha256") == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert report == expected
    assert _candidate_check(report)["locator_resolution"] == (
        "conflict" if conflict else "matched_span"
    )
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"))
    assert checker.main([str(repository["root"]), "--resolve-locators"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["source_checks"] == expected["source_checks"]
    assert PRIVATE not in captured.out
    assert _state(repository["root"]) == before
    assert {path.name for path in tmp_path.iterdir()} == {"repository"}


@pytest.mark.parametrize("issue", ["input", "root"])
def test_opt_in_cli_still_rejects_invalid_input_or_root_without_partial_report(
    repository: dict[str, Any], issue: str
) -> None:
    root = repository["root"]
    payload = json.dumps(_document(_reference(repository))).encode()
    if issue == "input":
        payload = b"not JSON"
    else:
        root = root / PRIVATE
    result = _cli(root, payload, resolve_locators=True)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.decode().strip() == ERROR
