"""Independent numerical and effect-boundary checks for synthetic detection counts."""

from __future__ import annotations

import builtins
import copy
import hashlib
import importlib.util
import io
import json
import math
import os
import socket
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "tools" / "analysis" / "review_detection.py"
PRIVATE_MARKER = "PRIVATE_SYNTHETIC_INPUT_DO_NOT_ECHO"


@pytest.fixture
def detection(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("review_detection", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _document(n: object = 10, k: object = 5, **changes: object) -> dict[str, object]:
    document = {"schema_version": "1.0", "record_origin": "synthetic", "n": n, "k": k}
    document.update(changes)
    return document


def _fraction_cdf(n: int, k: int, probability: float) -> Fraction:
    """Exact arithmetic at a supplied float; deliberately does not solve for a root."""
    p = Fraction.from_float(probability)
    q = 1 - p
    return sum(
        (math.comb(n, j) * p**j * q ** (n - j) for j in range(k + 1)),
        start=Fraction(0),
    )


def _assert_independent_tails(result: dict[str, Any]) -> None:
    n, k = result["n"], result["k"]
    if k:
        assert abs(_fraction_cdf(n, k - 1, result["lower"]) - Fraction(39, 40)) < Fraction(
            1, 10**12
        )
    else:
        assert result["lower"] == 0
    if k < n:
        assert abs(_fraction_cdf(n, k, result["upper"]) - Fraction(1, 40)) < Fraction(1, 10**12)
    else:
        assert result["upper"] == 1


def test_no_positive_units_have_no_estimate_interval_or_precision_claim(detection: Any) -> None:
    report = detection.build_detection(_document(0, 0))

    assert report["calculation_status"] == "no_positive_units"
    assert report["conditional_result"] == {
        "n": 0,
        "k": 0,
        "proportion": None,
        "lower": None,
        "upper": None,
        "width": None,
        "precision_met": None,
    }


@pytest.mark.parametrize("n", [1, 2, 17, 104])
@pytest.mark.parametrize("all_detected", [False, True])
def test_extreme_counts_match_analytic_endpoints(
    detection: Any, n: int, all_detected: bool
) -> None:
    k = n if all_detected else 0
    result = detection.build_detection(_document(n, k))["conditional_result"]
    endpoint = 0.025 ** (1 / n)

    assert result["lower"] == pytest.approx(endpoint if all_detected else 0, rel=0, abs=2e-14)
    assert result["upper"] == pytest.approx(1 if all_detected else 1 - endpoint, rel=0, abs=2e-14)
    assert result["proportion"] == (1 if all_detected else 0)
    assert result["width"] == result["upper"] - result["lower"]
    assert result["precision_met"] is (result["width"] <= 0.20)


@pytest.mark.parametrize("n,k", [(2, 1), (9, 1), (9, 4), (17, 16), (103, 51), (103, 52)])
def test_mixed_counts_satisfy_exact_rational_cdf_tails(detection: Any, n: int, k: int) -> None:
    report = detection.build_detection(_document(n, k))
    result = report["conditional_result"]

    assert report["calculation_status"] == "calculated"
    assert set(result) == {"n", "k", "proportion", "lower", "upper", "width", "precision_met"}
    assert result["n"] == n and result["k"] == k
    assert result["proportion"] == k / n
    assert 0 < result["lower"] < k / n < result["upper"] < 1
    assert result["width"] == result["upper"] - result["lower"]
    _assert_independent_tails(result)


@pytest.mark.parametrize("k", [51, 52])
def test_103_center_counts_do_not_meet_twenty_percentage_point_total_width(
    detection: Any, k: int
) -> None:
    result = detection.build_detection(_document(103, k))["conditional_result"]

    assert result["width"] == pytest.approx(0.20029998252241171465, rel=0, abs=2e-14)
    assert result["width"] > 0.20
    assert result["precision_met"] is False


def test_all_104_outcomes_meet_width_and_independent_tail_conditions(detection: Any) -> None:
    results = [
        detection.build_detection(_document(104, k))["conditional_result"] for k in range(105)
    ]
    for result in results:
        _assert_independent_tails(result)
        assert result["width"] == result["upper"] - result["lower"]
        assert result["width"] < 0.20
        assert result["precision_met"] is True

    worst = max(results, key=lambda result: result["width"])
    assert worst["k"] == 52, "The maximizer must follow from enumeration, not an assumption."
    assert worst["width"] == pytest.approx(0.19932214919876625592, rel=0, abs=2e-14)


def test_results_do_not_grant_real_research_or_scoring_admission(detection: Any) -> None:
    document = _document(104, 52)
    original = copy.deepcopy(document)
    report = detection.build_detection(document)

    assert document == original
    assert report["schema_version"] == "1.0"
    assert report["measurement"] == "synthetic_review_detection"
    assert report["record_origin"] == "synthetic"
    assert report["source_assurance"] == "synthetic_supplied_counts"
    assert report["method"] == "clopper_pearson_equal_tailed"
    assert report["coverage"] == 0.95
    assert report["target_width"] == 0.20
    assert report["verified_n_max"] == 104
    assert report["method_status"] == "design_pending"
    assert report["probability_status"] == "unestimated"
    assert report["model_score_update_status"] == "not_implemented"
    assert report["actual_model_identity"] == "unknown"
    assert report["execution_allowed"] is False
    assert report["permission_effect"] == "none"
    assert report["ledger_effect"] == "none"
    assert "input_sha256" not in report and "executed_tool_sha256" not in report

    report["conditional_result"]["n"] = 0
    assert document == original
    assert detection.build_detection(document)["conditional_result"]["n"] == 104


@pytest.mark.parametrize("field", ["n", "k"])
@pytest.mark.parametrize("value", [True, False, 1.0, "1", None, [], {}, float("nan"), float("inf")])
def test_counts_must_be_integers_without_boolean_or_float_coercion(
    detection: Any, field: str, value: object
) -> None:
    with pytest.raises(ValueError):
        detection.build_detection(_document(**{field: value}))


@pytest.mark.parametrize("n,k", [(-1, 0), (105, 0), (2**2048, 1), (10, -1), (10, 11), (0, 1)])
def test_counts_outside_the_verified_domain_are_rejected(detection: Any, n: int, k: int) -> None:
    with pytest.raises(ValueError):
        detection.build_detection(_document(n, k))


@pytest.mark.parametrize("origin", ["real", "historical", "supplied", "Synthetic", None, True])
def test_non_synthetic_origin_cannot_be_relabelled(detection: Any, origin: object) -> None:
    with pytest.raises(ValueError):
        detection.build_detection(_document(record_origin=origin))


@pytest.mark.parametrize("version", ["2.0", "1", 1.0, 1, True, None])
def test_unsupported_schema_versions_are_rejected(detection: Any, version: object) -> None:
    with pytest.raises(ValueError):
        detection.build_detection(_document(schema_version=version))


@pytest.mark.parametrize("field", ["schema_version", "record_origin", "n", "k"])
def test_every_input_field_is_required(detection: Any, field: str) -> None:
    document = _document()
    del document[field]
    with pytest.raises(ValueError):
        detection.build_detection(document)


@pytest.mark.parametrize("document", [None, [], "synthetic", 1, True])
def test_input_must_be_an_object(detection: Any, document: object) -> None:
    with pytest.raises(ValueError):
        detection.build_detection(document)


@pytest.mark.parametrize("extra", ["approved", "execution_allowed", "source", "model_id"])
def test_extra_fields_cannot_supply_evidence_identity_or_permissions(
    detection: Any, extra: str
) -> None:
    with pytest.raises(ValueError):
        detection.build_detection(_document(**{extra: True}))


def _cli(payload: bytes, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "ascii"
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT)],
        input=payload,
        capture_output=True,
        check=False,
        cwd=cwd,
        env=environment,
        timeout=10,
    )


def test_standalone_cli_hashes_exact_input_and_executed_source_bytes(
    detection: Any, tmp_path: Path
) -> None:
    payload = b' { "schema_version": "1.0", "record_origin": "synthetic", "n": 17, "k": 4 }\n'
    original_source = SCRIPT.read_bytes()

    completed = _cli(payload, tmp_path)

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == b""
    assert completed.stdout.isascii()
    report = json.loads(completed.stdout)
    assert report.pop("input_sha256") == hashlib.sha256(payload).hexdigest()
    assert report.pop("executed_tool_sha256") == hashlib.sha256(original_source).hexdigest()
    assert report == detection.build_detection(json.loads(payload))
    assert SCRIPT.read_bytes() == original_source
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("field", ["schema_version", "record_origin", "n", "k"])
def test_cli_rejects_duplicate_keys_even_with_a_valid_last_value(field: str) -> None:
    document = _document()
    field_literal = json.dumps(field)
    pair = f"{field_literal}: {json.dumps(document[field])}"
    payload = json.dumps(document).replace(pair, f'{field_literal}: "{PRIVATE_MARKER}", {pair}', 1)
    assert json.loads(payload) == document

    result = _cli(payload.encode())

    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.strip()
    assert PRIVATE_MARKER.encode() not in result.stderr
    assert b"Traceback" not in result.stderr


@pytest.mark.parametrize(
    "payload",
    [
        b"not JSON PRIVATE_SYNTHETIC_INPUT_DO_NOT_ECHO",
        b"\xffPRIVATE_SYNTHETIC_INPUT_DO_NOT_ECHO",
        b"\xff\xfe",
        b'{"n":NaN,"private":"PRIVATE_SYNTHETIC_INPUT_DO_NOT_ECHO"}',
        b'{"k":Infinity,"private":"PRIVATE_SYNTHETIC_INPUT_DO_NOT_ECHO"}',
        b'{"k":-Infinity,"private":"PRIVATE_SYNTHETIC_INPUT_DO_NOT_ECHO"}',
        b"null",
        b"[]",
        b"[" * 1100 + b"]" * 1100,
        json.dumps(_document(record_origin=PRIVATE_MARKER)).encode(),
        json.dumps(_document(n=PRIVATE_MARKER)).encode(),
        json.dumps(_document(private=PRIVATE_MARKER)).encode(),
    ],
)
def test_cli_parse_and_validation_errors_are_safe_without_partial_output(payload: bytes) -> None:
    result = _cli(payload)

    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.strip()
    assert PRIVATE_MARKER.encode() not in result.stderr
    assert b"Traceback" not in result.stderr


def _deny_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Synthetic calculation attempted an external effect.")

    for module, names in (
        (socket, ("socket", "create_connection", "getaddrinfo")),
        (subprocess, ("Popen", "run", "call", "check_call", "check_output")),
        (os, ("open", "system", "popen", "mkdir", "remove", "unlink", "rename", "replace")),
        (Path, ("open", "read_bytes", "read_text", "write_bytes", "write_text", "mkdir")),
        (builtins, ("open",)),
        (io, ("open",)),
    ):
        for name in names:
            monkeypatch.setattr(module, name, denied)


def test_pure_function_does_not_read_write_spawn_or_connect(detection: Any) -> None:
    document = _document(104, 52)
    original = copy.deepcopy(document)
    with pytest.MonkeyPatch.context() as guard:
        _deny_effects(guard)
        report = detection.build_detection(document)

    assert document == original
    assert report["conditional_result"]["precision_met"] is True


def test_main_only_reads_own_source_for_hash_and_emits_stdout(
    detection: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = json.dumps(_document()).encode()
    source_bytes = SCRIPT.read_bytes()
    reads: list[Path] = []

    def read_own_source(path: Path) -> bytes:
        assert path == SCRIPT
        reads.append(path)
        return source_bytes

    with pytest.MonkeyPatch.context() as guard:
        guard.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload), encoding="utf-8"))
        guard.setattr(sys, "dont_write_bytecode", False)
        _deny_effects(guard)
        guard.setattr(Path, "read_bytes", read_own_source)
        code = detection.main([])
        assert sys.dont_write_bytecode is True

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    assert reads == [SCRIPT]
    report = json.loads(captured.out)
    assert report["input_sha256"] == hashlib.sha256(payload).hexdigest()
    assert report["executed_tool_sha256"] == hashlib.sha256(source_bytes).hexdigest()


def test_main_reports_stdin_read_failure_without_exposing_error_text(
    detection: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class UnreadableBuffer:
        def read(self) -> bytes:
            raise OSError(PRIVATE_MARKER)

    class UnreadableInput:
        buffer = UnreadableBuffer()

    monkeypatch.setattr(sys, "stdin", UnreadableInput())
    code = detection.main([])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.out == ""
    assert captured.err.strip()
    assert PRIVATE_MARKER not in captured.err
    assert "Traceback" not in captured.err


def test_source_hash_read_failure_has_no_partial_output(
    detection: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def failed_read(path: Path) -> bytes:
        raise OSError(PRIVATE_MARKER)

    monkeypatch.setattr(
        sys,
        "stdin",
        io.TextIOWrapper(io.BytesIO(json.dumps(_document()).encode()), encoding="utf-8"),
    )
    monkeypatch.setattr(Path, "read_bytes", failed_read)

    assert detection.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip()
    assert PRIVATE_MARKER not in captured.err
    assert "Traceback" not in captured.err
