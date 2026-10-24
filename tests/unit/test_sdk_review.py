"""Offline counterexamples for the opt-in fixed-document SDK review client."""

from __future__ import annotations

import builtins
import copy
import hashlib
import importlib
import importlib.metadata
import json
import subprocess
import threading
import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from aiflow import sdk_review


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return result.stdout.rstrip("\r\n")


def commit(repository: Path, message: str) -> str:
    git(repository, "add", ".")
    git(
        repository,
        "-c",
        "user.name=SDK Review Tests",
        "-c",
        "user.email=sdk-review@example.invalid",
        "commit",
        "-m",
        message,
    )
    return git(repository, "rev-parse", "HEAD")


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-b", "main")
    (root / "docs").mkdir()
    (root / ".gitignore").write_text("/build/\n", encoding="utf-8")
    (root / "docs/candidate.md").write_text(
        "# Contract\n\nOriginal requirement.\n", encoding="utf-8"
    )
    (root / "docs/reference.md").write_text("# Existing contract\n\nRead only.\n", encoding="utf-8")
    reference = commit(root, "docs: existing requirements")
    (root / "docs/candidate.md").write_text(
        "# Contract\n\nUpdated requirement.\n", encoding="utf-8"
    )
    candidate = commit(root, "docs: naturally required contract revision")
    return root, candidate, reference


def request(fixture: tuple[Path, str, str], **changes: Any) -> dict[str, Any]:
    root, candidate, reference = fixture
    values: dict[str, Any] = {
        "root": root,
        "candidate": candidate,
        "reference": reference,
        "documents": ["docs/candidate.md"],
        "reference_documents": ["docs/reference.md"],
        "question": "Does the candidate contradict the declared read-only contract?",
    }
    values.update(changes)
    return sdk_review.prepare_request(**values)


def report(**changes: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "outcome": "APPROVE",
        "summary": "No contradiction found.",
        "findings": [],
    }
    value.update(changes)
    return value


def finding(**changes: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "finding_id": "RF-001",
        "severity": "medium",
        "title": "The candidate conflicts with the existing requirement",
        "path": "docs/candidate.md",
        "line": 3,
        "evidence": "Candidate line 3 permits an action prohibited by the reference.",
    }
    value.update(changes)
    return value


def arguments(fixture: tuple[Path, str, str], output: Path, *, execute: bool = False) -> list[str]:
    _root, candidate, reference = fixture
    values = [
        "--candidate",
        candidate,
        "--reference",
        reference,
        "--document",
        "docs/candidate.md",
        "--reference-document",
        "docs/reference.md",
        "--question",
        "Check the read-only requirement against the reference.",
        "--output",
        str(output),
    ]
    if execute:
        values.append("--execute")
    return values


def runtime_result(raw: str | None = None, *, status: str = "completed") -> dict[str, Any]:
    return {
        "status": status,
        "report": json.dumps(report()) if raw is None else raw,
        "runtime_version": "0.163.0",
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "actual_model_identity": "unknown",
        "settled_cost": "unknown",
    }


def test_request_reads_fixed_blobs_and_hashes_the_supplied_prompt(
    repository: tuple[Path, str, str],
) -> None:
    root, candidate, reference = repository
    (root / "docs/candidate.md").write_text("UNCOMMITTED PRIVATE REPLACEMENT\n", encoding="utf-8")
    before = (root / "docs/candidate.md").read_bytes()

    prepared = request(repository)

    assert prepared["candidate"] == candidate
    assert prepared["reference"] == reference
    assert (
        prepared["input_sha256"] == hashlib.sha256(prepared["prompt"].encode("utf-8")).hexdigest()
    )
    assert len(prepared["documents"]) == 2
    selected = next(value for value in prepared["documents"] if value["role"] == "candidate")
    expected = git(root, "show", f"{candidate}:docs/candidate.md") + "\n"
    assert selected["path"] == "docs/candidate.md"
    assert selected["content"] == expected
    assert selected["blob"] == git(root, "rev-parse", f"{candidate}:docs/candidate.md")
    assert selected["bytes"] == len(expected.encode("utf-8"))
    assert selected["sha256"] == hashlib.sha256(expected.encode("utf-8")).hexdigest()
    assert selected["lines"] == 3
    assert expected in prepared["prompt"]
    assert prepared["question"] in prepared["prompt"]
    assert "UNCOMMITTED PRIVATE REPLACEMENT" not in json.dumps(prepared)
    assert str(root) not in json.dumps(prepared["manifest"])
    assert (root / "docs/candidate.md").read_bytes() == before
    assert not (root / "build").exists()


def test_same_path_at_distinct_commits_is_not_a_duplicate_selection(
    repository: tuple[Path, str, str],
) -> None:
    prepared = request(repository, reference_documents=["docs/candidate.md"])
    assert {value["role"] for value in prepared["documents"]} == {"candidate", "reference"}
    assert len({value["blob"] for value in prepared["documents"]}) == 2


@pytest.mark.parametrize("value", ["HEAD", "a" * 12, "A" * 40, "0" * 40])
@pytest.mark.parametrize("field", ["candidate", "reference"])
def test_request_requires_available_complete_commits(
    repository: tuple[Path, str, str], value: str, field: str
) -> None:
    with pytest.raises(ValueError):
        request(repository, **{field: value})


@pytest.mark.parametrize(
    "path",
    [
        "../docs/candidate.md",
        "/docs/candidate.md",
        "C:/docs/candidate.md",
        "docs\\candidate.md",
        "README.md",
        "docs/../docs/candidate.md",
        "docs//candidate.md",
        "docs/missing.md",
    ],
)
def test_request_rejects_unsafe_or_unavailable_document_paths(
    repository: tuple[Path, str, str], path: str
) -> None:
    with pytest.raises(ValueError):
        request(repository, documents=[path])


@pytest.mark.parametrize("field", ["documents", "reference_documents"])
def test_request_rejects_duplicate_selections(
    repository: tuple[Path, str, str], field: str
) -> None:
    path = "docs/candidate.md" if field == "documents" else "docs/reference.md"
    with pytest.raises(ValueError):
        request(repository, **{field: [path, path]})


@pytest.mark.parametrize("change", [{"documents": []}, {"question": "  "}])
def test_request_requires_a_candidate_document_and_a_real_question(
    repository: tuple[Path, str, str], change: dict[str, Any]
) -> None:
    with pytest.raises(ValueError):
        request(repository, **change)


def test_request_rejects_symlink_git_entries_without_needing_windows_symlink_privileges(
    repository: tuple[Path, str, str],
) -> None:
    root, _candidate, _reference = repository
    blob = (
        subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=root,
            input=b"candidate.md",
            capture_output=True,
            check=True,
            timeout=10,
        )
        .stdout.decode("ascii")
        .strip()
    )
    git(root, "update-index", "--add", "--cacheinfo", f"120000,{blob},docs/link.md")
    git(
        root,
        "-c",
        "user.name=SDK Review Tests",
        "-c",
        "user.email=sdk-review@example.invalid",
        "commit",
        "-m",
        "docs: represent a symlink entry",
    )
    with pytest.raises(ValueError):
        request(repository, candidate=git(root, "rev-parse", "HEAD"), documents=["docs/link.md"])


@pytest.mark.parametrize(
    "contents", [b"\xff", b"x" * 70_000], ids=["invalid-utf8", "too-many-bytes"]
)
def test_request_rejects_invalid_utf8_and_excess_input_bytes(
    repository: tuple[Path, str, str], contents: bytes
) -> None:
    root, _candidate, _reference = repository
    (root / "docs/candidate.md").write_bytes(contents)
    candidate = commit(root, "docs: invalid review material")
    with pytest.raises(ValueError):
        request(repository, candidate=candidate)


def test_report_accepts_a_valid_candidate_location(repository: tuple[Path, str, str]) -> None:
    expected = report(outcome="REQUEST_CHANGES", findings=[finding()])
    assert sdk_review.validate_report(json.dumps(expected), request(repository)) == expected
    assert sdk_review.validate_report(json.dumps(report()), request(repository)) == report()


@pytest.mark.parametrize(
    "change",
    [
        {"finding_id": "invented"},
        {"severity": "unknown"},
        {"title": " "},
        {"path": "docs/reference.md"},
        {"path": "../docs/candidate.md"},
        {"line": 0},
        {"line": 4},
        {"line": True},
        {"line": 1.0},
        {"evidence": " "},
    ],
)
def test_report_rejects_invalid_or_unsupplied_locations_and_finding_facts(
    repository: tuple[Path, str, str], change: dict[str, Any]
) -> None:
    with pytest.raises(ValueError):
        sdk_review.validate_report(
            json.dumps(report(outcome="REQUEST_CHANGES", findings=[finding(**change)])),
            request(repository),
        )


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "[]",
        '{"outcome":"APPROVE","outcome":"REQUEST_CHANGES","summary":"s","findings":[]}',
        json.dumps({"outcome": "APPROVE", "summary": "s"}),
        json.dumps(report(unexpected="private")),
        json.dumps(report(outcome="unknown")),
        json.dumps(report(summary=" ")),
        json.dumps(report(summary="x" * 70_000)),
        json.dumps(report(findings=[finding(), finding()])),
        json.dumps(report(findings=[finding(finding_id=f"RF-{index:03d}") for index in range(21)])),
        json.dumps(report(findings=[finding()])),
        json.dumps(report(outcome="REQUEST_CHANGES")),
    ],
    ids=[
        "not-json",
        "not-object",
        "duplicate-key",
        "missing-field",
        "unknown-field",
        "unknown-outcome",
        "empty-summary",
        "too-many-bytes",
        "duplicate-finding",
        "too-many-findings",
        "approve-with-finding",
        "change-without-finding",
    ],
)
def test_report_rejects_invalid_shape_duplicate_ids_and_excess_output(
    repository: tuple[Path, str, str], raw: str
) -> None:
    with pytest.raises(ValueError):
        sdk_review.validate_report(raw, request(repository))


def test_preview_does_not_import_sdk_start_runtime_or_create_output(
    repository: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _candidate, _reference = repository
    monkeypatch.chdir(root)
    output = root / "build/review-preview"
    original_import = builtins.__import__
    original_run = subprocess.run
    commands: list[list[str]] = []

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        assert not name.startswith(("codex", "openai_codex")), "preview imported the SDK"
        return original_import(name, *args, **kwargs)

    def guarded_run(command: list[str], **kwargs: Any) -> Any:
        commands.append(command)
        assert command[0] == "git", "preview started a non-Git subprocess"
        return original_run(command, **kwargs)

    def forbidden_sdk(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("preview called the SDK runner")

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(subprocess, "run", guarded_run)
    monkeypatch.setattr(sdk_review, "_run_sdk", forbidden_sdk)

    assert sdk_review.main(arguments(repository, output)) == 0
    assert commands
    assert not output.exists()
    assert not output.parent.exists()
    assert not capsys.readouterr().err


def test_execute_records_started_before_the_only_runtime_call_and_refuses_reuse(
    repository: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _candidate, _reference = repository
    monkeypatch.chdir(root)
    output = root / "build/review-success"
    calls: list[dict[str, Any]] = []

    def fake_sdk(
        prepared: dict[str, Any], workdir: Path, expected_instructions: Any
    ) -> dict[str, Any]:
        calls.append(copy.deepcopy(prepared))
        assert (
            json.loads((output / "receipt.json").read_text(encoding="utf-8"))["status"] == "started"
        )
        return runtime_result()

    monkeypatch.setattr(sdk_review, "_run_sdk", fake_sdk)

    assert sdk_review.main(arguments(repository, output, execute=True)) == 0
    receipt_path = output / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "completed"
    assert receipt["report"] == report()
    before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    assert sdk_review.main(arguments(repository, output, execute=True)) == 1
    assert len(calls) == 1
    assert before == {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}


@pytest.mark.parametrize("failure", ["failed", "unknown", "invalid-report", "exception"])
def test_execute_preserves_failure_receipts_and_never_replays(
    repository: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    root, _candidate, _reference = repository
    monkeypatch.chdir(root)
    output = root / f"build/review-{failure}"
    calls = 0

    def fake_sdk(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if failure == "exception":
            raise RuntimeError("PRIVATE RUNTIME DETAIL MUST NOT APPEAR")
        if failure == "invalid-report":
            return runtime_result("PRIVATE MALFORMED MODEL CONTENT")
        return runtime_result(status=failure)

    monkeypatch.setattr(sdk_review, "_run_sdk", fake_sdk)
    assert sdk_review.main(arguments(repository, output, execute=True)) == 1
    receipt_path = output / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] in {"failed", "unknown"}
    before = receipt_path.read_bytes()
    assert sdk_review.main(arguments(repository, output, execute=True)) == 1
    assert receipt_path.read_bytes() == before
    assert calls == 1
    error = capsys.readouterr().err
    assert "PRIVATE" not in error
    assert str(root) not in error


class DumpModel:
    def __init__(self, value: dict[str, Any]) -> None:
        self.value = value

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        return copy.deepcopy(self.value)


@pytest.fixture
def fake_sdk(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    home = tmp_path / "sdk-home"
    home.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path / "programdata"))
    for name in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "CODEX_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    state = SimpleNamespace(
        home=home,
        versions={"openai-codex": "0.163.0", "openai-codex-cli-bin": "0.163.0"},
        imports=[],
        constructors=[],
        requests=[],
        turns=[],
        run_calls=0,
        interrupt_calls=0,
        close_calls=0,
        runtime_version="0.163.0",
        account_type="chatgpt",
        config_change=lambda value: None,
        thread_change=lambda value: None,
        instruction_paths=[],
        result_status="completed",
        run_error=None,
        close_error=False,
        block_turn=False,
        block_startup=False,
        block_client_start=False,
        confirm_cancel=False,
        interrupt_error=False,
        approval_method=None,
        run_started=threading.Event(),
        run_release=threading.Event(),
        run_finished=threading.Event(),
        startup_started=threading.Event(),
        startup_release=threading.Event(),
        start_release=threading.Event(),
        late_close=threading.Event(),
    )
    real_import = importlib.import_module
    real_version = importlib.metadata.version

    def version(distribution: str) -> str:
        if distribution not in state.versions:
            return real_version(distribution)
        value = state.versions[distribution]
        if value is None:
            raise importlib.metadata.PackageNotFoundError(distribution)
        return str(value)

    class Handle:
        id = "owned-turn"

        def run(self) -> Any:
            state.run_calls += 1
            state.run_started.set()
            try:
                if state.block_turn:
                    state.run_release.wait()
                if state.run_error is not None:
                    raise state.run_error
                return SimpleNamespace(
                    status=SimpleNamespace(value=state.result_status),
                    final_response=json.dumps(
                        {"outcome": "APPROVE", "summary": "No contradiction found.", "findings": []}
                    ),
                    usage=DumpModel({"input_tokens": 10, "output_tokens": 5}),
                )
            finally:
                state.run_finished.set()

        def interrupt(self) -> None:
            state.interrupt_calls += 1
            if state.interrupt_error:
                raise RuntimeError("PRIVATE INTERRUPT DETAIL")
            if state.confirm_cancel:
                state.result_status = "interrupted"
                state.run_release.set()

    class Thread:
        def __init__(self, client: Any, identifier: str) -> None:
            assert identifier == "owned-thread"

        def turn(self, prompt: str, **kwargs: Any) -> Handle:
            state.turns.append({"prompt": prompt, **kwargs})
            if state.approval_method is not None:
                state.approval_response = state.approval_handler(state.approval_method, {})
            return Handle()

    class Client:
        def __init__(self, *, config: Any, approval_handler: Any) -> None:
            self.config = config
            state.constructors.append(config)
            state.approval_handler = approval_handler

        def start(self) -> None:
            state.startup_started.set()
            if state.block_client_start:
                state.start_release.wait()

        def initialize(self) -> Any:
            state.startup_started.set()
            if state.block_startup:
                state.startup_release.wait()
            return SimpleNamespace(serverInfo=SimpleNamespace(version=state.runtime_version))

        def request(self, method: str, params: dict[str, Any], **kwargs: Any) -> Any:
            state.requests.append((method, copy.deepcopy(params)))
            if method == "account/read":
                return SimpleNamespace(
                    account=SimpleNamespace(root=SimpleNamespace(type=state.account_type))
                )
            if method == "config/read":
                config_path = state.home / "config.toml"
                configuration = (
                    tomllib.loads(config_path.read_text(encoding="utf-8"))
                    if config_path.is_file()
                    else {}
                )
                # The pinned CLI splits override paths literally, without TOML key unquoting.
                for override in self.config.config_overrides:
                    key, separator, raw_value = override.partition("=")
                    assert separator
                    parts = key.split(".")
                    destination = configuration
                    for part in parts[:-1]:
                        destination = destination.setdefault(part, {})
                    destination[parts[-1]] = tomllib.loads(f"value={raw_value}")["value"]
                state.effective_config = copy.deepcopy(configuration)
                state.config_change(configuration)
                return SimpleNamespace(config=DumpModel(configuration))
            assert method == "thread/start", f"unexpected SDK RPC: {method}"
            started = SimpleNamespace(
                sandbox=SimpleNamespace(
                    root=SimpleNamespace(type="readOnly", network_access=False)
                ),
                approval_policy=SimpleNamespace(root=SimpleNamespace(value="never")),
                model_provider="openai",
                cwd=SimpleNamespace(root=self.config.cwd),
                instruction_sources=[
                    SimpleNamespace(root=str(path)) for path in state.instruction_paths
                ],
                thread=SimpleNamespace(id="owned-thread"),
                model="reported-model",
            )
            state.thread_change(started)
            return started

        def close(self) -> None:
            state.close_calls += 1
            if state.close_calls >= 2:
                state.late_close.set()
            state.run_release.set()
            state.startup_release.set()
            if state.close_error:
                raise RuntimeError("PRIVATE CLOSE DETAIL")

    models = SimpleNamespace(
        GetAccountResponse=object(), ConfigReadResponse=object(), ThreadStartResponse=object()
    )
    state.sdk = SimpleNamespace(
        CodexConfig=lambda **kwargs: SimpleNamespace(**kwargs),
        Thread=Thread,
        ApprovalMode=SimpleNamespace(deny_all="fake-deny-all"),
        Sandbox=SimpleNamespace(read_only="fake-read-only"),
    )
    modules = {
        "openai_codex": state.sdk,
        "openai_codex.client": SimpleNamespace(CodexClient=Client),
        "openai_codex.generated.v2_all": models,
        "openai_codex._initialize_metadata": SimpleNamespace(
            validate_initialize_metadata=lambda value: value
        ),
    }

    def import_module(name: str, package: str | None = None) -> Any:
        if name.startswith("openai_codex"):
            state.imports.append(name)
            assert name in modules, f"unexpected SDK module: {name}"
            return modules[name]
        return real_import(name, package)

    monkeypatch.setattr(importlib.metadata, "version", version)
    monkeypatch.setattr(importlib, "import_module", import_module)
    return state


def run_fake(
    fake_sdk: Any, tmp_path: Path, expected: dict[str, str] | None = None
) -> dict[str, Any]:
    return sdk_review._run_sdk(
        {"prompt": "Review the fixed supplied text.", "output_schema": sdk_review.OUTPUT_SCHEMA},
        tmp_path,
        {} if expected is None else expected,
    )


def test_runtime_uses_standard_read_only_and_one_turn_on_windows(
    fake_sdk: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sdk_review.sys, "platform", "win32")
    receipt = run_fake(fake_sdk, tmp_path)
    assert receipt["status"] == "completed"
    assert fake_sdk.run_calls == len(fake_sdk.turns) == 1
    params = next(params for method, params in fake_sdk.requests if method == "thread/start")
    assert params["sandbox"] == "read-only"
    assert params["approvalPolicy"] == "never"
    assert params["ephemeral"] is True
    assert params["developerInstructions"] == ""
    assert fake_sdk.turns[0]["sandbox"] == fake_sdk.sdk.Sandbox.read_only
    assert fake_sdk.turns[0]["approval_mode"] == fake_sdk.sdk.ApprovalMode.deny_all
    assert fake_sdk.close_calls == 1


def test_explicit_codex_home_does_not_require_an_os_home(
    fake_sdk: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable_home(cls: type[Path]) -> Path:
        raise RuntimeError("Could not determine home directory")

    monkeypatch.setattr(Path, "home", classmethod(unavailable_home))
    assert run_fake(fake_sdk, tmp_path)["status"] == "completed"


def test_execute_explicit_instruction_home_does_not_require_an_os_home(
    repository: tuple[Path, str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _candidate, _reference = repository
    home = root / "sdk-home"
    home.mkdir()
    instructions = home / "AGENTS.md"
    instructions.write_bytes(b"Declared global guidance.\n")
    digest = hashlib.sha256(instructions.read_bytes()).hexdigest()
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.chdir(root)

    def unavailable_home(cls: type[Path]) -> Path:
        raise RuntimeError("Could not determine home directory")

    monkeypatch.setattr(Path, "home", classmethod(unavailable_home))
    monkeypatch.setattr(sdk_review, "_run_sdk", lambda *args: runtime_result())
    argv = arguments(repository, root / "build/explicit-home", execute=True)
    assert sdk_review.main([*argv, "--global-instructions-sha256", digest]) == 0


def test_runtime_disables_inherited_notify_and_accepts_official_chatgpt_default(
    fake_sdk: Any, tmp_path: Path
) -> None:
    (fake_sdk.home / "config.toml").write_text(
        'notify=["private-notification-command"]\n'
        'chatgpt_base_url="https://chatgpt.com/backend-api/"\n',
        encoding="utf-8",
    )
    receipt = run_fake(fake_sdk, tmp_path)
    assert receipt["status"] == "completed"
    assert fake_sdk.effective_config["notify"] == []


@pytest.mark.parametrize("change", ["notify", "endpoint"])
def test_runtime_rejects_notification_or_custom_chatgpt_endpoint(
    fake_sdk: Any, tmp_path: Path, change: str
) -> None:
    def corrupt(configuration: dict[str, Any]) -> None:
        if change == "notify":
            configuration["notify"] = ["unexpected-command"]
        else:
            configuration["chatgpt_base_url"] = "https://unexpected.invalid/backend-api/"

    fake_sdk.config_change = corrupt
    receipt = run_fake(fake_sdk, tmp_path)
    assert receipt["status"] == "failed"
    assert fake_sdk.turns == []


@pytest.mark.parametrize("distribution", ["openai-codex", "openai-codex-cli-bin"])
@pytest.mark.parametrize("version", [None, "0.162.0"])
def test_runtime_rejects_missing_or_wrong_packages_before_construction(
    fake_sdk: Any, tmp_path: Path, distribution: str, version: str | None
) -> None:
    fake_sdk.versions[distribution] = version
    assert run_fake(fake_sdk, tmp_path)["status"] != "completed"
    assert fake_sdk.constructors == fake_sdk.imports == fake_sdk.turns == []


@pytest.mark.parametrize(
    "name", ["OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "CODEX_BASE_URL"]
)
def test_runtime_rejects_unexpected_billing_or_provider_environment_before_construction(
    fake_sdk: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setenv(name, "private-not-for-output")
    receipt = run_fake(fake_sdk, tmp_path)
    assert receipt["status"] != "completed"
    assert fake_sdk.constructors == fake_sdk.imports == fake_sdk.turns == []
    assert "private-not-for-output" not in json.dumps(receipt)


@pytest.mark.parametrize("change", ["account", "runtime", "shell", "mcp", "provider", "search"])
def test_runtime_rejects_effective_authentication_or_configuration_before_turn(
    fake_sdk: Any, tmp_path: Path, change: str
) -> None:
    if change == "account":
        fake_sdk.account_type = "apiKey"
    elif change == "runtime":
        fake_sdk.runtime_version = "0.162.0"
    else:

        def corrupt(configuration: dict[str, Any]) -> None:
            if change == "shell":
                configuration["features"]["shell_tool"] = True
            elif change == "mcp":
                configuration["mcp_servers"] = {"unexpected": {"enabled": True}}
            elif change == "provider":
                configuration["model_provider"] = "other"
            else:
                configuration["web_search"] = "live"

        fake_sdk.config_change = corrupt
    assert run_fake(fake_sdk, tmp_path)["status"] != "completed"
    assert fake_sdk.turns == []
    assert fake_sdk.close_calls == 1


@pytest.mark.parametrize(
    "change", ["write", "network", "approval", "provider", "cwd", "instructions"]
)
def test_runtime_rejects_unexpected_thread_receipts_before_turn(
    fake_sdk: Any, tmp_path: Path, change: str
) -> None:
    def corrupt(started: Any) -> None:
        if change == "write":
            started.sandbox.root.type = "workspaceWrite"
        elif change == "network":
            started.sandbox.root.network_access = True
        elif change == "approval":
            started.approval_policy.root.value = "onRequest"
        elif change == "provider":
            started.model_provider = "other"
        elif change == "cwd":
            started.cwd.root = str(tmp_path.parent)
        else:
            started.instruction_sources = [SimpleNamespace(root=str(tmp_path / "unexpected.md"))]

    fake_sdk.thread_change = corrupt
    assert run_fake(fake_sdk, tmp_path)["status"] != "completed"
    assert fake_sdk.turns == []
    assert fake_sdk.close_calls == 1


def test_runtime_binds_explicit_instruction_hash_without_publishing_the_path(
    fake_sdk: Any, tmp_path: Path
) -> None:
    instructions = tmp_path / "instructions.md"
    instructions.write_bytes(b"Declared global guidance.\n")
    digest = hashlib.sha256(instructions.read_bytes()).hexdigest()
    fake_sdk.instruction_paths = [instructions]
    receipt = run_fake(fake_sdk, tmp_path, {str(instructions): digest})
    assert receipt["status"] == "completed"
    assert receipt["inherited_instruction_hashes"] == [digest]
    assert str(instructions) not in json.dumps(receipt)


def test_runtime_rejects_changed_instruction_bytes_before_turn(
    fake_sdk: Any, tmp_path: Path
) -> None:
    instructions = tmp_path / "instructions.md"
    instructions.write_bytes(b"Original.\n")
    digest = hashlib.sha256(instructions.read_bytes()).hexdigest()
    fake_sdk.instruction_paths = [instructions]
    fake_sdk.thread_change = lambda value: instructions.write_bytes(b"Changed during setup.\n")
    receipt = run_fake(fake_sdk, tmp_path, {str(instructions): digest})
    assert receipt["status"] != "completed"
    assert fake_sdk.turns == []


@pytest.mark.parametrize(
    ("final_status", "expected_status"),
    [("failed", "failed"), ("interrupted", "failed"), ("inProgress", "unknown")],
)
def test_runtime_preserves_noncomplete_final_results(
    fake_sdk: Any, tmp_path: Path, final_status: str, expected_status: str
) -> None:
    fake_sdk.result_status = final_status
    receipt = run_fake(fake_sdk, tmp_path)
    assert receipt["status"] == expected_status
    assert fake_sdk.run_calls == len(fake_sdk.turns) == 1


def test_runtime_close_failure_cannot_report_success(fake_sdk: Any, tmp_path: Path) -> None:
    fake_sdk.close_error = True
    receipt = run_fake(fake_sdk, tmp_path)
    assert receipt["status"] != "completed"
    assert fake_sdk.run_calls == len(fake_sdk.turns) == 1
    assert "PRIVATE CLOSE DETAIL" not in json.dumps(receipt)


def shorten_sdk_deadline(
    monkeypatch: pytest.MonkeyPatch, fake_sdk: Any, expired_wait: int
) -> list[float | None]:
    """Replace public waits, keeping actual local fake-worker coordination."""
    waits: list[float | None] = []

    class DeadlineEvent:
        def __init__(self) -> None:
            self.event = threading.Event()

        def set(self) -> None:
            self.event.set()

        def is_set(self) -> bool:
            return self.event.is_set()

        def wait(self, timeout: float | None = None) -> bool:
            waits.append(timeout)
            if timeout == expired_wait:
                if timeout == 120:
                    assert fake_sdk.run_started.wait(1), "fake turn did not start"
                elif timeout == 30:
                    assert fake_sdk.startup_started.wait(1), "fake startup did not start"
                return False
            if timeout == 10 and not fake_sdk.confirm_cancel:
                return False
            return self.event.wait(None if timeout is None else min(timeout, 1))

    monkeypatch.setattr(
        sdk_review,
        "threading",
        SimpleNamespace(Thread=threading.Thread, Event=DeadlineEvent, Lock=threading.Lock),
    )
    return waits


@pytest.mark.parametrize("confirmed", [False, True])
def test_runtime_deadline_interrupts_only_owned_turn_and_preserves_confirmation(
    fake_sdk: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, confirmed: bool
) -> None:
    fake_sdk.block_turn = True
    fake_sdk.confirm_cancel = confirmed
    waits = shorten_sdk_deadline(monkeypatch, fake_sdk, 120)

    try:
        receipt = run_fake(fake_sdk, tmp_path)
    finally:
        fake_sdk.run_release.set()

    assert receipt["status"] == ("failed" if confirmed else "unknown")
    assert receipt["timeout"] is True
    assert receipt["cancel_requested"] is True
    assert receipt["cancel_confirmed"] is confirmed
    assert receipt["report"] is None
    assert fake_sdk.run_calls == len(fake_sdk.turns) == fake_sdk.interrupt_calls == 1
    assert fake_sdk.close_calls == 1
    assert 120 in waits and 10 in waits and 5 in waits


def test_runtime_cancel_request_failure_is_unknown_without_a_final_confirmation(
    fake_sdk: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_sdk.block_turn = True
    fake_sdk.interrupt_error = True
    shorten_sdk_deadline(monkeypatch, fake_sdk, 120)

    try:
        receipt = run_fake(fake_sdk, tmp_path)
    finally:
        fake_sdk.run_release.set()

    assert receipt["status"] == "unknown"
    assert receipt["cancel_requested"] is True
    assert receipt["cancel_confirmed"] is False
    assert fake_sdk.run_calls == fake_sdk.interrupt_calls == 1
    assert "PRIVATE INTERRUPT DETAIL" not in json.dumps(receipt)


def test_runtime_startup_deadline_does_not_request_a_turn(
    fake_sdk: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_sdk.block_startup = True
    waits = shorten_sdk_deadline(monkeypatch, fake_sdk, 30)

    try:
        receipt = run_fake(fake_sdk, tmp_path)
    finally:
        fake_sdk.startup_release.set()

    assert receipt["status"] == "unknown"
    assert receipt["timeout"] is True
    assert fake_sdk.turns == []
    assert fake_sdk.interrupt_calls == 0
    assert fake_sdk.close_calls == 1
    assert 30 in waits and 120 not in waits


def test_runtime_close_deadline_cannot_report_success(
    fake_sdk: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    waits = shorten_sdk_deadline(monkeypatch, fake_sdk, 5)
    receipt = run_fake(fake_sdk, tmp_path)
    assert receipt["status"] == "unknown"
    assert receipt["close_error"] is True
    assert receipt["report"] is None
    assert fake_sdk.run_calls == len(fake_sdk.turns) == fake_sdk.close_calls == 1
    assert 5 in waits


def test_runtime_turn_exception_is_not_retried_or_reported_as_a_result(
    fake_sdk: Any, tmp_path: Path
) -> None:
    fake_sdk.run_error = RuntimeError("PRIVATE TURN DETAIL")
    receipt = run_fake(fake_sdk, tmp_path)
    assert receipt["status"] == "unknown"
    assert receipt["report"] is None
    assert fake_sdk.run_calls == len(fake_sdk.turns) == 1
    assert fake_sdk.close_calls == 1
    assert "PRIVATE TURN DETAIL" not in json.dumps(receipt)


@pytest.mark.parametrize(
    "method",
    [
        "item/commandExecution/requestApproval",
        "item/fileChange/requestApproval",
        "unexpected/method",
    ],
)
def test_runtime_server_side_tool_requests_are_rejected_and_never_authorize(
    fake_sdk: Any, tmp_path: Path, method: str
) -> None:
    fake_sdk.approval_method = method
    receipt = run_fake(fake_sdk, tmp_path)
    assert receipt["status"] == "failed"
    assert receipt["unexpected_approval_request"] is True
    assert receipt["report"] is None
    assert len(fake_sdk.turns) == 1
    assert fake_sdk.close_calls == 1
    if method != "unexpected/method":
        assert fake_sdk.approval_response == {"decision": "decline"}


def test_runtime_late_start_is_closed_without_mutating_returned_unknown_receipt(
    fake_sdk: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_sdk.block_client_start = True
    shorten_sdk_deadline(monkeypatch, fake_sdk, 30)

    try:
        receipt = run_fake(fake_sdk, tmp_path)
        assert receipt["status"] == "unknown"
        assert receipt["timeout"] is True
        assert fake_sdk.close_calls == 1
        assert fake_sdk.turns == []
        snapshot = copy.deepcopy(receipt)
        fake_sdk.start_release.set()
        assert fake_sdk.late_close.wait(2), "late owned start was not closed"
        assert fake_sdk.close_calls == 2
        assert fake_sdk.turns == []
        assert receipt == snapshot
    finally:
        fake_sdk.start_release.set()


def test_runtime_accepts_the_exact_pinned_version_with_a_reported_build_suffix(
    fake_sdk: Any, tmp_path: Path
) -> None:
    fake_sdk.runtime_version = "0.163.0 (stable build)"
    receipt = run_fake(fake_sdk, tmp_path)
    assert receipt["status"] == "completed"
    assert receipt["runtime_version"] == "0.163.0"
    assert fake_sdk.run_calls == len(fake_sdk.turns) == fake_sdk.close_calls == 1


def test_runtime_user_interrupt_cancels_once_closes_and_returns_a_stable_safe_receipt(
    fake_sdk: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_sdk.block_turn = True
    fake_sdk.confirm_cancel = True
    shorten_sdk_deadline(monkeypatch, fake_sdk, -1)
    event_type = sdk_review.threading.Event
    original_wait = event_type.wait
    interrupted = False

    def interrupt_once(event: Any, timeout: float | None = None) -> bool:
        nonlocal interrupted
        if timeout == 120 and not interrupted:
            assert fake_sdk.run_started.wait(1), "fake turn did not start"
            interrupted = True
            raise KeyboardInterrupt
        return bool(original_wait(event, timeout))

    monkeypatch.setattr(event_type, "wait", interrupt_once)
    try:
        receipt = run_fake(fake_sdk, tmp_path)
    finally:
        fake_sdk.run_release.set()

    assert interrupted
    assert receipt["status"] == "failed"
    assert receipt["user_interrupted"] is True
    assert receipt["error_code"] == "SDK_REVIEW_USER_INTERRUPTED"
    assert receipt["cancel_requested"] is True
    assert receipt["cancel_confirmed"] is True
    assert receipt["report"] is None
    assert fake_sdk.run_calls == len(fake_sdk.turns) == fake_sdk.interrupt_calls == 1
    assert fake_sdk.close_calls == 1
    snapshot = copy.deepcopy(receipt)
    assert fake_sdk.run_finished.wait(1)
    assert receipt == snapshot
    assert str(tmp_path) not in json.dumps(receipt)


def test_runtime_disables_inherited_mcp_entries_without_creating_quoted_server_names(
    fake_sdk: Any, tmp_path: Path
) -> None:
    (fake_sdk.home / "config.toml").write_text(
        '[mcp_servers.fixture-server]\ncommand = "synthetic-command"\n'
        'args = ["--offline-fixture"]\nenabled = true\n'
        '[mcp_servers.other_2]\ncommand = "synthetic-other"\nenabled = true\n',
        encoding="utf-8",
    )

    receipt = run_fake(fake_sdk, tmp_path)

    assert receipt["status"] == "completed"
    assert fake_sdk.effective_config["mcp_servers"] == {
        "fixture-server": {
            "command": "synthetic-command",
            "args": ["--offline-fixture"],
            "enabled": False,
        },
        "other_2": {"command": "synthetic-other", "enabled": False},
    }
    overrides = [
        value
        for value in fake_sdk.constructors[0].config_overrides
        if value.startswith("mcp_servers.")
    ]
    assert set(overrides) == {
        "mcp_servers.fixture-server.enabled=false",
        "mcp_servers.other_2.enabled=false",
    }
    assert fake_sdk.run_calls == len(fake_sdk.turns) == 1


@pytest.mark.parametrize("name", ["contains.dot", 'contains"quote'])
def test_runtime_rejects_unsupported_mcp_names_before_sdk_construction(
    fake_sdk: Any, tmp_path: Path, name: str
) -> None:
    (fake_sdk.home / "config.toml").write_text(
        f'[mcp_servers.{json.dumps(name)}]\ncommand = "synthetic-command"\nenabled = true\n',
        encoding="utf-8",
    )

    receipt = run_fake(fake_sdk, tmp_path)

    assert receipt["status"] == "failed"
    assert fake_sdk.constructors == []
    assert fake_sdk.turns == []


@pytest.mark.parametrize("supplemental", [False, True])
def test_shared_execution_returns_the_saved_receipt_and_keeps_trigger_binding_optional(
    repository: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    supplemental: bool,
) -> None:
    root, candidate, _reference = repository
    prepared = request(repository)
    output = root / "build/shared-review"
    binding = {
        "node": "review_context_implementation",
        "task_id": "TASK-0087",
        "context_sha256": "a" * 64,
    }
    expected_report = (
        report(outcome="REQUEST_CHANGES", findings=[finding()]) if supplemental else report()
    )
    calls = 0

    def fake_sdk(*_args: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        started = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
        assert started["status"] == "started"
        assert started.get("trigger_binding") == (binding if supplemental else None)
        return runtime_result(json.dumps(expected_report))

    monkeypatch.setattr(sdk_review, "_run_sdk", fake_sdk)
    receipt = sdk_review.execute_review(
        root, prepared, output, trigger_binding=binding if supplemental else None
    )

    assert receipt == json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "completed"
    assert receipt["report"] == expected_report
    assert receipt["manifest"]["candidate"] == candidate
    assert ("trigger_binding" in receipt) is supplemental
    binding["task_id"] = "TASK-9999"
    if supplemental:
        assert receipt["trigger_binding"]["task_id"] == "TASK-0087"
    assert calls == 1
    with pytest.raises(ValueError):
        sdk_review.execute_review(root, prepared, output)
    assert calls == 1
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "change",
    [
        {"node": "design"},
        {"task_id": "TASK-87"},
        {"context_sha256": "bad-hash"},
        {"authorization": "approved"},
    ],
)
def test_shared_execution_rejects_invalid_trigger_markers_before_output_or_sdk(
    repository: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
    change: dict[str, str],
) -> None:
    root, _candidate, _reference = repository
    output = root / "build/invalid-trigger"
    binding = {
        "node": "review_context_implementation",
        "task_id": "TASK-0087",
        "context_sha256": "a" * 64,
        **change,
    }

    def forbidden(*_args: Any) -> dict[str, Any]:
        raise AssertionError("Invalid marker must not dispatch the SDK")

    monkeypatch.setattr(sdk_review, "_run_sdk", forbidden)
    with pytest.raises(ValueError):
        sdk_review.execute_review(root, request(repository), output, trigger_binding=binding)
    assert not output.exists()


@pytest.mark.parametrize("failure", ["failed", "unknown", "invalid-report", "exception"])
def test_shared_execution_preserves_failure_and_safe_exception_receipts(
    repository: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    root, _candidate, _reference = repository
    output = root / f"build/shared-{failure}"
    binding = {
        "node": "review_context_implementation",
        "task_id": "TASK-0087",
        "context_sha256": "b" * 64,
    }

    def fake_sdk(*_args: Any) -> dict[str, Any]:
        if failure == "exception":
            raise RuntimeError("PRIVATE RUNTIME DETAIL MUST NOT APPEAR")
        if failure == "invalid-report":
            return runtime_result("PRIVATE MALFORMED MODEL CONTENT")
        return runtime_result(status=failure)

    monkeypatch.setattr(sdk_review, "_run_sdk", fake_sdk)
    if failure in {"exception", "invalid-report"}:
        with pytest.raises(ValueError) as raised:
            sdk_review.execute_review(root, request(repository), output, trigger_binding=binding)
        assert "PRIVATE" not in str(raised.value)
    else:
        assert (
            sdk_review.execute_review(root, request(repository), output, trigger_binding=binding)[
                "status"
            ]
            == failure
        )
    saved = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    assert saved["status"] in {"failed", "unknown"}
    assert saved["trigger_binding"] == binding
    assert "report" not in saved
    assert "PRIVATE" not in json.dumps(saved)


def test_standalone_execution_reuses_the_shared_executor_and_existing_stdout(
    repository: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, candidate, reference = repository
    monkeypatch.chdir(root)
    output = root / "build/shared-cli"
    calls: list[tuple[Path, dict[str, Any], Path, dict[str, Any]]] = []

    def fake_execute(
        actual_root: Path, prepared: dict[str, Any], actual_output: Path, **kwargs: Any
    ) -> dict[str, Any]:
        calls.append((actual_root, prepared, actual_output, kwargs))
        return {"status": "completed", "input_sha256": prepared["input_sha256"]}

    monkeypatch.setattr(sdk_review, "execute_review", fake_execute)
    assert sdk_review.main(arguments(repository, output, execute=True)) == 0
    assert len(calls) == 1
    assert calls[0][0] == root and calls[0][2] == output
    assert calls[0][1]["candidate"] == candidate
    assert calls[0][1]["reference"] == reference
    assert calls[0][3] == {"global_instructions_sha256": None}
    assert json.loads(capsys.readouterr().out) == {
        "status": "completed",
        "input_sha256": calls[0][1]["input_sha256"],
    }
