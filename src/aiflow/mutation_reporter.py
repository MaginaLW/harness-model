"""Controlled pytest subprocess for the five reviewed detector signatures.

This reporter shares a process with the tests and is not a security sandbox.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import stat
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

_PYTEST: Any = None
_STOPPED_SETUP = {"failed", "skipped", "xfailed"}


def _protocol() -> ModuleType:
    path = Path(__file__).with_name("mutation_protocol.py")
    spec = importlib.util.spec_from_file_location("_aiflow_mutation_protocol", path)
    if spec is None or spec.loader is None:
        raise ValueError("report protocol unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_WIRE = _protocol()
_CONTRACTS = {
    "MUT-V2-001": (
        "tests/unit/test_policy.py",
        _WIRE.REVIEWED_INPUT_SHA256["tests/unit/test_policy.py"],
        "test_v2_policy_requires_ordered_semantic_prefix_and_fixed_required_extras",
        "src/aiflow/policy.py",
        "aiflow.policy",
        "_validate_cross_file",
        "policy_valid",
        (206,),
    ),
    "MUT-V2-002": (
        "tests/integration/test_verify_command.py",
        _WIRE.REVIEWED_INPUT_SHA256["tests/integration/test_verify_command.py"],
        "test_v2_actor_rejections_happen_before_plan_or_runner",
        "src/aiflow/verifier_service.py",
        "aiflow.verifier_service",
        "validate_verifier_actor",
        "actor_unexpected",
        (1272,),
    ),
    "MUT-V2-003": (
        "tests/integration/test_mutation_manifest_contract.py",
        _WIRE.REVIEWED_INPUT_SHA256["tests/integration/test_mutation_manifest_contract.py"],
        "test_v2_code_approval_rejects_nonpassing_required_check",
        "src/aiflow/approval.py",
        "aiflow.approval",
        "_v2_evidence_current",
        "approval_assert",
        (148,),
    ),
    "MUT-V2-004": (
        "tests/integration/test_mutation_manifest_contract.py",
        _WIRE.REVIEWED_INPUT_SHA256["tests/integration/test_mutation_manifest_contract.py"],
        "test_v2_gate_rejects_non_killed_mutation",
        "src/aiflow/gate.py",
        "aiflow.gate",
        "_v2_gate_facts",
        "gate_assert",
        (169,),
    ),
    "MUT-V2-005": (
        "tests/unit/test_evidence.py",
        _WIRE.REVIEWED_INPUT_SHA256["tests/unit/test_evidence.py"],
        "test_v2_snapshot_rejects_mutation_of_bound_verification_facts",
        "src/aiflow/evidence.py",
        "aiflow.evidence",
        "validate_v2_snapshot",
        "snapshot_raises",
        (165,),
    ),
}


def _safe_file(root: Path, relative: str) -> Path:
    current = root
    parts = relative.split("/")
    if any(part in {"", ".", ".."} or "\\" in part or ":" in part for part in parts):
        raise ValueError("invalid controlled path")
    for index, part in enumerate(parts):
        current = current / part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("controlled path contains a link")
        if index < len(parts) - 1:
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError("invalid controlled directory")
        elif not stat.S_ISREG(info.st_mode):
            raise ValueError("invalid controlled file")
    return current


def _test_digest(path: Path) -> str:
    raw = path.read_bytes()
    raw.decode("utf-8", "strict")
    normalized = raw.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise ValueError("invalid detector line ending")
    return hashlib.sha256(normalized).hexdigest()


def _node_map(mutation_id: str) -> dict[str, str]:
    test_path, _, function, *_ = _CONTRACTS[mutation_id]
    prefix = f"{test_path}::{function}"
    if mutation_id == "MUT-V2-002":
        return {
            f"{prefix}[ -VERIFIER_ACTOR_REQUIRED]": "blank",
            f"{prefix}[ implementer -VERIFIER_ACTOR_NOT_INDEPENDENT]": "same_actor",
        }
    return {prefix: "only"}


def _module_path(module: ModuleType) -> Path:
    if not isinstance(module.__file__, str):
        raise ValueError("module source unavailable")
    return Path(module.__file__).resolve()


def _reference_ok(mutation_id: str, root: Path, digest: str, item: Any) -> bool:
    test_path, test_hash, test_name, target_path, module_name, symbol, _, _ = _CONTRACTS[
        mutation_id
    ]
    try:
        detector = _safe_file(root, test_path)
        target = _safe_file(root, target_path)
        package = _safe_file(root, "src/aiflow/__init__.py")
        conftests = {
            parent / "conftest.py"
            for parent in (root, root / "tests", detector.parent)
            if (parent / "conftest.py").is_file()
        }
        loaded_conftests = {
            _module_path(plugin)
            for plugin in item.config.pluginmanager.get_plugins()
            if isinstance(plugin, ModuleType)
            and isinstance(filename := getattr(plugin, "__file__", None), str)
            and Path(filename).name == "conftest.py"
        }
        if (
            _test_digest(detector) != test_hash
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
            or item.config.rootpath != root
            or item.config.inipath != _safe_file(root, "pyproject.toml")
            or loaded_conftests != conftests
            or getattr(item.module, test_name) is not item.obj
            or Path(item.obj.__code__.co_filename).resolve() != detector
        ):
            return False
        module = sys.modules[module_name]
        aiflow = sys.modules["aiflow"]
        function = getattr(module, symbol)
        if (
            Path(item.module.__file__).resolve() != detector.resolve()
            or _module_path(module) != target.resolve()
            or _module_path(aiflow) != package.resolve()
            or Path(function.__code__.co_filename).resolve() != target.resolve()
        ):
            return False
        if mutation_id in {"MUT-V2-001", "MUT-V2-002", "MUT-V2-005"}:
            errors = sys.modules["aiflow.errors"]
            errors_path = _safe_file(root, "src/aiflow/errors.py")
            exception_name = "PolicyError" if mutation_id == "MUT-V2-001" else "ContractError"
            if _module_path(errors) != errors_path.resolve() or getattr(
                item.module, exception_name
            ) is not getattr(errors, exception_name):
                return False
        if mutation_id == "MUT-V2-002":
            service = sys.modules["aiflow.verification_service"]
            service_path = _safe_file(root, "src/aiflow/verification_service.py")
            helpers = sys.modules["test_begin_close_commands"]
            helper_path = _safe_file(root, "tests/integration/test_begin_close_commands.py")
            return (
                item.module.verification_service is service
                and _module_path(service) == service_path.resolve()
                and service.validate_verifier_actor is function
                and _module_path(helpers) == helper_path
                and all(
                    getattr(item.module, name) is getattr(helpers, name)
                    and Path(getattr(helpers, name).__code__.co_filename).resolve() == helper_path
                    for name in (
                        "create_repository",
                        "start",
                        "make_ready",
                        "commit_all",
                        "run_git",
                    )
                )
            )
        if mutation_id in {"MUT-V2-003", "MUT-V2-004"}:
            return getattr(item.module, module_name.rsplit(".", 1)[1]) is module
        return getattr(item.module, symbol) is function
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        return False


def _failure(mutation_id: str, item: Any, call: Any, detector: Path) -> dict[str, str]:
    unknown = {"exception": "unknown", "anchor": "unknown", "semantic": "unknown"}
    if call.excinfo is None:
        return unknown
    error = call.excinfo.value
    try:
        lines = _CONTRACTS[mutation_id][7]
        matched = {
            entry.lineno + 1
            for entry in call.excinfo.traceback
            if Path(str(entry.path)).resolve() == detector.resolve() and entry.lineno + 1 in lines
        }
        if len(matched) != 1:
            return unknown
        anchor = _CONTRACTS[mutation_id][6]
        if mutation_id == "MUT-V2-001":
            errors = sys.modules["aiflow.errors"]
            if (
                type(error) is errors.PolicyError
                and getattr(error, "code", None) == "POLICY_CHECK_REFERENCE_INVALID"
            ):
                return {
                    "exception": "policy_error",
                    "anchor": anchor,
                    "semantic": "policy_check_reference_invalid",
                }
        elif mutation_id == "MUT-V2-002":
            if (
                type(error) is AssertionError
                and str(error) == "V2 rejection must happen before plan parsing or runner start"
            ):
                return {
                    "exception": "assertion_error",
                    "anchor": anchor,
                    "semantic": "actor_sentinel",
                }
        elif mutation_id in {"MUT-V2-003", "MUT-V2-004"}:
            terminal = call.excinfo.traceback[-1]
            if (
                type(error) is AssertionError
                and Path(str(terminal.path)).resolve() == detector.resolve()
                and terminal.lineno + 1 in lines
            ):
                return {"exception": "assertion_error", "anchor": anchor, "semantic": "none"}
        elif mutation_id == "MUT-V2-005":
            trace = call.excinfo.traceback
            contract = sys.modules["aiflow.errors"].ContractError
            if (
                len(trace) >= 3
                and Path(str(trace[-3].path)).resolve() == detector.resolve()
                and trace[-3].lineno + 1 in lines
                and trace[-2].frame.code.raw is type(_PYTEST.raises(contract)).__exit__.__code__
                and trace[-1].frame.code.raw is type(_PYTEST.fail).__call__.__code__
                and type(error) is _PYTEST.fail.Exception
                and str(error) == "DID NOT RAISE ContractError"
            ):
                return {
                    "exception": "pytest_failed",
                    "anchor": anchor,
                    "semantic": "missing_contract_error",
                }
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        return unknown
    return unknown


class _Reporter:
    def __init__(self, mutation_id: str, root: Path, target_sha256: str) -> None:
        self.mutation_id = mutation_id
        self.root = root
        self.target_sha256 = target_sha256
        self.nodes = _node_map(mutation_id)
        self.cases: dict[str, dict[str, Any]] = {
            token: {
                "case": token,
                "setup": "notrun",
                "call": "notrun",
                "teardown": "notrun",
                "failure": None,
            }
            for token in self.nodes.values()
        }
        self.collected = False
        self.exitstatus: int | None = None
        self.reference_ok = True
        self.events = 0
        self.invalid = False

    def pytest_collection_finish(self, session: Any) -> None:
        if self.collected or self.exitstatus is not None:
            self.invalid = True
            return
        self.collected = (
            len(session.items) == len(self.nodes)
            and {item.nodeid for item in session.items} == self.nodes.keys()
        )
        if not self.collected:
            self.invalid = True
            _PYTEST.exit("invalid detector collection", returncode=2)

    def pytest_sessionfinish(self, session: Any, exitstatus: int) -> None:
        if not self.collected or self.exitstatus is not None or exitstatus not in {0, 1}:
            self.invalid = True
        self.exitstatus = exitstatus

    def pytest_runtest_makereport(self, item: Any, call: Any) -> Any:
        outcome = yield
        report = outcome.get_result()
        token = self.nodes.get(item.nodeid)
        self.events += 1
        if (
            not self.collected
            or self.exitstatus is not None
            or token is None
            or self.events > 3 * len(self.nodes)
            or report.when not in {"setup", "call", "teardown"}
            or report.nodeid != item.nodeid
            or report.when != call.when
        ):
            self.invalid = True
            return
        case = self.cases[token]
        if (
            case[report.when] != "notrun"
            or (report.when == "call" and case["setup"] != "passed")
            or (
                report.when == "teardown"
                and case["call"] == "notrun"
                and case["setup"] not in _STOPPED_SETUP
            )
        ):
            self.invalid = True
            return
        state = report.outcome
        if hasattr(report, "wasxfail"):
            state = "xfailed" if report.skipped else "xpassed"
        case[report.when] = state
        self.reference_ok = self.reference_ok and _reference_ok(
            self.mutation_id, self.root, self.target_sha256, item
        )
        if report.when == "call" and state == "failed":
            case["failure"] = _failure(
                self.mutation_id, item, call, self.root / _CONTRACTS[self.mutation_id][0]
            )

    def report(self) -> dict[str, Any]:
        if (
            not self.collected
            or self.exitstatus is None
            or self.invalid
            or self.events != 3 * len(self.nodes)
        ):
            raise ValueError("invalid detector run")
        return {
            "protocol": "1.0",
            "mutation_id": self.mutation_id,
            "python": "3.11",
            "pytest": "9.1.1",
            "platform": "windows",
            "cases": list(self.cases.values()),
            "imports": {"target_sha256": self.target_sha256, "reference_ok": self.reference_ok},
            "complete": True,
        }

    def stopped_before_call(self) -> bool:
        """Recognize pytest omitting a call after its setup failed or requested a skip."""
        if not self.collected or self.exitstatus is None or self.invalid or not self.reference_ok:
            return False
        omitted = 0
        for case in self.cases.values():
            if case["setup"] == "notrun" or case["teardown"] == "notrun":
                return False
            if case["call"] == "notrun":
                if case["setup"] not in _STOPPED_SETUP:
                    return False
                omitted += 1
        return omitted > 0 and self.events + omitted == 3 * len(self.nodes)


def main(argv: list[str]) -> int:
    """Run exactly one fixed detector; write only a bounded report to stdout."""
    global _PYTEST
    report_fd = os.dup(1)
    os.set_inheritable(report_fd, False)
    null_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(null_fd, 1)
    os.dup2(null_fd, 2)
    os.close(null_fd)
    try:
        if os.read(0, 1) != b"":
            return 2
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        os.environ.pop("PYTEST_ADDOPTS", None)
        os.environ.pop("PYTEST_PLUGINS", None)
        import pytest

        _PYTEST = pytest
        pytest.hookimpl(hookwrapper=True)(_Reporter.pytest_runtest_makereport)
        if len(argv) != 3 or argv[0] not in _CONTRACTS:
            return 2
        mutation_id, raw_root, digest = argv
        if (
            sys.version_info[:2] != (3, 11)
            or pytest.__version__ != "9.1.1"
            or sys.platform != "win32"
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            return 2
        root = Path(raw_root).resolve(strict=True)
        test_path, test_hash, function, target_path, *_ = _CONTRACTS[mutation_id]
        detector = _safe_file(root, test_path)
        target = _safe_file(root, target_path)
        if (
            _test_digest(detector) != test_hash
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            return 2
        if any(name == "aiflow" or name.startswith("aiflow.") for name in sys.modules):
            return 2
        sys.path[:0] = [str(root), str(root / "src")]
        reporter = _Reporter(mutation_id, root, digest)
        result = int(
            pytest.main(
                [
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "-o",
                    "addopts=",
                    "-c",
                    str(_safe_file(root, "pyproject.toml")),
                    "--confcutdir",
                    str(root),
                    "--rootdir",
                    str(root),
                    f"{test_path}::{function}",
                ],
                plugins=[reporter],
            )
        )
        if result not in {0, 1} or result != reporter.exitstatus:
            return 2
        if reporter.stopped_before_call():
            return int(_WIRE.EARLY_STOP_EXIT_CODE)
        payload = _WIRE.encode_report(reporter.report())
        _WIRE.parse_report(payload, mutation_id, digest)
        written = 0
        while written < len(payload):
            count = os.write(report_fd, payload[written:])
            if count <= 0:
                return 2
            written += count
        return result
    except BaseException:
        return 2
    finally:
        os.close(report_fd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
