"""Pure byte, JSON and lexical safety boundaries for external reviews."""

from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from aiflow import cli, external_review
from aiflow.errors import ContractError, StorageError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_SECRET = "SYNTHETIC_UNIT_INPUT_SECRET"


@pytest.mark.parametrize(
    "path",
    [
        r"\\synthetic-server\share\file.json",
        r"\\?\C:\synthetic\file.json",
        r"C:\synthetic\file.json:ads",
        r"C:\synthetic\NUL.json",
        r"C:\synthetic\COM1",
        r"C:\synthetic\CONIN$",
        r"C:\synthetic\CONOUT$",
        r"C:\synthetic\COM¹.json",
        r"C:\synthetic\LPT²",
        "synthetic.json.",
        "synthetic.json ",
    ],
)
def test_unsafe_windows_lexical_paths_are_rejected_before_metadata(
    path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def unexpected_metadata(self: Path, *args: object, **kwargs: object) -> os.stat_result:
        calls.append(self)
        raise AssertionError("Unsafe lexical input reached filesystem metadata")

    monkeypatch.setattr(Path, "lstat", unexpected_metadata)
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(Path(path), 1024)
    assert caught.value.code.startswith("EXTERNAL_REVIEW_")
    assert calls == []


def assert_safe_error(error: ContractError, code: str) -> None:
    assert error.code == code
    assert SYNTHETIC_SECRET not in json.dumps(error.to_dict())


@pytest.mark.parametrize(
    "payload,code",
    [
        (b"\xef\xbb\xbf{}", "EXTERNAL_REVIEW_JSON_INVALID"),
        (b"\xff", "EXTERNAL_REVIEW_JSON_INVALID"),
        (b'{"unknown":NaN}', "EXTERNAL_REVIEW_JSON_INVALID"),
        (b'{"unknown":Infinity}', "EXTERNAL_REVIEW_JSON_INVALID"),
        (b'{"unknown":1e9999}', "EXTERNAL_REVIEW_JSON_INVALID"),
        (b'{"unknown":"\\ud800"}', "EXTERNAL_REVIEW_JSON_INVALID"),
        (b"[]", "EXTERNAL_REVIEW_JSON_INVALID"),
        (b'{"unclosed":', "EXTERNAL_REVIEW_JSON_INVALID"),
        (
            b'{"SYNTHETIC_UNIT_INPUT_SECRET":1,"SYNTHETIC_UNIT_INPUT_SECRET":2}',
            "EXTERNAL_REVIEW_JSON_DUPLICATE_KEY",
        ),
        (b'{"SYNTHETIC_UNIT_INPUT_SECRET":"unknown"}', "EXTERNAL_REVIEW_CONTRACT_INVALID"),
    ],
)
def test_strict_json_loader_refuses_invalid_bytes_without_reflecting_input(
    payload: bytes, code: str
) -> None:
    with pytest.raises(ContractError) as caught:
        external_review._load_json_bytes(payload, "external-review", PROJECT_ROOT)
    assert_safe_error(caught.value, code)


@pytest.mark.parametrize(
    "contract_name",
    ["external-review", "external-review-import", "external-review-repository-mapping"],
)
def test_strict_loader_accepts_real_contract_fixture_without_git(contract_name: str) -> None:
    value = json.loads(
        (PROJECT_ROOT / f"tests/fixtures/contracts/valid/{contract_name}.json").read_text()
    )
    compact = external_review.canonical_json(value).encode("utf-8")
    pretty = json.dumps(value, ensure_ascii=False, indent=4).encode("utf-8")
    assert external_review._load_json_bytes(compact, contract_name, PROJECT_ROOT) == value
    assert external_review._load_json_bytes(pretty, contract_name, PROJECT_ROOT) == value
    assert external_review.canonical_sha256(json.loads(compact)) == (
        external_review.canonical_sha256(json.loads(pretty))
    )


@pytest.mark.parametrize("depth", [32, 33])
def test_json_depth_is_bounded_before_contract_validation(depth: int) -> None:
    payload = b"[" * depth + b"0" + b"]" * depth
    with pytest.raises(ContractError) as caught:
        external_review._load_json_bytes(payload, "external-review", PROJECT_ROOT)
    assert_safe_error(
        caught.value,
        "EXTERNAL_REVIEW_DEPTH_LIMIT" if depth == 33 else "EXTERNAL_REVIEW_JSON_INVALID",
    )


def test_json_scanner_ignores_brackets_and_escaped_quotes_inside_narrative() -> None:
    narrative = json.dumps({"description": '[{}] "quoted" \\ narrative ' * 40})
    assert external_review._bounded_json_text(narrative.encode()) == narrative


@pytest.mark.parametrize("unsupported", [{"a", "b"}, float("nan"), float("inf"), "\ud800"])
def test_canonical_digest_refuses_unsupported_or_nonutf8_values(unsupported: object) -> None:
    with pytest.raises(ContractError) as caught:
        external_review.canonical_sha256({SYNTHETIC_SECRET: unsupported})
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_JSON_INVALID")


@pytest.mark.parametrize("payload,limit", [(b"", 0), (b"opaque\x00\xff", 8), (b"1234", 4)])
def test_bounded_reader_accepts_exact_limits_and_opaque_bytes_without_writes(
    tmp_path: Path, payload: bytes, limit: int
) -> None:
    source = tmp_path / "synthetic.bin"
    source.write_bytes(payload)
    before = source.stat()
    assert external_review._read_bounded_file(source, limit) == payload
    assert source.read_bytes() == payload
    after = source.stat()
    assert (after.st_size, after.st_mtime_ns, after.st_ctime_ns) == (
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    assert sorted(path.name for path in tmp_path.iterdir()) == [source.name]


@pytest.mark.parametrize("kind", ["missing", "directory", "oversized"])
def test_bounded_reader_refuses_unreadable_nonregular_and_oversized_sources(
    tmp_path: Path, kind: str
) -> None:
    source = tmp_path / "synthetic.bin"
    if kind == "directory":
        source.mkdir()
    elif kind == "oversized":
        source.write_bytes(b"12345")
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(source, 4)
    assert_safe_error(
        caught.value,
        {
            "missing": "EXTERNAL_REVIEW_INPUT_UNREADABLE",
            "directory": "EXTERNAL_REVIEW_PATH_INVALID",
            "oversized": "EXTERNAL_REVIEW_SIZE_LIMIT",
        }[kind],
    )


@pytest.mark.parametrize("replace_on_open", [1, 2], ids=["first-handle", "second-handle"])
def test_bounded_reader_detects_replacement_before_each_handle_identity_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replace_on_open: int
) -> None:
    source = tmp_path / "synthetic.bin"
    source.write_bytes(b"same-size")
    replacement = tmp_path / "synthetic-replacement.bin"
    replacement.write_bytes(b"same-size")
    original_open = Path.open
    calls = 0

    def replace_before_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        if self == external_review._io_path(source) and args and args[0] == "rb":
            calls += 1
            if calls == replace_on_open:
                os.replace(replacement, source)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", replace_before_open)
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(source, 32)
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_INPUT_CHANGED")
    assert calls == replace_on_open
    assert not replacement.exists()


def test_bounded_reader_stops_growth_at_limit_plus_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "synthetic.bin"
    source.write_bytes(b"123")
    original_open = Path.open
    triggered = False

    class GrowingReader:
        def __init__(self, stream: Any) -> None:
            self.stream = stream

        def __enter__(self) -> GrowingReader:
            return self

        def __exit__(self, *args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return int(self.stream.fileno())

        def read(self, limit: int) -> bytes:
            nonlocal triggered
            triggered = True
            assert limit == 5
            with original_open(source, "ab") as writer:
                writer.write(b"45")
            return bytes(self.stream.read(limit))

    def grow_when_read(self: Path, *args: Any, **kwargs: Any) -> Any:
        stream = original_open(self, *args, **kwargs)
        if self == external_review._io_path(source) and args and args[0] == "rb":
            return GrowingReader(stream)
        return stream

    monkeypatch.setattr(Path, "open", grow_when_read)
    with pytest.raises(ContractError) as caught:
        external_review._read_bounded_file(source, 4)
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_SIZE_LIMIT")
    assert triggered


@pytest.mark.parametrize(
    "reference",
    [
        "https://example.invalid/%2525252541/report",
        "https://example.invalid/%GG/report",
        "https://example.invalid:443/report",
        "https://example.invalid/%40secret/report",
        "https://example.invalid/report?token=SYNTHETIC_UNIT_INPUT_SECRET",
        "https://example.invalid/report#SYNTHETIC_UNIT_INPUT_SECRET",
    ],
)
def test_encoded_or_sensitive_url_boundaries_refuse_without_git(reference: str) -> None:
    with pytest.raises(ContractError) as caught:
        external_review._https_reference(reference)
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_REFERENCE_INVALID")


@pytest.mark.parametrize("failure_stage", ["build", "parse"])
@pytest.mark.parametrize("broken_stderr", [False, True])
def test_cli_early_domain_errors_are_safe(
    failure_stage: str,
    broken_stderr: bool,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret_path = r"C:\synthetic\SYNTHETIC_UNIT_INPUT_SECRET\report.json"

    def fail(*_args: object, **_kwargs: object) -> Any:
        raise StorageError(secret_path, details={"secret": SYNTHETIC_SECRET})

    class FailingParser:
        parse_args = staticmethod(fail)

    monkeypatch.setattr(cli, "build_parser", fail if failure_stage == "build" else FailingParser)
    if broken_stderr:
        original_print = print

        def print_with_closed_stderr(*args: object, **kwargs: Any) -> None:
            if kwargs.get("file") is cli.sys.stderr:
                raise BrokenPipeError(secret_path)
            original_print(*args, **kwargs)

        monkeypatch.setattr("builtins.print", print_with_closed_stderr)

    assert cli.main(["external-review", "preflight", secret_path]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    if broken_stderr:
        assert captured.err == ""
    else:
        assert json.loads(captured.err) == {
            "status": "rejected",
            "reason_codes": ["STORAGE_ERROR"],
        }
    assert secret_path not in captured.err
    assert SYNTHETIC_SECRET not in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "identity",
    [
        "{root}\n",
        "{root}\n{head}\nmain\nextra\n",
        "{root}\ninvalid-head\nmain\n",
        "{root}\n{head}\n\n",
        "{root}\n{head}\nmain branch\n",
        "{root}\n{head}\nmain\x00branch\n",
        "{root}\n{head}\nmain\x7fbranch\n",
        "{root}/wrong\n{head}\nmain\n",
    ],
)
def test_checkout_rejects_invalid_git_identity_before_status(
    tmp_path: Path, identity: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def identity_only(root: Path, *arguments: str) -> bytes:
        calls.append(arguments)
        assert len(calls) == 1
        return identity.format(root=root.as_posix(), head="a" * 40).encode()

    monkeypatch.setattr(external_review, "_read_only_git", identity_only)
    with pytest.raises(ContractError) as caught:
        external_review._read_only_checkout(tmp_path)
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_GIT_BINDING_STALE")
    assert len(calls) == 1


class GitProcess:
    """Only owned process operations are available; direct wait is forbidden."""

    pid = 421

    def __init__(
        self,
        events: list[object],
        *,
        initial: BaseException | None = None,
        returncode: int | None = None,
        drain_error: BaseException | None = None,
        kill_error: BaseException | None = None,
        close_error: BaseException | None = None,
    ) -> None:
        self.events = events
        self.initial = initial
        self.returncode = returncode
        self.drain_error = drain_error
        self.kill_error = kill_error
        self.stdout = SimpleNamespace(close=lambda: self.close("stdout", close_error))
        self.stderr = SimpleNamespace(close=lambda: self.close("stderr", close_error))

    def poll(self) -> int | None:
        return self.returncode

    def kill(self) -> None:
        self.events.append("direct_kill")
        if self.returncode is not None:
            return  # Popen.kill() cannot signal a known-reaped retained child.
        if self.kill_error is not None:
            raise self.kill_error
        self.returncode = -9

    def wait(self, *, timeout: int) -> int:
        raise AssertionError(f"An extra direct wait({timeout}) changes the configured bound")

    def communicate(self, *, timeout: int) -> tuple[bytes, bytes]:
        self.events.append(("communicate", timeout))
        if timeout == 10 and self.initial is not None:
            raise self.initial
        if timeout == 5 and self.drain_error is not None:
            raise self.drain_error
        assert timeout in {5, 10}
        self.returncode = 0 if self.returncode is None else self.returncode
        return b"opaque\x00\xff\r\n", SYNTHETIC_SECRET.encode()

    def close(self, name: str, error: BaseException | None) -> None:
        self.events.append(f"close_{name}")
        if error is not None:
            raise error


def git_platform(
    platform: str, events: list[object], monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    environment = {**os.environ, "SystemRoot": "C:/Windows", "GIT_OPTIONAL_LOCKS": "1"}
    monkeypatch.setattr(
        external_review,
        "os",
        SimpleNamespace(
            name=platform,
            environ=environment,
            killpg=lambda pid, sig: events.append(("killpg", pid, sig)),
        ),
    )
    monkeypatch.setattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(signal, "SIGKILL", 9, raising=False)
    return environment


@pytest.mark.parametrize("platform", ["nt", "posix"])
@pytest.mark.parametrize("returncode", [0, 7])
def test_read_only_git_preserves_binary_transport_and_completed_command(
    tmp_path: Path, platform: str, returncode: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[object] = []
    environment = git_platform(platform, events, monkeypatch)
    original_environment = dict(environment)
    actual_environment = dict(os.environ)
    process = GitProcess(events, returncode=returncode)
    spawns: list[tuple[list[str], dict[str, Any]]] = []

    def spawn(argv: list[str], **options: Any) -> GitProcess:
        spawns.append((argv, options))
        return process

    def forbidden_cleanup(_process: Any) -> None:
        raise AssertionError("A drained command must not be cleaned up again")

    monkeypatch.setattr(subprocess, "Popen", spawn)
    monkeypatch.setattr(external_review, "_cleanup_read_only_git", forbidden_cleanup)
    arguments = ("rev-parse", "HEAD", SYNTHETIC_SECRET)
    if returncode == 0:
        assert external_review._read_only_git(tmp_path, *arguments) == b"opaque\x00\xff\r\n"
    else:
        with pytest.raises(ContractError) as caught:
            external_review._read_only_git(tmp_path, *arguments)
        assert_safe_error(caught.value, "EXTERNAL_REVIEW_GIT_BINDING_STALE")
        assert str(tmp_path) not in json.dumps(caught.value.to_dict())
    assert spawns == [
        (
            ["git", "--no-optional-locks", *arguments],
            {
                "cwd": tmp_path,
                "env": {**environment, "GIT_OPTIONAL_LOCKS": "0"},
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "start_new_session": platform != "nt",
                "creationflags": 512 if platform == "nt" else 0,
            },
        )
    ]
    assert spawns[0][1]["env"] is not environment
    assert "stdin" not in spawns[0][1]  # The existing inherited stdin is retained.
    assert "text" not in spawns[0][1] and "encoding" not in spawns[0][1]
    assert environment == original_environment and dict(os.environ) == actual_environment
    assert events == [("communicate", 10), "close_stdout", "close_stderr"]


def test_read_only_git_spawn_failure_is_safe_without_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = OSError(f"spawn failed {SYNTHETIC_SECRET} {tmp_path}")

    def fail_spawn(*args: object, **options: object) -> Any:
        raise original

    def forbidden_cleanup(_process: Any) -> None:
        raise AssertionError("Failed spawn returned no owned process")

    monkeypatch.setattr(subprocess, "Popen", fail_spawn)
    monkeypatch.setattr(external_review, "_cleanup_read_only_git", forbidden_cleanup)
    with pytest.raises(ContractError) as caught:
        external_review._read_only_git(tmp_path, SYNTHETIC_SECRET)
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_GIT_BINDING_STALE")
    assert caught.value.__cause__ is original
    assert str(tmp_path) not in json.dumps(caught.value.to_dict())


@pytest.mark.parametrize("platform", ["nt", "posix"])
@pytest.mark.parametrize("already_exited", [False, True])
@pytest.mark.parametrize("failure_kind", ["timeout", "oserror", "interrupt", "exit", "unexpected"])
def test_read_only_git_owns_cleanup_and_preserves_initiating_exception(
    tmp_path: Path,
    platform: str,
    already_exited: bool,
    failure_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = {
        "timeout": subprocess.TimeoutExpired(SYNTHETIC_SECRET, 10, b"partial", b"secret"),
        "oserror": OSError(SYNTHETIC_SECRET),
        "interrupt": KeyboardInterrupt(SYNTHETIC_SECRET),
        "exit": SystemExit(SYNTHETIC_SECRET),
        "unexpected": RuntimeError(SYNTHETIC_SECRET),
    }[failure_kind]
    original_args = original.args
    events: list[object] = []
    git_platform(platform, events, monkeypatch)
    direct = GitProcess(events, initial=original, returncode=0 if already_exited else None)
    spawns: list[tuple[list[str], dict[str, Any]]] = []

    class Helper:
        def wait(self, *, timeout: int) -> int:
            events.append(("helper_wait", timeout))
            assert timeout == 5
            return 0

    def spawn(argv: list[str], **options: Any) -> Any:
        spawns.append((argv, options))
        return direct if len(spawns) == 1 else Helper()

    monkeypatch.setattr(subprocess, "Popen", spawn)
    expected_error = ContractError if failure_kind in {"timeout", "oserror"} else type(original)
    with pytest.raises(expected_error) as caught:
        external_review._read_only_git(tmp_path, SYNTHETIC_SECRET)
    if isinstance(caught.value, ContractError):
        assert_safe_error(caught.value, "EXTERNAL_REVIEW_GIT_BINDING_STALE")
        assert caught.value.__cause__ is original
    else:
        assert caught.value is original and caught.value.args == original_args
    expected: list[object] = [("communicate", 10)]
    if not already_exited:
        if platform == "nt":
            assert spawns[1] == (
                [str(Path("C:/Windows") / "System32" / "taskkill.exe"), "/PID", "421", "/T", "/F"],
                {
                    "stdin": subprocess.DEVNULL,
                    "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL,
                    "creationflags": 0x08000000,
                },
            )
            expected.append(("helper_wait", 5))
        else:
            expected.append(("killpg", direct.pid, signal.SIGKILL))
    expected.append("direct_kill")
    assert len(spawns) == (2 if platform == "nt" and not already_exited else 1)
    assert events == expected + [("communicate", 5), "close_stdout", "close_stderr"]


@pytest.mark.parametrize(
    "secondary_stage",
    ["spawn", "wait", "helper_kill", "helper_wait", "direct_kill", "drain", "close"],
)
@pytest.mark.parametrize("failure_kind", ["interrupt", "exit", "unexpected"])
def test_read_only_git_secondary_cleanup_failures_do_not_replace_first_exception(
    tmp_path: Path,
    secondary_stage: str,
    failure_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = {
        "interrupt": KeyboardInterrupt("first interrupt"),
        "exit": SystemExit("first exit"),
        "unexpected": RuntimeError("first unexpected failure"),
    }[failure_kind]
    events: list[object] = []
    git_platform("nt", events, monkeypatch)
    direct = GitProcess(
        events,
        initial=original,
        drain_error=KeyboardInterrupt("secondary drain") if secondary_stage == "drain" else None,
        kill_error=OSError("secondary direct kill") if secondary_stage == "direct_kill" else None,
        close_error=OSError("secondary close") if secondary_stage == "close" else None,
    )
    spawns = 0

    class Helper:
        def wait(self, *, timeout: int) -> int:
            events.append(("helper_wait", timeout))
            if secondary_stage == "wait":
                raise OSError("secondary wait")
            if timeout == 5:
                raise subprocess.TimeoutExpired("secondary helper", timeout)
            assert timeout == 1
            if secondary_stage == "helper_wait":
                raise subprocess.TimeoutExpired("secondary final helper", timeout)
            return 0

        def kill(self) -> None:
            events.append("helper_kill")
            if secondary_stage == "helper_kill":
                raise SystemExit("secondary helper kill")

    def spawn(argv: list[str], **options: object) -> Any:
        nonlocal spawns
        spawns += 1
        if spawns == 1:
            return direct
        events.append("helper_spawn")
        if secondary_stage == "spawn":
            raise OSError("secondary helper spawn")
        return Helper()

    monkeypatch.setattr(subprocess, "Popen", spawn)
    with pytest.raises(type(original)) as caught:
        external_review._read_only_git(tmp_path, "rev-parse", "HEAD")
    assert caught.value is original
    assert events[0] == ("communicate", 10)
    assert "direct_kill" in events and ("communicate", 5) in events
    assert [item for item in events if isinstance(item, tuple) and item[0] == "helper_wait"] == (
        [] if secondary_stage == "spawn" else [("helper_wait", 5), ("helper_wait", 1)]
    )
    if secondary_stage == "drain":
        assert "close_stdout" not in events and "close_stderr" not in events
    else:
        assert "close_stdout" in events and "close_stderr" in events


@pytest.mark.parametrize("platform", ["nt", "posix"])
def test_read_only_git_failed_drain_cannot_close_pipes_or_return_partial_output(
    tmp_path: Path, platform: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[object] = []
    git_platform(platform, events, monkeypatch)
    initial = subprocess.TimeoutExpired(SYNTHETIC_SECRET, 10, b"partial", b"partial error")
    process = GitProcess(
        events,
        initial=initial,
        returncode=0,
        drain_error=subprocess.TimeoutExpired("drain", 5, b"more partial", b"more error"),
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(ContractError) as caught:
        external_review._read_only_git(tmp_path, SYNTHETIC_SECRET)
    assert_safe_error(caught.value, "EXTERNAL_REVIEW_GIT_BINDING_STALE")
    assert caught.value.__cause__ is initial
    assert events == [("communicate", 10), "direct_kill", ("communicate", 5)]


@pytest.mark.parametrize("failure_kind", ["interrupt", "exit", "unexpected"])
def test_read_only_git_first_close_failure_preserves_original_identity_without_cleanup(
    tmp_path: Path, failure_kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = {
        "interrupt": KeyboardInterrupt("first close interrupt"),
        "exit": SystemExit("first close exit"),
        "unexpected": RuntimeError("first close unexpected failure"),
    }[failure_kind]
    events: list[object] = []
    process = GitProcess(events, returncode=0, close_error=original)

    def forbidden_cleanup(_process: Any) -> None:
        raise AssertionError("The first close failed after a successful drain")

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(external_review, "_cleanup_read_only_git", forbidden_cleanup)
    with pytest.raises(type(original)) as caught:
        external_review._read_only_git(tmp_path, "rev-parse", "HEAD")
    assert caught.value is original
    assert events == [("communicate", 10), "close_stdout", "close_stdout", "close_stderr"]


@pytest.mark.parametrize("cleanup_failure", [ProcessLookupError, OSError, KeyboardInterrupt])
def test_read_only_git_failed_posix_group_signal_preserves_original_exception(
    tmp_path: Path, cleanup_failure: type[BaseException], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = RuntimeError("first synthetic failure")
    events: list[object] = []
    git_platform("posix", events, monkeypatch)

    def failed_group(pid: int, sig: int) -> None:
        events.append(("killpg", pid, sig))
        raise cleanup_failure("secondary group failure")

    monkeypatch.setattr(external_review.os, "killpg", failed_group)
    process = GitProcess(events, initial=original)
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **options: process)
    with pytest.raises(RuntimeError) as caught:
        external_review._read_only_git(tmp_path, "rev-parse", "HEAD")
    assert caught.value is original
    assert events == [
        ("communicate", 10),
        ("killpg", process.pid, signal.SIGKILL),
        "direct_kill",
        ("communicate", 5),
        "close_stdout",
        "close_stderr",
    ]
