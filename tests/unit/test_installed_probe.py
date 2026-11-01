"""Real baseline behavior for the five fixed, package-owned governance probes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "probe_id, expected_cases",
    [
        (
            "MUT-V2-001",
            [
                ("policy_complete", {"version": "2.6.0"}),
                ("policy_missing_targeted_mutation", {"error": "POLICY_CHECK_REFERENCE_INVALID"}),
            ],
        ),
        (
            "MUT-V2-002",
            [
                (
                    "verifier_blank",
                    {"errors": ["VERIFIER_IMPLEMENTER_MISSING", "VERIFIER_ACTOR_REQUIRED"]},
                ),
                ("verifier_distinct", {"actors": ["implementer", "independent-verifier"]}),
                ("verifier_same", {"error": "VERIFIER_ACTOR_NOT_INDEPENDENT"}),
            ],
        ),
        (
            "MUT-V2-003",
            [
                ("approval_passing_checks", {"current": True, "mutation_calls": 1}),
                ("approval_failed_required_check", {"current": False, "mutation_calls": 0}),
            ],
        ),
        (
            "MUT-V2-004",
            [
                (
                    "gate_killed_mutations",
                    {"checks_current": True, "mutation_killed": True, "mutation_calls": 1},
                ),
                (
                    "gate_survived_mutation",
                    {"checks_current": True, "mutation_killed": False, "mutation_calls": 1},
                ),
            ],
        ),
        (
            "MUT-V2-005",
            [
                ("snapshot_unchanged", {"errors": [None, None], "same_snapshot": True}),
                (
                    "snapshot_tampered",
                    {"errors": ["EVIDENCE_SNAPSHOT_STALE", "EVIDENCE_SNAPSHOT_STALE"]},
                ),
            ],
        ),
    ],
    ids=[f"MUT-V2-{index:03d}" for index in range(1, 6)],
)
def test_fixed_installed_probe_baseline(
    probe_id: str,
    expected_cases: list[tuple],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Keep missing implementation a test failure, not a suite collection failure.
    import aiflow.installed_probe as probe
    from aiflow.installed_probe import run_probe

    if probe_id == "MUT-V2-001":
        from aiflow.resource_bundle import build_bundle

        # Editable/source installs have no bundled resources. Supply real built
        # bytes at the resource boundary; the bundle validator and guard run as-is.
        manifest, files = build_bundle(Path(__file__).resolve().parents[2])
        bundle = tmp_path / "bundle"
        bundle.mkdir()
        for relative, data in files.items():
            destination = bundle / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        monkeypatch.setattr(probe, "_bundle_root", lambda: bundle)

    report = run_probe(probe_id)

    assert set(report) == {"protocol", "probe_id", "cases", "terminal"}
    assert report["protocol"] == "installed-probe-v1"
    assert report["probe_id"] == probe_id
    assert report["terminal"] == "complete"
    assert isinstance(report["cases"], list)
    assert [(case["id"], case["observed"]) for case in report["cases"]] == expected_cases
    for case in report["cases"]:
        assert set(case) == {"id", "setup", "call", "teardown", "observed", "exception"}
        assert (case["setup"], case["call"], case["teardown"]) == ("passed", "passed", "passed")
        assert case["exception"] is None
    assert json.loads(json.dumps(report, allow_nan=False)) == report


@pytest.mark.parametrize(
    "probe_id",
    ["", "MUT-V2-000", "MUT-V2-006", "../MUT-V2-001", "MUT-V2-001 "],
)
def test_installed_probe_selection_is_closed(probe_id: str) -> None:
    from aiflow.installed_probe import run_probe

    with pytest.raises(ValueError):
        run_probe(probe_id)


@pytest.mark.parametrize("failed_phase", ["setup", "call", "teardown"])
def test_probe_protocol_retains_exception_phase_and_terminal_traceback(
    monkeypatch: pytest.MonkeyPatch, failed_phase: str
) -> None:
    """Fault-inject the case lifecycle, without a Job or execution-PASS claim."""
    import aiflow.installed_probe as probe

    def failure():
        raise RuntimeError("synthetic " + failed_phase + " failure")

    def setup(_probe_id, _case_id, stack, context):
        if failed_phase == "setup":
            failure()
        context["observed"] = {"synthetic_protocol_fixture": True}
        if failed_phase == "teardown":
            stack.callback(failure)

    def call(context):
        if failed_phase == "call":
            failure()

    monkeypatch.setattr(probe, "_setup", setup)
    monkeypatch.setitem(probe._CASE_CALLS, "policy_complete", call)
    result = probe._run_case("MUT-V2-001", "policy_complete")
    assert result[failed_phase] == "failed"
    assert result["setup"] == ("failed" if failed_phase == "setup" else "passed")
    assert (
        result["call"] == {"setup": "not_run", "call": "failed", "teardown": "passed"}[failed_phase]
    )
    assert result["teardown"] == ("failed" if failed_phase == "teardown" else "passed")
    assert result["exception"]["type"] == "RuntimeError"
    assert result["exception"]["message"] == "synthetic " + failed_phase + " failure"
    assert result["exception"]["frames"][-1]["function"] == "failure"
    assert result["exception"]["frames"][-1]["path"] == __file__
