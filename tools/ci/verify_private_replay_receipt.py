"""Read-only verification of a staged receipt. No PR code or private originals are loaded."""

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

REPOSITORY = "MaginaLW/harness-model"
ORDINARY = ".github/workflows/ai-quality-gate.yml"
PROTECTED = ".github/workflows/private-replay-receipt.yml"
NAMESPACE = "aiflow-private-v2-receipt-v1"
V2_NAMESPACE = "aiflow-private-v2-receipt-v2"
V2_CHECKS = frozenset(
    "contract scope ruff_check ruff_format_check smoke unit_tests regression_tests mypy "
    "coverage_xml diff_coverage acceptance integration "
    "targeted_mutation independent_verifier".split()
)
READ = Callable[[str], dict[str, Any]]


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def field(value: object, pattern: str, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(pattern, value, re.ASCII):
        raise ValueError(f"Invalid {name}")
    return value


def canonical(statement: Mapping[str, object]) -> bytes:
    return json.dumps(statement, sort_keys=True, separators=(",", ":")).encode("ascii")


def public_snapshot(evidence: Mapping[str, Any]) -> str:
    # Match aiflow.evidence.verification_snapshot_sha256 without importing code from a PR.
    projection = dict(evidence)
    del projection["phase"], projection["verification_snapshot_sha256"]
    projection["review_refs"] = {
        k: v for k, v in evidence["review_refs"].items() if k != "implementation"
    }
    body = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def check_final_reviews_and_results(evidence: Mapping[str, Any]) -> None:
    reviews = evidence["review_refs"]
    require(set(reviews) == {"design", "implementation"}, "Final review references missing")
    for ref in reviews.values():
        require(
            isinstance(ref, dict) and set(ref) == {"review_id", "context_sha256"},
            "Invalid final review reference",
        )
        field(ref["review_id"], r"REV-[0-9]{4,}", "review ID")
        field(ref["context_sha256"], r"[0-9a-f]{64}", "review context")
    require(
        isinstance(evidence["verifier_actor"], str) and bool(evidence["verifier_actor"].strip()),
        "Independent verifier missing",
    )
    field(evidence["verifier_context_sha256"], r"[0-9a-f]{64}", "verifier context")
    passed = set()
    for check in evidence["checks"]:
        require(type(check["required"]) is bool, "Invalid check")
        if check["required"]:
            require(check["status"] == "passed", "Required check did not pass")
            passed.add(check["check_id"])
    require(
        {"acceptance", "integration", "targeted_mutation", "independent_verifier"} <= passed,
        "Required V2 check missing",
    )
    results = evidence["targeted_mutation"]["results"]
    require(
        [r["mutation_id"] for r in results] == [f"MUT-V2-{n:03}" for n in range(1, 6)]
        and all(r["outcome"] == "killed" for r in results),
        "Invalid mutation results",
    )


def github_read(path: str) -> dict[str, Any]:
    result = subprocess.run(
        ["gh", "api", "--hostname", "github.com", "--method", "GET", f"repos/{REPOSITORY}/{path}"],
        capture_output=True,
        timeout=30,
        check=True,
    )
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError("Invalid API response")
    return value


_BASE_WORKFLOW_BLOB = "e8f71c6a189446b0ba8f5b61e22cbd8ea9b7c2d9"
_MARKED_WORKFLOW_BLOB = "5027a41d3fbc9b64e189b6d6c337636a4b5c4e37"
_MARKER_LINES = (
    b"      - name: Replay request merge=${{ github.sha }} workflow=${{ github.workflow_sha }}\n"
    b"        run: ':'\n"
)
_CHECKOUT_LINE = b"      - uses: actions/checkout@v7\n"


def _reviewed_workflow(read: READ, revision: str, expected_blob: str) -> bytes:
    response = read(f"contents/{ORDINARY}?ref={revision}")
    require(
        response["sha"] == expected_blob and response["encoding"] == "base64",
        "Unreviewed ordinary workflow",
    )
    raw = base64.b64decode(response["content"].replace("\n", ""), validate=True)
    header = f"blob {len(raw)}\0".encode("ascii")
    require(
        hashlib.sha1(header + raw, usedforsecurity=False).hexdigest() == expected_blob,
        "Ordinary workflow bytes do not match Git blob",
    )
    return raw


def ordinary_observation(
    read: READ, run: Mapping[str, Any], base: str, head: str
) -> dict[str, object]:
    run_id, attempt, workflow_id, suite_id = (
        run["id"],
        run["run_attempt"],
        run["workflow_id"],
        run["check_suite_id"],
    )
    require(
        all(type(value) is int and value > 0 for value in (run_id, attempt, workflow_id, suite_id))
        and run["path"] == ORDINARY
        and run["name"] == "ai-quality-gate"
        and run["event"] == "pull_request"
        and run["head_sha"] == head
        and run["referenced_workflows"] == []
        and run["status"] == "completed"
        and run["conclusion"] == "failure",
        "Unexpected ordinary workflow run",
    )
    jobs = read(f"actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100")
    require(
        type(jobs["total_count"]) is int
        and jobs["total_count"] == 1
        and isinstance(jobs["jobs"], list)
        and len(jobs["jobs"]) == 1,
        "Expected one ordinary job",
    )
    job = jobs["jobs"][0]
    job_id = job["id"]
    require(
        type(job_id) is int
        and job_id > 0
        and type(job["run_id"]) is int
        and job["run_id"] == run_id
        and type(job["run_attempt"]) is int
        and job["run_attempt"] == attempt
        and job["head_sha"] == head
        and job["workflow_name"] == job["name"] == "ai-quality-gate"
        and job["check_run_url"] == f"https://api.github.com/repos/{REPOSITORY}/check-runs/{job_id}"
        and job["status"] == "completed"
        and job["conclusion"] == "failure",
        "Ordinary job binding mismatch",
    )
    check = read(f"check-runs/{job_id}")
    details_url = f"https://github.com/{REPOSITORY}/actions/runs/{run_id}/job/{job_id}"
    require(
        type(check["id"]) is int
        and check["id"] == job_id
        and type(check["check_suite"]["id"]) is int
        and check["check_suite"]["id"] == suite_id
        and type(check["app"]["id"]) is int
        and check["app"]["id"] == 15368
        and check["name"] == job["name"]
        and check["head_sha"] == head
        and check["status"] == "completed"
        and check["conclusion"] == "failure"
        and check["details_url"] == details_url,
        "Ordinary check binding mismatch",
    )
    steps = job["steps"]
    require(isinstance(steps, list) and len(steps) == 18, "Unexpected ordinary job steps")
    marker = field(
        steps[1]["name"], r"Replay request merge=[0-9a-f]{40} workflow=[0-9a-f]{40}", "marker"
    )
    merge, workflow = re.findall(r"[0-9a-f]{40}", marker)
    expected = (
        ("Set up job", "success"),
        (marker, "success"),
        ("Run actions/checkout@v7", "success"),
        ("Run actions/setup-python@v7", "success"),
        ("Run astral-sh/setup-uv@v10.0.1", "success"),
        ("Install locked project environment", "success"),
        ("Resolve PR governance", "success"),
        ("Attach exact PR head branch", "success"),
        ("Read repository identity", "success"),
        ("Validate contracts", "success"),
        ("Validate retained task records", "skipped"),
        ("Verify and Gate", "failure"),
        ("Maintenance quality checks", "skipped"),
        ("Upload AI Flow diagnostics", "success"),
        ("Post Run astral-sh/setup-uv@v10.0.1", "skipped"),
        ("Post Run actions/setup-python@v7", "skipped"),
        ("Post Run actions/checkout@v7", "success"),
        ("Complete job", "success"),
    )
    # The runner leaves gaps before post-action cleanup. Preserve execution order.
    previous = 0
    for index, (step, (name, conclusion)) in enumerate(zip(steps, expected, strict=True), 1):
        number = step["number"]
        require(
            type(number) is int
            and number > previous
            and (index > 14 or number == index)
            and step["name"] == name
            and step["status"] == "completed"
            and step["conclusion"] == conclusion,
            "Unexpected ordinary step or outcome",
        )
        previous = number

    commit = read(f"git/commits/{merge}")
    require(
        workflow == merge
        and commit["sha"] == merge
        and [parent["sha"] for parent in commit["parents"]] == [base, head],
        "Ordinary workflow source or merge parents mismatch",
    )
    before = _reviewed_workflow(read, base, _BASE_WORKFLOW_BLOB)
    after = _reviewed_workflow(read, head, _MARKED_WORKFLOW_BLOB)
    executed = _reviewed_workflow(read, workflow, _MARKED_WORKFLOW_BLOB)
    require(
        after == executed
        and before.count(_CHECKOUT_LINE) == 1
        and after == before.replace(_CHECKOUT_LINE, _MARKER_LINES + _CHECKOUT_LINE, 1),
        "Ordinary workflow differs beyond the reviewed marker",
    )
    return {
        "workflow_path": ORDINARY,
        "workflow_id": workflow_id,
        "event": run["event"],
        "run_id": run_id,
        "run_attempt": attempt,
        "check_run_id": job_id,
        "app_id": check["app"]["id"],
        "conclusion": run["conclusion"],
        "merge_sha": merge,
        "merge_parents": [base, head],
        "workflow_sha": workflow,
        "base_workflow_blob": _BASE_WORKFLOW_BLOB,
        "head_workflow_blob": _MARKED_WORKFLOW_BLOB,
        "executed_workflow_blob": _MARKED_WORKFLOW_BLOB,
    }


def request_bindings(
    env: Mapping[str, str], read: READ, *, v2: bool
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Authenticate the request and collect independently observable public fields."""
    sha = r"[0-9a-f]{40}"
    digest = r"[0-9a-f]{64}"
    positive_id = r"[1-9][0-9]*"
    trusted = field(env["TRUSTED_WORKFLOW_SHA"], sha, "protected commit")
    protected_ref = f"{REPOSITORY}/{PROTECTED}@refs/heads/main"
    require(
        env["GITHUB_REPOSITORY"] == REPOSITORY
        and env["GITHUB_EVENT_NAME"] == "workflow_dispatch"
        and env["GITHUB_REF"] == "refs/heads/main"
        and env["GITHUB_WORKFLOW_REF"] == protected_ref
        and env["GITHUB_SHA"] == env["GITHUB_WORKFLOW_SHA"] == trusted
        and read("git/ref/heads/main")["object"]["sha"] == trusted,
        "Untrusted verification run",
    )
    pr_id = int(field(env["PR_NUMBER"], positive_id, "PR number"))
    task = field(env["TASK_ID"], r"TASK-[0-9]{4,}", "task")
    ordinary_id = int(field(env["ORDINARY_RUN_ID"], positive_id, "ordinary run"))
    app_id = int(field(env["RECEIPT_APP_ID"], positive_id, "dedicated App"))
    require(app_id != 15368, "Dedicated App required")
    pr = read(f"pulls/{pr_id}")
    base, head = pr["base"], pr["head"]
    head_sha = field(head["sha"], sha, "PR head")
    require(
        pr["number"] == pr_id
        and pr["state"] == "open"
        and base["repo"]["full_name"] == head["repo"]["full_name"] == REPOSITORY
        and base["ref"] == "main"
        and base["sha"] == trusted,
        "PR binding mismatch",
    )
    run = read(f"actions/runs/{ordinary_id}")
    workflow = read("actions/workflows/ai-quality-gate.yml")
    require(
        workflow["path"] == ORDINARY
        and run["workflow_id"] == workflow["id"]
        and run["id"] == ordinary_id
        and run["event"] == "pull_request"
        and run["repository"]["full_name"] == run["head_repository"]["full_name"] == REPOSITORY
        and run["head_sha"] == head_sha
        and run["head_branch"] == head["ref"]
        and type(run["run_attempt"]) is int
        and run["run_attempt"] > 0
        and any(
            p["number"] == pr_id and p["base"]["sha"] == trusted and p["head"]["sha"] == head_sha
            for p in run["pull_requests"]
        ),
        "Ordinary workflow binding mismatch",
    )
    observed: dict[str, Any] = {}
    if v2:
        ordinary = ordinary_observation(read, run, trusted, head_sha)
        original_blob = ordinary["base_workflow_blob"]
        repository_id = base["repo"]["id"]
        require(
            type(repository_id) is int
            and repository_id > 0
            and all(
                canonical_id == repository_id and type(canonical_id) is int
                for canonical_id in (
                    head["repo"]["id"],
                    run["repository"]["id"],
                    run["head_repository"]["id"],
                )
            ),
            "Repository ID mismatch",
        )
        observed.update(github_repository_id=repository_id, head_ref=head["ref"], ordinary=ordinary)
    else:
        original_blob = field(
            read(f"contents/{ORDINARY}?ref={trusted}")["sha"], sha, "workflow blob"
        )
        require(
            read(f"contents/{ORDINARY}?ref={head_sha}")["sha"] == original_blob,
            "Ordinary workflow changed",
        )
    data = read(f"contents/.ai/tasks/{task}/evidence.json?ref={head_sha}")
    require(data["encoding"] == "base64", "Invalid evidence encoding")
    evidence = json.loads(base64.b64decode(data["content"].replace("\n", ""), validate=True))
    require(
        evidence["schema_version"] == "2.0"
        and evidence["repository_id"] == "b85e5a53-4935-4436-bdbc-c26a241bfae8"
        and evidence["task_id"] == task
        and evidence["branch"] == head["ref"]
        and evidence["base_commit"] == trusted
        and evidence["mode"] == "local"
        and evidence["phase"] == "final"
        and evidence["verification_level"] == "V2"
        and evidence["conclusion"] == "passed",
        "Invalid public final evidence",
    )
    for name in ("spec_sha256", "policy_sha256", "classification_input_sha256"):
        field(evidence.get(name), digest, name)
    units = evidence.get("decision_unit_ids")
    require(isinstance(units, list) and bool(units), "Invalid decision_unit_ids")
    for unit in units:
        field(unit, r"DU-[0-9]{3,}", "decision_unit_ids item")
    require(len(set(units)) == len(units), "Duplicate decision_unit_ids")
    require(public_snapshot(evidence) == evidence["verification_snapshot_sha256"], "Stale snapshot")
    check_final_reviews_and_results(evidence)
    subject = field(evidence["subject_commit"], sha, "subject")
    for ancestor, descendant in ((trusted, subject), (subject, head_sha)):
        comparison = read(f"compare/{ancestor}...{descendant}?per_page=1")
        require(comparison["merge_base_commit"]["sha"] == ancestor, "Subject ancestry mismatch")
        if v2:
            check_marker_scope(comparison["files"], task, software=ancestor == trusted)
    if v2:
        # This stdlib-only verifier supports the frozen policy that defines the fourteen checks.
        policy = read(f"contents/.ai/policy/verification-levels.yaml?ref={trusted}")
        require(policy["sha"] == "ec1511b24896fe5c7c169ec4c397c07eaa406ca8", "Unreviewed V2 policy")
        final_ids = [c["check_id"] for c in evidence["checks"]]
        require(all(isinstance(name, str) for name in final_ids), "Invalid final check ID")
        require(len(set(final_ids)) == len(final_ids), "Duplicate final check ID")
        required = {c["check_id"] for c in evidence["checks"] if c["required"]}
        require(required == V2_CHECKS, "Incomplete final V2 checks")
        observed.update(
            repository=REPOSITORY,
            pr=pr_id,
            task_id=task,
            base=trusted,
            head=head_sha,
            subject=subject,
            decision_unit_ids=units,
            evidence={
                k: evidence[k]
                for k in ("spec_sha256", "policy_sha256", "classification_input_sha256")
            },
        )
        observed["evidence"].update(
            local_final_snapshot=evidence["verification_snapshot_sha256"],
            mutation_evidence_sha256=evidence["targeted_mutation"]["mutation_evidence_sha256"],
        )
    bindings = {
        "protocol": NAMESPACE,
        "result": "private-v2-gates-passed",
        "repository": REPOSITORY,
        "pr": pr_id,
        "base": trusted,
        "head": head_sha,
        "task": task,
        "subject": subject,
        "verification_snapshot_sha256": field(
            evidence["verification_snapshot_sha256"], digest, "snapshot"
        ),
        "mutation_evidence_sha256": field(
            evidence["targeted_mutation"]["mutation_evidence_sha256"], digest, "mutation evidence"
        ),
        "ordinary_workflow": ORDINARY,
        "ordinary_workflow_blob": original_blob,
        "ordinary_run": ordinary_id,
        "ordinary_attempt": run["run_attempt"],
        "protected_workflow": protected_ref,
        "protected_workflow_sha": trusted,
        "protected_run": int(field(env["GITHUB_RUN_ID"], positive_id, "protected run")),
        "protected_attempt": int(
            field(env["GITHUB_RUN_ATTEMPT"], positive_id, "protected attempt")
        ),
        "verifier_sha256": field(env["VERIFIER_SHA256"], digest, "verifier"),
        "engine_sha256": field(env["ENGINE_SHA256"], digest, "private engine"),
        "app_id": app_id,
        "check_run": int(field(env["CHECK_RUN_ID"], positive_id, "staging check")),
    }
    return bindings, observed


def statement_for(env: Mapping[str, str], read: READ) -> dict[str, object]:
    """The original v1 wire statement."""
    return request_bindings(env, read, v2=False)[0]


def staged_output(statement: Mapping[str, object], read: READ) -> tuple[str, object]:
    check = read(f"check-runs/{statement['check_run']}")
    require(
        check["id"] == statement["check_run"]
        and check["app"]["id"] == statement["app_id"]
        and check["name"] == "private-v2-receipt/staged"
        and check["head_sha"] == statement["head"]
        and check["status"] == "completed"
        and check["conclusion"] == "success",
        "Untrusted staging check",
    )
    signature = check["output"]["summary"]
    if not isinstance(signature, str) or len(signature) > 4096:
        raise ValueError("Invalid signature")
    return signature, check["output"].get("text")


def check_marker_scope(files: list[dict[str, Any]], task: str, *, software: bool) -> None:
    # Compare returns at most 300 files. A truncated inventory cannot prove a clean core diff.
    require(isinstance(files, list) and 0 < len(files) < 300, "Incomplete compare inventory")
    allowed = {ORDINARY, "tests/integration/test_github_workflow.py"} if software else set()
    seen = set()
    for item in files:
        require(item["status"] in {"added", "modified"}, "Unexpected marker file change")
        path = item["filename"]
        require(path in allowed or path.startswith(f".ai/tasks/{task}/"), "Unexpected marker scope")
        seen.add(path)
    require(not software or ORDINARY in seen, "Missing marker workflow change")


def unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        require(name not in result, "Duplicate receipt field")
        result[name] = value
    return result


def count(value: object, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError("Invalid R2 measurement")
    return value


def expected_replay(replay: Mapping[str, Any], head: str) -> dict[str, Any]:
    checks = replay["checks_passed"]
    require(
        isinstance(checks, list) and len(checks) == len(V2_CHECKS) and set(checks) == V2_CHECKS,
        "Incomplete R2 checks",
    )
    coverage = replay["core_coverage"]
    totals = {
        k: count(coverage[k])
        for k in ("lines-covered", "lines-valid", "branches-covered", "branches-valid")
    }
    for kind in ("lines", "branches"):
        require(
            0 < totals[kind + "-valid"] and totals[kind + "-covered"] <= totals[kind + "-valid"],
            "Invalid core coverage counts",
        )
    require(
        100 * (totals["lines-covered"] + totals["branches-covered"])
        >= 85 * (totals["lines-valid"] + totals["branches-valid"]),
        "Core coverage below threshold",
    )
    return {
        "round": "R2",
        "attestation": {
            "mode": "ci",
            "verification_level": "V2",
            "phase": "pre_implementation_review",
            "conclusion": "passed",
            "attestation_head": head,
            "attestation_governance_only": True,
        },
        "checks_passed": checks,
        "existing_mutations_killed": 5,
        "new_mutation_actions": 0,
        "pytest_passed": count(replay["pytest_passed"], 1),
        "pytest_skipped": count(replay["pytest_skipped"]),
        "core_coverage": totals,
        "no_mapped_core_diff": True,
        "maintenance_exit_codes": dict.fromkeys(
            (
                "maintenance_coverage",
                "whitespace",
                "maintenance_lint",
                "maintenance_format",
                "maintenance_mypy",
            ),
            0,
        ),
        "gate": {
            "route": "REVIEW",
            "verification_level": "V2",
            "passed": True,
            "reason_codes": [],
            "exit_code": 0,
        },
    }


def v2_statement(
    bindings: Mapping[str, Any], observed: dict[str, Any], text: object, commitment: str, key: str
) -> dict[str, Any]:
    if not isinstance(text, str) or not 0 < len(text) <= 16384:
        raise ValueError("Missing or oversized R2 text")
    body = text.encode("utf-8")
    require(len(body) <= 16384 and body.endswith(b"\n"), "Invalid R2 wire bytes")
    digest = hashlib.sha256(body).digest()
    require(
        hashlib.sha256(V2_NAMESPACE.encode("ascii") + b"\0" + digest).hexdigest() == commitment,
        "Unapproved fixed fields",
    )
    fixed = json.loads(body, object_pairs_hook=unique_fields)
    observed["replay"] = expected_replay(fixed["replay"], bindings["head"])
    for name in ("redacted_receipt_sha256", "ci_sha256", "ci_snapshot", "gate_sha256"):
        observed["evidence"][name] = field(fixed["evidence"][name], r"[0-9a-f]{64}", name)
    # Compare the entire schema, including extra keys, JSON types (false vs 0) and nested values.
    require(canonical(fixed) == canonical(observed), "Fixed R2 fields differ from expected")
    key_blob = base64.b64decode(key.split()[1], validate=True)
    fingerprint = base64.b64encode(hashlib.sha256(key_blob).digest()).decode("ascii").rstrip("=")
    return {
        "protocol": V2_NAMESPACE,
        "algorithm": "ssh-ed25519",
        "signer_fingerprint": "SHA256:" + fingerprint,
        "protected_workflow_ref": bindings["protected_workflow"],
        "protected_workflow_sha": bindings["protected_workflow_sha"],
        "verifier_sha256": bindings["verifier_sha256"],
        "engine_sha256": bindings["engine_sha256"],
        "protected_run": bindings["protected_run"],
        "protected_attempt": bindings["protected_attempt"],
        "app_id": bindings["app_id"],
        "staging_check_id": bindings["check_run"],
        "final_check_name": "private-v2-receipt/verified",
        "fixed_fields_sha256": digest.hex(),
    }


def check_protected_run(bindings: Mapping[str, Any], read: READ) -> None:
    run = read(f"actions/runs/{bindings['protected_run']}")
    require(
        type(run["id"]) is int
        and run["id"] == bindings["protected_run"]
        and type(run["run_attempt"]) is int
        and run["run_attempt"] == bindings["protected_attempt"]
        and run["repository"]["full_name"] == REPOSITORY
        and run["path"] == PROTECTED
        and run["event"] == "workflow_dispatch"
        and run["head_branch"] == "main"
        and run["head_sha"] == bindings["base"],
        "Protected workflow run mismatch",
    )


def verify(env: Mapping[str, str], read: READ) -> None:
    try:
        commitment = env.get("V2_APPROVAL_COMMITMENT", "")
        v2 = bool(commitment)
        if v2:
            field(commitment, r"[0-9a-f]{64}", "v2 approval commitment")
        statement, observed = request_bindings(env, read, v2=v2)
        signature, text = staged_output(statement, read)
        key = field(env["RECEIPT_PUBLIC_KEY"], r"ssh-ed25519 [A-Za-z0-9+/]+={0,2}", "Ed25519 key")
        wire = statement
        namespace = NAMESPACE
        if v2:
            check_protected_run(statement, read)
            wire = v2_statement(statement, observed, text, commitment, key)
            namespace = V2_NAMESPACE
        with tempfile.TemporaryDirectory() as directory:
            signers = Path(directory, "allowed_signers")
            sig = Path(directory, "receipt.sig")
            signers.write_bytes(f"private-verifier {key}\n".encode("ascii"))
            sig.write_bytes(signature.encode("ascii"))
            result = subprocess.run(
                [
                    "ssh-keygen",
                    "-Y",
                    "verify",
                    "-f",
                    str(signers),
                    "-I",
                    "private-verifier",
                    "-n",
                    namespace,
                    "-s",
                    str(sig),
                ],
                input=canonical(wire),
                capture_output=True,
                timeout=10,
            )
            require(result.returncode == 0, "Receipt signature rejected")
        # These pointers can advance while API calls and signature verification are in flight.
        latest = read(f"pulls/{statement['pr']}")
        latest_signature, latest_text = staged_output(statement, read)
        latest_attempt = read(f"actions/runs/{statement['ordinary_run']}")["run_attempt"]
        require(
            latest["state"] == "open"
            and latest["base"]["ref"] == "main"
            and latest["base"]["sha"] == statement["base"]
            and latest["head"]["sha"] == statement["head"]
            and latest_signature == signature
            and (not v2 or latest_text == text)
            and type(latest_attempt) is int
            and latest_attempt == statement["ordinary_attempt"]
            and read("git/ref/heads/main")["object"]["sha"] == statement["base"],
            "Request changed during verification",
        )
        if v2:
            check_protected_run(statement, read)
    except (KeyError, TypeError, AttributeError, UnicodeError, RecursionError) as error:
        raise ValueError("Invalid receipt input") from error


if __name__ == "__main__":
    try:
        verify(os.environ, github_read)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        sys.exit(f"Receipt verification failed ({type(error).__name__}).")
    print("Staged receipt signature verified.")
