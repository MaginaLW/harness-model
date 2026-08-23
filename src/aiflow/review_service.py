"""Immutable structured REVIEW contexts, records, and finding resolutions."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from aiflow.contracts import require_valid_contract
from aiflow.errors import ContractError, StorageError
from aiflow.evidence import validate_v2_snapshot
from aiflow.freshness import current_classification_input_digest
from aiflow.policy import load_policy_bundle
from aiflow.specification import specification_digest
from aiflow.storage import atomic_write_json, read_task_json, resolve_task_path
from aiflow.task_service import read_task_record_strict, record_task_event

ReviewStage = Literal["design", "implementation"]
_APPROVABLE_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS"})
_BLOCKING_SEVERITIES = frozenset({"critical", "high"})
_GIT_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class ReviewResult:
    """The immutable files and event written for a review operation."""

    context: Mapping[str, Any]
    record: Mapping[str, Any]
    event_recorded: bool


@dataclass(frozen=True)
class ReviewAssessment:
    """A current structured review suitable for a stage-specific approval."""

    context: Mapping[str, Any]
    record: Mapping[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical(value: Mapping[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _context_digest(context: Mapping[str, object]) -> str:
    stable = {key: value for key, value in context.items() if key != "context_sha256"}
    return hashlib.sha256(_canonical(stable).encode("utf-8")).hexdigest()


def _artifact_digest(value: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _stage(stage: str) -> ReviewStage:
    if stage not in {"design", "implementation"}:
        raise ContractError("Review stage is invalid", code="REVIEW_STAGE_INVALID")
    return stage  # type: ignore[return-value]


def _classification(root: Path, task_id: str) -> dict[str, Any]:
    value = read_task_json(root, task_id, "classification.json", contract_name="classification")
    if not isinstance(value, dict):
        raise ContractError(
            "Review classification is invalid", code="REVIEW_CLASSIFICATION_INVALID"
        )
    return value


def _context_content(
    task: Mapping[str, object], classification: Mapping[str, object]
) -> dict[str, object]:
    units = task.get("decision_units")
    decisions: list[dict[str, object]] = []
    if isinstance(units, list):
        for unit in units:
            if isinstance(unit, Mapping):
                decisions.append(
                    {
                        "decision_unit_id": unit.get("decision_unit_id"),
                        "goal": unit.get("goal"),
                        "impact_scope": unit.get("impact_scope"),
                        "planned_actions": unit.get("planned_actions"),
                    }
                )
    return {
        "goal": task.get("goal"),
        "allowed_scope": task.get("allowed_scope"),
        "decision_units": decisions,
        "route": classification.get("effective_route"),
        "verification_level": classification.get("effective_verification_level"),
    }


def _committed_diff_summary(root: Path, base_commit: str, subject_commit: str) -> dict[str, object]:
    """Return deterministic committed-path and numstat facts without patch content."""
    arguments = (
        "diff",
        "--numstat",
        "--no-renames",
        "--format=",
        base_commit,
        subject_commit,
        "--",
    )
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise ContractError(
            "Could not summarize review diff before timeout",
            code="REVIEW_DIFF_TIMEOUT",
        ) from error
    except OSError as error:
        raise ContractError(
            "Could not run Git for review diff", code="REVIEW_DIFF_FAILED"
        ) from error
    if result.returncode != 0:
        raise ContractError(
            "Could not summarize committed review diff",
            code="REVIEW_DIFF_FAILED",
            details={"returncode": result.returncode},
        )
    try:
        output = result.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError(
            "Review diff summary is not valid UTF-8", code="REVIEW_DIFF_INVALID"
        ) from error

    files: list[dict[str, object]] = []
    total_additions = 0
    total_deletions = 0
    for line in output.splitlines():
        parts = line.split("\t", maxsplit=2)
        if len(parts) != 3 or not parts[2]:
            raise ContractError("Review diff summary is invalid", code="REVIEW_DIFF_INVALID")
        additions_raw, deletions_raw, path = parts
        binary = additions_raw == "-" and deletions_raw == "-"
        if binary:
            additions: int | None = None
            deletions: int | None = None
        else:
            try:
                additions = int(additions_raw)
                deletions = int(deletions_raw)
            except ValueError as error:
                raise ContractError(
                    "Review diff summary is invalid", code="REVIEW_DIFF_INVALID"
                ) from error
            total_additions += additions
            total_deletions += deletions
        files.append(
            {
                "path": path.replace("\\", "/"),
                "additions": additions,
                "deletions": deletions,
                "binary": binary,
            }
        )
    files.sort(key=lambda item: str(item["path"]))
    return {
        "changed_paths": [str(item["path"]) for item in files],
        "files": files,
        "totals": {
            "files": len(files),
            "additions": total_additions,
            "deletions": total_deletions,
        },
    }


def _verification_summary(evidence: Mapping[str, object]) -> dict[str, object]:
    """Select replayable verification facts while excluding logs and command output."""
    checks = evidence.get("checks")
    required_checks = []
    if isinstance(checks, list):
        required_checks = sorted(
            (
                {"check_id": check.get("check_id"), "status": check.get("status")}
                for check in checks
                if isinstance(check, Mapping) and check.get("required") is True
            ),
            key=lambda item: str(item["check_id"]),
        )
    return {
        "verification_level": evidence.get("verification_level"),
        "required_checks": required_checks,
        "unverified_scenarios": evidence.get("unverified_scenarios"),
        "reproduce_command": evidence.get("reproduce_command"),
    }


def build_review_context(repository_root: Path, task_id: str, stage: str) -> Mapping[str, Any]:
    """Build a deterministic minimal context bound to current governed facts."""
    review_stage = _stage(stage)
    root = repository_root.resolve()
    record = read_task_record_strict(root, task_id)
    task = record.task
    classification = _classification(root, task_id)
    policy = load_policy_bundle(root)
    spec_path = resolve_task_path(root, task_id, "spec.md")
    try:
        spec_sha256 = specification_digest(spec_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise StorageError(
            "Could not read review specification", code="REVIEW_SPEC_READ_FAILED"
        ) from error
    units = task.get("decision_units")
    if not isinstance(units, list):
        raise ContractError("Review task decision units are invalid", code="REVIEW_CONTEXT_INVALID")
    unit_ids = [str(unit.get("decision_unit_id")) for unit in units if isinstance(unit, Mapping)]
    digest, _synchronized = current_classification_input_digest(
        task, units, classification, record.events
    )
    context: dict[str, Any] = {
        "schema_version": "1.0",
        "review_stage": review_stage,
        "task_id": task_id,
        "decision_unit_ids": unit_ids,
        "repository_id": task.get("repository_id"),
        "branch": task.get("branch"),
        "base_commit": task.get("base_commit"),
        "spec_sha256": spec_sha256,
        "policy_sha256": policy.sha256,
        "classification_input_sha256": digest,
        "content": _context_content(task, classification),
    }
    if review_stage == "implementation":
        subject = task.get("subject_commit")
        if not isinstance(subject, str):
            raise ContractError(
                "Implementation review requires a subject", code="REVIEW_SUBJECT_MISSING"
            )
        evidence = read_task_json(root, task_id, "evidence.json", contract_name="evidence")
        if not isinstance(evidence, dict) or evidence.get("conclusion") != "passed":
            raise ContractError(
                "Implementation review requires passed evidence", code="REVIEW_EVIDENCE_INVALID"
            )
        context["subject_commit"] = subject
        if evidence.get("schema_version") == "2.0":
            try:
                validate_v2_snapshot(evidence)
            except ContractError as error:
                raise ContractError(
                    "Implementation review requires current V2 verification evidence",
                    code="REVIEW_EVIDENCE_INVALID",
                ) from error
            snapshot = evidence.get("verification_snapshot_sha256")
            if not isinstance(snapshot, str):
                raise ContractError(
                    "Implementation review requires V2 verification snapshot",
                    code="REVIEW_EVIDENCE_INVALID",
                )
            context["schema_version"] = "2.0"
            context["verification_snapshot_sha256"] = snapshot
        else:
            context["evidence_sha256"] = _artifact_digest(evidence)
        base = task.get("base_commit")
        if not isinstance(base, str):
            raise ContractError(
                "Implementation review requires a base commit", code="REVIEW_BASE_MISSING"
            )
        context["content"]["diff_summary"] = _committed_diff_summary(root, base, subject)
        context["content"]["verification_summary"] = _verification_summary(evidence)
    context["context_sha256"] = _context_digest(context)
    require_valid_contract("review-context", context)
    return context


def validate_review_context(context: Mapping[str, object]) -> None:
    """Validate a structured context and its canonical hash."""
    require_valid_contract("review-context", context)
    expected = _context_digest(context)
    if context.get("context_sha256") != expected:
        raise ContractError("Review context hash is invalid", code="REVIEW_CONTEXT_HASH_INVALID")


def _validate_findings(record: Mapping[str, object]) -> None:
    findings = record.get("findings")
    if not isinstance(findings, list):
        return
    identifiers = [
        finding.get("finding_id") for finding in findings if isinstance(finding, Mapping)
    ]
    if len(identifiers) != len(set(identifiers)):
        raise ContractError("Review finding IDs must be unique", code="REVIEW_FINDING_DUPLICATE")
    if record.get("outcome") in _APPROVABLE_OUTCOMES:
        blocking = [
            finding
            for finding in findings
            if isinstance(finding, Mapping)
            and finding.get("severity") in _BLOCKING_SEVERITIES
            and finding.get("status") != "resolved"
        ]
        if blocking:
            raise ContractError(
                "Approving review contains unresolved high-severity findings",
                code="REVIEW_FINDING_UNRESOLVED",
            )


def validate_review_record(record: Mapping[str, object], context: Mapping[str, object]) -> None:
    """Validate immutable record shape, stage/task binding, and its context reference."""
    validate_review_context(context)
    require_valid_contract("review-record", record)
    if record.get("task_id") != context.get("task_id") or record.get("review_stage") != context.get(
        "review_stage"
    ):
        raise ContractError(
            "Review record stage or task does not match context", code="REVIEW_CONTEXT_MISMATCH"
        )
    if record.get("context_sha256") != context.get("context_sha256"):
        raise ContractError(
            "Review record context hash does not match", code="REVIEW_CONTEXT_MISMATCH"
        )
    _validate_findings(record)


def review_is_approvable(record: Mapping[str, object]) -> bool:
    """Return whether the reviewed conclusion can support an approval."""
    try:
        _validate_findings(record)
    except ContractError:
        return False
    return record.get("outcome") in _APPROVABLE_OUTCOMES


def _review_directory(root: Path, task_id: str) -> Path:
    return resolve_task_path(root, task_id, "reviews")


def _context_path(root: Path, task_id: str, digest: str) -> Path:
    return resolve_task_path(root, task_id, Path("review-contexts") / f"{digest}.json")


def _record_path(root: Path, task_id: str, review_id: str, revision: int) -> Path:
    return resolve_task_path(root, task_id, Path("reviews") / f"{review_id}-r{revision:04d}.json")


def _write_immutable(path: Path, value: Mapping[str, object]) -> bool:
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise StorageError(
                "Could not read immutable review artifact", code="REVIEW_STORAGE_INVALID"
            ) from error
        if existing != dict(value):
            raise ContractError(
                "Review artifact conflicts with existing revision", code="REVIEW_IMMUTABLE_CONFLICT"
            )
        return False
    atomic_write_json(path, value)
    return True


def _review_event_exists(
    root: Path,
    task_id: str,
    *,
    event_type: str,
    review_id: str,
    revision: int,
    finding_id: str | None = None,
) -> bool:
    record = read_task_record_strict(root, task_id)
    for event in record.events:
        payload = event.get("payload")
        if event.get("event_type") != event_type or not isinstance(payload, Mapping):
            continue
        if payload.get("review_id") != review_id or payload.get("revision") != revision:
            continue
        if finding_id is None or payload.get("finding_id") == finding_id:
            return True
    return False


def _record_input(value: Path | Mapping[str, object]) -> dict[str, Any]:
    if isinstance(value, Path):
        try:
            raw = json.loads(value.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ContractError(
                "Review record input is invalid", code="REVIEW_INPUT_INVALID"
            ) from error
    else:
        raw = dict(value)
    if not isinstance(raw, dict):
        raise ContractError("Review record input is invalid", code="REVIEW_INPUT_INVALID")
    return raw


def record_review(
    repository_root: Path,
    task_id: str,
    *,
    input_path: Path | Mapping[str, object],
    actor: str,
) -> ReviewResult:
    """Persist an immutable structured review record; exact replay is idempotent."""
    if not actor.strip():
        raise ContractError("Review actor is required", code="REVIEW_ACTOR_INVALID")
    root = repository_root.resolve()
    candidate = _record_input(input_path)
    stage = candidate.get("review_stage")
    context = dict(build_review_context(root, task_id, str(stage)))
    provided_context = candidate.get("context_sha256")
    if provided_context != context["context_sha256"]:
        raise ContractError(
            "Review record context hash does not match current facts",
            code="REVIEW_CONTEXT_MISMATCH",
        )
    provided_task = candidate.get("task_id")
    if provided_task is not None and provided_task != task_id:
        raise ContractError("Review record task does not match", code="REVIEW_CONTEXT_MISMATCH")
    provided_reviewer = candidate.get("reviewer")
    if provided_reviewer is not None and provided_reviewer != actor.strip():
        raise ContractError("Review record actor does not match", code="REVIEW_ACTOR_INVALID")
    candidate["task_id"] = task_id
    candidate["reviewer"] = actor.strip()
    candidate.setdefault("schema_version", "1.0")
    candidate.setdefault("revision", 1)
    if candidate["revision"] != 1:
        raise ContractError(
            "Initial review record revision must be one", code="REVIEW_REVISION_INVALID"
        )
    validate_review_record(candidate, context)
    review_id = str(candidate["review_id"])
    revision = int(candidate["revision"])
    context_changed = _write_immutable(
        _context_path(root, task_id, str(context["context_sha256"])), context
    )
    record_changed = _write_immutable(_record_path(root, task_id, review_id, revision), candidate)
    event_recorded = False
    if (
        context_changed
        or record_changed
        or not _review_event_exists(
            root,
            task_id,
            event_type="review_recorded",
            review_id=review_id,
            revision=revision,
        )
    ):
        record_task_event(
            root,
            task_id,
            event_type="review_recorded",
            actor=actor,
            payload={
                "review_id": review_id,
                "revision": revision,
                "review_stage": stage,
                "context_sha256": context["context_sha256"],
            },
        )
        event_recorded = True
    return ReviewResult(context, candidate, event_recorded)


def _latest_record(root: Path, task_id: str, review_id: str) -> dict[str, Any]:
    directory = _review_directory(root, task_id)
    records: list[dict[str, Any]] = []
    if directory.is_dir():
        for path in directory.glob(f"{review_id}-r*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                records.append(value)
    if not records:
        raise ContractError("Review record is missing", code="REVIEW_RECORD_MISSING")
    return max(records, key=lambda value: int(value.get("revision", 0)))


def list_review_records(
    repository_root: Path, task_id: str, *, stage: str | None = None
) -> tuple[Mapping[str, Any], ...]:
    """Return validated latest immutable revisions, optionally for one stage."""
    selected_stage = _stage(stage) if stage is not None else None
    root = repository_root.resolve()
    directory = _review_directory(root, task_id)
    latest: dict[str, dict[str, Any]] = {}
    if not directory.is_dir():
        return ()
    for path in sorted(directory.glob("REV-*-r*.json")):
        value = read_task_json(
            root, task_id, Path("reviews") / path.name, contract_name="review-record"
        )
        if not isinstance(value, dict):
            raise ContractError("Review record is invalid", code="REVIEW_RECORD_INVALID")
        identifier = str(value.get("review_id"))
        revision = int(value.get("revision", 0))
        if path.name != f"{identifier}-r{revision:04d}.json":
            raise ContractError("Review record filename is invalid", code="REVIEW_RECORD_INVALID")
        current = latest.get(identifier)
        if current is None or revision > int(current.get("revision", 0)):
            latest[identifier] = value
    result: list[Mapping[str, Any]] = []
    for value in sorted(latest.values(), key=lambda item: str(item.get("review_id"))):
        if selected_stage is not None and value.get("review_stage") != selected_stage:
            continue
        digest = value.get("context_sha256")
        if not isinstance(digest, str):
            raise ContractError("Review context is invalid", code="REVIEW_CONTEXT_MISMATCH")
        context = read_task_json(
            root,
            task_id,
            Path("review-contexts") / f"{digest}.json",
            contract_name="review-context",
        )
        if not isinstance(context, dict):
            raise ContractError("Review context is invalid", code="REVIEW_CONTEXT_MISMATCH")
        validate_review_record(value, context)
        result.append(value)
    return tuple(result)


def validate_review_artifacts(repository_root: Path, task_id: str) -> None:
    """Validate every immutable context and record, including historical revisions."""
    root = repository_root.resolve()
    contexts: dict[str, dict[str, Any]] = {}
    contexts_directory = resolve_task_path(root, task_id, "review-contexts")
    if contexts_directory.is_dir():
        for path in sorted(contexts_directory.glob("*.json")):
            value = read_task_json(
                root,
                task_id,
                Path("review-contexts") / path.name,
                contract_name="review-context",
            )
            if not isinstance(value, dict):
                raise ContractError("Review context is invalid", code="REVIEW_CONTEXT_INVALID")
            validate_review_context(value)
            digest = str(value["context_sha256"])
            if path.name != f"{digest}.json":
                raise ContractError(
                    "Review context filename is invalid", code="REVIEW_CONTEXT_HASH_INVALID"
                )
            contexts[digest] = value
    records_directory = _review_directory(root, task_id)
    if not records_directory.is_dir():
        return
    for path in sorted(records_directory.glob("*.json")):
        value = read_task_json(
            root, task_id, Path("reviews") / path.name, contract_name="review-record"
        )
        if not isinstance(value, dict):
            raise ContractError("Review record is invalid", code="REVIEW_RECORD_INVALID")
        identifier = str(value["review_id"])
        revision = int(value["revision"])
        if path.name != f"{identifier}-r{revision:04d}.json":
            raise ContractError("Review record filename is invalid", code="REVIEW_RECORD_INVALID")
        digest = str(value["context_sha256"])
        context = contexts.get(digest)
        if context is None:
            raise ContractError("Review context is missing", code="REVIEW_CONTEXT_MISMATCH")
        validate_review_record(value, context)


def resolve_review_finding(
    repository_root: Path, task_id: str, *, review_id: str, finding_id: str, reason: str, actor: str
) -> ReviewResult:
    """Append a revision resolving one open finding without changing history."""
    if not actor.strip() or not reason.strip():
        raise ContractError("Review resolution is invalid", code="REVIEW_RESOLUTION_INVALID")
    root = repository_root.resolve()
    previous = _latest_record(root, task_id, review_id)
    digest = previous.get("context_sha256")
    if not isinstance(digest, str):
        raise ContractError("Review record context is invalid", code="REVIEW_CONTEXT_MISMATCH")
    context = read_task_json(
        root, task_id, Path("review-contexts") / f"{digest}.json", contract_name="review-context"
    )
    if not isinstance(context, dict):
        raise ContractError("Review context is invalid", code="REVIEW_CONTEXT_MISMATCH")
    candidate = json.loads(json.dumps(previous))
    candidate["revision"] = int(previous["revision"]) + 1
    candidate["recorded_at"] = _now()
    changed = False
    for finding in candidate["findings"]:
        if finding["finding_id"] == finding_id:
            if finding["status"] == "resolved":
                resolution = finding.get("resolution")
                if (
                    isinstance(resolution, dict)
                    and resolution.get("reason") == reason.strip()
                    and resolution.get("actor") == actor.strip()
                ):
                    revision = int(previous["revision"])
                    event_recorded = False
                    if not _review_event_exists(
                        root,
                        task_id,
                        event_type="review_finding_resolved",
                        review_id=review_id,
                        revision=revision,
                        finding_id=finding_id,
                    ):
                        record_task_event(
                            root,
                            task_id,
                            event_type="review_finding_resolved",
                            actor=actor,
                            payload={
                                "review_id": review_id,
                                "revision": revision,
                                "finding_id": finding_id,
                            },
                        )
                        event_recorded = True
                    return ReviewResult(context, previous, event_recorded)
                raise ContractError(
                    "Review finding is already resolved", code="REVIEW_FINDING_RESOLVED"
                )
            finding["status"] = "resolved"
            finding["resolution"] = {
                "reason": reason.strip(),
                "actor": actor.strip(),
                "resolved_at": candidate["recorded_at"],
            }
            changed = True
    if not changed:
        raise ContractError("Review finding is missing", code="REVIEW_FINDING_MISSING")
    validate_review_record(candidate, context)
    _write_immutable(_record_path(root, task_id, review_id, int(candidate["revision"])), candidate)
    record_task_event(
        root,
        task_id,
        event_type="review_finding_resolved",
        actor=actor,
        payload={
            "review_id": review_id,
            "revision": candidate["revision"],
            "finding_id": finding_id,
        },
    )
    return ReviewResult(context, candidate, True)


def latest_review_assessment(
    repository_root: Path,
    task_id: str,
    stage: str,
    decision_unit_ids: Sequence[str] | None = None,
    evidence_sha256: str | None = None,
    verification_snapshot_sha256: str | None = None,
) -> ReviewAssessment:
    """Return the latest current, approvable review for one stage or raise a stable error."""
    review_stage = _stage(stage)
    root = repository_root.resolve()
    expected = build_review_context(root, task_id, review_stage)
    records_dir = _review_directory(root, task_id)
    candidates: list[dict[str, Any]] = []
    if records_dir.is_dir():
        for path in records_dir.glob("REV-*-r*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and value.get("review_stage") == review_stage:
                candidates.append(value)
    if not candidates:
        raise ContractError("Current review record is missing", code="REVIEW_RECORD_MISSING")
    latest_by_id: dict[str, dict[str, Any]] = {}
    for review_record in candidates:
        identifier = str(review_record.get("review_id"))
        if int(review_record.get("revision", 0)) > int(
            latest_by_id.get(identifier, {}).get("revision", 0)
        ):
            latest_by_id[identifier] = review_record
    by_revision = {
        (str(value.get("review_id")), int(value.get("revision", 0))): value
        for value in latest_by_id.values()
    }
    current_record = read_task_record_strict(root, task_id)
    selected: dict[str, Any] | None = None
    for event in reversed(current_record.events):
        if event.get("event_type") not in {"review_recorded", "review_finding_resolved"}:
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        revision = payload.get("revision")
        if not isinstance(revision, int):
            continue
        value = by_revision.get((str(payload.get("review_id")), revision))
        if value is not None and value.get("review_stage") == review_stage:
            selected = value
            break
    if selected is None:
        raise ContractError("Current review record is missing", code="REVIEW_RECORD_MISSING")
    current_ids = set(decision_unit_ids or expected["decision_unit_ids"])
    if (
        selected.get("context_sha256") != expected["context_sha256"]
        or not current_ids.issubset(set(expected["decision_unit_ids"]))
        or (evidence_sha256 is not None and expected.get("evidence_sha256") != evidence_sha256)
        or (
            verification_snapshot_sha256 is not None
            and expected.get("verification_snapshot_sha256") != verification_snapshot_sha256
        )
    ):
        raise ContractError("Review record is stale", code="REVIEW_RECORD_STALE")
    validate_review_record(selected, expected)
    if not review_is_approvable(selected):
        raise ContractError(
            "Review outcome cannot support approval", code="REVIEW_OUTCOME_NOT_APPROVABLE"
        )
    return ReviewAssessment(expected, selected)
