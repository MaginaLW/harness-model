"""Closed installed-engine mutation recording and pure-file replay.

The trusted caller obtains current Git authority before replay. These internal
APIs do not enable Node V2, grant authority, or replace native mutation evidence.
"""

from __future__ import annotations

import ast
import ctypes
import importlib.machinery
import os
import re
import secrets
import stat
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from aiflow import mutation_evidence as native
from aiflow import mutation_runner as operators
from aiflow import node_execution as node
from aiflow.approval import (
    ApprovalContext,
    _logical_identity,
    _utc,
    approval_is_current,
    canonical_action_sha256,
    matching_approval,
    validate_action_file,
)
from aiflow.contracts import require_valid_contract
from aiflow.decision_units import parse_decision_units
from aiflow.errors import AiflowError, ContractError
from aiflow.freshness import current_classification_input_digest
from aiflow.git_context import collect_git_context
from aiflow.installed_probe import validate_probe_contract
from aiflow.mutation_manifest import MutationDeclaration
from aiflow.node_verification import _ordered_paths, _path
from aiflow.policy import is_node_policy, is_node_policy_candidate, load_policy_bundle
from aiflow.redaction import redact_text
from aiflow.specification import specification_digest
from aiflow.state import replay_events
from aiflow.storage import read_task_json, resolve_task_path
from aiflow.task_service import read_task_record_strict, record_task_event
from aiflow.verifier_service import (
    build_verifier_context,
    context_sha256,
    current_implementer_actor,
    validate_verifier_actor,
    validate_verifier_context,
)

ACTION_TYPE = "installed_engine_mutation_v1"
PROBE_IDS = tuple(f"MUT-V2-{number:03d}" for number in range(1, 6))
_TARGETS = {
    "MUT-V2-001": ("policy.py", "_validate_cross_file", "drop_targeted_mutation_required_check"),
    "MUT-V2-002": ("verifier_service.py", "validate_verifier_actor", "allow_same_verifier_actor"),
    "MUT-V2-003": ("approval.py", "_v2_evidence_current", "allow_nonpassing_required_check"),
    "MUT-V2-004": ("gate.py", "_v2_gate_facts", "accept_non_killed_mutation"),
    "MUT-V2-005": ("evidence.py", "validate_v2_snapshot", "ignore_snapshot_mismatch"),
}
_RUN_REF = re.compile(r"\.ai/tasks/(TASK-[0-9]{4,})/logs/IMUT-[0-9a-f]{16}/run\.json\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TIMEOUT = 60


@dataclass(frozen=True)
class InstalledMutationInputs:
    repository_id: str
    task_id: str
    decision_unit_ids: tuple[str, ...]
    branch: str
    base_commit: str
    subject_commit: str
    subject_tree: str
    spec_sha256: str
    policy_sha256: str
    classification_input_sha256: str
    implementer_actor: str
    verifier_actor: str
    verifier_context_sha256: str
    materials: bytes

    @property
    def sha256(self) -> str:
        return node._sha(node._canonical(_input_document(self)))


@dataclass(frozen=True)
class InstalledMutationReference:
    ref: str
    size: int
    sha256: str


@dataclass(frozen=True)
class InstalledMutationCurrent:
    inputs: InstalledMutationInputs
    reference: InstalledMutationReference
    root_snapshot: bytes
    allowed_git_paths: tuple[str, ...]


@dataclass(frozen=True)
class InstalledMutationFacts:
    current: bool
    all_killed: bool
    results: tuple[tuple[str, str], ...]
    reason_codes: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.current and self.all_killed


def _error(message: str, code: str = "INSTALLED_MUTATION_INVALID") -> ContractError:
    return ContractError(message, code=code)


def _closed(value: object, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise _error("Installed mutation original has an invalid closed shape")
    return value


def _input_document(inputs: InstalledMutationInputs) -> dict[str, Any]:
    if (
        type(inputs) is not InstalledMutationInputs
        or type(inputs.materials) is not bytes
        or len(inputs.materials) > node.MAX_JSON_BYTES
    ):
        raise _error("Current installed mutation inputs are invalid")
    value = asdict(inputs)
    materials = node._json_bytes(inputs.materials)
    _closed(
        materials, {"kind", "version", "engine", "interpreter", "host_tools", "probes", "operators"}
    )
    if (
        node._canonical(materials) != inputs.materials
        or materials["kind"] != ACTION_TYPE
        or type(materials["version"]) is not int
        or materials["version"] != 1
    ):
        raise _error("Installed mutation materials are not canonical")
    value["materials"] = materials
    for key in ("base_commit", "subject_commit", "subject_tree"):
        if not isinstance(value[key], str) or not re.fullmatch(r"[0-9a-f]{40}", value[key]):
            raise _error("Installed mutation commit binding is invalid")
    for key in (
        "spec_sha256",
        "policy_sha256",
        "classification_input_sha256",
        "verifier_context_sha256",
    ):
        if not isinstance(value[key], str) or not _SHA.fullmatch(value[key]):
            raise _error("Installed mutation digest binding is invalid")
    if not re.fullmatch(r"TASK-[0-9]{4,}", inputs.task_id) or not inputs.decision_unit_ids:
        raise _error("Installed mutation task binding is invalid")
    if (
        type(inputs.decision_unit_ids) is not tuple
        or len(set(inputs.decision_unit_ids)) != len(inputs.decision_unit_ids)
        or any(not re.fullmatch(r"DU-[0-9]{3,}", unit) for unit in inputs.decision_unit_ids)
    ):
        raise _error("Installed mutation decision units are invalid")
    if any(
        not isinstance(value[key], str) or not value[key].strip()
        for key in ("repository_id", "branch", "implementer_actor", "verifier_actor")
    ):
        raise _error("Installed mutation identity binding is invalid")
    validate_verifier_actor(inputs.implementer_actor, inputs.verifier_actor)
    return value


def _transformed_source(mutation_id: str, original: bytes) -> bytes:
    """Derive the fixed source overlay without compiling transported source."""
    if mutation_id not in _TARGETS:
        raise _error("Unknown installed mutation", "INSTALLED_MUTATION_UNKNOWN")
    filename, symbol, operator = _TARGETS[mutation_id]
    try:
        tree = ast.parse(original.decode("utf8"), filename=filename)
        functions = [
            item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == symbol
        ]
        if len(functions) != 1:
            raise ValueError("missing or ambiguous symbol")
        function = functions[0]
        outside = operators._outside_target_dump(tree, symbol)
        changed = False
        if mutation_id == "MUT-V2-001":
            for extras_name, comparison in (
                (
                    "extras",
                    "tuple(check['id'] for check in v2_checks[len(v1_checks):]) != extras",
                ),
                (
                    "node_v2_extras",
                    "tuple(check['id'] for check in node_v2_checks[len(NODE_V1_CHECKS):]) "
                    "!= node_v2_extras",
                ),
            ):
                extras = [
                    item
                    for item in ast.walk(function)
                    if isinstance(item, ast.Assign)
                    and len(item.targets) == 1
                    and isinstance(item.targets[0], ast.Name)
                    and item.targets[0].id == extras_name
                ]
                if len(extras) != 1 or ast.literal_eval(extras[0].value) != (
                    "acceptance",
                    "integration",
                    "targeted_mutation",
                    "independent_verifier",
                ):
                    raise ValueError("unknown complete extras")
                expected = ast.dump(
                    ast.parse(comparison, mode="eval").body, include_attributes=False
                )
                comparisons = [
                    item
                    for item in ast.walk(function)
                    if isinstance(item, ast.Compare)
                    and ast.dump(item, include_attributes=False) == expected
                ]
                if len(comparisons) != 1:
                    raise ValueError("missing or ambiguous comparison")
                comparisons[0].ops = [ast.NotIn()]
                comparisons[0].comparators = [
                    ast.Tuple(
                        elts=[
                            ast.Name(id=extras_name, ctx=ast.Load()),
                            ast.Tuple(
                                elts=[
                                    ast.Constant(value=value)
                                    for value in (
                                        "acceptance",
                                        "integration",
                                        "independent_verifier",
                                    )
                                ],
                                ctx=ast.Load(),
                            ),
                        ],
                        ctx=ast.Load(),
                    )
                ]
            changed = True
        elif mutation_id == "MUT-V2-002":
            changed = operators._replace_guard(
                function,
                lambda item: (
                    ast.unparse(item.test) == "implementer == verifier"
                    and operators._raises_contract_code(item, "VERIFIER_ACTOR_NOT_INDEPENDENT")
                ),
            )
        elif mutation_id == "MUT-V2-003":
            changed = operators._replace_guard(
                function,
                lambda item: (
                    ast.unparse(item.test)
                    == (
                        "any((by_id[identifier].get('status') != 'passed' "
                        "for identifier in expected))"
                    )
                    and operators._returns_literal_false(item)
                ),
            )
        elif mutation_id == "MUT-V2-004":
            assignments = [
                item
                for item in ast.walk(function)
                if isinstance(item, ast.Assign)
                and ast.unparse(item.value) == "mutation_facts.passed"
                and any(
                    ast.unparse(target) == "result['v2_mutation_killed']" for target in item.targets
                )
            ]
            if len(assignments) == 1:
                assignments[0].value = ast.Constant(value=True)
                changed = True
        else:
            changed = operators._replace_guard(
                function,
                lambda item: (
                    ast.unparse(item.test)
                    == (
                        "not isinstance(snapshot, str) or snapshot != "
                        "verification_snapshot_sha256(evidence)"
                    )
                    and operators._raises_contract_code(item, "EVIDENCE_SNAPSHOT_STALE")
                ),
            )
        if not changed or operators._outside_target_dump(tree, symbol) != outside:
            raise ValueError("unknown operator shape")
        return (ast.unparse(ast.fix_missing_locations(tree)) + "\n").encode("utf8")
    except (ValueError, TypeError, SyntaxError, UnicodeError, RecursionError) as error:
        raise _error(
            "Installed mutation operator precondition failed", "INSTALLED_MUTATION_OPERATOR_INVALID"
        ) from error


def _transformed(mutation_id: str, original: bytes) -> bytes:
    result = _transformed_source(mutation_id, original)
    try:
        compile(result, _TARGETS[mutation_id][0], "exec")
    except (ValueError, TypeError, SyntaxError, UnicodeError, RecursionError) as error:
        raise _error(
            "Installed mutation operator precondition failed", "INSTALLED_MUTATION_OPERATOR_INVALID"
        ) from error
    return result


def _mutate(mutation_id: str, path: Path) -> None:
    if mutation_id not in _TARGETS:
        raise _error("Unknown installed mutation", "INSTALLED_MUTATION_UNKNOWN")
    filename, symbol, operator = _TARGETS[mutation_id]
    if not isinstance(path, Path) or path.name != filename:
        raise _error(
            "Installed mutation file target differs", "INSTALLED_MUTATION_OPERATOR_INVALID"
        )
    original = node._read(path)
    expected = _transformed(mutation_id, original)
    if mutation_id != "MUT-V2-001":
        declaration = MutationDeclaration(
            mutation_id,
            mutation_id,
            "src/aiflow/" + filename,
            symbol,
            operator,
            "aiflow.installed_probe",
            "killed",
        )
        try:
            operators._apply_mutation(declaration, path)
        except (operators._RunFailure, OSError) as error:
            raise _error(
                "Installed mutation operator failed", "INSTALLED_MUTATION_OPERATOR_INVALID"
            ) from error
        if node._read(path) != expected:
            raise _error("Native operator differs from the fixed installed transformation")
    else:
        before = node._safe_info(path)
        with path.open("r+b") as stream:
            if node._identity(os.fstat(stream.fileno())) != node._identity(before):
                raise _error("Mutation file identity changed")
            stream.write(expected)
            stream.truncate()
            stream.flush()
            os.fsync(stream.fileno())


def _file(path: Path) -> dict[str, Any]:
    data = node._read(path)
    return {
        "path": str(path),
        "size": len(data),
        "sha256": node._sha(data),
        "identity": node._identity(node._safe_info(path)),
    }


def _probe_contract() -> dict[str, Any]:
    from aiflow import installed_probe

    path = Path(installed_probe.__file__).absolute()
    tree = ast.parse(node._read(path))
    anchors = {}
    for probe_id in PROBE_IDS:
        name = installed_probe.ASSERTION_ANCHORS[probe_id]
        functions = [
            item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == name
        ]
        if len(functions) != 1:
            raise _error("Probe assertion function is ambiguous")
        assertions = [item for item in ast.walk(functions[0]) if isinstance(item, ast.Assert)]
        if len(assertions) != 1:
            raise _error("Probe assertion anchor is ambiguous")
        anchors[probe_id] = {"function": name, "line": assertions[0].lineno}
    return {
        "protocol": installed_probe.PROTOCOL,
        "source": _file(path),
        "cases": installed_probe.CASE_SPECS,
        "mutant_observations": installed_probe.MUTANT_OBSERVATIONS,
        "anchors": anchors,
    }


def _interpreter() -> dict[str, Any]:
    if (
        os.name != "nt"
        or ctypes.sizeof(ctypes.c_void_p) != 8
        or sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 11)
        or not __debug__
        or not sys.dont_write_bytecode
    ):
        raise _error(
            "Installed mutations require Windows x64 CPython 3.11 with bytecode writes disabled",
            "INSTALLED_MUTATION_HOST_UNSUPPORTED",
        )
    prefix = Path(sys.prefix).resolve()
    base = Path(sys.base_prefix).resolve()
    executable = Path(sys.executable).resolve()
    base_executable = Path(getattr(sys, "_base_executable", "")).resolve()
    site = prefix / "Lib/site-packages"
    if (
        prefix == base
        or executable != prefix / "Scripts/python.exe"
        or not site.is_dir()
        or base_executable != base / "python.exe"
    ):
        raise _error("Installed interpreter layout is unsupported")
    return {
        "executable": _file(executable),
        "base_executable": _file(base_executable),
        "runtime": _file(base / "python311.dll"),
        "prefix": str(prefix),
        "site": str(site),
        "base_prefix": str(base),
        "implementation": sys.implementation.name,
        "version": list(sys.version_info[:3]),
        "cache_tag": sys.implementation.cache_tag,
    }


def _closure(engine: Mapping[str, Any], prefix: Path) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for distribution in engine["distributions"]:
        for row in distribution["files"]:
            files[row["path"]] = row
    startup = engine["startup"]
    for row in startup["files"]:
        files[row["path"]] = row
    if startup["pyvenv_configuration"] is not None:
        row = startup["pyvenv_configuration"]
        files[row["path"]] = row
    rows: dict[str, dict[str, Any]] = {}
    for absolute, row in files.items():
        path = Path(absolute).resolve(strict=True)
        try:
            relative = _path(path.relative_to(prefix).as_posix())
        except ValueError as error:
            raise _error("Declared installed file escapes the fixed environment") from error
        if not (
            relative.startswith("Lib/site-packages/")
            or relative.startswith("Scripts/")
            or relative == "pyvenv.cfg"
        ):
            raise _error("Installed closure has an unsupported file role")
        rows[relative] = {
            "path": relative,
            "kind": "file",
            **{key: row[key] for key in ("size", "sha256", "identity")},
        }
        parent = Path(relative).parent
        while str(parent) != ".":
            name = parent.as_posix()
            rows[name] = {
                "path": name,
                "kind": "directory",
                "identity": node._identity(node._safe_info(prefix / parent, directory=True)),
            }
            parent = parent.parent
    ordered = sorted(rows.values(), key=lambda item: item["path"].encode("utf8"))
    if len(ordered) > node.MAX_ENTRIES:
        raise _error("Installed closure exceeds its entry budget")
    total = sum(item["size"] for item in ordered if item["kind"] == "file")
    if total > node.MAX_TOTAL_BYTES:
        raise _error("Installed closure exceeds its byte budget")
    return {
        "root": str(prefix),
        "identity": node._identity(node._safe_info(prefix, directory=True)),
        "entries": ordered,
        "total_bytes": total,
    }


def _materials() -> bytes:
    interpreter = _interpreter()
    budget = [node.MAX_ENTRIES, node.MAX_TOTAL_BYTES]
    for role in ("executable", "base_executable", "runtime"):
        node._take_budget(budget, interpreter[role]["size"])
    engine = node._engine(budget=budget)
    probes = _probe_contract()
    installation = Path(interpreter["site"])
    if (
        Path(probes["source"]["path"]) != installation / "aiflow/installed_probe.py"
        or Path(__file__).absolute() != installation / "aiflow/installed_mutations.py"
    ):
        raise _error("Installed mutation modules are outside the ordinary distribution")
    engine_document = {
        "installed": engine,
        "closure": _closure(engine, Path(interpreter["prefix"])),
    }
    return node._canonical(
        {
            "kind": ACTION_TYPE,
            "version": 1,
            "engine": engine_document,
            "interpreter": interpreter,
            "host_tools": node._host_tools(budget=budget),
            "probes": probes,
            "operators": {
                "declarations": _TARGETS,
                "source": _file(Path(__file__).absolute()),
                "native_source": _file(Path(operators.__file__).absolute()),
                "bootstrap_sha256": node._sha(_BOOTSTRAP.encode()),
            },
        }
    )


def _node_v2_policy(root: Path) -> bool:
    bundle = load_policy_bundle(root)
    return (
        is_node_policy_candidate(bundle.documents)
        and bundle.policy_version == "3.2.0"
        and is_node_policy(bundle)
    )


def _require_pending_approval(root: Path, task_id: str, *, executing: bool, node_v2: bool) -> None:
    """Only read-only Node V2 replay admits the existing valid code marker."""
    if executing or not node_v2:
        native._require_no_pending_approval(root, task_id)
        return
    marker = resolve_task_path(root, task_id) / "approval_pending.json"
    try:
        marker.lstat()
    except FileNotFoundError:
        return
    node._safe_info(marker)
    evidence = node._json(resolve_task_path(root, task_id) / "evidence.json")
    if (
        not isinstance(evidence, dict)
        or evidence.get("schema_version") != "3.2"
        or evidence.get("verification_level") != "V2"
        or evidence.get("phase") != "final"
        or evidence.get("mode") != "local"
    ):
        raise _error("Only current Node V2 final code approval may be pending")
    from aiflow.evidence import validate_v2_snapshot

    validate_v2_snapshot(evidence)
    classification = read_task_json(
        root, task_id, "classification.json", contract_name="classification"
    )
    if (
        not isinstance(classification, Mapping)
        or classification.get("effective_verification_level") != "V2"
    ):
        raise _error("Only a Node V2 task may have this pending code approval")
    record = read_task_record_strict(root, task_id)
    # This helper validates the exact registered marker and review originals;
    # it neither rebuilds review context nor replays Node or mutation evidence.
    node._governance_snapshot(root, task_id, record.events)


def _authority(
    root: Path, task_id: str, verifier_actor: str, *, executing: bool = True
) -> tuple[InstalledMutationInputs, dict[str, Any], dict[str, Any]]:
    if not sys.dont_write_bytecode:
        raise _error(
            "Parent bytecode writes must be disabled", "INSTALLED_MUTATION_HOST_UNSUPPORTED"
        )
    node._ancestors(root)
    record = read_task_record_strict(root, task_id)
    task = record.task
    task, classification, policy_sha = native._validate_bindings(
        root, task_id, str(task["subject_commit"])
    )
    bundle = load_policy_bundle(root)
    node_v2 = (
        is_node_policy_candidate(bundle.documents)
        and bundle.policy_version == "3.2.0"
        and is_node_policy(bundle)
    )
    if (
        (executing and task["current_state"] != "IMPLEMENTING")
        or classification.get("effective_verification_level") != "V2"
        or (is_node_policy_candidate(bundle.documents) and not node_v2)
    ):
        raise _error("Installed mutation preparation requires a supported IMPLEMENTING V2 task")
    _require_pending_approval(root, task_id, executing=executing, node_v2=node_v2)
    approvals = native._action_approvals(root, task_id)
    native._require_current_spec_approvals(
        task_id, task, classification, approvals, policy_sha256=policy_sha
    )
    units = parse_decision_units(task)
    if not any(
        "action_approval" in unit.get("permission_requirements", [])
        and unit.get("verification_requirements", {}).get("targeted_mutation_required") is True
        for unit in units
    ):
        raise _error("Installed mutation task lacks the required explicit action facts")
    context = collect_git_context(root)
    prefix = f".ai/tasks/{task_id}/"
    if any(path != prefix[:-1] and not path.startswith(prefix) for path in context.dirty_paths):
        raise _error("Installed mutation worktree is not governance-only")
    implementer, verifier = validate_verifier_actor(
        current_implementer_actor(record.events), verifier_actor
    )
    verifier_context = build_verifier_context(root, task_id)
    result = InstalledMutationInputs(
        str(task["repository_id"]),
        task_id,
        tuple(str(unit["decision_unit_id"]) for unit in units),
        str(task["branch"]),
        str(task["base_commit"]),
        str(task["subject_commit"]),
        node._git(root, "rev-parse", str(task["subject_commit"]) + "^{tree}").decode().strip(),
        str(task["frozen_spec_sha256"]),
        policy_sha,
        str(classification["classification_input_sha256"]),
        implementer,
        verifier,
        context_sha256(verifier_context),
        _materials(),
    )
    _input_document(result)
    return result, task, verifier_context


def prepare_installed_mutations(
    root: Path, task_id: str, *, verifier_actor: str
) -> InstalledMutationInputs:
    """Collect authority-side live facts; no action consumption, run or process probe."""
    return _authority(Path(root).absolute(), task_id, verifier_actor)[0]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _summary(inputs: InstalledMutationInputs) -> str:
    return node._canonical({"kind": ACTION_TYPE, "inputs_sha256": inputs.sha256}).decode()


def _approval_context(
    inputs: InstalledMutationInputs, unit: str, digest: str | None = None
) -> ApprovalContext:
    return ApprovalContext(
        inputs.task_id,
        unit,
        "IMPLEMENTING",
        inputs.spec_sha256,
        inputs.policy_sha256,
        inputs.base_commit,
        inputs.subject_commit,
        digest,
    )


def _normalize_action(
    root: Path, path: Path, inputs: InstalledMutationInputs, *, now: str
) -> Mapping[str, object]:
    action = validate_action_file(node._json(path), subject_commit=inputs.subject_commit, now=now)
    record = read_task_record_strict(root, inputs.task_id)
    units = {str(unit["decision_unit_id"]): unit for unit in parse_decision_units(record.task)}
    unit = units.get(str(action.get("decision_unit_id")))
    if (
        action.get("action_type") != ACTION_TYPE
        or action.get("target") != inputs.task_id
        or action.get("parameter_summary") != _summary(inputs)
        or action.get("classification_input_sha256") != inputs.classification_input_sha256
        or unit is None
        or "action_approval" not in unit.get("permission_requirements", [])
        or unit.get("verification_requirements", {}).get("targeted_mutation_required") is not True
    ):
        raise _error(
            "Installed mutation action does not match the exact current inputs",
            "ACTION_BINDING_STALE",
        )
    return action


def _select_action(
    root: Path, inputs: InstalledMutationInputs
) -> tuple[Path, Mapping[str, object], Mapping[str, object]]:
    native._require_no_pending_approval(root, inputs.task_id)
    approvals = native._action_approvals(root, inputs.task_id)
    used = native._used_action_digests(root, inputs.task_id)
    task_dir = resolve_task_path(root, inputs.task_id)
    found = []
    spent = False
    for path in sorted(task_dir.glob("action-installed-engine-mutation-*.json")):
        raw = node._json(path)
        if not isinstance(raw, dict):
            raise _error("Installed mutation action is invalid", "ACTION_FILE_INVALID")
        if not isinstance(raw.get("subject_commit"), str):
            raise _error("Installed action subject is missing", "ACTION_FILE_INVALID")
        if raw["subject_commit"] != inputs.subject_commit:
            continue
        try:
            action = _normalize_action(root, path, inputs, now=_now())
        except ContractError as error:
            if error.code == "ACTION_APPROVAL_EXPIRED":
                continue
            raise
        digest = canonical_action_sha256(action)
        approval = matching_approval(
            approvals,
            approval_type="action",
            context=_approval_context(inputs, str(action["decision_unit_id"]), digest),
        )
        if approval is None:
            continue
        receipt = task_dir / "logs" / f"installed-action-use-{digest}.json"
        claim = task_dir / "logs" / f"installed-action-launch-{digest}.json"
        if digest in used or os.path.lexists(receipt) or os.path.lexists(claim):
            spent = True
        else:
            found.append((path, action, approval))
    if len(found) > 1:
        raise _error("Installed mutation approvals are ambiguous", "ACTION_APPROVAL_AMBIGUOUS")
    if not found:
        raise _error(
            "Installed mutation action approval is used, missing or ambiguous",
            "ACTION_APPROVAL_USED" if spent else "ACTION_APPROVAL_REQUIRED",
        )
    return found[0]


def _consume_action(root: Path, inputs: InstalledMutationInputs, run_ref: str) -> dict[str, Any]:
    _select_action(root, inputs)
    with native._locked_action_consumption(root, inputs.task_id):
        fresh = prepare_installed_mutations(
            root, inputs.task_id, verifier_actor=inputs.verifier_actor
        )
        if fresh.sha256 != inputs.sha256:
            raise _error("Installed mutation inputs changed before action consumption")
        path, action, approval = _select_action(root, inputs)
        digest = canonical_action_sha256(action)
        logs = resolve_task_path(root, inputs.task_id, "logs")
        receipt = logs / f"installed-action-use-{digest}.json"
        timestamp = _now()
        use = {
            "kind": ACTION_TYPE,
            "version": 1,
            "task_id": inputs.task_id,
            "inputs_sha256": inputs.sha256,
            "action_sha256": digest,
            "action_ref": path.relative_to(root).as_posix(),
            "decision_unit_id": action["decision_unit_id"],
            "created_at": timestamp,
            "single_use": True,
        }
        node._write_new(receipt, node._canonical(use))
        identity = node._identity(node._safe_info(receipt))
        record_task_event(
            root,
            inputs.task_id,
            event_type="approval_recorded",
            actor="aiflow-installed-mutations",
            payload={
                "approval_type": "action",
                "action_status": "consumed",
                "action_sha256": digest,
                "receipt_ref": receipt.relative_to(root).as_posix(),
                "receipt_device": identity["device"],
                "receipt_inode": identity["inode"],
                "kind": ACTION_TYPE,
                "inputs_sha256": inputs.sha256,
            },
        )
        claim = logs / f"installed-action-launch-{digest}.json"
        claim_data = {
            "kind": ACTION_TYPE,
            "version": 1,
            "task_id": inputs.task_id,
            "action_sha256": digest,
            "inputs_sha256": inputs.sha256,
            "receipt_ref": receipt.relative_to(root).as_posix(),
            "receipt_identity": identity,
            "run_ref": run_ref,
            "claimed_at": timestamp,
            "single_use": True,
        }
        node._write_new(claim, node._canonical(claim_data))
        return {
            "digest": digest,
            "action_ref": path.relative_to(root).as_posix(),
            "approval_sha256": node._sha(node._canonical(approval)),
            "receipt": _file(receipt),
            "claim": _file(claim),
            "decision_unit_id": str(action["decision_unit_id"]),
        }


_BOOTSTRAP = r"""
import contextlib,hashlib,json,sys
from pathlib import Path
from types import FunctionType

def _contextmanager_template():
    yield

_contextmanager_code=contextlib.contextmanager(_contextmanager_template).__code__

def _guard_origin(value,namespace,path,name):
    if Path(value.__code__.co_filename).absolute()==path:
        return True
    wrapped=getattr(value,'__wrapped__',None)
    closure=value.__closure__
    if (value.__code__ is not _contextmanager_code
        or value.__globals__ is not vars(contextlib)
        or value.__code__.co_freevars!=('func',)
        or closure is None or len(closure)!=1
        or not isinstance(wrapped,FunctionType)):
        return False
    try:
        original=closure[0].cell_contents
    except ValueError:
        return False
    return (original is wrapped and wrapped.__module__==name
        and wrapped.__globals__ is namespace
        and bool(wrapped.__code__.co_flags & 0x20)
        and Path(wrapped.__code__.co_filename).absolute()==path)
site,probe_id,cache=(Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]))
assert __debug__ and sys.implementation.name=='cpython'
assert sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.optimize==0
assert sys.dont_write_bytecode and Path(sys.pycache_prefix)==cache
sys.path.insert(0,str(site))
from aiflow.installed_probe import run_probe
report=run_probe(probe_id)
loaded=[]
roots={'aiflow','yaml','_yaml','jsonschema','attrs','attr','referencing',
       'jsonschema_specifications','rpds','typing_extensions','setuptools','_distutils_hack'}
for name,module in sorted(tuple(sys.modules.items())):
    if name.split('.',1)[0] not in roots:
        continue
    origin=getattr(getattr(module,'__spec__',None),'origin',None)
    filename=getattr(module,'__file__',None)
    if filename is None:
        if getattr(getattr(module,'__spec__',None),'submodule_search_locations',None) is None:
            raise RuntimeError('MISSING_MODULE_ORIGIN')
        continue
    path=Path(filename).absolute()
    relative=path.relative_to(site).as_posix()
    if origin!=filename:
        raise RuntimeError('MODULE_ORIGIN_MISMATCH')
    if name=='aiflow' or name.startswith('aiflow.'):
        for value in vars(module).values():
            if isinstance(value,FunctionType) and value.__module__==name:
                if not _guard_origin(value,vars(module),path,name):
                    raise RuntimeError('GUARD_CODE_ORIGIN_MISMATCH')
    data=path.read_bytes()
    loaded.append({'name':name,'path':relative,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
facts={'executable':sys.executable,'base_executable':sys._base_executable,
       'base_prefix':sys.base_prefix,'implementation':sys.implementation.name,
       'version':list(sys.version_info[:3]),'cache_tag':sys.implementation.cache_tag,
       'isolated':sys.flags.isolated,'no_site':sys.flags.no_site,
       'optimize':sys.flags.optimize,'dont_write_bytecode':sys.dont_write_bytecode,
       'debug':__debug__,'cache_prefix':sys.pycache_prefix}
envelope={'kind':'installed-probe-execution-v1','probe':report,'loaded':loaded,'interpreter':facts}
sys.stdout.buffer.write((json.dumps(envelope,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8'))
sys.stdout.buffer.flush()
ok=all(c['setup']==c['call']==c['teardown']=='passed' for c in report['cases'])
raise SystemExit(0 if ok else 1)
"""


def _environment(phase: Path, interpreter: Mapping[str, Any]) -> dict[str, str]:
    return _phase_environment(phase, interpreter, node._windows_root())


def _phase_environment(phase: Path, interpreter: Mapping[str, Any], system: Path) -> dict[str, str]:
    """The fixed environment, also checked as producing-coordinate data."""
    return {
        "SystemRoot": str(system),
        "COMSPEC": str(system / "System32/cmd.exe"),
        "PATH": os.pathsep.join(
            (str(Path(interpreter["base_executable"]["path"]).parent), str(system / "System32"))
        ),
        "HOME": str(phase / "h"),
        "USERPROFILE": str(phase / "h"),
        "APPDATA": str(phase / "h"),
        "LOCALAPPDATA": str(phase / "h"),
        "TMPDIR": str(phase / "t"),
        "TEMP": str(phase / "t"),
        "TMP": str(phase / "t"),
    }


def _argv(phase: Path, probe_id: str, materials: Mapping[str, Any]) -> tuple[str, ...]:
    return (
        str(materials["interpreter"]["executable"]["path"]),
        "-I",
        "-S",
        "-B",
        "-X",
        "pycache_prefix=" + str(phase / "c"),
        "-c",
        _BOOTSTRAP,
        str(phase / "i/Lib/site-packages"),
        probe_id,
        str(phase / "c"),
    )


def _retained_file(row: object, *, os_role: str | None = None) -> None:
    item = _closed(row, {"path", "size", "sha256", "identity"})
    path = Path(item["path"])
    data = node._read(path, os_role=os_role)
    if (
        len(data) != item["size"]
        or node._sha(data) != item["sha256"]
        or node._canonical(node._identity(node._safe_info(path, os_role=os_role)))
        != node._canonical(item["identity"])
    ):
        raise _error("Bound installed original changed", "INSTALLED_MUTATION_MATERIAL_STALE")


def _current_materials(inputs: InstalledMutationInputs) -> dict[str, Any]:
    material = _input_document(inputs)["materials"]
    if _materials() != inputs.materials:
        raise _error(
            "Current installed engine/probe/interpreter inputs differ",
            "INSTALLED_MUTATION_MATERIAL_STALE",
        )
    return cast(dict[str, Any], material)


def _receipt(
    phase: Path,
    stage: Mapping[str, Any],
    probe_id: str,
    materials: Mapping[str, Any],
    *,
    producing_phase: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    receipt = node._json(phase / "raw/receipt.json")
    keys = {
        "returncode",
        "timed_out",
        "stdout_overflow",
        "stderr_overflow",
        "cleanup",
        "execution_error",
        "receipt",
        "stdout_sha256",
        "stderr_sha256",
        "stdout_size",
        "stderr_size",
        "argv",
        "cwd",
        "environment_sha256",
        "timeout_seconds",
        "duration_ms",
    }
    _closed(receipt, keys)
    if node._canonical(receipt) != node._canonical(stage["receipt"]):
        raise _error("Installed process receipt differs from its original")
    if type(receipt["returncode"]) is not int or receipt["returncode"] not in (0, 1):
        raise _error(
            "Installed probe has an unsupported exit", "INSTALLED_MUTATION_PROCESS_INVALID"
        )
    # A mutant's real exit 1 is permitted, never rewritten in retained evidence.
    # All non-exit success conditions remain the existing Job runner conditions.
    if not node._successful({**receipt, "returncode": 0}):
        raise _error(
            "Installed process cleanup or stream facts are unverified",
            "INSTALLED_MUTATION_PROCESS_INVALID",
        )
    for key in ("timed_out", "stdout_overflow", "stderr_overflow", "execution_error"):
        if type(receipt[key]) is not bool:
            raise _error("Installed process flag has the wrong type")
    for key in ("stdout_size", "stderr_size", "duration_ms", "timeout_seconds"):
        if type(receipt[key]) is not int or receipt[key] < 0:
            raise _error("Installed process integer has the wrong type")
    observed = _closed(
        receipt["receipt"],
        {
            "process_id",
            "creation_time_filetime",
            "created_suspended",
            "assigned",
            "initial_membership",
            "resumed",
            "job_empty",
            "stdout_eof",
            "stderr_eof",
            "terminate_requested",
            "closed",
        },
    )
    if (
        any(
            type(observed[key]) is not int or observed[key] <= 0
            for key in ("process_id", "creation_time_filetime")
        )
        or any(
            observed[key] is not True
            for key in (
                "created_suspended",
                "assigned",
                "initial_membership",
                "resumed",
                "job_empty",
                "stdout_eof",
                "stderr_eof",
                "closed",
            )
        )
        or observed["terminate_requested"] is not False
    ):
        raise _error(
            "Installed process Job ownership is incomplete", "INSTALLED_MUTATION_PROCESS_INVALID"
        )
    coordinates = phase if producing_phase is None else producing_phase
    expected_environment = (
        _environment(phase, materials["interpreter"]) if environment is None else environment
    )
    if (
        receipt["argv"] != list(_argv(coordinates, probe_id, materials))
        or receipt["cwd"] != str(coordinates)
        or receipt["timeout_seconds"] != _TIMEOUT
        or receipt["environment_sha256"] != node._sha(node._canonical(expected_environment))
    ):
        raise _error("Installed process roles differ from the fixed plan")
    for stream in ("stdout", "stderr"):
        data = node._read(phase / "raw" / f"{stream}.raw", limit=1024 * 1024)
        if (
            receipt[stream + "_size"] != len(data)
            or receipt[stream + "_sha256"] != node._sha(data)
            or node._read(phase / "raw" / f"{stream}.log", limit=1024 * 1024)
            != redact_text(data.decode("utf8", errors="replace")).encode()
        ):
            raise _error("Installed probe raw stream has changed")
    if receipt["stderr_size"] != 0:
        raise _error("The fixed installed probe must not write stderr")
    return cast(dict[str, Any], receipt)


def _envelope(
    phase: Path,
    stage: Mapping[str, Any],
    probe_id: str,
    materials: Mapping[str, Any],
    *,
    producing_phase: Path | None = None,
    retained_inventory: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    _closed(stage, {"closure", "cache", "receipt"})
    coordinates = phase if producing_phase is None else producing_phase
    closure = (
        node._inventory(phase / "i")
        if retained_inventory is None
        else _ci_subinventory(retained_inventory, "i")
    )
    if node._canonical(closure) != node._canonical(stage["closure"]):
        raise _error("Executed installed copy changed")
    cache = (
        node._inventory(phase / "c")
        if retained_inventory is None
        else _ci_subinventory(retained_inventory, "c")
    )
    if cache["entries"] or node._canonical(cache) != node._canonical(stage["cache"]):
        raise _error("Installed probe bytecode cache was not isolated")
    receipt = _receipt(
        phase,
        stage,
        probe_id,
        materials,
        producing_phase=producing_phase,
        environment=environment,
    )
    data = node._read(phase / "raw/stdout.raw", limit=1024 * 1024)
    report = node._json_bytes(data)
    _closed(report, {"kind", "probe", "loaded", "interpreter"})
    if (
        report["kind"] != "installed-probe-execution-v1"
        or data != node._canonical(report) + b"\n"
        or node._read(phase / "report.json", limit=1024 * 1024) != node._canonical(report)
    ):
        raise _error("Installed probe report is missing, ambiguous or noncanonical")
    expected_interpreter = materials["interpreter"]
    expected = {
        "executable": expected_interpreter["executable"]["path"],
        "base_executable": expected_interpreter["base_executable"]["path"],
        "base_prefix": expected_interpreter["base_prefix"],
        "implementation": expected_interpreter["implementation"],
        "version": expected_interpreter["version"],
        "cache_tag": expected_interpreter["cache_tag"],
        "isolated": 1,
        "no_site": 1,
        "optimize": 0,
        "dont_write_bytecode": True,
        "debug": True,
        "cache_prefix": str(coordinates / "c"),
    }
    if node._canonical(report["interpreter"]) != node._canonical(expected):
        raise _error("Installed probe ran with the wrong interpreter or cache")
    files = {
        item["path"].removeprefix("Lib/site-packages/"): item
        for item in closure["entries"]
        if item["kind"] == "file" and item["path"].startswith("Lib/site-packages/")
    }
    loaded = report["loaded"]
    if not isinstance(loaded, list) or not loaded or len(loaded) > node.MAX_ENTRIES:
        raise _error("Installed probe loaded-module inventory is invalid")
    names = []
    for module in loaded:
        _closed(module, {"name", "path", "size", "sha256"})
        relative = _path(module["path"])
        original = files.get(relative)
        if (
            not isinstance(module["name"], str)
            or not re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", module["name"]
            )
            or original is None
            or node._canonical({key: module[key] for key in ("size", "sha256")})
            != node._canonical({key: original[key] for key in ("size", "sha256")})
        ):
            raise _error("Probe loaded unbound installed bytes")
        if module["name"].split(".", 1)[0] not in {
            "aiflow",
            "yaml",
            "_yaml",
            "jsonschema",
            "attrs",
            "attr",
            "referencing",
            "jsonschema_specifications",
            "rpds",
            "typing_extensions",
            "setuptools",
            "_distutils_hack",
        }:
            raise _error("Installed probe reported an unknown module namespace")
        stem = module["name"].replace(".", "/")
        paths = {stem + ".py", stem + "/__init__.py"}
        paths.update(stem + suffix for suffix in importlib.machinery.EXTENSION_SUFFIXES)
        if relative not in paths:
            raise _error("Installed module name differs from its bound file role")
        names.append(module["name"])
    if (
        names != sorted(set(names))
        or "aiflow" not in names
        or "aiflow.installed_probe" not in names
        or "aiflow." + _TARGETS[probe_id][0].removesuffix(".py") not in names
    ):
        raise _error("Installed probe did not load its actual guard")
    probe = _closed(report["probe"], {"protocol", "probe_id", "cases", "terminal"})
    if (
        probe["protocol"] != materials["probes"]["protocol"]
        or probe["probe_id"] != probe_id
        or probe["terminal"] != "complete"
    ):
        raise _error("Installed probe selection or terminal marker differs")
    cases = probe["cases"]
    expected_cases = materials["probes"]["cases"][probe_id]
    if not isinstance(cases, list) or len(cases) != len(expected_cases):
        raise _error("Installed probe case inventory differs")
    for case, (case_id, _observation) in zip(cases, expected_cases, strict=True):
        _closed(case, {"id", "setup", "call", "teardown", "observed", "exception"})
        if case["id"] != case_id or any(
            case[role] not in {"passed", "failed", "not_run"}
            for role in ("setup", "call", "teardown")
        ):
            raise _error("Installed probe phases or cases are invalid")
        if case["exception"] is not None:
            exception = _closed(case["exception"], {"type", "message", "frames"})
            if (
                not isinstance(exception["type"], str)
                or not isinstance(exception["message"], str)
                or not isinstance(exception["frames"], list)
                or not 1 <= len(exception["frames"]) <= 64
            ):
                raise _error("Installed probe exception is incomplete")
            for frame in exception["frames"]:
                _closed(frame, {"path", "line", "function"})
                if (
                    type(frame["line"]) is not int
                    or frame["line"] < 1
                    or not isinstance(frame["path"], str)
                    or not isinstance(frame["function"], str)
                ):
                    raise _error("Installed probe traceback is invalid")
    any_failure = any(
        case[role] != "passed" for case in cases for role in ("setup", "call", "teardown")
    )
    if receipt["returncode"] != int(any_failure):
        raise _error("Installed probe exit and report disagree")
    allowed_files = (
        {"i/" + item["path"] for item in closure["entries"] if item["kind"] == "file"}
        | {"report.json"}
        | {
            "raw/" + name
            for name in ("receipt.json", "stdout.raw", "stderr.raw", "stdout.log", "stderr.log")
        }
    )
    allowed_directories = {
        "i/" + item["path"] for item in closure["entries"] if item["kind"] == "directory"
    } | {"i", "c", "h", "t", "raw"}
    inventory = node._inventory(phase) if retained_inventory is None else retained_inventory
    for item in inventory["entries"]:
        if item["path"] not in (allowed_files if item["kind"] == "file" else allowed_directories):
            raise _error("Installed probe created undeclared output")
    return probe


def _baseline_passes(
    report: Mapping[str, Any], probe_id: str, materials: Mapping[str, Any]
) -> bool:
    expected = materials["probes"]["cases"][probe_id]
    return all(
        case["setup"] == case["call"] == case["teardown"] == "passed"
        and case["exception"] is None
        and node._canonical(case["observed"]) == node._canonical(observed)
        for case, (_case_id, observed) in zip(report["cases"], expected, strict=True)
    )


def _derive_mutant(
    report: Mapping[str, Any], probe_id: str, phase: Path, materials: Mapping[str, Any]
) -> str:
    if _baseline_passes(report, probe_id, materials):
        return "survived"
    expected = materials["probes"]["cases"][probe_id]
    for case, (_case_id, observed) in zip(report["cases"][:-1], expected[:-1], strict=True):
        if (
            case["setup"] != "passed"
            or case["call"] != "passed"
            or case["teardown"] != "passed"
            or case["exception"] is not None
            or node._canonical(case["observed"]) != node._canonical(observed)
        ):
            return "unverified"
    case = report["cases"][-1]
    exception = case["exception"]
    anchor = materials["probes"]["anchors"][probe_id]
    if (
        case["setup"] != "passed"
        or case["call"] != "failed"
        or case["teardown"] != "passed"
        or node._canonical(case["observed"])
        != node._canonical(materials["probes"]["mutant_observations"][probe_id])
        or not isinstance(exception, dict)
        or exception["type"] != "AssertionError"
    ):
        return "unverified"
    terminal = exception["frames"][-1]
    if terminal != {
        "path": str(phase / "i/Lib/site-packages/aiflow/installed_probe.py"),
        "line": anchor["line"],
        "function": anchor["function"],
    }:
        return "unverified"
    return "killed"


def _run_stage(
    phase: Path,
    pair: dict[str, Any],
    role: str,
    probe_id: str,
    materials: Mapping[str, Any],
    budget: list[int],
) -> None:
    phase.mkdir()
    source = materials["engine"]["closure"]
    for row in source["entries"]:
        node._take_budget(budget, row.get("size", 0))
    copied = node._copy_tree(Path(source["root"]), phase / "i", source)
    stage: dict[str, Any] = {"closure": copied, "cache": None, "receipt": None}
    pair[role] = stage
    if role == "mutant":
        relative = "Lib/site-packages/aiflow/" + _TARGETS[probe_id][0]
        target = phase / "i" / relative
        original = node._read(target)
        _mutate(probe_id, target)
        changed = node._read(target)
        pair["overlay"] = {
            "path": relative,
            "before_sha256": node._sha(original),
            "after_sha256": node._sha(changed),
        }
        stage["closure"] = node._inventory(phase / "i")
    for name in ("c", "t", "h"):
        (phase / name).mkdir()
    stage["cache"] = node._inventory(phase / "c")
    stage["receipt"] = node._process(
        _argv(phase, probe_id, materials),
        cwd=phase,
        environment=_environment(phase, materials["interpreter"]),
        timeout=_TIMEOUT,
        output=phase / "raw",
    )
    raw = node._read(phase / "raw/stdout.raw", limit=1024 * 1024)
    parsed = node._json_bytes(raw)
    node._write_new(phase / "report.json", node._canonical(parsed))
    _envelope(phase, stage, probe_id, materials)


def _pure_task(root: Path, inputs: InstalledMutationInputs) -> None:
    record = read_task_record_strict(root, inputs.task_id)
    task = record.task
    classification = read_task_json(
        root, inputs.task_id, "classification.json", contract_name="classification"
    )
    if not isinstance(classification, Mapping):
        raise _error("Current installed mutation classification is invalid")
    digest, _synchronized = current_classification_input_digest(
        task, task["decision_units"], classification, record.events
    )
    actual = (
        str(task["repository_id"]),
        str(task["branch"]),
        str(task["base_commit"]),
        str(task["subject_commit"]),
        str(task["frozen_spec_sha256"]),
        load_policy_bundle(root).sha256,
        digest,
        tuple(str(unit["decision_unit_id"]) for unit in parse_decision_units(task)),
        current_implementer_actor(record.events),
    )
    expected = (
        inputs.repository_id,
        inputs.branch,
        inputs.base_commit,
        inputs.subject_commit,
        inputs.spec_sha256,
        inputs.policy_sha256,
        inputs.classification_input_sha256,
        inputs.decision_unit_ids,
        inputs.implementer_actor,
    )
    if (
        actual != expected
        or classification.get("effective_verification_level") != "V2"
        or classification.get("policy_sha256") != inputs.policy_sha256
        or classification.get("classification_input_sha256") != inputs.classification_input_sha256
        or specification_digest(
            (resolve_task_path(root, inputs.task_id, "spec.md")).read_text(encoding="utf8")
        )
        != inputs.spec_sha256
    ):
        raise _error("Current installed mutation task facts are stale")


def _action_originals(
    root: Path, inputs: InstalledMutationInputs, original: object, run: Path
) -> None:
    action = _closed(
        original,
        {"digest", "action_ref", "approval_sha256", "receipt", "claim", "decision_unit_id"},
    )
    digest = action["digest"]
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise _error("Installed action digest is invalid")
    logs = resolve_task_path(root, inputs.task_id, "logs")
    receipt_path = logs / f"installed-action-use-{digest}.json"
    claim_path = logs / f"installed-action-launch-{digest}.json"
    if action["receipt"]["path"] != str(receipt_path) or action["claim"]["path"] != str(claim_path):
        raise _error("Installed action originals have the wrong roles")
    _retained_file(action["receipt"])
    _retained_file(action["claim"])
    claim = _closed(
        node._json(claim_path),
        {
            "kind",
            "version",
            "task_id",
            "action_sha256",
            "inputs_sha256",
            "receipt_ref",
            "receipt_identity",
            "run_ref",
            "claimed_at",
            "single_use",
        },
    )
    expected_claim = {
        "kind": ACTION_TYPE,
        "version": 1,
        "task_id": inputs.task_id,
        "action_sha256": digest,
        "inputs_sha256": inputs.sha256,
        "receipt_ref": receipt_path.relative_to(root).as_posix(),
        "receipt_identity": action["receipt"]["identity"],
        "run_ref": run.relative_to(root).as_posix(),
        "claimed_at": claim["claimed_at"],
        "single_use": True,
    }
    if node._canonical(claim) != node._canonical(expected_claim):
        raise _error("Installed action launch claim differs")
    path = root / _path(action["action_ref"])
    task_dir = resolve_task_path(root, inputs.task_id)
    if (
        path.parent != task_dir
        or not path.name.startswith("action-installed-engine-mutation-")
        or path.suffix != ".json"
    ):
        raise _error("Installed action file is outside its namespace")
    normalized = _normalize_action(root, path, inputs, now=claim["claimed_at"])
    unit = str(normalized["decision_unit_id"])
    if canonical_action_sha256(normalized) != digest or unit != action["decision_unit_id"]:
        raise _error("Installed action bytes changed")
    use = node._json(receipt_path)
    expected_use = {
        "kind": ACTION_TYPE,
        "version": 1,
        "task_id": inputs.task_id,
        "inputs_sha256": inputs.sha256,
        "action_sha256": digest,
        "action_ref": action["action_ref"],
        "decision_unit_id": unit,
        "created_at": claim["claimed_at"],
        "single_use": True,
    }
    if node._canonical(use) != node._canonical(expected_use):
        raise _error("Installed action consumption receipt differs")
    used = native._used_action_digests(root, inputs.task_id)
    identity = action["receipt"]["identity"]
    if used.get(digest) != (
        receipt_path.relative_to(root).as_posix(),
        identity["device"],
        identity["inode"],
    ):
        raise _error("Installed action consumption lacks its ledger event")
    approvals = native._action_approvals(root, inputs.task_id)
    selected = [
        approval
        for approval in approvals
        if node._sha(node._canonical(approval)) == action["approval_sha256"]
    ]
    if (
        len(selected) != 1
        or not approval_is_current(
            selected[0], _approval_context(inputs, unit, digest), now=claim["claimed_at"]
        )
        or _utc(cast(str, selected[0]["approved_at"])) > _utc(claim["claimed_at"])
    ):
        raise _error("Installed action approval is missing or stale")


def _pair_originals(
    run: Path, index: int, pair: object, probe_id: str, materials: Mapping[str, Any]
) -> str:
    value = _closed(pair, {"id", "overlay", "baseline", "mutant"})
    if value["id"] != probe_id or value["baseline"] is None or value["mutant"] is None:
        raise _error("Installed mutation pair is incomplete")
    original = materials["engine"]["closure"]
    baseline = value["baseline"]["closure"]
    mutant = value["mutant"]["closure"]
    b = run / str(index) / "b"
    m = run / str(index) / "m"
    if baseline["root"] != str(b / "i") or mutant["root"] != str(m / "i"):
        raise _error("Installed execution copy has the wrong role")
    if node._canonical(node._content(baseline)) != node._canonical(node._content(original)):
        raise _error("Baseline copy differs from the installed closure")
    relative = "Lib/site-packages/aiflow/" + _TARGETS[probe_id][0]
    source = node._read(b / "i" / relative)
    transformed = _transformed(probe_id, source)
    changed = node._read(m / "i" / relative)
    overlay = {
        "path": relative,
        "before_sha256": node._sha(source),
        "after_sha256": node._sha(transformed),
    }
    if node._canonical(value["overlay"]) != node._canonical(overlay) or changed != transformed:
        raise _error("Installed mutation overlay differs from the fixed operator")
    content = node._content(baseline)
    expected = []
    for row in content:
        copied = dict(row)
        if row["path"] == relative:
            copied.update(size=len(transformed), sha256=node._sha(transformed))
        expected.append(copied)
    if node._canonical(node._content(mutant)) != node._canonical(expected):
        raise _error("Installed mutant contains an undeclared change")
    original_identities = {
        (row["identity"]["device"], row["identity"]["inode"])
        for row in original["entries"]
        if row["kind"] == "file"
    }
    for inventory in (baseline, mutant):
        if any(
            (row["identity"]["device"], row["identity"]["inode"]) in original_identities
            for row in inventory["entries"]
            if row["kind"] == "file"
        ):
            raise _error("Installed execution copy shares original file identities")
    baseline_report = _envelope(b, value["baseline"], probe_id, materials)
    mutant_report = _envelope(m, value["mutant"], probe_id, materials)
    if not _baseline_passes(baseline_report, probe_id, materials):
        return "unverified"
    return _derive_mutant(mutant_report, probe_id, m, materials)


def record_installed_mutations(
    root: Path, task_id: str, *, verifier_actor: str, expected_inputs_sha256: str
) -> InstalledMutationReference:
    """Consume one current local action and retain one immutable closed run."""
    root = Path(root).absolute()
    inputs, _task, context = _authority(root, task_id, verifier_actor)
    if (
        not isinstance(expected_inputs_sha256, str)
        or not _SHA.fullmatch(expected_inputs_sha256)
        or inputs.sha256 != expected_inputs_sha256
    ):
        raise _error("Installed mutation preparation changed before recording")
    name = "IMUT-" + secrets.token_hex(8)
    run = resolve_task_path(root, task_id, "logs") / name
    action = _consume_action(root, inputs, run.relative_to(root).as_posix())
    run.mkdir()
    before = node._root_snapshot(root, task_id, run)
    node._write_new(run / "context.json", node._canonical(context))
    materials = _input_document(inputs)["materials"]
    pairs: list[dict[str, Any]] = [
        {"id": probe_id, "overlay": None, "baseline": None, "mutant": None}
        for probe_id in PROBE_IDS
    ]
    failure = None
    budget = [node.MAX_ENTRIES, node.MAX_TOTAL_BYTES]
    try:
        for index, probe_id in enumerate(PROBE_IDS):
            _action_originals(root, inputs, action, run)
            (run / str(index)).mkdir()
            pair = pairs[index]
            _run_stage(run / str(index) / "b", pair, "baseline", probe_id, materials, budget)
            baseline = _envelope(run / str(index) / "b", pair["baseline"], probe_id, materials)
            if not _baseline_passes(baseline, probe_id, materials):
                raise _error(
                    "Installed mutation baseline failed", "INSTALLED_MUTATION_BASELINE_INVALID"
                )
            _run_stage(run / str(index) / "m", pair, "mutant", probe_id, materials, budget)
            _pair_originals(run, index, pair, probe_id, materials)
        _current_materials(inputs)
    except (AiflowError, OSError, ValueError, TypeError, KeyError) as error:
        failure = (
            error.code if isinstance(error, AiflowError) else "INSTALLED_MUTATION_EXECUTION_INVALID"
        )
    after = node._root_snapshot(root, task_id, run)
    if node._canonical(after) != node._canonical(before):
        failure = "INSTALLED_MUTATION_ROOT_CHANGED"
    document = {
        "kind": "installed-mutation-run-v1",
        "version": 1,
        "inputs": _input_document(inputs),
        "action": action,
        "before": before,
        "after": after,
        "pairs": pairs,
        "failure": failure,
    }
    raw = node._canonical(document)
    if len(raw) > node.MAX_JSON_BYTES:
        raise _error("Installed mutation run exceeds its retained size budget")
    node._write_new(run / "run.json", raw)
    reference = InstalledMutationReference(
        (run / "run.json").relative_to(root).as_posix(), len(raw), node._sha(raw)
    )
    node._write_new(
        run / "completion.json",
        node._canonical(
            {
                "kind": "installed-mutation-completion-v1",
                "version": 1,
                "inputs_sha256": inputs.sha256,
                "reference": asdict(reference),
                "failure": failure,
            }
        ),
    )
    return reference


def _reference_path(root: Path, reference: InstalledMutationReference) -> Path:
    if (
        type(reference) is not InstalledMutationReference
        or type(reference.size) is not int
        or not 0 < reference.size <= node.MAX_JSON_BYTES
        or not isinstance(reference.sha256, str)
        or not _SHA.fullmatch(reference.sha256)
        or not isinstance(reference.ref, str)
        or not _RUN_REF.fullmatch(reference.ref)
    ):
        raise _error("Installed mutation reference is invalid")
    return root / _path(reference.ref)


def _run_original(root: Path, reference: InstalledMutationReference) -> dict[str, Any]:
    path = _reference_path(root, reference)
    raw = node._read(path, limit=node.MAX_JSON_BYTES)
    if len(raw) != reference.size or node._sha(raw) != reference.sha256:
        raise _error("Installed mutation run digest differs")
    document = _closed(
        node._json_bytes(raw),
        {"kind", "version", "inputs", "action", "before", "after", "pairs", "failure"},
    )
    if (
        raw != node._canonical(document)
        or document["kind"] != "installed-mutation-run-v1"
        or type(document["version"]) is not int
        or document["version"] != 1
    ):
        raise _error("Installed mutation run has an invalid protocol")
    expected = {
        "kind": "installed-mutation-completion-v1",
        "version": 1,
        "inputs_sha256": node._sha(node._canonical(document["inputs"])),
        "reference": asdict(reference),
        "failure": document["failure"],
    }
    if node._canonical(node._json(path.parent / "completion.json")) != node._canonical(expected):
        raise _error("Installed mutation completion is missing or differs")
    return document


def _validate_node_pre_archive(
    root: Path,
    reference: InstalledMutationReference,
    inputs: InstalledMutationInputs,
    run: Path,
) -> None:
    from aiflow.evidence import validate_node_evidence, validate_v2_snapshot

    archive = run / "evidence.json"
    raw = node._read(archive, limit=node.MAX_JSON_BYTES)
    evidence = node._json_bytes(raw)
    validate_node_evidence(evidence)
    validate_v2_snapshot(evidence)
    if (
        raw != node._canonical(evidence)
        or evidence["schema_version"] != "3.2"
        or evidence["verification_level"] != "V2"
        or evidence["mode"] != "local"
        or evidence["phase"] != "pre_implementation_review"
    ):
        raise _error("Installed Node pre archive has the wrong role")
    for key in (
        "task_id",
        "repository_id",
        "branch",
        "base_commit",
        "subject_commit",
        "spec_sha256",
        "policy_sha256",
        "classification_input_sha256",
        "verifier_actor",
        "verifier_context_sha256",
    ):
        if evidence[key] != getattr(inputs, key):
            raise _error("Installed Node pre archive has a foreign task binding")
    if tuple(evidence["decision_unit_ids"]) != inputs.decision_unit_ids:
        raise _error("Installed Node pre archive has foreign decision units")
    installed = evidence["installed_mutation"]
    if (
        node._canonical(installed["reference"]) != node._canonical(asdict(reference))
        or installed["inputs_sha256"] != inputs.sha256
        or installed["results"] != [[probe, "killed"] for probe in PROBE_IDS]
    ):
        raise _error("Installed Node pre archive has a foreign mutation original")
    compact = evidence["node_binding"]
    run_ref = compact["run"]
    original_path = run / "node/run.json"
    original = node._read(original_path, limit=node.MAX_JSON_BYTES)
    if (
        compact["subject_tree"] != inputs.subject_tree
        or run_ref["ref"] != f"logs/{run.name}/node/run.json"
        or run_ref["size"] != len(original)
        or run_ref["sha256"] != node._sha(original)
    ):
        raise _error("Installed Node pre archive has a foreign Node run")
    node_run = node._json_bytes(original)
    if (
        not isinstance(node_run, dict)
        or node_run.get("kind") != "aiflow-node-run-3.2"
        or node._canonical(node_run.get("installed_mutation"))
        != node._canonical(
            {
                "reference": asdict(reference),
                "inputs_sha256": inputs.sha256,
                "results": [[probe, "killed"] for probe in PROBE_IDS],
            }
        )
    ):
        raise _error("Installed Node run does not bind this exact mutation original")
    current = node._json(resolve_task_path(root, inputs.task_id) / "evidence.json")
    validate_node_evidence(current)
    validate_v2_snapshot(current)
    if (
        current.get("schema_version") != "3.2"
        or current.get("verification_level") != "V2"
        or current.get("mode") != "local"
        or current.get("verification_snapshot_sha256") != evidence["verification_snapshot_sha256"]
    ):
        raise _error("Installed Node pre archive differs from the current stable snapshot")


def _validate_run_children(root: Path, reference: InstalledMutationReference) -> None:
    """Validate the one owned run's roles; Node replay owns its Node subtree."""
    root = Path(root).absolute()
    run = _reference_path(root, reference).parent
    document = _run_original(root, reference)
    value = dict(_closed(document["inputs"], set(InstalledMutationInputs.__dataclass_fields__)))
    units = value["decision_unit_ids"]
    if not isinstance(units, list):
        raise _error("Installed original decision units are invalid")
    value["decision_unit_ids"] = tuple(units)
    value["materials"] = node._canonical(value["materials"])
    inputs = InstalledMutationInputs(**value)
    _input_document(inputs)
    if inputs.task_id != reference.ref.split("/")[2]:
        raise _error("Installed original belongs to a different task")
    children = {child.name for child in run.iterdir()}
    expected = {"context.json", "run.json", "completion.json", *(str(i) for i in range(5))}
    if children.intersection({"node", "evidence.json"}) and _node_v2_policy(root):
        classification = read_task_json(
            root, inputs.task_id, "classification.json", contract_name="classification"
        )
        if (
            not isinstance(classification, Mapping)
            or classification.get("effective_verification_level") != "V2"
        ):
            raise _error("Only Node V2 may own additional installed run roles")
        if "node" in children:
            node._safe_info(run / "node", directory=True)
            expected.add("node")
        if "evidence.json" in children:
            if "node" not in children:
                raise _error("Installed Node archive has no owned Node role")
            _validate_node_pre_archive(root, reference, inputs, run)
            expected.add("evidence.json")
    if children != expected:
        raise _error("Installed run contains missing or undeclared outputs")
    for name in ("context.json", "run.json", "completion.json"):
        node._safe_info(run / name)
    for index in range(5):
        pair = run / str(index)
        node._safe_info(pair, directory=True)
        if {child.name for child in pair.iterdir()} != {"b", "m"}:
            raise _error("Installed pair contains missing or undeclared phases")
        for phase in ("b", "m"):
            node._safe_info(pair / phase, directory=True)


def _absolute(value: object) -> Path:
    if not isinstance(value, str):
        raise _error("Installed root path is invalid")
    path = Path(value)
    if not path.is_absolute() or str(path) != value or ".." in path.parts:
        raise _error("Installed root path is not canonical and absolute")
    return path


def _snapshot_identity(value: object, *, metadata: bool = False) -> dict[str, Any]:
    keys = {"device", "inode", "nlink", "size", "mtime_ns", "ctime_ns", "mode", "attributes"}
    if metadata:
        keys.add("change_time_ns")
    identity = _closed(value, keys)
    if (
        any(type(item) is not int for item in identity.values())
        or any(identity[key] < 0 for key in ("device", "inode", "size", "attributes"))
        or identity["nlink"] < 1
        or not (stat.S_ISREG(identity["mode"]) or stat.S_ISDIR(identity["mode"]))
    ):
        raise _error("Installed root identity is invalid")
    return identity


def _snapshot(
    value: object, root: Path, inputs: InstalledMutationInputs, *, current: bool = False
) -> dict[str, Any]:
    snapshot = _closed(
        value,
        {
            "identity",
            "git",
            "files",
            "task",
            "events",
            "governance",
            "metadata",
            "git_audit",
        },
    )
    _snapshot_identity(snapshot["identity"])
    git = _closed(snapshot["git"], {"head", "tree", "index_sha256", "git_directory"})
    if (
        any(
            not isinstance(git[key], str) or not re.fullmatch(r"[0-9a-f]{40}", git[key])
            for key in ("head", "tree")
        )
        or not isinstance(git["index_sha256"], str)
        or not _SHA.fullmatch(git["index_sha256"])
    ):
        raise _error("Historical installed Git identity is invalid")
    git_dir = _absolute(git["git_directory"])
    audit = _closed(snapshot["git_audit"], {"git", "common", "ref", "logs"})
    common = _absolute(audit["common"])
    if _absolute(audit["git"]) != git_dir or audit["ref"] != "refs/heads/" + inputs.branch:
        raise _error("Historical installed Git roles differ")
    _path(audit["ref"])
    logs = _closed(audit["logs"], {str(git_dir / "logs/HEAD"), str(common / "logs" / audit["ref"])})
    for row in logs.values():
        row = _closed(row, {"size", "sha256"})
        if (
            type(row["size"]) is not int
            or not 0 <= row["size"] <= node.MAX_JSON_BYTES
            or not isinstance(row["sha256"], str)
            or not _SHA.fullmatch(row["sha256"])
        ):
            raise _error("Historical installed reflog prefix is invalid")
    files = snapshot["files"]
    if not isinstance(files, list) or len(files) > node.MAX_ENTRIES:
        raise _error("Historical protected inventory is invalid")
    for row in files:
        row = _closed(row, {"path", "size", "sha256", "identity"})
        _path(row["path"])
        _snapshot_identity(row["identity"])
        if (
            type(row["size"]) is not int
            or not 0 <= row["size"] <= node.MAX_FILE_BYTES
            or not isinstance(row["sha256"], str)
            or not _SHA.fullmatch(row["sha256"])
        ):
            raise _error("Historical protected file is invalid")
    _ordered_paths([row["path"] for row in files])
    metadata = snapshot["metadata"]
    if not isinstance(metadata, list) or not 0 < len(metadata) <= node.MAX_ENTRIES:
        raise _error("Historical complete metadata is invalid")
    paths = []
    for row in metadata:
        row = _closed(row, {"path", "identity"})
        path = _absolute(row["path"])
        if not any(path.is_relative_to(parent) for parent in (root, git_dir, common)):
            raise _error("Historical metadata is outside its declared roots")
        _snapshot_identity(row["identity"], metadata=True)
        paths.append(row["path"])
    if (
        paths != sorted(set(paths), key=lambda path: path.encode("utf8"))
        or len({path.casefold() for path in paths}) != len(paths)
        or str(root) not in paths
    ):
        raise _error("Historical metadata membership is invalid")
    governance = _closed(snapshot["governance"], {"paths", "immutable", "approvals"})
    registered = _ordered_paths(governance["paths"])
    prefix = f".ai/tasks/{inputs.task_id}/"
    if any(not path.startswith(prefix) for path in registered) or not isinstance(
        governance["immutable"], dict
    ):
        raise _error("Historical governance roles are invalid")
    for path, digest in governance["immutable"].items():
        if path not in registered or not isinstance(digest, str) or not _SHA.fullmatch(digest):
            raise _error("Historical immutable review binding is invalid")
    if not isinstance(governance["approvals"], list):
        raise _error("Historical approval prefix is invalid")
    for approval in governance["approvals"]:
        require_valid_contract("approval", approval)
    if not isinstance(snapshot["task"], dict) or not isinstance(snapshot["events"], list):
        raise _error("Historical task history is invalid")
    replay_events(snapshot["events"], task_id=inputs.task_id)
    approvals: list[Mapping[str, object]] = []
    identities: set[str] = set()
    for event in snapshot["events"]:
        if event["event_type"] not in {"spec_approved", "code_approved", "approval_recorded"}:
            continue
        payload = event["payload"]
        # Consumption records no approval addition. Approval retries may carry
        # an already-present candidate with a newer approved_at; keep the first
        # original, matching the existing approval ledger's logical identity.
        if "approvals" not in payload and event["event_type"] == "approval_recorded":
            continue
        additions = payload.get("approvals")
        if not isinstance(additions, list):
            raise _error("Historical approval event has no valid inventory")
        for approval in additions:
            require_valid_contract("approval", approval)
            identity = _logical_identity(approval)
            if identity not in identities:
                identities.add(identity)
                approvals.append(approval)
    if node._canonical(approvals) != node._canonical(governance["approvals"]):
        marker = resolve_task_path(root, inputs.task_id) / "approval_pending.json"
        if not current or not marker.exists() or not _node_v2_policy(root):
            raise _error("Historical approval inventory differs from its event history")
        _require_pending_approval(root, inputs.task_id, executing=False, node_v2=True)
        record = read_task_record_strict(root, inputs.task_id)
        live = node._governance_snapshot(root, inputs.task_id, record.events)
        if node._canonical(snapshot["events"]) != node._canonical(record.events) or node._canonical(
            governance
        ) != node._canonical(live):
            raise _error("Current pending approval inventory is not the exact validated live state")
    return snapshot


def _root_transition(
    root: Path,
    inputs: InstalledMutationInputs,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    allowed_git: tuple[str, ...],
    run: Path,
    action: Mapping[str, Any],
) -> None:
    consumed = before["events"][-1]
    identity = action["receipt"]["identity"]
    expected_consumption = {
        "approval_type": "action",
        "action_status": "consumed",
        "action_sha256": action["digest"],
        "receipt_ref": Path(action["receipt"]["path"]).relative_to(root).as_posix(),
        "receipt_device": identity["device"],
        "receipt_inode": identity["inode"],
        "kind": ACTION_TYPE,
        "inputs_sha256": inputs.sha256,
    }
    if (
        consumed["event_type"] != "approval_recorded"
        or consumed["actor"] != "aiflow-installed-mutations"
        or consumed["from_state"] != "IMPLEMENTING"
        or consumed["to_state"] != "IMPLEMENTING"
        or node._canonical(consumed["payload"]) != node._canonical(expected_consumption)
    ):
        raise _error("Historical snapshot does not end at this action consumption")
    if before["git"]["head"] == after["git"]["head"] and (
        before["git"]["tree"] != after["git"]["tree"]
        or node._canonical(before["git_audit"]) != node._canonical(after["git_audit"])
    ):
        raise _error("Installed unchanged HEAD has inconsistent historical Git facts")
    for key in ("identity", "files", "task"):
        if node._canonical(before[key]) != node._canonical(after[key]):
            raise _error("Protected installed root input changed")
    old, new = before["governance"], after["governance"]
    for path, digest in old["immutable"].items():
        if new["immutable"].get(path) != digest:
            raise _error("An existing installed review original changed")
    if node._canonical(new["approvals"][: len(old["approvals"])]) != node._canonical(
        old["approvals"]
    ):
        raise _error("Installed approval history was rewritten")
    events, prefix = after["events"], before["events"]
    if node._canonical(events[: len(prefix)]) != node._canonical(prefix):
        raise _error("Installed event history was rewritten")
    for event in events[len(prefix) :]:
        if event["event_type"] == "verification_started":
            if (
                event["from_state"] != "IMPLEMENTING"
                or event["to_state"] != "VERIFYING"
                or event["actor"] != inputs.verifier_actor
                or event["payload"] != {}
            ):
                raise _error("Installed verification start is not the same verifier transition")
        elif event["event_type"] not in {
            "verification_passed",
            "evidence_generated",
            "final_review_required",
            "merge_approved_automatically",
            "code_approved",
            "merge_recorded",
            "review_recorded",
            "approval_recorded",
            "review_finding_resolved",
        }:
            raise _error("Unexpected installed task governance advancement")
    # Re-derive historical review roles from its exact replayable prefix. The
    # helper reads current approvals; their historical prefix is checked above.
    marker = resolve_task_path(root, inputs.task_id) / "approval_pending.json"
    if marker.exists() and _node_v2_policy(root):
        historical = node._governance_snapshot(root, inputs.task_id, prefix, include_pending=False)
    else:
        historical = node._governance_snapshot(root, inputs.task_id, prefix)
    if any(
        node._canonical(old[key]) != node._canonical(historical[key])
        for key in ("paths", "immutable")
    ):
        raise _error("Historical installed review inventory is incomplete")
    allowed = {root / path for path in new["paths"]} | {Path(path) for path in allowed_git} | {run}
    node._check_root_metadata(before["metadata"], after["metadata"], allowed)


def _complete_current_root(
    root: Path, inputs: InstalledMutationInputs, snapshot: Mapping[str, Any], run: Path
) -> None:
    """Reread complete physical membership using already authority-bound roots."""
    roots = [root]
    for value in (snapshot["git_audit"]["git"], snapshot["git_audit"]["common"]):
        directory = Path(value)
        if not any(directory.is_relative_to(parent) for parent in roots):
            roots = [parent for parent in roots if not parent.is_relative_to(directory)]
            roots.append(directory)
    pending = list(roots)
    rows: list[dict[str, Any]] = []
    while pending:
        path = pending.pop()
        if path == run:
            continue
        if len(rows) >= node.MAX_ENTRIES:
            raise _error("Current installed root metadata exceeds its entry budget")
        identity = node._metadata_identity(path)
        rows.append({"path": str(path), "identity": identity})
        if stat.S_ISDIR(identity["mode"]):
            with os.scandir(path) as children:
                pending.extend(Path(child.path) for child in children)
            if node._metadata_identity(path) != identity:
                raise _error("Current installed directory changed during enumeration")
    rows.sort(key=lambda row: row["path"].encode("utf8"))
    if (
        node._canonical(rows) != node._canonical(snapshot["metadata"])
        or node._identity(node._safe_info(root, directory=True)) != snapshot["identity"]
    ):
        raise _error("Current installed root metadata changed after authority collection")
    for row in snapshot["files"]:
        data = node._read(root / row["path"])
        if (
            len(data) != row["size"]
            or node._sha(data) != row["sha256"]
            or node._identity(node._safe_info(root / row["path"])) != row["identity"]
        ):
            raise _error("Current protected installed original changed")
    record = read_task_record_strict(root, inputs.task_id)
    task = {
        key: value
        for key, value in record.task.items()
        if key not in {"current_state", "updated_at"}
    }
    governance = node._governance_snapshot(root, inputs.task_id, record.events)
    if any(
        node._canonical(actual) != node._canonical(snapshot[key])
        for key, actual in (
            ("task", task),
            ("events", list(record.events)),
            ("governance", governance),
        )
    ):
        raise _error("Current installed task facts changed after authority collection")


def collect_installed_mutation_current(
    root: Path, reference: InstalledMutationReference, *, verifier_actor: str
) -> InstalledMutationCurrent:
    """Collect exact-reference live authority without consuming, recovery or writes."""
    root = Path(root).absolute()
    document = _run_original(root, reference)
    path = _reference_path(root, reference)
    task_id = path.parents[2].name
    inputs, _task, _context = _authority(root, task_id, verifier_actor, executing=False)
    if node._canonical(document["inputs"]) != node._canonical(_input_document(inputs)):
        raise _error("Installed mutation current binding differs")
    before = _snapshot(document["before"], root, inputs)
    _snapshot(document["after"], root, inputs)
    if node._canonical(before) != node._canonical(document["after"]):
        raise _error("Installed mutation changed the original root")
    current = _snapshot(node._root_snapshot(root, task_id, path.parent), root, inputs, current=True)
    if (
        any(
            before["git_audit"][key] != current["git_audit"][key]
            for key in ("git", "common", "ref")
        )
        or before["git"]["git_directory"] != current["git"]["git_directory"]
    ):
        raise _error("Installed Git administration moved")
    old_head, head = before["git"]["head"], current["git"]["head"]
    if (
        node._git(root, "rev-parse", old_head + "^{tree}").decode("utf8").strip()
        != before["git"]["tree"]
    ):
        raise _error("Historical installed HEAD tree differs from its commit")
    if old_head != head:
        node._git(root, "merge-base", "--is-ancestor", old_head, head)
    for args in (
        ("diff", "--name-only", "-z", old_head, head, "--"),
        ("diff", "--name-only", "-z", "--cached", head, "--"),
    ):
        changed = node._git(root, *args).decode("utf8").split("\0")
        if any(path and path not in current["governance"]["paths"] for path in changed):
            raise _error("Installed Git advancement changed a non-governance path")
    allowed = tuple(sorted(str(path) for path in node._git_audit_delta(root, before, current)))
    _action_originals(root, inputs, document["action"], path.parent)
    _root_transition(root, inputs, before, current, allowed, path.parent, document["action"])
    return InstalledMutationCurrent(inputs, reference, node._canonical(current), allowed)


def replay_installed_mutations(
    root: Path, reference: InstalledMutationReference, *, current: InstalledMutationCurrent
) -> InstalledMutationFacts:
    """Read originals only; the collector establishes exact-reference live authority."""
    results: tuple[tuple[str, str], ...] = ()
    try:
        root = Path(root).absolute()
        path = _reference_path(root, reference)
        if type(current) is not InstalledMutationCurrent or current.reference != reference:
            raise _error("Current installed authority belongs to another reference")
        inputs = current.inputs
        _input_document(inputs)
        if (
            reference.ref.split("/")[2] != inputs.task_id
            or type(current.root_snapshot) is not bytes
            or len(current.root_snapshot) > node.MAX_JSON_BYTES
        ):
            raise _error("Current installed authority has an invalid task or snapshot")
        actual = _snapshot(node._json_bytes(current.root_snapshot), root, inputs, current=True)
        if (
            node._canonical(actual) != current.root_snapshot
            or type(current.allowed_git_paths) is not tuple
            or current.allowed_git_paths != tuple(sorted(set(current.allowed_git_paths)))
        ):
            raise _error("Current installed authority is not canonical")
        git_roots = (
            _absolute(actual["git_audit"]["git"]),
            _absolute(actual["git_audit"]["common"]),
        )
        for value in current.allowed_git_paths:
            allowed = _absolute(value)
            if not any(
                allowed != directory and allowed.is_relative_to(directory)
                for directory in git_roots
            ):
                raise _error("Current installed Git allowance is outside its exact roles")
            if allowed.exists():
                node._safe_info(allowed)
        document = _run_original(root, reference)
        if node._canonical(document["inputs"]) != node._canonical(_input_document(inputs)):
            raise _error("Installed mutation current binding differs")
        before = _snapshot(document["before"], root, inputs)
        _snapshot(document["after"], root, inputs)
        if node._canonical(before) != node._canonical(document["after"]):
            raise _error("Installed mutation changed the original task tree")
        _pure_task(root, inputs)
        _require_pending_approval(
            root,
            inputs.task_id,
            executing=False,
            node_v2=_node_v2_policy(root)
            if (resolve_task_path(root, inputs.task_id) / "approval_pending.json").exists()
            else False,
        )
        materials = _current_materials(inputs)
        context = node._json(path.parent / "context.json")
        validate_verifier_context(context)
        if context_sha256(context) != inputs.verifier_context_sha256:
            raise _error("Installed mutation verifier context differs")
        _action_originals(root, inputs, document["action"], path.parent)
        _complete_current_root(root, inputs, actual, path.parent)
        _root_transition(
            root, inputs, before, actual, current.allowed_git_paths, path.parent, document["action"]
        )
        _validate_run_children(root, reference)
        pairs = document["pairs"]
        if not isinstance(pairs, list) or len(pairs) != len(PROBE_IDS):
            raise _error("Installed mutation run has an incomplete probe inventory")
        results = tuple(
            (probe_id, _pair_originals(path.parent, index, pair, probe_id, materials))
            for index, (probe_id, pair) in enumerate(zip(PROBE_IDS, pairs, strict=True))
        )
        failure = document["failure"]
        if failure is not None and (
            not isinstance(failure, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", failure)
        ):
            raise _error("Installed mutation failure marker is invalid")
        all_killed = failure is None and all(outcome == "killed" for _probe_id, outcome in results)
        return InstalledMutationFacts(
            True, all_killed, results, () if all_killed else ("INSTALLED_MUTATION_NOT_KILLED",)
        )
    except (AiflowError, OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        code = error.code if isinstance(error, AiflowError) else "INSTALLED_MUTATION_INVALID"
        return InstalledMutationFacts(False, False, results, (code,))


def _ci_inventory(value: object) -> dict[str, Any]:
    """Validate producing metadata as data, never by opening its absolute root."""
    inventory = _closed(value, {"root", "identity", "entries", "total_bytes"})
    _absolute(inventory["root"])
    identity = _snapshot_identity(inventory["identity"])
    if (
        not stat.S_ISDIR(identity["mode"])
        or identity["attributes"] & 0x400
        or identity["inode"] <= 0
    ):
        raise _error("CI installed inventory root is unsafe")
    entries = inventory["entries"]
    if not isinstance(entries, list) or len(entries) > node.MAX_ENTRIES:
        raise _error("CI installed inventory exceeds its entry limit")
    paths: list[str] = []
    kinds: dict[str, str] = {}
    total = 0
    for row in entries:
        if not isinstance(row, dict) or row.get("kind") not in {"directory", "file"}:
            raise _error("CI installed inventory has an invalid member")
        file = row["kind"] == "file"
        _closed(row, {"path", "kind", "identity"} | ({"size", "sha256"} if file else set()))
        relative = _path(row["path"])
        current = _snapshot_identity(row["identity"])
        if (
            current["attributes"] & 0x400
            or current["inode"] <= 0
            or not (stat.S_ISREG(current["mode"]) if file else stat.S_ISDIR(current["mode"]))
        ):
            raise _error("CI installed inventory member is unsafe")
        if file:
            if (
                type(row["size"]) is not int
                or not 0 <= row["size"] <= node.MAX_FILE_BYTES
                or row["size"] != current["size"]
                or current["nlink"] != 1
                or not isinstance(row["sha256"], str)
                or _SHA.fullmatch(row["sha256"]) is None
            ):
                raise _error("CI installed file binding is invalid")
            total += row["size"]
        paths.append(relative)
        kinds[relative] = row["kind"]
    if (
        paths != sorted(set(paths), key=lambda name: name.encode("utf8"))
        or len({name.casefold() for name in paths}) != len(paths)
        or type(inventory["total_bytes"]) is not int
        or inventory["total_bytes"] != total
        or total > node.MAX_TOTAL_BYTES
    ):
        raise _error("CI installed inventory is aliased, unordered or over budget")
    for name in paths:
        parent = Path(name).parent
        while str(parent) != ".":
            if kinds.get(parent.as_posix()) != "directory":
                raise _error("CI installed inventory omits a directory role")
            parent = parent.parent
    return inventory


def _ci_subinventory(inventory: Mapping[str, Any], name: str) -> dict[str, Any]:
    root = next((row for row in inventory["entries"] if row["path"] == name), None)
    if root is None or root["kind"] != "directory":
        raise _error("CI installed phase omits a fixed directory role")
    entries = [
        {**row, "path": row["path"][len(name) + 1 :]}
        for row in inventory["entries"]
        if row["path"].startswith(name + "/")
    ]
    return {
        "root": str(Path(inventory["root"]) / name),
        "identity": root["identity"],
        "entries": entries,
        "total_bytes": sum(row["size"] for row in entries if row["kind"] == "file"),
    }


def _ci_pair_bindings(admission: Mapping[str, Any], materials: Mapping[str, Any]) -> dict[str, str]:
    # This is trusted installed kernel code, never an imported package member.
    from aiflow.node_ci import validate_node_ci_document

    validate_node_ci_document(admission, kind="aiflow-node-ci-admission")
    claim = _closed(
        admission,
        {
            "kind",
            "schema_version",
            "descriptor_sha256",
            "platform",
            "input_materials_sha256",
            "engine_content_sha256",
            "claimed_at",
        },
    )
    if claim["kind"] != "aiflow-node-ci-admission" or claim["schema_version"] != "1.0":
        raise _error("Installed CI admission is unsupported")
    for key in ("descriptor_sha256", "input_materials_sha256", "engine_content_sha256"):
        if not isinstance(claim[key], str) or _SHA.fullmatch(claim[key]) is None:
            raise _error("Installed CI admission digest is invalid")
    if not isinstance(claim["platform"], dict) or not claim["platform"]:
        raise _error("Installed CI admission omits its producing platform")
    if not isinstance(claim["claimed_at"], str):
        raise _error("Installed CI admission time is invalid")
    claimed = datetime.fromisoformat(claim["claimed_at"].replace("Z", "+00:00"))
    if claimed.utcoffset() is None:
        raise _error("Installed CI admission time has no timezone")
    _closed(
        materials, {"kind", "version", "engine", "interpreter", "host_tools", "probes", "operators"}
    )
    if (
        materials["kind"] != ACTION_TYPE
        or type(materials["version"]) is not int
        or materials["version"] != 1
        or len(node._canonical(materials)) > node.MAX_JSON_BYTES
    ):
        raise _error("Installed CI materials have an invalid format")
    engine = _closed(materials["engine"], {"installed", "closure"})
    original = _ci_inventory(engine["closure"])
    interpreter = _closed(
        materials["interpreter"],
        {
            "executable",
            "base_executable",
            "runtime",
            "prefix",
            "site",
            "base_prefix",
            "implementation",
            "version",
            "cache_tag",
        },
    )
    prefix = _absolute(interpreter["prefix"])
    base = _absolute(interpreter["base_prefix"])
    if (
        original["root"] != str(prefix)
        or prefix == base
        or interpreter["site"] != str(prefix / "Lib/site-packages")
        or interpreter["implementation"] != "cpython"
        or not isinstance(interpreter["version"], list)
        or len(interpreter["version"]) != 3
        or any(type(number) is not int or number < 0 for number in interpreter["version"])
        or interpreter["version"][:2] != [3, 11]
        or interpreter["cache_tag"] != "cpython-311"
    ):
        raise _error("Installed CI interpreter coordinates are invalid")
    for key, path in (
        ("executable", prefix / "Scripts/python.exe"),
        ("base_executable", base / "python.exe"),
        ("runtime", base / "python311.dll"),
    ):
        item = _closed(interpreter[key], {"path", "size", "sha256", "identity"})
        if item["path"] != str(path):
            raise _error("Installed CI interpreter has the wrong fixed role")
    operators_document = _closed(
        materials["operators"], {"declarations", "source", "native_source", "bootstrap_sha256"}
    )
    if node._canonical(operators_document["declarations"]) != node._canonical(
        _TARGETS
    ) or operators_document["bootstrap_sha256"] != node._sha(_BOOTSTRAP.encode()):
        raise _error("Installed CI fixed operator contract differs")
    return {
        "admission_sha256": node._sha(node._canonical(admission)),
        "engine_content_sha256": claim["engine_content_sha256"],
    }


def _ci_attempt_coordinates(admission: Mapping[str, Any], workspace: Path) -> Path:
    """Evaluate the fixed run recipe without opening producing paths."""
    platform = admission["platform"]
    return (
        _absolute(str(workspace))
        / ".tmp/node-ci"
        / (f"{platform['run_id']}-{platform['run_attempt']}")
    )


def _ci_live_attempt(attempt: Path, admission: Mapping[str, Any]) -> None:
    workspace = _absolute(os.environ.get("GITHUB_WORKSPACE"))
    if attempt != _ci_attempt_coordinates(admission, workspace):
        raise _error(
            "Installed CI attempt differs from its actual workflow run",
            "INSTALLED_MUTATION_ATTEMPT_INVALID",
        )


def _ci_system_root(materials: Mapping[str, Any]) -> Path:
    """Derive the producing Windows root from fixed host roles without host I/O."""
    tools = materials["host_tools"]
    cmd = _closed(tools["cmd"], {"path", "size", "sha256", "identity"})
    system = _absolute(cmd["path"]).parent.parent
    for role, relative in node._OS_TOOL_PATHS.items():
        item = _closed(tools[role], {"path", "size", "sha256", "identity"})
        expected = system / relative
        if item["path"] != str(expected):
            raise _error("Installed CI host tools have inconsistent producing coordinates")
        config = tools[role + "_config"]
        if (
            config is not None
            and _closed(config, {"path", "size", "sha256", "identity"})["path"]
            != str(expected) + ".config"
        ):
            raise _error("Installed CI host tool configuration has the wrong role")
    return system


def _ci_probe_originals(phase: Path, materials: Mapping[str, Any]) -> None:
    source = node._read(phase / "i/Lib/site-packages/aiflow/installed_probe.py")
    validate_probe_contract(materials["probes"], source)
    files = {row["path"]: row for row in materials["engine"]["closure"]["entries"]}
    prefix = Path(materials["engine"]["closure"]["root"])
    for declared, relative in (
        (materials["probes"]["source"], "Lib/site-packages/aiflow/installed_probe.py"),
        (materials["operators"]["source"], "Lib/site-packages/aiflow/installed_mutations.py"),
        (materials["operators"]["native_source"], "Lib/site-packages/aiflow/mutation_runner.py"),
    ):
        item = _closed(declared, {"path", "size", "sha256", "identity"})
        if (
            item["path"] != str(prefix / relative)
            or relative not in files
            or node._canonical({key: item[key] for key in ("size", "sha256", "identity")})
            != node._canonical(
                {key: files[relative][key] for key in ("size", "sha256", "identity")}
            )
        ):
            raise _error("Installed CI probe/operator source is outside its bound closure")


def _ci_role_inventory(phase: Path, manifest: object, role: str) -> dict[str, Any]:
    value = _closed(manifest, {"id", "root", "identity", "entries", "total_bytes"})
    if value["id"] != role:
        raise _error("Installed CI phase has the wrong manifest role")
    inventory = _ci_inventory(
        {key: value[key] for key in ("root", "identity", "entries", "total_bytes")}
    )
    members = {row["path"]: row["kind"] for row in inventory["entries"]}
    if {name: kind for name, kind in members.items() if "/" not in name} != {
        "i": "directory",
        "c": "directory",
        "h": "directory",
        "t": "directory",
        "raw": "directory",
        "report.json": "file",
    } or {name for name in members if name.startswith("raw/")} != {
        "raw/receipt.json",
        "raw/stdout.raw",
        "raw/stderr.raw",
        "raw/stdout.log",
        "raw/stderr.log",
    }:
        raise _error("Installed CI phase omits a fixed original or empty directory")
    if node._canonical(node._content(node._inventory(phase))) != node._canonical(
        node._content(inventory)
    ):
        raise _error("Transported installed CI phase content differs from its original")
    return inventory


def _ci_pair_originals(
    baseline_path: Path,
    mutant_path: Path,
    pair: object,
    probe_id: str,
    materials: Mapping[str, Any],
    baseline_inventory: Mapping[str, Any],
    mutant_inventory: Mapping[str, Any],
) -> str:
    value = _closed(pair, {"id", "overlay", "baseline", "mutant"})
    if value["id"] != probe_id or value["baseline"] is None or value["mutant"] is None:
        raise _error("Installed CI mutation pair is incomplete")
    b = _absolute(baseline_inventory["root"])
    m = _absolute(mutant_inventory["root"])
    baseline = value["baseline"]["closure"]
    mutant = value["mutant"]["closure"]
    if baseline["root"] != str(b / "i") or mutant["root"] != str(m / "i"):
        raise _error("Installed CI execution copy has the wrong producing role")
    original = materials["engine"]["closure"]
    if node._canonical(node._content(baseline)) != node._canonical(node._content(original)):
        raise _error("Installed CI baseline differs from the complete installed closure")
    relative = "Lib/site-packages/aiflow/" + _TARGETS[probe_id][0]
    source = node._read(baseline_path / "i" / relative)
    transformed = _transformed_source(probe_id, source)
    changed = node._read(mutant_path / "i" / relative)
    expected_overlay = {
        "path": relative,
        "before_sha256": node._sha(source),
        "after_sha256": node._sha(transformed),
    }
    if (
        node._canonical(value["overlay"]) != node._canonical(expected_overlay)
        or changed != transformed
    ):
        raise _error("Installed CI overlay differs from the fixed actual mutation")
    expected = []
    for row in node._content(baseline):
        expected.append(
            {
                **row,
                **(
                    {"size": len(transformed), "sha256": node._sha(transformed)}
                    if row["path"] == relative
                    else {}
                ),
            }
        )
    if node._canonical(node._content(mutant)) != node._canonical(expected):
        raise _error("Installed CI mutant contains an undeclared change")
    _ci_probe_originals(baseline_path, materials)
    reports = []
    for path, stage, coordinates, inventory in (
        (baseline_path, value["baseline"], b, baseline_inventory),
        (mutant_path, value["mutant"], m, mutant_inventory),
    ):
        reports.append(
            _envelope(
                path,
                stage,
                probe_id,
                materials,
                producing_phase=coordinates,
                retained_inventory=inventory,
                environment=_phase_environment(
                    coordinates, materials["interpreter"], _ci_system_root(materials)
                ),
            )
        )
    if not _baseline_passes(reports[0], probe_id, materials):
        return "unverified"
    return _derive_mutant(reports[1], probe_id, m, materials)


def _ci_pairs_facts(
    roots: Mapping[str, Path],
    admission: Mapping[str, Any],
    materials: Mapping[str, Any],
    pairs: Mapping[str, Any],
    role_manifests: Mapping[str, Any],
    *,
    producing_attempt: Path | None = None,
) -> dict[str, Any]:
    results: list[list[str]] = []
    try:
        binding = _ci_pair_bindings(admission, materials)
        value = _closed(pairs, {"admission_sha256", "engine_content_sha256", "pairs", "failure"})
        if any(value[key] != item for key, item in binding.items()):
            raise _error("Installed CI pairs belong to another admission or engine")
        failure = value["failure"]
        if failure is not None and (
            not isinstance(failure, str) or re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", failure) is None
        ):
            raise _error("Installed CI failure marker is invalid")
        if not isinstance(value["pairs"], list) or len(value["pairs"]) != len(PROBE_IDS):
            raise _error("Installed CI proof omits a fixed mutation pair")
        inventories = {}
        original = materials["engine"]["closure"]
        if producing_attempt is None:
            source_role = _closed(
                role_manifests["source"], {"id", "root", "identity", "entries", "total_bytes"}
            )
            source = _absolute(source_role["root"])
            node_role = _closed(
                role_manifests["node"], {"id", "root", "identity", "entries", "total_bytes"}
            )
            node_root = _absolute(node_role["root"])
            producing_attempt = _ci_attempt_coordinates(admission, source.parent)
            if (
                source_role["id"] != "source"
                or source.name != "source"
                or node_role["id"] != "node"
                or node_root != producing_attempt / "node"
            ):
                raise _error(
                    "CI pair source/Node coordinates differ from the admitted attempt",
                    "INSTALLED_MUTATION_ATTEMPT_INVALID",
                )
        source_root = _absolute(original["root"])
        identities = {
            (row["identity"]["device"], row["identity"]["inode"]) for row in original["entries"]
        }
        identities.add((original["identity"]["device"], original["identity"]["inode"]))
        budget = [node.MAX_ENTRIES, node.MAX_TOTAL_BYTES]
        producing_roots: list[Path] = []
        for index in range(len(PROBE_IDS)):
            for suffix in ("b", "m"):
                role = f"pair-{index}-{suffix}"
                inventory = _ci_role_inventory(roots[role], role_manifests[role], role)
                coordinates = _absolute(inventory["root"])
                if (
                    coordinates.name != role
                    or coordinates.parent != producing_attempt
                    or coordinates.is_relative_to(source_root)
                    or source_root.is_relative_to(coordinates)
                    or any(
                        coordinates.is_relative_to(other) or other.is_relative_to(coordinates)
                        for other in producing_roots
                    )
                ):
                    raise _error("Installed CI producing phase roots overlap or have aliases")
                producing_roots.append(coordinates)
                for row in [{"identity": inventory["identity"]}, *inventory["entries"]]:
                    identity = row["identity"]
                    key = (identity["device"], identity["inode"])
                    if key in identities or identity["inode"] <= 0:
                        raise _error("Installed CI copies share producing physical identities")
                    identities.add(key)
                for row in _ci_subinventory(inventory, "i")["entries"]:
                    node._take_budget(budget, row.get("size", 0))
                inventories[role] = inventory
        if len({path.parent for path in producing_roots}) != 1:
            raise _error("Installed CI phases belong to different attempts")
        for index, (probe_id, pair) in enumerate(zip(PROBE_IDS, value["pairs"], strict=True)):
            b, m = f"pair-{index}-b", f"pair-{index}-m"
            results.append(
                [
                    probe_id,
                    _ci_pair_originals(
                        roots[b],
                        roots[m],
                        pair,
                        probe_id,
                        materials,
                        inventories[b],
                        inventories[m],
                    ),
                ]
            )
        passed = failure is None and all(outcome == "killed" for _probe, outcome in results)
        return {
            "passed": passed,
            "results": results,
            "reason_codes": [] if passed else ["INSTALLED_MUTATION_NOT_KILLED"],
        }
    except (
        AiflowError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        SyntaxError,
    ) as error:
        code = error.code if isinstance(error, AiflowError) else "INSTALLED_MUTATION_INVALID"
        return {"passed": False, "results": results, "reason_codes": [code]}


def validate_ci_pair_run(
    *,
    attempt_root: Path,
    admission: Mapping[str, Any],
    materials: Mapping[str, Any],
    pairs: Mapping[str, Any],
) -> dict[str, Any]:
    """Read current producing originals; no task/action recovery or Current result."""
    try:
        attempt = Path(attempt_root).absolute()
        _ci_pair_bindings(admission, materials)
        _ci_live_attempt(attempt, admission)
        if _materials() != node._canonical(materials):
            raise _error("Current CI ordinary inputs differ from the recorded materials")
        roots = {
            f"pair-{index}-{suffix}": attempt / f"pair-{index}-{suffix}"
            for index in range(5)
            for suffix in ("b", "m")
        }
        manifests = {role: {"id": role, **node._inventory(path)} for role, path in roots.items()}
        facts = _ci_pairs_facts(
            roots, admission, materials, pairs, manifests, producing_attempt=attempt
        )
        if _materials() != node._canonical(materials):
            raise _error("Current CI ordinary inputs changed during pair revalidation")
        return facts
    except (AiflowError, OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        return {
            "passed": False,
            "results": [],
            "reason_codes": [
                error.code if isinstance(error, AiflowError) else "INSTALLED_MUTATION_INVALID"
            ],
        }


def record_ci_pairs(
    *, attempt_root: Path, admission: Mapping[str, Any], materials: Mapping[str, Any]
) -> dict[str, Any]:
    """Run ten fresh ordinary copies under the already-created exclusive CI claim."""
    attempt = Path(attempt_root).absolute()
    binding = _ci_pair_bindings(admission, materials)
    _ci_live_attempt(attempt, admission)
    node._ancestors(attempt)
    if _materials() != node._canonical(materials):
        raise _error("CI installed inputs differ from the actual ordinary installation")
    original = materials["engine"]["closure"]
    if attempt.is_relative_to(Path(original["root"])):
        raise _error("CI installed outputs overlap their ordinary input installation")
    for index in range(5):
        for suffix in ("b", "m"):
            if os.path.lexists(attempt / f"pair-{index}-{suffix}"):
                raise _error("CI installed phase was already claimed")
    document: dict[str, Any] = {
        **binding,
        "pairs": [
            {"id": probe_id, "overlay": None, "baseline": None, "mutant": None}
            for probe_id in PROBE_IDS
        ],
        "failure": None,
    }
    budget = [node.MAX_ENTRIES, node.MAX_TOTAL_BYTES]
    try:
        for index, probe_id in enumerate(PROBE_IDS):
            node._unchanged(original)
            pair = document["pairs"][index]
            for suffix, stage in (("b", "baseline"), ("m", "mutant")):
                phase = attempt / f"pair-{index}-{suffix}"
                _run_stage(phase, pair, stage, probe_id, materials, budget)
                if stage == "baseline" and not _baseline_passes(
                    _envelope(phase, pair[stage], probe_id, materials), probe_id, materials
                ):
                    raise _error(
                        "Installed CI baseline failed", "INSTALLED_MUTATION_BASELINE_INVALID"
                    )
        facts = validate_ci_pair_run(
            attempt_root=attempt, admission=admission, materials=materials, pairs=document
        )
        if not facts["passed"]:
            document["failure"] = facts["reason_codes"][0]
    except (
        AiflowError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        SyntaxError,
    ) as error:
        document["failure"] = (
            error.code if isinstance(error, AiflowError) else "INSTALLED_MUTATION_EXECUTION_INVALID"
        )
    return document


def replay_ci_pairs(
    *,
    package_root: Path,
    admission: Mapping[str, Any],
    materials: Mapping[str, Any],
    pairs: Mapping[str, Any],
    role_manifests: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive fresh-pair content facts, opening only retained package role members."""
    package = Path(package_root).absolute()
    roots = {
        f"pair-{index}-{suffix}": package / "originals" / f"pair-{index}-{suffix}"
        for index in range(5)
        for suffix in ("b", "m")
    }
    return _ci_pairs_facts(roots, admission, materials, pairs, role_manifests)
