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


def statement_for(env: Mapping[str, str], read: READ) -> dict[str, object]:
    """Build the signed statement from configuration and independent GitHub reads."""
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
    original_blob = field(read(f"contents/{ORDINARY}?ref={trusted}")["sha"], sha, "workflow blob")
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
    return {
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


def staged_signature(statement: Mapping[str, object], read: READ) -> str:
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
    return signature


def verify(env: Mapping[str, str], read: READ) -> None:
    try:
        statement = statement_for(env, read)
        signature = staged_signature(statement, read)
        key = field(env["RECEIPT_PUBLIC_KEY"], r"ssh-ed25519 [A-Za-z0-9+/]+={0,2}", "Ed25519 key")
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
                    NAMESPACE,
                    "-s",
                    str(sig),
                ],
                input=canonical(statement),
                capture_output=True,
                timeout=10,
            )
            require(result.returncode == 0, "Receipt signature rejected")
        # These pointers can advance while API calls and signature verification are in flight.
        latest = read(f"pulls/{statement['pr']}")
        require(
            latest["state"] == "open"
            and latest["base"]["ref"] == "main"
            and latest["base"]["sha"] == statement["base"]
            and latest["head"]["sha"] == statement["head"]
            and staged_signature(statement, read) == signature
            and read(f"actions/runs/{statement['ordinary_run']}")["run_attempt"]
            == statement["ordinary_attempt"]
            and read("git/ref/heads/main")["object"]["sha"] == statement["base"],
            "Request changed during verification",
        )
    except (KeyError, TypeError, AttributeError, UnicodeError) as error:
        raise ValueError("Invalid receipt input") from error


if __name__ == "__main__":
    try:
        verify(os.environ, github_read)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        sys.exit(f"Receipt verification failed ({type(error).__name__}).")
    print("Staged receipt signature verified.")
