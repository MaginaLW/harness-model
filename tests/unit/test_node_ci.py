"""Independent transport-shape tests; synthetic documents prove no CI execution."""

from __future__ import annotations

import json
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_PATH = Path(__file__).resolve().parents[2] / ".ai/schemas/node-ci.schema.json"
SHA = "a" * 64
HEAD = "4" * 40
BRANCH = "refs/heads/codex/synthetic-node-ci"
SOURCE_WORKFLOW = ".github/workflows/node-engine-artifacts.yml"
TARGET_WORKFLOW = ".github/workflows/aiflow-node-ci.yml"
COMMON_ROLES = (
    "source",
    "artifact",
    "engine",
    "runtime",
    "dependencies",
    "host",
    "preflight",
    "control",
    "node",
)
CHECK_IDS = (
    "contract",
    "scope",
    "smoke",
    "node_build",
    "node_check",
    "diff_whitespace",
    "ts_coverage",
    "ts_total_lines",
    "ts_diff_lines",
    "acceptance",
    "integration",
    "targeted_mutation",
    "independent_verifier",
)


def synthetic_python_provision(artifact: Path, source_tuple: dict, engine: dict) -> Any:
    """Tiny public wheel/install originals; no pip, Python, SDK, or Job executes."""
    import io
    import zipfile
    from types import SimpleNamespace

    from test_node_ci_platform import _job_receipt

    from aiflow import installed_mutations, node_ci
    from aiflow import node_execution as node

    site = Path(engine["startup"]["python_environment"]["active_site_roots"][0])
    prefix = Path(engine["startup"]["python_environment"]["prefix"])
    names = (
        "attrs",
        "jsonschema",
        "jsonschema-specifications",
        "pyyaml",
        "referencing",
        "rpds-py",
        "typing-extensions",
    )
    wheels, requirements, packages = [], [], []
    for name in names:
        normalized, version = name.replace("-", "_"), "1.0"
        metadata = f"{normalized}-{version}.dist-info"
        members = {
            f"{normalized}/__init__.py": b"# Public synthetic dependency, never imported.\n",
            f"{metadata}/METADATA": (
                f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n".encode()
            ),
            f"{metadata}/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            f"{metadata}/RECORD": b"",
        }
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            for member, raw in members.items():
                archive.writestr(zipfile.ZipInfo(member, (2020, 1, 1, 0, 0, 0)), raw)
        raw = output.getvalue()
        filename = f"{normalized}-{version}-py3-none-any.whl"
        path = artifact / "inputs/wheels" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        files = []
        for member, content in members.items():
            installed = site / member
            installed.parent.mkdir(parents=True, exist_ok=True)
            installed.write_bytes(content)
            files.append(installed_mutations._file(installed))
        engine["distributions"].append({"name": name, "version": version, "files": files})
        requirements.append(f"{name}=={version} --hash=sha256:{node_ci._sha(raw)}")
        packages.append(
            f'[[package]]\nname = "{name}"\nversion = "{version}"\n'
            f'wheels = [{{ url = "https://files.pythonhosted.org/public/{filename}", '
            f'hash = "sha256:{node_ci._sha(raw)}", size = {len(raw)} }}]\n'
        )
        wheels.append(path)
    lock_raw = ("version = 1\n" + "\n".join(packages)).encode()
    (artifact / "inputs/uv.lock").write_bytes(lock_raw)
    (artifact / "inputs/runtime-requirements.txt").write_text(
        "\n".join(requirements) + "\n", encoding="utf8", newline="\n"
    )
    commands = {
        "runtime-install": [
            str(prefix / "Scripts/python.exe"),
            "-I",
            "-B",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-cache-dir",
            "--find-links",
            str(prefix.parent / "artifact/inputs/wheels"),
            "--require-hashes",
            "-r",
            str(prefix.parent / "artifact/inputs/runtime-requirements.txt"),
        ],
        "engine-install": [
            str(prefix / "Scripts/python.exe"),
            "-I",
            "-B",
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-cache-dir",
            "--no-deps",
            str(prefix.parent / "artifact" / source_tuple["engine_artifact"]["wheel"]["member"]),
        ],
    }
    (artifact / "provision").mkdir()
    for name, argv in commands.items():
        stdout, stderr = b"Synthetic installation transcript only.\n", b""
        receipt = {
            "argv": argv,
            "returncode": 0,
            "cleanup": "confirmed",
            "receipt": _job_receipt(),
            "cwd": str(prefix.parent),
            "duration_ms": 1,
            "environment_sha256": node_ci._sha(b"public synthetic install environment"),
            "timeout_seconds": 180,
            **dict.fromkeys(
                ("timed_out", "execution_error", "stdout_overflow", "stderr_overflow"), False
            ),
            "stdout_size": len(stdout),
            "stdout_sha256": node_ci._sha(stdout),
            "stderr_size": len(stderr),
            "stderr_sha256": node_ci._sha(stderr),
        }
        for suffix, raw in (
            ("receipt.json", node_ci._canonical(receipt)),
            ("stdout.raw", stdout),
            ("stderr.raw", stderr),
        ):
            (artifact / "provision" / f"{name}.{suffix}").write_bytes(raw)
    for row in engine["startup"]["site_roots"]:
        row["identity"] = node._identity(node._safe_info(Path(row["path"]), directory=True))
    return SimpleNamespace(lock_raw=lock_raw, wheels=wheels, engine=engine, artifact=artifact)


@pytest.fixture(scope="module")
def node_ci_schema() -> dict[str, Any]:
    # Intentionally independent of the deferred contracts.SCHEMA_FILES registration.
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _contract(schema: dict[str, Any], definition: str | None = None) -> Draft202012Validator:
    selected = (
        schema
        if definition is None
        else {"$defs": schema["$defs"], "$ref": f"#/$defs/{definition}"}
    )
    return Draft202012Validator(selected, format_checker=FormatChecker())


def _ref(path: str) -> dict[str, Any]:
    return {"ref": path, "size": 1, "sha256": SHA}


def _chosen_artifact(origin: str = "direct") -> dict[str, Any]:
    wheel_directory = "direct" if origin == "direct" else "sdist-rebuilt"
    return {
        "origin": origin,
        "source_repository_id": 1319293089,
        "source_full_name": "MaginaLW/harness-model",
        "workflow_id": 11,
        "workflow_path": SOURCE_WORKFLOW,
        "workflow_ref": BRANCH,
        "workflow_sha256": SHA,
        "source_head": HEAD,
        "run_id": 12,
        "run_attempt": 1,
        "job_id": 13,
        "artifact_id": 14,
        "artifact_name": "aiflow-node-engine-12-1",
        "artifact_digest": "sha256:" + SHA,
        "wheel": {
            "member": f"{wheel_directory}/aiflow-0.2.0-py3-none-any.whl",
            "size": 1,
            "sha256": SHA,
        },
        "sdist": {"member": "sdist/aiflow-0.2.0.tar.gz", "size": 1, "sha256": SHA},
        "build_manifest": {"member": "build-manifest.json", "size": 1, "sha256": SHA},
    }


def _platform() -> dict[str, Any]:
    return {
        "provider": "github",
        "repository_id": 42,
        "full_name": "example/synthetic-target",
        "workflow_id": 21,
        "workflow_path": TARGET_WORKFLOW,
        "workflow_ref": BRANCH,
        "workflow_sha256": SHA,
        "event": "pull_request",
        "head_sha": HEAD,
        "run_id": 22,
        "run_attempt": 1,
        "job_id": 23,
        "job_key": "aiflow-node-ci",
        "check_run_id": 24,
        "check_name": "aiflow-node-ci",
        "app_id": 15368,
    }


def _binding(level: str) -> dict[str, Any]:
    return {
        "repository_id": "00000000-0000-4000-8000-000000000042",
        "task_id": "TASK-0001",
        "branch": BRANCH,
        "base_commit": "1" * 40,
        "subject_commit": "2" * 40,
        "subject_tree": "3" * 40,
        "policy_sha256": SHA,
        "spec_sha256": SHA,
        "classification_input_sha256": SHA,
        "decision_unit_ids": ["DU-001"],
        "verification_level": level,
    }


def _review(number: int) -> dict[str, Any]:
    return {
        "record": _ref(f"control/reviews/REV-{number:04}-r0001.json"),
        "context": _ref(f"control/review-contexts/{SHA}.json"),
        "review_id": f"REV-{number:04}",
        "revision": 1,
        "context_sha256": SHA,
    }


def _v2_tuple() -> dict[str, Any]:
    return {
        "snapshot_sha256": SHA,
        "verifier_actor": "synthetic-verifier",
        "verifier_context": _ref(f"control/verifier-contexts/{SHA}.json"),
        "design": _review(1),
        "implementation": _review(2),
    }


def _pairs() -> dict[str, Any]:
    return {
        "admission_sha256": SHA,
        "engine_content_sha256": SHA,
        "pairs": [
            {"id": f"MUT-V2-{number:03}", "overlay": None, "baseline": None, "mutant": None}
            for number in range(1, 6)
        ],
        "failure": "SYNTHETIC_NOT_EXECUTED",
    }


def _coverage() -> dict[str, Any]:
    return {
        "scope_files": 1,
        "total": {"covered": 0, "executable": 1, "threshold": 85},
        "changed": {"covered": 0, "executable": 1, "threshold": 90, "applicability": "applicable"},
        "method": "vitest-4.1.10-istanbul-vite-8.2.1-oxc-es2024-zero-hit-ts-ast-wire-v2",
    }


def _products() -> dict[str, Any]:
    # The fixed shared product inventory, not values extracted from the schema under test.
    return {
        "report": _ref("node/products/report.json"),
        "inventory_sha256": SHA,
        "acceptance": [
            {
                "file": "tests/local/personal-dot-integration.test.ts",
                "full_name": (
                    "personal dot authenticated MCP + unified WeChat host (offline) "
                    "persists duplicate input once, publishes one event, executes original "
                    "text once and replies to the saved conversation once"
                ),
            },
            {
                "file": "tests/local/personal-dot-integration.test.ts",
                "full_name": (
                    "personal dot authenticated MCP + unified WeChat host (offline) "
                    "rejects unauthenticated event calls, foreign targets and direct "
                    "submissions before any dispatch"
                ),
            },
        ],
        "integration": [
            {
                "file": "tests/local/weixin-shared-integration.test.ts",
                "full_name": (
                    "synthetic Weixin, HTTP and shared runtime integration persists a "
                    "polled task contract and returns its terminal result through "
                    "the same shared host"
                ),
            },
            {
                "file": "tests/local/weixin-shared-integration.test.ts",
                "full_name": (
                    "synthetic Weixin, HTTP and shared runtime integration runs the isolated "
                    "shared host with durable duplicate and uncertain reply handling"
                ),
            },
            {
                "file": "tests/local/weixin-shared-integration.test.ts",
                "full_name": (
                    "synthetic Weixin, HTTP and shared runtime integration shares route-bound "
                    "tasks, reads, stop and client lifetime with a second client"
                ),
            },
        ],
    }


def _identity(*, directory: bool = True) -> dict[str, int]:
    return {
        "device": 0,
        "inode": 18446744073709551615,
        "nlink": 1,
        "size": 0 if directory else 1,
        "mtime_ns": 1790000000000000000,
        "ctime_ns": 1790000000000000001,
        "mode": 0o40755 if directory else 0o100644,
        "attributes": 16 if directory else 0,
    }


def _documents(level: str = "V2") -> dict[str, dict[str, Any]]:
    """Hand-authored Norm shapes; failed/unexecuted originals are not kernel proof."""
    roles = list(COMMON_ROLES)
    if level == "V2":
        roles.extend(f"pair-{number}-{phase}" for number in range(5) for phase in ("b", "m"))
    count = {"V0": 6, "V1": 9, "V2": 13}[level]
    return {
        "StaticDeclaration": {
            "kind": "aiflow-node-ci-producer",
            "schema_version": "1.0",
            "repository": {
                "repository_id": _binding(level)["repository_id"],
                "provider_repository_id": 42,
                "full_name": "example/synthetic-target",
            },
            "profile": {"id": "agent-bridge-node", "revision": 2},
            "policy_version": "3.2.0",
            "workflow": {"path": TARGET_WORKFLOW, "ref": BRANCH, "sha256": SHA},
            "producer": {
                "job_key": "aiflow-node-ci",
                "check_name": "aiflow-node-ci",
                "app_id": 15368,
                "event": "pull_request",
            },
            "tier_contracts": {"V0": SHA, "V1": SHA, "V2": SHA},
            "engine_source": {
                "repository_id": 1319293089,
                "full_name": "MaginaLW/harness-model",
                "workflow_path": SOURCE_WORKFLOW,
                "workflow_ref": BRANCH,
                "workflow_sha256": SHA,
                "job_key": "node-engine-artifacts",
                "artifact_name": "aiflow-node-engine-<run_id>-<run_attempt>",
            },
            "engine_artifact": _chosen_artifact(),
            "artifact_policy": {
                "ci_artifact_name": "aiflow-node-ci-<run_id>-<run_attempt>",
                "retention_days": 1,
                "visibility_scope": "private_target_repository",
            },
        },
        "AttestedSource": {
            "kind": "aiflow-node-ci-attested-source",
            "schema_version": "1.0",
            "binding": _binding(level),
            "attestation_head": HEAD,
            "static_declaration": _ref("control/node-ci-producer.json"),
            "engine_artifact": _chosen_artifact(),
            "source_evidence": {"original": _ref("control/evidence.json"), "canonical_sha256": SHA},
            "task": _ref("control/task.yaml"),
            "events": _ref("control/events.jsonl"),
            "classification": _ref("control/classification.json"),
            "spec": _ref("control/spec.md"),
            "policy_members": [
                _ref(f"control/policy/{name}.yaml")
                for name in ("hard-rules", "permissions", "routing", "verification-levels")
            ],
            "approvals": _ref("control/approvals.json"),
            "applicable_spec_approvals": [
                {"record_sha256": SHA, "decision_unit_id": "DU-001", "approval_type": "spec"}
            ],
            "applicable_code_approvals": [
                {
                    "record_sha256": SHA,
                    "decision_unit_id": "DU-001",
                    "approval_type": "code",
                    "evidence_sha256": SHA,
                }
            ],
            "v2": _v2_tuple() if level == "V2" else None,
        },
        "Descriptor": {
            "kind": "aiflow-node-ci-descriptor",
            "schema_version": "1.0",
            "source_tuple_sha256": SHA,
            "static_declaration_sha256": SHA,
            "engine_artifact_sha256": SHA,
            "execution_contract_sha256": SHA,
            "verification_level": level,
            "attestation_head": HEAD,
        },
        "Admission": {
            "kind": "aiflow-node-ci-admission",
            "schema_version": "1.0",
            "descriptor_sha256": SHA,
            "platform": _platform(),
            "input_materials_sha256": SHA,
            "engine_content_sha256": SHA,
            "claimed_at": "2026-01-01T00:00:00Z",
        },
        "Prepared": {
            "kind": "aiflow-node-ci-prepared-3.3",
            "schema_version": "1.0",
            "descriptor": _ref("control/descriptor.json"),
            "source_tuple": _ref("control/source-tuple.json"),
            "admission": _ref("control/admission.json"),
            "platform": _platform(),
            "profile": {"id": "agent-bridge-node", "revision": 2},
            "verification_level": level,
            "execution_contract_sha256": SHA,
            "manifests": {
                name: _ref(f"control/{name}.json")
                for name in (
                    "source",
                    "node",
                    "npm",
                    "dependencies",
                    "engine",
                    "host_tools",
                    "preflight",
                )
            },
        },
        "Run": {
            "kind": "aiflow-node-ci-run-3.3",
            "schema_version": "1.0",
            "prepared": _ref("control/prepared.json"),
            "descriptor_sha256": SHA,
            "platform": _platform(),
            "inputs": {},
            "environment": {},
            "roots": {},
            "executions": [],
            "coverage": None,
            "product_tests": None,
            "installed_mutation": _pairs() if level == "V2" else None,
            "outputs": {},
            "failure": "SYNTHETIC_NOT_EXECUTED",
        },
        "Evidence": {
            "kind": "aiflow-node-ci-evidence",
            "schema_version": "3.3",
            "mode": "ci",
            "binding": _binding(level),
            "generated_at": "2026-01-01T00:00:00Z",
            "conclusion": "failed",
            "source_binding_kind": "attested_committed_tuple",
            "source_tuple": _ref("control/source-tuple.json"),
            "descriptor": _ref("control/descriptor.json"),
            "platform": _platform(),
            "prepared": _ref("control/prepared.json"),
            "run": _ref("node/run.json"),
            "checks": [
                {"check_id": name, "required": True, "status": "unverified", "executions": []}
                for name in CHECK_IDS[:count]
            ],
            "node_binding": {
                "profile": {"id": "agent-bridge-node", "revision": 2},
                "subject_tree": "3" * 40,
                "prepared": _ref("control/prepared.json"),
                "run": _ref("node/run.json"),
                "materials_sha256": SHA,
                "semantic_contract_sha256": SHA,
                "execution_contract_sha256": SHA,
                "environment_sha256": SHA,
                "coverage": None if level == "V0" else _coverage(),
                "product_tests": _products() if level == "V2" else None,
            },
            "installed_mutation": _pairs() if level == "V2" else None,
            "reproduce_command": [
                "python",
                "-m",
                "aiflow",
                "verify",
                "TASK-0001",
                "--ci",
                "--node-ci",
            ],
            "known_limitations": [
                "Original-host LOCAL originals are required; synthetic test has no execution "
                "authority."
            ],
        },
        "Manifest": {
            "id": "control",
            "root": "C:/synthetic/project/.tmp/node-ci/22-1/control",
            "identity": _identity(),
            "entries": [
                {"path": "raw", "kind": "directory", "identity": _identity()},
                {
                    "path": "raw/receipt.json",
                    "kind": "file",
                    "identity": _identity(directory=False),
                    "size": 1,
                    "sha256": SHA,
                },
            ],
            "total_bytes": 1,
        },
        "Index": {
            "kind": "aiflow-node-ci-originals",
            "schema_version": "1.0",
            "evidence": _ref("node/evidence.json"),
            "descriptor": _ref("control/descriptor.json"),
            "source_tuple": _ref("control/source-tuple.json"),
            "roles": [{"id": role, "manifest": _ref(f"manifests/{role}.json")} for role in roles],
        },
        "BuildManifest": {
            "kind": "aiflow-node-engine-build",
            "schema_version": "1.0",
            "repository_id": 1319293089,
            "source_head": HEAD,
            "workflow_path": SOURCE_WORKFLOW,
            "workflow_blob_sha256": SHA,
            "job_key": "node-engine-artifacts",
            "run_id": 12,
            "run_attempt": 1,
            "python_version": [3, 11, 9],
            "setuptools_version": "82.0.1",
            "members": [
                {
                    "path": "direct/aiflow-0.2.0-py3-none-any.whl",
                    "origin": "direct",
                    "size": 1,
                    "sha256": SHA,
                },
                {"path": "sdist/aiflow-0.2.0.tar.gz", "origin": "source", "size": 1, "sha256": SHA},
                {
                    "path": "sdist-rebuilt/aiflow-0.2.0-py3-none-any.whl",
                    "origin": "sdist_rebuilt",
                    "size": 1,
                    "sha256": SHA,
                },
            ],
            "package_payload_sha256": SHA,
            "resource_manifest_sha256": SHA,
        },
    }


def _schema_nodes(value: object) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _schema_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _schema_nodes(child)


def _completed_evidence_shape(level: str) -> dict[str, Any]:
    """Structural success branch only: no files/processes/platform facts authenticate it."""
    document = _documents(level)["Evidence"]
    document["conclusion"] = "passed"
    execution_number = 1
    for check in document["checks"]:
        check["status"] = "passed"
        count = (
            0
            if check["check_id"]
            in {"ts_total_lines", "ts_diff_lines", "targeted_mutation", "independent_verifier"}
            else 3
            if check["check_id"] == "diff_whitespace"
            else 2
            if check["check_id"] == "ts_coverage"
            else 1
        )
        for _ in range(count):
            execution_id = f"EXEC-{execution_number:03}"
            check["executions"].append(
                {
                    "execution_id": execution_id,
                    "argv_template": ["synthetic-never-executed"],
                    "cwd_role": "isolated",
                    "timeout_seconds": 30,
                    "returncode": 0,
                    "timed_out": False,
                    "duration_ms": 0,
                    **{
                        stream: {
                            "bytes": 0,
                            "sha256": SHA,
                            "raw_ref": f"node/raw/{execution_id}/{stream}.raw",
                            "log_ref": f"node/raw/{execution_id}/{stream}.log",
                        }
                        for stream in ("stdout", "stderr")
                    },
                    "stdout_overflow": False,
                    "stderr_overflow": False,
                    "cleanup": "confirmed",
                    "execution_error": False,
                }
            )
            execution_number += 1
    if level == "V2":
        document["installed_mutation"]["failure"] = None
        for pair in document["installed_mutation"]["pairs"]:
            pair["overlay"] = {
                "path": "aiflow/synthetic.py",
                "before_sha256": SHA,
                "after_sha256": "b" * 64,
            }
            pair["baseline"] = {}
            pair["mutant"] = {}
    return document


def test_node_ci_schema_is_valid_and_all_refs_resolve_locally(
    node_ci_schema: dict[str, Any],
) -> None:
    Draft202012Validator.check_schema(node_ci_schema)
    references = [node["$ref"] for node in _schema_nodes(node_ci_schema) if "$ref" in node]
    assert references
    for reference in references:
        assert reference.startswith("#/$defs/"), reference
        target = node_ci_schema
        for part in reference[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        assert isinstance(target, (dict, bool)), reference


@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
def test_norm_document_shapes_validate_without_claiming_execution(
    node_ci_schema: dict[str, Any], level: str
) -> None:
    validator = _contract(node_ci_schema)
    for name, document in _documents(level).items():
        validator.validate(document)
        _contract(node_ci_schema, name).validate(document)


@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
def test_completed_evidence_shape_is_distinct_from_early_failure(
    node_ci_schema: dict[str, Any], level: str
) -> None:
    validator = _contract(node_ci_schema)
    validator.validate(_completed_evidence_shape(level))
    early = _documents(level)["Evidence"]
    early["node_binding"]["coverage"] = None
    early["node_binding"]["product_tests"] = None
    early["installed_mutation"] = None
    validator.validate(early)


@pytest.mark.parametrize("origin", ["direct", "sdist_rebuilt"])
def test_chosen_engine_artifact_keeps_both_actual_origin_shapes(
    node_ci_schema: dict[str, Any], origin: str
) -> None:
    _contract(node_ci_schema, "ChosenEngineArtifact").validate(_chosen_artifact(origin))


@pytest.mark.parametrize(
    "name,missing",
    [
        ("StaticDeclaration", "engine_artifact"),
        ("AttestedSource", "events"),
        ("Descriptor", "execution_contract_sha256"),
        ("Admission", "platform"),
        ("Prepared", "manifests"),
        ("Run", "failure"),
        ("Evidence", "source_binding_kind"),
        ("Index", "roles"),
        ("Manifest", "identity"),
        ("BuildManifest", "members"),
    ],
)
def test_top_level_documents_are_closed_and_require_authority_fields(
    node_ci_schema: dict[str, Any], name: str, missing: str
) -> None:
    validator = _contract(node_ci_schema)
    unknown = _documents()[name]
    unknown["current"] = True
    assert not validator.is_valid(unknown)
    incomplete = _documents()[name]
    del incomplete[missing]
    assert not validator.is_valid(incomplete)


@pytest.mark.parametrize(
    "path", ["../outside", "/absolute", "C:/outside", "a\\b", "a//b", "a/./b", "a/../b", "a\x00b"]
)
def test_ref_rejects_unsafe_transport_destinations(
    node_ci_schema: dict[str, Any], path: str
) -> None:
    assert not _contract(node_ci_schema, "Ref").is_valid(_ref(path))


@pytest.mark.parametrize("sha", ["a" * 63, "A" * 64, "g" * 64, SHA + "\n"])
def test_ref_rejects_malformed_digests(node_ci_schema: dict[str, Any], sha: str) -> None:
    assert not _contract(node_ci_schema, "Ref").is_valid(
        {**_ref("control/input.json"), "sha256": sha}
    )


@pytest.mark.parametrize("size", [True, -1, 134217729, "1"])
def test_ref_rejects_bool_negative_oversize_or_string_size(
    node_ci_schema: dict[str, Any], size: object
) -> None:
    assert not _contract(node_ci_schema, "Ref").is_valid(
        {**_ref("control/input.json"), "size": size}
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("run_id", True),
        ("run_attempt", 0),
        ("job_id", -1),
        ("artifact_id", 9007199254740992),
        ("artifact_digest", SHA),
        ("source_repository_id", 42),
    ],
)
def test_chosen_artifact_rejects_bad_provider_coordinates(
    node_ci_schema: dict[str, Any], field: str, value: object
) -> None:
    document = _chosen_artifact()
    document[field] = value
    assert not _contract(node_ci_schema, "ChosenEngineArtifact").is_valid(document)


@pytest.mark.parametrize(
    "change", ["profile", "workflow", "event", "app", "visibility", "limits", "uuid"]
)
def test_static_declaration_rejects_old_or_expanded_authority(
    node_ci_schema: dict[str, Any], change: str
) -> None:
    document = _documents()["StaticDeclaration"]
    if change == "profile":
        document["profile"]["revision"] = 1
    elif change == "workflow":
        document["workflow"]["path"] = SOURCE_WORKFLOW
    elif change == "event":
        document["producer"]["event"] = "workflow_dispatch"
    elif change == "app":
        document["producer"]["app_id"] = 1
    elif change == "visibility":
        document["artifact_policy"]["visibility_scope"] = "public"
    elif change == "limits":
        document["artifact_policy"]["max_archive_bytes"] = 1
    else:
        document["repository"]["repository_id"] = "42"
    assert not _contract(node_ci_schema).is_valid(document)


@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
def test_attested_source_requires_v2_context_only_at_v2(
    node_ci_schema: dict[str, Any], level: str
) -> None:
    document = _documents(level)["AttestedSource"]
    document["v2"] = None if level == "V2" else _v2_tuple()
    assert not _contract(node_ci_schema).is_valid(document)


@pytest.mark.parametrize(
    "change",
    ["duplicate_du", "empty_du", "bool_revision", "spec_evidence", "code_without_evidence"],
)
def test_source_tuple_rejects_ambiguous_scope_review_or_approval_shape(
    node_ci_schema: dict[str, Any], change: str
) -> None:
    document = _documents()["AttestedSource"]
    if change == "duplicate_du":
        document["binding"]["decision_unit_ids"] *= 2
    elif change == "empty_du":
        document["binding"]["decision_unit_ids"] = []
    elif change == "bool_revision":
        document["v2"]["implementation"]["revision"] = True
    elif change == "spec_evidence":
        document["applicable_spec_approvals"][0]["evidence_sha256"] = SHA
    else:
        del document["applicable_code_approvals"][0]["evidence_sha256"]
    assert not _contract(node_ci_schema).is_valid(document)


@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
@pytest.mark.parametrize("change", ["order", "missing", "extra", "coverage", "pairs"])
def test_evidence_tier_check_inventory_coverage_and_pairs_are_disjoint(
    node_ci_schema: dict[str, Any], level: str, change: str
) -> None:
    document = _completed_evidence_shape(level)
    _contract(node_ci_schema).validate(document)
    if change == "order":
        document["checks"][0], document["checks"][1] = document["checks"][1], document["checks"][0]
    elif change == "missing":
        document["checks"].pop()
    elif change == "extra":
        document["checks"].append(deepcopy(document["checks"][0]))
    elif change == "coverage":
        document["node_binding"]["coverage"] = _coverage() if level == "V0" else None
    else:
        document["installed_mutation"] = None if level == "V2" else _pairs()
    assert not _contract(node_ci_schema).is_valid(document)


@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
def test_product_projection_follows_tier(node_ci_schema: dict[str, Any], level: str) -> None:
    document = _completed_evidence_shape(level)
    _contract(node_ci_schema).validate(document)
    document["node_binding"]["product_tests"] = None if level == "V2" else _products()
    assert not _contract(node_ci_schema).is_valid(document)


@pytest.mark.parametrize("threshold", ["total", "changed"])
def test_evidence_keeps_existing_coverage_thresholds(
    node_ci_schema: dict[str, Any], threshold: str
) -> None:
    document = _documents()["Evidence"]
    document["node_binding"]["coverage"][threshold]["threshold"] -= 1
    assert not _contract(node_ci_schema).is_valid(document)


@pytest.mark.parametrize("change", ["order", "duplicate", "missing", "extra", "unknown"])
def test_pairs_require_five_fixed_ordered_identifiers(
    node_ci_schema: dict[str, Any], change: str
) -> None:
    document = _pairs()
    if change == "order":
        document["pairs"].reverse()
    elif change == "duplicate":
        document["pairs"][1] = deepcopy(document["pairs"][0])
    elif change == "missing":
        document["pairs"].pop()
    elif change == "extra":
        document["pairs"].append(deepcopy(document["pairs"][0]))
    else:
        document["pairs"][0]["id"] = "MUT-V2-006"
    assert not _contract(node_ci_schema, "CiPairs").is_valid(document)


@pytest.mark.parametrize("level", ["V0", "V2"])
@pytest.mark.parametrize("change", ["order", "duplicate", "missing", "extra", "mixed", "unknown"])
def test_portable_index_has_only_exact_ordered_common_or_pair_role_sets(
    node_ci_schema: dict[str, Any], level: str, change: str
) -> None:
    document = _documents(level)["Index"]
    if change == "order":
        document["roles"].reverse()
    elif change == "duplicate":
        document["roles"][1] = deepcopy(document["roles"][0])
    elif change == "missing":
        document["roles"].pop()
    elif change == "extra":
        document["roles"].append(deepcopy(document["roles"][0]))
    elif change == "mixed":
        document["roles"][0]["id"] = "pair-0-b" if level == "V0" else "node"
    else:
        document["roles"][0]["id"] = "cache"
    assert not _contract(node_ci_schema).is_valid(document)


@pytest.mark.parametrize(
    "change",
    [
        "identity_bool",
        "identity_fraction",
        "identity_negative",
        "identity_extra",
        "symlink",
        "traversal",
        "file_oversize",
        "role_oversize",
        "role_bool",
    ],
)
def test_role_manifest_rejects_unsafe_identity_entries_and_counts(
    node_ci_schema: dict[str, Any], change: str
) -> None:
    document = _documents()["Manifest"]
    if change == "identity_bool":
        document["identity"]["inode"] = True
    elif change == "identity_fraction":
        document["identity"]["mtime_ns"] = 1.5
    elif change == "identity_negative":
        document["identity"]["mtime_ns"] = -1
    elif change == "identity_extra":
        document["identity"]["target"] = "outside"
    elif change == "symlink":
        document["entries"][0]["kind"] = "symlink"
    elif change == "traversal":
        document["entries"][1]["path"] = "../outside"
    elif change == "file_oversize":
        document["entries"][1]["size"] = 134217729
    elif change == "role_oversize":
        document["total_bytes"] = 536870913
    else:
        document["total_bytes"] = True
    assert not _contract(node_ci_schema).is_valid(document)


@pytest.mark.parametrize("contents", [b"", b"abc", b"x" * 17])
@pytest.mark.parametrize("grow_during_read", [False, True])
def test_original_reader_bounds_allocation_and_still_rejects_growth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    contents: bytes,
    grow_during_read: bool,
) -> None:
    from contextlib import contextmanager

    from aiflow import node_ci
    from aiflow.errors import AiflowError

    original = tmp_path / "original.bin"
    original.write_bytes(contents)
    real_open = Path.open
    requests: list[int] = []

    @contextmanager
    def observed_open(path, *args, **kwargs):
        with real_open(path, *args, **kwargs) as handle:
            if path != original:
                yield handle
                return

            class ObservedReader:
                def fileno(self):
                    return handle.fileno()

                def read(self, size):
                    requests.append(size)
                    assert size <= len(contents) + 1
                    if grow_during_read:
                        with real_open(original, "ab") as writer:
                            writer.write(b"!")
                    return handle.read(size)

            yield ObservedReader()

    monkeypatch.setattr(Path, "open", observed_open)
    if grow_during_read:
        with pytest.raises(AiflowError, match="CI original changed during reading"):
            node_ci._read(original)
    else:
        assert node_ci._read(original) == contents
    assert requests == [len(contents) + 1]


def test_original_reader_rejects_oversize_before_opening(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow import node_ci
    from aiflow.errors import AiflowError

    original = tmp_path / "oversize.bin"
    original.write_bytes(b"ab")

    def unexpected_open(*args, **kwargs):
        pytest.fail("An oversized original must be rejected before opening")

    monkeypatch.setattr(Path, "open", unexpected_open)
    with pytest.raises(AiflowError) as caught:
        node_ci._read(original, limit=1)
    assert caught.value.code == "NODE_CI_LIMIT_EXCEEDED"


def test_role_manifest_enforces_entry_limit(node_ci_schema: dict[str, Any]) -> None:
    document = _documents()["Manifest"]
    document["entries"] = [document["entries"][0]] * 20001
    errors = _contract(node_ci_schema, "Manifest").iter_errors(document)
    assert any(
        error.validator == "maxItems" and list(error.path) == ["entries"] for error in errors
    )


@pytest.mark.parametrize(
    "change", ["order", "missing", "extra", "origin", "bool_python", "python_minor"]
)
def test_build_manifest_requires_exact_public_members_and_python_shape(
    node_ci_schema: dict[str, Any], change: str
) -> None:
    document = _documents()["BuildManifest"]
    if change == "order":
        document["members"].reverse()
    elif change == "missing":
        document["members"].pop()
    elif change == "extra":
        document["members"].append(
            {"path": "private.json", "origin": "source", "size": 1, "sha256": SHA}
        )
    elif change == "origin":
        document["members"][0]["origin"] = "sdist_rebuilt"
    elif change == "bool_python":
        document["python_version"][2] = True
    else:
        document["python_version"][1] = 12
    assert not _contract(node_ci_schema).is_valid(document)


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_ci_stream_uses_portable_node_role_coordinates(
    node_ci_schema: dict[str, Any], stream: str
) -> None:
    document = {
        "bytes": 0,
        "sha256": SHA,
        "raw_ref": f"node/raw/EXEC-001/{stream}.raw",
        "log_ref": f"node/raw/EXEC-001/{stream}.log",
    }
    validator = _contract(node_ci_schema, "node_stream")
    validator.validate(document)
    local = {**document, "raw_ref": f"logs/RUN-0001/raw/EXEC-001/{stream}.raw"}
    assert not validator.is_valid(local)
    wrong_extension = {**document, "log_ref": document["raw_ref"]}
    assert not validator.is_valid(wrong_extension)


def _runtime_change(document: dict[str, Any], path: tuple[str | int, ...], value: Any) -> None:
    owner: Any = document
    for key in path[:-1]:
        owner = owner[key]
    owner[path[-1]] = value


@pytest.mark.parametrize(
    "raw",
    [
        b'{"kind":"one","kind":"two"}',
        b'{"nested":{"size":1,"size":2}}',
        b'{"size":NaN}',
        b'{"size":Infinity}',
        b'{"size":-Infinity}',
        b'{"value":"\xff"}',
    ],
)
def test_runtime_wire_reader_rejects_ambiguous_or_nonfinite_bytes(raw: bytes) -> None:
    from aiflow import node_ci
    from aiflow.errors import ContractError

    with pytest.raises(ContractError):
        node_ci._json(raw)


@pytest.mark.parametrize(
    "name",
    [
        "StaticDeclaration",
        "AttestedSource",
        "Descriptor",
        "Admission",
        "Prepared",
        "Index",
        "BuildManifest",
    ],
)
def test_runtime_document_validation_is_pure_and_does_not_grant_current(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    import subprocess

    from aiflow import node_ci

    document = _documents()[name]
    original = deepcopy(document)
    attempts = []

    def forbidden(*args: Any, **kwargs: Any) -> None:
        attempts.append((args, kwargs))
        raise AssertionError("Closed metadata validation attempted I/O or execution")

    for attribute in ("_read", "_write_new", "github_get"):
        monkeypatch.setattr(node_ci, attribute, forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    result = node_ci.validate_node_ci_document(document)
    assert result == original == document
    assert "current" not in result
    assert attempts == []


@pytest.mark.parametrize(
    "name,path,value",
    [
        ("StaticDeclaration", ("profile", "revision"), 2.0),
        ("StaticDeclaration", ("producer", "app_id"), 15368.0),
        ("Prepared", ("profile", "revision"), 2.0),
        ("AttestedSource", ("binding", "decision_unit_ids"), ["DU-001", "DU-001"]),
        ("AttestedSource", ("applicable_code_approvals", 0, "decision_unit_id"), "DU-999"),
        ("AttestedSource", ("v2", "implementation", "revision"), True),
        ("Admission", ("platform", "run_attempt"), True),
        ("Admission", ("platform", "workflow_path"), ".github/workflows/unreviewed.yml"),
        ("Prepared", ("manifests", "engine", "ref"), "../engine.json"),
        ("Descriptor", ("attestation_head",), "A" * 40),
        ("BuildManifest", ("python_version", 2), True),
    ],
)
def test_runtime_closed_models_reject_wrong_types_and_mixed_authority(
    name: str, path: tuple[str | int, ...], value: Any
) -> None:
    from aiflow import node_ci
    from aiflow.errors import ContractError

    document = _documents()[name]
    _runtime_change(document, path, value)
    with pytest.raises(ContractError):
        node_ci.validate_node_ci_document(document)


@pytest.mark.parametrize("level", ["V0", "V1", "V2"])
def test_unregistered_caps_reject_before_planning_or_any_proof(
    monkeypatch: pytest.MonkeyPatch, level: str
) -> None:
    from aiflow import evidence, node_ci
    from aiflow.errors import ContractError

    monkeypatch.setattr(node_ci, "CI_CAPS_REGISTERED", False)
    monkeypatch.setattr(node_ci, "CI_CAPS", dict.fromkeys(("V0", "V1", "V2"), (0, 0, 0, 0, 0)))
    assert node_ci.CI_CAPS_REGISTERED is False
    assert node_ci.CI_CAPS == dict.fromkeys(("V0", "V1", "V2"), (0, 0, 0, 0, 0))
    attempts = []

    def forbidden(*args: Any, **kwargs: Any) -> None:
        attempts.append((args, kwargs))
        raise AssertionError("Unregistered capacity reached planning, writes or execution")

    monkeypatch.setenv("CI_CAPS_REGISTERED", "true")
    monkeypatch.setattr(evidence, "_node_evidence_plan", forbidden)
    for attribute in ("_read", "_write_new", "github_get"):
        monkeypatch.setattr(node_ci, attribute, forbidden)
    with pytest.raises(ContractError) as caught:
        node_ci.node_ci_execution_contract(level)
    assert caught.value.code == "NODE_CI_UNAVAILABLE"
    assert attempts == []


@pytest.mark.parametrize(
    "bad_row",
    [
        (1, 1, 1, 1),
        [1, 1, 1, 1, 1],
        (1, 1, 1, 1, True),
        (1, 1, 1, 1, 0),
        (1, 1, 1, -1, 1),
        (1, 1, 1, 16 * 1024 * 1024 + 1, 1),
    ],
)
def test_isolated_cap_validation_rejects_a_broken_nonselected_tier(
    monkeypatch: pytest.MonkeyPatch, bad_row: Any
) -> None:
    from aiflow import node_ci
    from aiflow.errors import ContractError

    # This deliberately synthetic in-memory table is restored by monkeypatch;
    # it neither registers production limits nor runs a physical kernel.
    monkeypatch.setattr(node_ci, "CI_CAPS_REGISTERED", True)
    monkeypatch.setattr(
        node_ci, "CI_CAPS", {"V0": (1, 1, 1, 1, 1), "V1": (1, 1, 1, 1, 1), "V2": bad_row}
    )
    with pytest.raises(ContractError) as caught:
        node_ci.node_ci_execution_contract("V0")
    assert caught.value.code == "NODE_CI_UNAVAILABLE"


def test_isolated_execution_contract_binds_all_tiers_without_weakening_the_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hashlib

    from aiflow import node_ci

    caps = dict.fromkeys(("V0", "V1", "V2"), (200, 1_000_000, 100_000, 16_384, 1_000_000))
    monkeypatch.setattr(node_ci, "CI_CAPS_REGISTERED", True)
    monkeypatch.setattr(node_ci, "CI_CAPS", caps)
    before = node_ci.node_ci_execution_contract("V2")
    assert [row["check_id"] for row in before["plan"]["checks"]] == list(CHECK_IDS)
    assert before["plan"]["checks"][7]["threshold"] == 85
    assert before["plan"]["checks"][8]["threshold"] == 90
    assert before["roles"] == list(COMMON_ROLES) + [
        f"pair-{index}-{side}" for index in range(5) for side in ("b", "m")
    ]
    old_digest = hashlib.sha256(node_ci._canonical(before)).hexdigest()
    monkeypatch.setattr(node_ci, "CI_CAPS", {**caps, "V0": (201, *caps["V0"][1:])})
    after = node_ci.node_ci_execution_contract("V2")
    assert hashlib.sha256(node_ci._canonical(after)).hexdigest() != old_digest


def _authority_put(path: Path, value: Any) -> None:
    """Write fixture metadata, never a physical execution original or Current."""
    from aiflow.node_ci import _canonical

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(value))


def _authority_builder(tmp_path: Path) -> Any:
    """Real Git/governance services around explicitly synthetic LOCAL claims.

    No Node material, Job, installed pair, live-local review or code approval is
    manufactured. Only the committed-metadata reader may attest this history;
    the missing physical originals can never establish actual LOCAL Current.
    """
    import shutil
    from types import SimpleNamespace

    import yaml
    from initialization_helpers import fixture_git
    from test_node_v2_contract import node_documents
    from test_node_v2_evidence import public_node_evidence

    from aiflow import node_ci, review_service
    from aiflow.approval import approve_task
    from aiflow.ask_service import answer_task
    from aiflow.classification_service import classify_task
    from aiflow.contracts import require_valid_contract
    from aiflow.evidence import (
        finalize_v2_evidence,
        prepare_v2_pre_evidence,
        validate_node_evidence,
    )
    from aiflow.facts_service import record_risk_facts
    from aiflow.specification import REQUIRED_SECTIONS
    from aiflow.state import utc_timestamp
    from aiflow.task_service import (
        begin_task,
        evaluate_and_sync_verification_subject,
        freeze_task,
        read_task_record_strict,
        record_task_event,
        start_task,
        transition_task_record,
    )
    from aiflow.verification_service import _finish_local_verification, _start_local_verification
    from aiflow.verifier_service import build_verifier_context, save_verifier_context

    roots: list[Path] = []

    def create(*, ask: bool = False, design_finding: bool = False) -> Any:
        root = tmp_path / f"r{len(roots)}"
        roots.append(root)
        root.mkdir()
        source = Path(__file__).resolve().parents[2]
        for name in ("policy", "schemas", "templates"):
            shutil.copytree(source / ".ai" / name, root / ".ai" / name)
        for name, document in node_documents().items():
            (root / ".ai/policy" / name).write_text(
                yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
            )
        (root / ".ai/repository-id").write_text(
            "00000000-0000-4000-8000-000000000042\n", encoding="utf-8"
        )
        (root / "fixture.py").write_text("value = 1\n", encoding="utf-8")
        (root / ".gitignore").write_text(".ai/tasks/*/logs/\n__pycache__/\n", encoding="utf-8")
        workflow = root / TARGET_WORKFLOW
        workflow.parent.mkdir(parents=True)
        workflow.write_bytes(b"# Synthetic workflow metadata; never dispatched.\n")
        declaration = _documents()["StaticDeclaration"]
        declaration["workflow"]["sha256"] = node_ci._sha(workflow.read_bytes())
        declaration["tier_contracts"] = {
            level: node_ci._sha(node_ci._canonical(node_ci.node_ci_execution_contract(level)))
            for level in ("V0", "V1", "V2")
        }
        _authority_put(root / ".ai/node-ci-producer.json", declaration)
        fixture_git(root, "init", "-b", "codex/synthetic-node-ci")
        fixture_git(root, "config", "user.name", "Public Fixture")
        fixture_git(root, "config", "user.email", "fixture@example.invalid")
        fixture_git(root, "config", "core.autocrlf", "true")
        fixture_git(root, "add", ".")
        fixture_git(root, "commit", "-m", "Synthetic CI declaration and public fixture")
        assert (
            start_task(
                root,
                objective="Synthetic CI metadata",
                allowed_scope=["fixture.py"],
                forbidden_actions=["push", "deploy"],
            ).task_id
            == "TASK-0001"
        )
        td = root / ".ai/tasks/TASK-0001"
        facts = {
            "impact_categories": [],
            "controlled_actions": [],
            "permission_requirements": ["action_approval"],
            "reversibility": "reversible",
            "business_direction_count": 2 if ask else 1,
            "scope": {"clear": True},
            "impact": {"level": "medium"},
            "protections": {"verified_backup": False, "dry_run": False},
            "verification": {"automatic": True, "tools_missing": False},
            "change_characteristics": {
                "mechanical": False,
                "behavior_changed": True,
                "code_modified": True,
                "interaction_scope": "cross_module",
                "regression_risk": True,
                "error_detectability": "high",
            },
            "verification_requirements": dict.fromkeys(
                (
                    "acceptance_required",
                    "integration_required",
                    "targeted_mutation_required",
                    "independent_verifier_required",
                ),
                True,
            ),
        }
        facts_path = tmp_path / f"f{len(roots)}.json"
        _authority_put(facts_path, facts)
        record_risk_facts(
            root,
            "TASK-0001",
            decision_unit_id="DU-001",
            input_path=facts_path,
            actor="fixture-classifier",
        )
        (td / "spec.md").write_text(
            "# Explicit synthetic metadata, not execution\n\n"
            + "\n\n".join(
                f"## {heading}\n\nRetain public synthetic metadata; execute no product."
                for heading in REQUIRED_SECTIONS.values()
            )
            + "\n",
            encoding="utf-8",
        )
        freeze_task(root, "TASK-0001", actor="fixture-specifier")
        classification = classify_task(root, "TASK-0001", actor="fixture-classifier")
        assert classification["effective_verification_level"] == "V2"
        assert classification["effective_route"] == ("ASK" if ask else "REVIEW")
        if ask:
            options = json.loads(
                (source / "tests/fixtures/contracts/valid/ask-options.json").read_text(
                    encoding="utf-8"
                )
            )
            options["generated_at"] = utc_timestamp()
            options_path = tmp_path / f"o{len(roots)}.json"
            _authority_put(options_path, options)
            answer_task(
                root,
                "TASK-0001",
                options_file=options_path,
                selected_option_id="OPT-01",
                actor="fixture-owner",
                reason="Public synthetic decision",
            )
        design_context = review_service.build_review_context(root, "TASK-0001", "design")
        design_result = review_service.record_review(
            root,
            "TASK-0001",
            actor="fixture-design-reviewer",
            input_path={
                "review_id": "REV-0001",
                "review_stage": "design",
                "context_sha256": design_context["context_sha256"],
                "recorded_at": utc_timestamp(),
                "outcome": "APPROVE_WITH_CONDITIONS" if design_finding else "APPROVE",
                "summary": "Synthetic metadata; no physical proof is accepted here.",
                "findings": [
                    {
                        "finding_id": "RF-001",
                        "severity": "low",
                        "title": "Synthetic nonblocking note",
                        "location": {"path": "fixture.py", "line": 1},
                        "evidence_refs": [],
                        "status": "open",
                    }
                ]
                if design_finding
                else [],
            },
        )
        if not ask:
            approve_task(
                root,
                "TASK-0001",
                approval_type="spec",
                actor="fixture-owner",
                reason="Synthetic metadata fixture only",
            )
        begin_task(root, "TASK-0001", actor="fixture-implementer")
        (root / "fixture.py").write_text("value = 2\n", encoding="utf-8")
        fixture_git(root, "add", "fixture.py")
        fixture_git(root, "commit", "-m", "Synthetic bounded implementation")
        assessment = evaluate_and_sync_verification_subject(
            root, "TASK-0001", mode="final", actor="independent-verifier"
        )
        assert assessment.gate_eligible
        verifier_context = build_verifier_context(root, "TASK-0001")
        save_verifier_context(root, "TASK-0001", verifier_context)
        record = read_task_record_strict(root, "TASK-0001")
        task = record.task
        evidence = public_node_evidence(root)
        for key in (
            "repository_id",
            "branch",
            "base_commit",
            "subject_commit",
            "frozen_spec_sha256",
        ):
            evidence["spec_sha256" if key == "frozen_spec_sha256" else key] = task[key]
        evidence["classification_input_sha256"] = classification["classification_input_sha256"]
        evidence["generated_at"] = utc_timestamp()
        evidence["verifier_context_sha256"] = verifier_context["context_sha256"]
        evidence["review_refs"] = {
            "design": {"review_id": "REV-0001", "context_sha256": design_context["context_sha256"]}
        }
        evidence["node_binding"]["subject_tree"] = fixture_git(
            root, "rev-parse", f"{task['subject_commit']}^{{tree}}"
        )
        evidence["node_binding_sha256"] = node_ci._sha(node_ci._canonical(evidence["node_binding"]))
        pre = prepare_v2_pre_evidence(evidence)
        _start_local_verification(root, "TASK-0001", record, "independent-verifier")
        _finish_local_verification(
            root,
            "TASK-0001",
            actor="independent-verifier",
            conclusion="passed",
            route=classification["effective_route"],
        )

        # Build a structurally correct committed implementation review without
        # calling the live reader with fabricated Current/passed facts.
        implementation_context = deepcopy(design_context)
        implementation_context.update(
            schema_version="2.0",
            review_stage="implementation",
            subject_commit=task["subject_commit"],
            verification_snapshot_sha256=pre["verification_snapshot_sha256"],
        )
        implementation_context["content"].update(
            diff_summary=review_service._committed_diff_summary(
                root, task["base_commit"], task["subject_commit"]
            ),
            verification_summary={
                **review_service._verification_summary(pre),
                "materials_sha256": pre["node_binding"]["materials_sha256"],
                "node_binding_sha256": pre["node_binding_sha256"],
            },
        )
        implementation_context["context_sha256"] = review_service._context_digest(
            implementation_context
        )
        implementation = {
            "schema_version": "1.0",
            "review_id": "REV-0002",
            "revision": 1,
            "task_id": "TASK-0001",
            "review_stage": "implementation",
            "reviewer": "fixture-code-reviewer",
            "recorded_at": utc_timestamp(),
            "context_sha256": implementation_context["context_sha256"],
            "outcome": "APPROVE",
            "summary": "Synthetic committed metadata only; no LOCAL originals.",
            "findings": [],
        }
        review_service.validate_review_record(implementation, implementation_context)
        _authority_put(
            td / f"review-contexts/{implementation_context['context_sha256']}.json",
            implementation_context,
        )
        _authority_put(td / "reviews/REV-0002-r0001.json", implementation)
        record_task_event(
            root,
            "TASK-0001",
            event_type="review_recorded",
            actor=implementation["reviewer"],
            payload={
                "review_id": "REV-0002",
                "revision": 1,
                "review_stage": "implementation",
                "context_sha256": implementation_context["context_sha256"],
            },
        )
        final = finalize_v2_evidence(pre, implementation)
        validate_node_evidence(final, require_passed=True)
        _authority_put(td / "evidence.json", final)
        if not ask:
            # A schema-valid historical claim, deliberately NOT approve_task's
            # live code-authority result. Combined Gate still lacks originals.
            code = {
                "schema_version": "1.0",
                "task_id": "TASK-0001",
                "decision_unit_id": "DU-001",
                "approval_type": "code",
                "actor": "fixture-owner",
                "reason": "Synthetic metadata only",
                "base_commit": task["base_commit"],
                "subject_commit": task["subject_commit"],
                "spec_sha256": task["frozen_spec_sha256"],
                "policy_sha256": classification["policy_sha256"],
                "approved_at": utc_timestamp(),
                "evidence_sha256": node_ci._sha(node_ci._canonical(final)),
            }
            require_valid_contract("approval", code)
            approvals = json.loads((td / "approvals.json").read_text(encoding="utf-8"))
            _authority_put(td / "approvals.json", [*approvals, code])
            transition_task_record(
                root,
                "TASK-0001",
                target_state="APPROVED_FOR_MERGE",
                event_type="code_approved",
                actor="fixture-owner",
                payload={
                    "approval_type": "code",
                    "approvals": [code],
                    "structured_review": {
                        key: implementation[key]
                        for key in ("review_id", "revision", "review_stage", "context_sha256")
                    },
                },
                satisfied_preconditions={"code_approval_valid"},
            )
        fixture_git(root, "add", ".ai/tasks/TASK-0001")
        fixture_git(root, "commit", "-m", "Retain synthetic committed governance claims")
        return SimpleNamespace(
            root=root,
            td=td,
            evidence=final,
            design=design_result.record,
            implementation=implementation,
            verifier_context=verifier_context,
            ask=ask,
        )

    return create


@pytest.fixture(scope="module")
def _immutable_authority_baselines(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """Build real histories once; no test ever receives a writable baseline."""
    from initialization_helpers import snapshot_tree

    from aiflow import node_ci

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(node_ci, "CI_CAPS_REGISTERED", True)
        patch.setattr(
            node_ci,
            "CI_CAPS",
            dict.fromkeys(("V0", "V1", "V2"), (200, 1_000_000, 100_000, 16_384, 1_000_000)),
        )
        create = _authority_builder(tmp_path_factory.mktemp("b"))
        baselines = {
            (False, False): create(),
            (True, False): create(ask=True),
            (False, True): create(design_finding=True),
        }
    fingerprints = {key: snapshot_tree(model.root) for key, model in baselines.items()}
    yield baselines
    for key, model in baselines.items():
        assert snapshot_tree(model.root) == fingerprints[key], "Immutable baseline was modified"


@pytest.fixture
def authority_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _immutable_authority_baselines: Any
) -> Any:
    """Each case receives a complete ordinary copy, never shared mutable Git."""
    import shutil

    from initialization_helpers import fixture_git

    from aiflow import node_ci

    # These isolated parser-contract values do not register production caps or
    # execute a kernel. They are restored after every case, including failures.
    monkeypatch.setattr(node_ci, "CI_CAPS_REGISTERED", True)
    monkeypatch.setattr(
        node_ci,
        "CI_CAPS",
        dict.fromkeys(("V0", "V1", "V2"), (200, 1_000_000, 100_000, 16_384, 1_000_000)),
    )
    roots: list[Path] = []

    def independent_copy(source: str, destination: str) -> str:
        result = shutil.copy2(source, destination)
        old, new = Path(source).stat(), Path(destination).stat()
        assert (old.st_dev, old.st_ino) != (new.st_dev, new.st_ino)
        assert new.st_nlink == 1
        return result

    def create(*, ask: bool = False, design_finding: bool = False) -> Any:
        baseline = _immutable_authority_baselines[(ask, design_finding)]
        root = tmp_path / f"r{len(roots)}"
        roots.append(root)
        shutil.copytree(baseline.root, root, copy_function=independent_copy)
        # The copied Git index contains the source inode cache. Refresh only
        # this independent copy before measuring the actual read-only reader.
        fixture_git(root, "update-index", "--refresh")
        model = deepcopy(baseline)
        model.root, model.td = root, root / ".ai/tasks/TASK-0001"
        return model

    return create


@pytest.mark.parametrize("ask", [False, True])
def test_synthetic_authority_fixture_uses_actual_events_without_local_originals(
    authority_fixture: Any, ask: bool
) -> None:
    from aiflow.task_service import read_task_record_strict

    model = authority_fixture(ask=ask)
    record = read_task_record_strict(model.root, "TASK-0001")
    events = [event["event_type"] for event in record.events]
    assert record.task["current_state"] == "APPROVED_FOR_MERGE"
    assert "risk_facts_recorded" in events and "verification_passed" in events
    assert ("ask_answered" in events) is ask
    assert ("spec_approved" in events) is (not ask)
    assert ("code_approved" in events) is (not ask)
    assert not (model.td / "logs/node-prepared").exists()
    assert not (model.td / "logs/IMUT-0123456789abcdef/run.json").exists()


def _authority_commit(model: Any) -> None:
    from initialization_helpers import fixture_git

    fixture_git(model.root, "add", ".ai/tasks/TASK-0001")
    fixture_git(model.root, "commit", "-m", "Synthetic governance counterexample")


def _authority_events(model: Any) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (model.td / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def _authority_write_events(model: Any, events: list[dict[str, Any]]) -> None:
    from aiflow.node_ci import _canonical

    (model.td / "events.jsonl").write_bytes(b"".join(_canonical(row) + b"\n" for row in events))


@pytest.mark.parametrize(
    "fault",
    [
        "classification-policy",
        "classification-du",
        "frozen-spec",
        "persisted-subject",
        "design-review-actor",
        "implementation-context",
        "verifier-context",
        "same-implementer-verifier",
        "verification-actor",
        "review-before-pass",
        "code-actor",
        "code-snapshot-instead-of-final",
        "stale-code-spec",
        "foreign-code-du",
        "missing-review",
        "missing-evidence",
        "pending-marker",
        "forged-current",
    ],
)
def test_committed_source_rejects_mixed_or_missing_authority_before_any_write(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import yaml

    from aiflow.errors import AiflowError
    from aiflow.task_service import read_task_record_strict

    model = authority_fixture()
    events = _authority_events(model)
    if fault.startswith("classification-"):
        value = json.loads((model.td / "classification.json").read_text(encoding="utf-8"))
        if fault == "classification-policy":
            value["policy_sha256"] = "f" * 64
        else:
            value["classifications"][0]["decision_unit_id"] = "DU-999"
        _authority_put(model.td / "classification.json", value)
    elif fault == "frozen-spec":
        with (model.td / "spec.md").open("a", encoding="utf-8") as stream:
            stream.write("\nUnapproved synthetic semantic change.\n")
    elif fault == "persisted-subject":
        task = yaml.safe_load((model.td / "task.yaml").read_text(encoding="utf-8"))
        task["subject_commit"] = task["base_commit"]
        (model.td / "task.yaml").write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
    elif fault == "design-review-actor":
        value = json.loads((model.td / "reviews/REV-0001-r0001.json").read_text(encoding="utf-8"))
        value["reviewer"] = "foreign-reviewer"
        _authority_put(model.td / "reviews/REV-0001-r0001.json", value)
    elif fault in {"implementation-context", "verifier-context"}:
        folder = "review-contexts" if fault == "implementation-context" else "verifier-contexts"
        digest = (
            model.implementation["context_sha256"]
            if fault == "implementation-context"
            else model.verifier_context["context_sha256"]
        )
        path = model.td / folder / f"{digest}.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["subject_commit"] = "f" * 40
        _authority_put(path, value)
    elif fault in {"same-implementer-verifier", "verification-actor", "code-actor"}:
        selected = {
            "same-implementer-verifier": "implementation_started",
            "verification-actor": "verification_passed",
            "code-actor": "code_approved",
        }[fault]
        event = next(row for row in events if row["event_type"] == selected)
        event["actor"] = (
            "independent-verifier" if fault == "same-implementer-verifier" else "foreign-actor"
        )
        _authority_write_events(model, events)
        # A syntactically valid replay is not sufficient role authorization.
        assert (
            read_task_record_strict(model.root, "TASK-0001").task["current_state"]
            == "APPROVED_FOR_MERGE"
        )
    elif fault == "review-before-pass":
        index = next(
            i
            for i, row in enumerate(events)
            if row["event_type"] == "review_recorded" and row["payload"]["review_id"] == "REV-0002"
        )
        review = events.pop(index)
        index = next(
            i for i, row in enumerate(events) if row["event_type"] == "verification_started"
        )
        review.update(from_state="IMPLEMENTING", to_state="IMPLEMENTING")
        events.insert(index, review)
        for sequence, event in enumerate(events, 1):
            event["sequence"] = sequence
        _authority_write_events(model, events)
        assert (
            read_task_record_strict(model.root, "TASK-0001").task["current_state"]
            == "APPROVED_FOR_MERGE"
        )
    elif fault in {"code-snapshot-instead-of-final", "stale-code-spec", "foreign-code-du"}:
        approvals = json.loads((model.td / "approvals.json").read_text(encoding="utf-8"))
        code = next(row for row in approvals if row["approval_type"] == "code")
        if fault == "code-snapshot-instead-of-final":
            code["evidence_sha256"] = model.evidence["verification_snapshot_sha256"]
        elif fault == "stale-code-spec":
            code["spec_sha256"] = "f" * 64
        else:
            code["decision_unit_id"] = "DU-999"
        _authority_put(model.td / "approvals.json", approvals)
        next(row for row in events if row["event_type"] == "code_approved")["payload"][
            "approvals"
        ] = [code]
        _authority_write_events(model, events)
    elif fault == "missing-review":
        (model.td / "reviews/REV-0002-r0001.json").unlink()
    elif fault == "missing-evidence":
        (model.td / "evidence.json").unlink()
    elif fault == "pending-marker":
        _authority_put(model.td / "approval_pending.json", {"synthetic": "must not recover"})
    else:
        value = json.loads((model.td / "classification.json").read_text(encoding="utf-8"))
        value["node_evidence_current"] = True
        _authority_put(model.td / "classification.json", value)
    _authority_commit(model)
    with pytest.raises(AiflowError):
        _read_authority_guarded(model.root, monkeypatch)
    if fault == "pending-marker":
        assert json.loads((model.td / "approval_pending.json").read_text(encoding="utf-8")) == {
            "synthetic": "must not recover"
        }


@pytest.mark.parametrize("fault", ["options-digest", "selection", "actor", "frozen-decision"])
def test_committed_source_replays_actual_ask_transaction_bindings(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from aiflow.errors import AiflowError

    model = authority_fixture(ask=True)
    events = _authority_events(model)
    answer = next(event for event in events if event["event_type"] == "ask_answered")
    payload = answer["payload"]
    if fault == "options-digest":
        payload["options_sha256"] = "f" * 64
    elif fault == "selection":
        payload["selected_option_id"] = "OPT-02"
    elif fault == "actor":
        payload["actor"] = "foreign-answerer"
    else:
        payload["specification_sha256"] = "f" * 64
    _authority_write_events(model, events)
    _authority_commit(model)
    with pytest.raises(AiflowError):
        _read_authority_guarded(model.root, monkeypatch)


def test_committed_source_checks_latest_review_instead_of_historical_approval(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow.errors import AiflowError
    from aiflow.review_service import build_review_context, record_review
    from aiflow.state import utc_timestamp

    model = authority_fixture()
    context = build_review_context(model.root, "TASK-0001", "design")
    record_review(
        model.root,
        "TASK-0001",
        actor="fixture-later-reviewer",
        input_path={
            "review_id": "REV-0003",
            "review_stage": "design",
            "context_sha256": context["context_sha256"],
            "recorded_at": utc_timestamp(),
            "outcome": "REQUEST_CHANGES",
            "summary": "Synthetic later refusal",
            "findings": [],
        },
    )
    _authority_commit(model)
    with pytest.raises(AiflowError):
        _read_authority_guarded(model.root, monkeypatch)


def test_committed_source_accepts_real_nonblocking_resolution_history(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow.review_service import resolve_review_finding

    model = authority_fixture(design_finding=True)
    resolved = resolve_review_finding(
        model.root,
        "TASK-0001",
        review_id="REV-0001",
        finding_id="RF-001",
        reason="Synthetic note resolved",
        actor="fixture-design-reviewer",
    )
    assert resolved.record["revision"] == 2
    _authority_commit(model)
    value, _declaration, _blobs = _read_authority_guarded(model.root, monkeypatch)
    assert value["v2"]["design"]["revision"] == 2
    assert value["applicable_spec_approvals"]


def _read_authority_guarded(
    root: Path, monkeypatch: pytest.MonkeyPatch, *, head: str | None = None
) -> tuple[dict[str, Any], dict[str, Any], dict[str, bytes]]:
    import subprocess

    from initialization_helpers import snapshot_tree

    from aiflow import approval, node_ci, node_execution, review_service, task_service

    attempts = []
    before = snapshot_tree(root)
    original_popen = subprocess.Popen

    def forbidden(*args: Any, **kwargs: Any) -> None:
        attempts.append((args, kwargs))
        raise AssertionError("Committed metadata reader entered live authority, write or execution")

    class GitOnlyPopen(original_popen):
        def __init__(self, argv: Any, *args: Any, **kwargs: Any) -> None:
            if not isinstance(argv, (tuple, list)) or Path(argv[0]).name.lower() not in {
                "git",
                "git.exe",
            }:
                forbidden(argv)
            super().__init__(argv, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "Popen", GitOnlyPopen)
        for module, names in (
            (node_ci, ("_write_new", "github_get")),
            (node_execution, ("_process", "recheck_node_evidence")),
            (review_service, ("build_review_context", "latest_review_assessment")),
            (approval, ("_evidence", "approve_task")),
            (task_service, ("load_task_record",)),
            (Path, ("write_bytes", "write_text", "mkdir", "unlink", "replace", "rename")),
        ):
            for name in names:
                patch.setattr(module, name, forbidden)
        try:
            result = node_ci._build_source_authority(root, "TASK-0001", head=head)
        finally:
            assert attempts == []
            after = snapshot_tree(root)
            # Existing read-only Git queries may refresh only the identical index.
            assert before[".git/index"][:2] == after[".git/index"][:2]
            assert before[".git/index"][4] == after[".git/index"][4]
            assert {key: row for key, row in before.items() if key != ".git/index"} == {
                key: row for key, row in after.items() if key != ".git/index"
            }
    return result


@pytest.mark.parametrize("ask", [False, True])
def test_committed_source_attests_real_governance_metadata_without_current(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch, ask: bool
) -> None:
    from aiflow import node_ci
    from aiflow.node_execution import _git

    model = authority_fixture(ask=ask)
    value, declaration, blobs = _read_authority_guarded(model.root, monkeypatch)
    assert value["kind"] == "aiflow-node-ci-attested-source"
    assert value["binding"]["repository_id"] == declaration["repository"]["repository_id"]
    assert value["v2"]["verifier_actor"] == "independent-verifier"
    assert value["source_evidence"]["canonical_sha256"] == node_ci._sha(
        node_ci._canonical(model.evidence)
    )
    assert blobs[value["events"]["ref"]] == _git(
        model.root, "show", f"{value['attestation_head']}:.ai/tasks/TASK-0001/events.jsonl"
    )
    assert "current" not in value and "node_evidence_current" not in value
    assert not hasattr(value, "current")
    assert bool(value["applicable_spec_approvals"]) is (not ask)
    assert bool(value["applicable_code_approvals"]) is (not ask)
    assert not (model.td / "logs/node-prepared").exists()


@pytest.mark.parametrize("entry", ["producer", "consumer"])
def test_production_entry_points_reject_unregistered_table_before_any_authority_or_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    from aiflow import gate, installed_mutations, node_ci, node_execution
    from aiflow.errors import ContractError

    monkeypatch.setattr(node_ci, "CI_CAPS_REGISTERED", False)
    monkeypatch.setattr(node_ci, "CI_CAPS", dict.fromkeys(("V0", "V1", "V2"), (0, 0, 0, 0, 0)))
    assert node_ci.CI_CAPS_REGISTERED is False
    assert all(row == (0, 0, 0, 0, 0) for row in node_ci.CI_CAPS.values())
    attempts = []

    def forbidden(*args: Any, **kwargs: Any) -> None:
        attempts.append((args, kwargs))
        raise AssertionError("Unregistered production entry reached authority or proof")

    for module, names in (
        (node_ci, ("_build_source_authority", "github_get", "_write_new")),
        (gate, ("evaluate_gate",)),
        (node_execution, ("prepare_ci_materials", "execute_ci_node")),
        (installed_mutations, ("record_ci_pairs",)),
        (Path, ("mkdir", "write_bytes", "write_text")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden, raising=False)
    if entry == "producer":
        with pytest.raises(ContractError) as caught:
            node_ci.verify_node_ci(
                tmp_path / "missing",
                "TASK-0001",
                run_dir=tmp_path / "a",
                output=tmp_path / "a/evidence.json",
                payload_root=tmp_path / "payload",
            )
        assert caught.value.code == "NODE_CI_UNAVAILABLE"
    else:
        result = node_ci.evaluate_node_ci_gate(
            tmp_path / "missing",
            "TASK-0001",
            run_id=22,
            attempt=1,
            download_dir=tmp_path / "downloads",
        )
        assert result["passed"] is False and result["local_current"] is False
        assert result["reason_codes"] == ["NODE_CI_UNAVAILABLE"]
    assert attempts == []


def test_producer_rejects_actual_invalid_committed_source_before_platform_or_claim(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    from aiflow import installed_mutations, node_ci, node_execution
    from aiflow.errors import AiflowError

    model = authority_fixture()
    value = json.loads((model.td / "classification.json").read_text(encoding="utf-8"))
    value["policy_sha256"] = "f" * 64
    _authority_put(model.td / "classification.json", value)
    _authority_commit(model)
    attempts, reads = [], []
    actual_reader = node_ci._build_source_authority

    def read(*args: Any, **kwargs: Any) -> Any:
        reads.append(True)
        return actual_reader(*args, **kwargs)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        attempts.append((args, kwargs))
        raise AssertionError("Invalid source reached platform, claim or physical proof")

    monkeypatch.setattr(node_ci, "_build_source_authority", read)
    for module, names in (
        (node_ci, ("github_get", "_write_new", "authenticate_workflow", "claim_ci_attempt")),
        (node_execution, ("prepare_ci_materials", "execute_ci_node")),
        (installed_mutations, ("record_ci_pairs",)),
        (Path, ("mkdir", "write_bytes", "write_text")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden, raising=False)
    attempt = model.root.parent / "a"
    with pytest.raises(AiflowError):
        node_ci.verify_node_ci(
            model.root,
            "TASK-0001",
            run_dir=attempt,
            output=attempt / "evidence.json",
            payload_root=attempt / "payload",
        )
    # Preserve the actual host guard: non-Windows rejects even earlier, without
    # pretending that fixture metadata certifies a supported physical runner.
    assert reads == ([True] if os.name == "nt" else [])
    assert attempts == []
    assert not attempt.exists()


@pytest.mark.parametrize("state", ["BLOCKED", "ESCALATED"])
def test_committed_source_rejects_currently_blocked_or_escalated_authority(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    from aiflow.errors import AiflowError
    from aiflow.task_service import transition_task_record

    model = authority_fixture()
    transition_task_record(
        model.root,
        "TASK-0001",
        target_state=state,
        event_type="task_blocked" if state == "BLOCKED" else "task_escalated",
        actor="fixture-owner",
        payload={"reason": "Synthetic stop"},
        satisfied_preconditions={
            "blocking_condition_recorded" if state == "BLOCKED" else "escalation_recorded"
        },
    )
    _authority_commit(model)
    with pytest.raises(AiflowError):
        _read_authority_guarded(model.root, monkeypatch)


def test_committed_source_does_not_rebind_spec_approval_to_later_subject(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = authority_fixture()
    approvals = json.loads((model.td / "approvals.json").read_text(encoding="utf-8"))
    spec = next(row for row in approvals if row["approval_type"] == "spec")
    assert spec["subject_commit"] != model.evidence["subject_commit"]
    value, _declaration, _blobs = _read_authority_guarded(model.root, monkeypatch)
    assert value["applicable_spec_approvals"]
    assert value["binding"]["subject_commit"] == model.evidence["subject_commit"]


def test_committed_source_preserves_lf_blob_independently_of_crlf_checkout(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aiflow.node_execution import _git

    model = authority_fixture()
    path = model.td / "events.jsonl"
    committed = _git(model.root, "show", "HEAD:.ai/tasks/TASK-0001/events.jsonl")
    physical = committed.replace(b"\n", b"\r\n")
    path.write_bytes(physical)
    value, _declaration, blobs = _read_authority_guarded(model.root, monkeypatch)
    assert physical != committed
    assert path.read_bytes() == physical
    assert blobs[value["events"]["ref"]] == committed


def test_committed_source_rejects_non_governance_intermediate_reversion(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from initialization_helpers import fixture_git

    from aiflow.errors import AiflowError

    model = authority_fixture()
    path = model.root / "fixture.py"
    original = path.read_bytes()
    path.write_bytes(b"value = 999\n")
    fixture_git(model.root, "add", "fixture.py")
    fixture_git(model.root, "commit", "-m", "Synthetic forbidden intermediate source change")
    path.write_bytes(original)
    fixture_git(model.root, "add", "fixture.py")
    fixture_git(model.root, "commit", "-m", "Restore endpoint bytes without erasing history")
    assert path.read_bytes() == original
    with pytest.raises(AiflowError):
        _read_authority_guarded(model.root, monkeypatch)


@pytest.mark.parametrize(
    "reason",
    [None, 7, {"why": "synthetic"}, True, " \t "],
    ids=["null", "integer", "object", "boolean", "blank"],
)
def test_committed_source_rejects_invalid_ask_reason_before_rendering(
    authority_fixture: Any, monkeypatch: pytest.MonkeyPatch, reason: Any
) -> None:
    import yaml

    from aiflow import ask_service
    from aiflow.errors import ContractError
    from aiflow.specification import specification_digest
    from aiflow.task_service import read_task_record_strict

    model = authority_fixture(ask=True)
    events = _authority_events(model)
    answer = next(event for event in events if event["event_type"] == "ask_answered")
    payload = answer["payload"]
    selected = next(
        option
        for option in payload["options"]["options"]
        if option["option_id"] == payload["selected_option_id"]
    )
    render = ask_service.render_frozen_decision_section
    section_arguments = {
        "decision_unit_id": payload["options"]["decision_unit_id"],
        "selected_option": selected,
        "actor": payload["actor"],
        "answered_at": payload["answered_at"],
    }
    old_section = render(**section_arguments, reason=payload["reason"])
    new_section = render(**section_arguments, reason=reason)
    spec_path = model.td / "spec.md"
    specification = spec_path.read_text(encoding="utf-8")
    assert specification.count(old_section) == 1
    specification = specification.replace(old_section, new_section)
    spec_path.write_text(specification, encoding="utf-8")
    spec_sha = specification_digest(specification)
    task_path = model.td / "task.yaml"
    task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
    task["frozen_spec_sha256"] = spec_sha
    task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
    payload.update(reason=reason, specification_sha256=spec_sha)
    _authority_write_events(model, events)
    _authority_commit(model)
    assert read_task_record_strict(model.root, "TASK-0001").task["frozen_spec_sha256"] == spec_sha

    # Keep the frozen section and ASK digest consistent: stale later evidence
    # must not mask a malformed reason reaching the actual reader's renderer.
    rendered_reasons: list[Any] = []

    def observe_render(**kwargs: Any) -> str:
        rendered_reasons.append(kwargs["reason"])
        return render(**kwargs)

    monkeypatch.setattr(ask_service, "render_frozen_decision_section", observe_render)
    with pytest.raises(ContractError) as caught:
        _read_authority_guarded(model.root, monkeypatch)
    assert rendered_reasons == []
    assert "ASK" in str(caught.value)


@pytest.fixture
def producer_coordination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, producer_authority_baseline: Any
) -> Any:
    """Actual producer orchestration around explicitly unexecuted kernel results.

    Provider bytes are a finite process transcript. Physical Node, interpreter
    discovery and wheel inspection are seams; none supplies real CI or Current.
    Source authority, admission, capture, copying, package replay and ZIP remain real.
    """
    import shutil
    import sys
    from dataclasses import replace
    from types import SimpleNamespace

    from initialization_helpers import fixture_git, snapshot_tree
    from test_node_ci_platform import (
        HEAD as API_HEAD,
    )
    from test_node_ci_platform import (
        _blob,
        _endpoints,
        _job_receipt,
        _process_result,
        _workflow_transcript,
    )

    from aiflow import installed_mutations, node_ci, process_runner
    from aiflow import node_execution as node

    baseline = producer_authority_baseline
    model = deepcopy(baseline.model)
    workspace = tmp_path
    source = workspace / "source"

    def independent_copy(old: str, new: str) -> str:
        result = shutil.copy2(old, new)
        before, after = Path(old).stat(), Path(new).stat()
        assert (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        assert after.st_nlink == 1
        return result

    shutil.copytree(model.root, source, copy_function=independent_copy)
    fixture_git(source, "update-index", "--refresh")
    model.root, model.td = source, source / ".ai/tasks/TASK-0001"
    monkeypatch.setattr(node_ci, "CI_CAPS_REGISTERED", True)
    monkeypatch.setattr(node_ci, "CI_CAPS", baseline.caps)
    declaration_path = source / ".ai/node-ci-producer.json"
    declaration = json.loads(declaration_path.read_text(encoding="utf-8"))
    selection = declaration["engine_artifact"]
    source_workflow = baseline.source_workflow
    attested = deepcopy(baseline.attested)
    attempt = workspace / ".tmp/node-ci/42-2"
    for name in ("artifact", "engine", "payload/node", "payload/dependencies/node_modules"):
        (attempt / name).mkdir(parents=True)
    for key in ("TEMP", "TMP", "TMPDIR"):
        monkeypatch.setenv(key, str(workspace / ".tmp"))
    monkeypatch.setenv("GITHUB_WORKSPACE", str(workspace))
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    monkeypatch.setenv("GH_TOKEN", "synthetic-public-transcript")
    monkeypatch.setattr(sys, "prefix", str(attempt / "engine"))
    gh = attempt / "artifact/gh.exe"
    gh.write_bytes(b"public synthetic client, never launched")
    monkeypatch.setattr(node_ci, "_gh_executable", lambda: gh)
    monkeypatch.setattr(node_ci, "GH_EXE_SHA256", node_ci._sha(gh.read_bytes()))
    (attempt / "artifact/engine-source.zip").write_bytes(b"unexecuted wheel inspection seam")

    target = _workflow_transcript(completed=False)
    target_endpoints = _endpoints()
    for record in target.values():
        # Replace only the transcript's selected head and branch, recursively.
        def bind(value: Any) -> Any:
            if isinstance(value, dict):
                return {key: bind(item) for key, item in value.items()}
            if isinstance(value, list):
                return [bind(item) for item in value]
            return {
                API_HEAD: attested["attestation_head"],
                "codex/synthetic": attested["binding"]["branch"],
            }.get(value, value)

        if isinstance(record, dict):
            record.update(bind(record))
        elif isinstance(record, list):
            record[:] = bind(record)
    target = {
        endpoint.replace(API_HEAD, attested["attestation_head"]): value
        for endpoint, value in target.items()
    }
    for key in ("merge_workflow", "head_workflow"):
        endpoint = target_endpoints[key].replace(API_HEAD, attested["attestation_head"])
        target[endpoint] = _blob((source / TARGET_WORKFLOW).read_bytes())
    public = _workflow_transcript(completed=True, source=True)
    public_endpoints = _endpoints(source=True)
    selected_head = selection["source_head"]

    def bind_public(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: bind_public(item) for key, item in value.items()}
        if isinstance(value, list):
            return [bind_public(item) for item in value]
        if isinstance(value, str):
            return value.replace(API_HEAD, selected_head).replace("codex/synthetic", "synthetic")
        return value

    public = {
        key.replace(API_HEAD, selected_head): bind_public(value) for key, value in public.items()
    }
    public[public_endpoints["workflow"]]["id"] = selection["workflow_id"]
    public[public_endpoints["run"]].update(
        id=selection["run_id"],
        run_attempt=selection["run_attempt"],
        workflow_id=selection["workflow_id"],
    )
    public[public_endpoints["jobs"]][0].update(
        id=selection["job_id"],
        run_id=selection["run_id"],
        run_attempt=selection["run_attempt"],
        started_at="2026-01-01T00:00:00Z",
        completed_at="2026-01-01T00:01:00Z",
    )
    for key in ("merge_workflow", "head_workflow"):
        public[public_endpoints[key].replace(API_HEAD, selected_head)] = _blob(source_workflow)
    public = {
        key.replace("/runs/42/attempts/2", "/runs/12/attempts/1"): value
        for key, value in public.items()
    }
    repository = selection["source_full_name"]
    public[f"repos/{repository}/actions/jobs/13"] = deepcopy(
        public[f"repos/{repository}/actions/runs/12/attempts/1/jobs"][0]
    )
    public[f"repos/{repository}/actions/runs/12/artifacts"] = [
        {
            "id": selection["artifact_id"],
            "name": selection["artifact_name"],
            "size_in_bytes": 1,
            "digest": selection["artifact_digest"],
            "expired": False,
            "created_at": "2026-01-01T00:00:30Z",
            "expires_at": "2099-01-01T00:00:30Z",
            "workflow_run": {
                "id": 12,
                "repository_id": selection["source_repository_id"],
                "head_repository_id": selection["source_repository_id"],
                "head_sha": selected_head,
            },
        }
    ]
    transcript = {**target, **public}
    calls: list[str] = []

    def provider(argv: tuple[str, ...], **_options: Any) -> Any:
        endpoint = argv[-1]
        calls.append(endpoint)
        lookup = endpoint.split("?per_page=", 1)[0]
        assert lookup in transcript, f"Unplanned provider access: {endpoint}"
        return replace(
            _process_result(), stdout=node_ci._canonical(transcript[lookup]), receipt=_job_receipt()
        )

    monkeypatch.setattr(process_runner, "run_node_process", provider)
    source_contract_calls: list[Any] = []

    def source_contract(root: Path, value: Any, *, revision: int) -> Any:
        assert root == source and value["subject_commit"] == attested["binding"]["subject_commit"]
        assert revision == 2
        source_contract_calls.append(value)
        return {}, {"synthetic": "dependency-lock"}

    monkeypatch.setattr(node, "_source_contract", source_contract)

    def dependencies(root: Path, lock: Any, *, revision: int, budget: Any = None) -> Any:
        assert root == attempt / "payload/dependencies/node_modules"
        assert lock == {"synthetic": "dependency-lock"} and revision == 2
        return node._inventory(root, budget=budget)

    monkeypatch.setattr(node, "_dependencies", dependencies)
    site = attempt / "engine/Lib/site-packages"
    engine_members = {
        "aiflow/__init__.py": b"# Public engine discovery seam, never imported.\n",
        "aiflow-0.2.0.dist-info/METADATA": b"Metadata-Version: 2.1\nName: aiflow\nVersion: 0.2.0\n",
    }
    for name, data in engine_members.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    configuration = attempt / "engine/pyvenv.cfg"
    configuration.write_bytes(b"include-system-site-packages = false\n")

    def engine_file(path: Path) -> Any:
        return {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": node_ci._sha(path.read_bytes()),
            "identity": node._identity(node._safe_info(path)),
        }

    runtime_distributions = []

    def engine(*, budget: Any = None) -> Any:
        if budget is None:
            budget = [node.MAX_ENTRIES, node.MAX_TOTAL_BYTES]
        node._take_budget(budget, configuration.stat().st_size)
        node._take_budget(budget)
        files = [engine_file(site / name) for name in engine_members]
        for row in files:
            node._take_budget(budget, row["size"])
        for directory in (site / "aiflow", site / "aiflow-0.2.0.dist-info"):
            assert directory.is_dir()
            node._take_budget(budget)
        for distribution in runtime_distributions:
            for row in distribution["files"]:
                node._take_budget(budget, row["size"])
            roots = {Path(row["path"]).relative_to(site).parts[0] for row in distribution["files"]}
            for _directory in roots:
                node._take_budget(budget)
        return {
            "python": str(attempt / "engine/python.exe"),
            "distributions": [
                {"name": "aiflow", "version": "0.2.0", "files": files},
                *deepcopy(runtime_distributions),
            ],
            "startup": {
                "files": [],
                "setuptools": False,
                "site_roots": [
                    {
                        "path": str(site),
                        "identity": node._identity(node._safe_info(site, directory=True)),
                    }
                ],
                "pyvenv_configuration": engine_file(configuration),
                "python_environment": {
                    "prefix": str(attempt / "engine"),
                    "base_prefix": str(attempt / "engine"),
                    "site_roots": [str(site)],
                    "active_site_roots": [str(site)],
                    "enable_user_site": False,
                },
            },
        }

    provision = synthetic_python_provision(attempt / "artifact", attested, engine())
    runtime_distributions.extend(provision.engine["distributions"][1:])
    lock_endpoint = f"repos/{repository}/contents/uv.lock?ref={selected_head}"
    transcript[lock_endpoint] = _blob(provision.lock_raw)
    monkeypatch.setattr(node, "_engine", engine)
    tool = attempt / "artifact/tool.exe"
    tool.write_bytes(b"public host tool")
    tool_ref = {
        "path": str(tool),
        "size": tool.stat().st_size,
        "sha256": node_ci._sha(tool.read_bytes()),
        "identity": node._identity(node._safe_info(tool)),
    }

    def host_tools(*, budget: Any = None) -> Any:
        if budget is not None:
            node._take_budget(budget, tool_ref["size"])
        return {"synthetic-tool": tool_ref, "absent": None}

    monkeypatch.setattr(node, "_host_tools", host_tools)
    pair_materials = {
        "interpreter": {key: dict(tool_ref) for key in ("base_executable", "runtime")}
    }
    monkeypatch.setattr(
        installed_mutations, "_materials", lambda: node_ci._canonical(pair_materials)
    )
    content_bindings: list[Any] = []

    def wheel_binding(archive: Path, chosen: Any, inputs: Any, contract: str) -> str:
        assert archive == attempt / "artifact/engine-source.zip" and chosen == selection
        assert inputs["source"]["subject_commit"] == attested["binding"]["subject_commit"]
        assert contract == declaration["tier_contracts"]["V2"]
        content_bindings.append(inputs)
        return SHA

    monkeypatch.setattr(node_ci, "_installed_wheel_binding", wheel_binding)
    steps: list[str] = []
    state = SimpleNamespace(fault=None)

    def prepare(root: Path, payload: Path, **kwargs: Any) -> Any:
        steps.append("prepare")
        assert root == source and payload == attempt / "payload"
        assert kwargs["source_tuple"] == attested and kwargs["attempt_root"] == attempt
        if state.fault == "prepare":
            raise RuntimeError("Synthetic prepare failure; retained claim")
        (attempt / "preflight").mkdir()
        document = _documents()["Prepared"]
        document.update(
            platform=kwargs["admission"]["platform"],
            execution_contract_sha256=declaration["tier_contracts"]["V2"],
        )
        for key, filename in (
            ("descriptor", "descriptor.json"),
            ("source_tuple", "source-tuple.json"),
            ("admission", "admission.json"),
        ):
            document[key] = node_ci._file_ref(attempt / "control" / filename, attempt)
        inputs = content_bindings[0]
        manifest_documents = {
            "source": inputs["source"],
            "node": {"runtime": inputs["runtime"]},
            "npm": node._inventory(attempt / "payload/node"),
            "dependencies": inputs["dependencies"],
            "engine": inputs["engine"],
            "host_tools": inputs["host_tools"],
            "preflight": node._inventory(attempt / "preflight"),
        }
        for (key, value), filename in zip(
            manifest_documents.items(), node.MANIFEST_NAMES, strict=True
        ):
            path = attempt / "control" / filename
            node_ci._write_new(path, node_ci._canonical(value))
            document["manifests"][key] = node_ci._file_ref(path, attempt)
        node_ci._write_new(attempt / "control/prepared.json", node_ci._canonical(document))
        return node_ci.validate_node_ci_document(document)

    pairs = _pairs()

    def record_pairs(**kwargs: Any) -> Any:
        steps.append("pairs")
        assert kwargs["materials"] == pair_materials and kwargs["attempt_root"] == attempt
        pairs["admission_sha256"] = node_ci._sha(node_ci._canonical(kwargs["admission"]))
        pairs["engine_content_sha256"] = kwargs["admission"]["engine_content_sha256"]
        for role in node_ci.role_ids("V2")[9:]:
            (attempt / role).mkdir()
        return deepcopy(pairs)

    def execute(root: Path, task_id: str, **kwargs: Any) -> Any:
        steps.append("execute")
        assert root == source and task_id == "TASK-0001" and kwargs["pairs"] == pairs
        if state.fault == "execute":
            raise RuntimeError("Synthetic execution failure; retained claim")
        document = _documents()["Run"]
        inputs = content_bindings[0]
        document["inputs"] = {
            key: inputs[key]
            for key in ("source", "runtime", "dependencies", "engine", "host_tools")
        }
        document["inputs"]["prepared_dependencies"] = inputs["dependencies"]
        document["roots"] = {
            "original": {
                "root": str(source),
                "inventory": node._inventory(source),
                "git": node._git_state(source),
                "binding": {
                    **attested["binding"],
                    "attestation_head": attested["attestation_head"],
                },
            },
            "clone": None,
            "checkout": None,
            "checkout_receipt": None,
        }
        document["outputs"] = dict.fromkeys(("build_dist", "dist", "fixtures", "node_inventory"))
        document.update(
            platform=kwargs["admission"]["platform"],
            prepared=node_ci._file_ref(attempt / "control/prepared.json", attempt),
            descriptor_sha256=node_ci._sha((attempt / "control/descriptor.json").read_bytes()),
            installed_mutation=deepcopy(kwargs["pairs"]),
        )
        (attempt / "node").mkdir()
        document["outputs"]["node_inventory"] = node._inventory(attempt / "node")
        node_ci._write_new(attempt / "node/run.json", node_ci._canonical(document))
        if state.fault == "source-changed":
            (source / "fixture.py").write_bytes(b"value = 42\n")
        if state.fault == "source-reattested":
            fixture_git(source, "commit", "--allow-empty", "-m", "Synthetic later attestation")
        if state.fault == "platform-changed":
            transcript[target_endpoints["check"]]["app"]["id"] = 1
        if state.fault == "platform-reassociated":
            transcript[target_endpoints["jobs"]][0]["id"] = 99
        return node_ci.validate_node_ci_document(document)

    def replay(**kwargs: Any) -> Any:
        steps.append("replay")
        assert kwargs["package_root"] == attempt / "package"
        assert tuple(kwargs["role_manifests"]) == node_ci.role_ids("V2")
        facts = _documents()["Evidence"]
        facts["node_binding"]["subject_tree"] = attested["binding"]["subject_tree"]
        facts["node_binding"]["prepared"] = node_ci._file_ref(
            attempt / "control/prepared.json", attempt
        )
        facts["node_binding"]["run"] = node_ci._file_ref(attempt / "node/run.json", attempt)
        facts["node_binding"].update(
            materials_sha256=node_ci._sha(node_ci._canonical(content_bindings[0])),
            semantic_contract_sha256=node_ci._sha(node_ci._canonical(node.SEMANTIC_CONTRACT_V2)),
            execution_contract_sha256=declaration["tier_contracts"]["V2"],
            environment_sha256=node_ci._sha(node_ci._canonical(kwargs["run"]["environment"])),
            coverage=None,
            product_tests=None,
        )
        return {
            "passed": False,
            "checks": facts["checks"],
            "node_binding": facts["node_binding"],
            "reason_codes": ["SYNTHETIC_NOT_EXECUTED"],
        }

    replay_reader = node.replay_ci_node
    monkeypatch.setattr(node, "prepare_ci_materials", prepare)
    monkeypatch.setattr(node, "execute_ci_node", execute)
    monkeypatch.setattr(node, "replay_ci_node", replay)
    monkeypatch.setattr(installed_mutations, "record_ci_pairs", record_pairs)
    return SimpleNamespace(
        model=model,
        source=source,
        attempt=attempt,
        state=state,
        steps=steps,
        transcript=transcript,
        calls=calls,
        tool=tool,
        attested=attested,
        content_bindings=content_bindings,
        source_contract_calls=source_contract_calls,
        provision=provision,
        lock_endpoint=lock_endpoint,
        replay_reader=replay_reader,
        before=snapshot_tree(source),
        snapshot=snapshot_tree,
    )


@pytest.fixture(scope="module")
def producer_authority_baseline(tmp_path_factory: pytest.TempPathFactory) -> Any:
    import sys
    from types import SimpleNamespace

    from initialization_helpers import snapshot_tree

    from aiflow import node_ci

    caps = dict.fromkeys(("V0", "V1", "V2"), (2000, 10_000_000, 2_000_000, 100_000, 20_000_000))
    source_workflow = b"# Public synthetic engine workflow, never dispatched.\n"
    put = _authority_put

    def initial_declaration(path: Path, value: Any) -> None:
        if path.name == "node-ci-producer.json":
            value["engine_source"].update(
                workflow_ref="refs/pull/7/merge", workflow_sha256=node_ci._sha(source_workflow)
            )
            value["engine_artifact"].update(
                workflow_ref="refs/pull/7/merge", workflow_sha256=node_ci._sha(source_workflow)
            )
        put(path, value)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(node_ci, "CI_CAPS_REGISTERED", True)
        patch.setattr(node_ci, "CI_CAPS", caps)
        patch.setattr(sys.modules[__name__], "_authority_put", initial_declaration)
        model = _authority_builder(tmp_path_factory.mktemp("pb"))()
        attested, _, _ = _read_authority_guarded(model.root, patch)
    fingerprint = snapshot_tree(model.root)
    yield SimpleNamespace(
        model=model, caps=caps, source_workflow=source_workflow, attested=attested
    )
    assert snapshot_tree(model.root) == fingerprint, "Producer immutable baseline was modified"


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "prepare",
        "execute",
        "source-changed",
        "source-reattested",
        "platform-changed",
        "platform-reassociated",
    ],
)
def test_public_producer_retains_claim_and_never_repairs_failed_transactions(
    producer_coordination: Any, fault: str | None
) -> None:
    from aiflow import node_ci
    from aiflow.errors import AiflowError

    case = producer_coordination
    case.state.fault = fault
    output = case.attempt / "evidence.json"

    def invoke() -> Any:
        return node_ci.verify_node_ci(
            case.source,
            "TASK-0001",
            run_dir=case.attempt,
            output=output,
            payload_root=case.attempt / "payload",
        )

    if fault is None:
        result = invoke()
        assert result["conclusion"] == "failed"
        assert result["binding"] == case.attested["binding"]
        assert result["source_binding_kind"] == "attested_committed_tuple"
        assert output.read_bytes() == node_ci._canonical(result)
        assert (case.attempt / "transport.zip").is_file()
        assert case.steps == ["prepare", "pairs", "execute", "replay", "replay"]
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        for definition, path in (
            ("Prepared", "control/prepared.json"),
            ("Run", "node/run.json"),
            ("Admission", "control/admission.json"),
            ("Evidence", "evidence.json"),
            ("Index", "package/index.json"),
        ):
            _contract(schema, definition).validate(
                json.loads((case.attempt / path).read_text(encoding="utf-8"))
            )
    else:
        with pytest.raises((AiflowError, RuntimeError)) as caught:
            invoke()
        assert case.steps == (
            ["prepare"] if fault == "prepare" else ["prepare", "pairs", "execute"]
        )
        if fault in {"prepare", "execute"}:
            assert isinstance(caught.value, RuntimeError) and "Synthetic" in str(caught.value)
        elif fault == "source-reattested":
            assert "source authority changed" in str(caught.value)
        elif fault == "platform-reassociated":
            assert "platform association changed" in str(caught.value)
        assert not output.exists() and not (case.attempt / "transport.zip").exists()
    assert (case.attempt / "control/admission.json").is_file()
    assert len(case.content_bindings) == len(case.source_contract_calls) == 1
    before_retry = case.snapshot(case.attempt)
    prior_steps = list(case.steps)
    with pytest.raises(AiflowError):
        invoke()
    assert case.snapshot(case.attempt) == before_retry and case.steps == prior_steps
    if fault not in {"source-changed", "source-reattested"}:
        after = case.snapshot(case.source)
        assert {key: row for key, row in after.items() if key != ".git/index"} == {
            key: row for key, row in case.before.items() if key != ".git/index"
        }


@pytest.mark.parametrize(
    "fault", ["wrong-engine", "spent-neighbor", "host-changed", "temporary-root", "credential"]
)
def test_public_producer_rejects_invalid_provision_before_kernel_or_reuse(
    producer_coordination: Any, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import sys

    from aiflow import node_ci
    from aiflow.errors import AiflowError

    case = producer_coordination
    if fault == "wrong-engine":
        monkeypatch.setattr(sys, "prefix", str(case.attempt / "elsewhere"))
    elif fault == "spent-neighbor":
        (case.attempt / "unknown").mkdir()
    elif fault == "temporary-root":
        monkeypatch.setenv("TMPDIR", str(case.source))
    elif fault == "credential":
        with (case.source / ".git/config").open("ab") as stream:
            stream.write(b"\n[http]\nextraheader = synthetic-sensitive-marker\n")
    else:
        original = node_ci._installed_wheel_binding

        def mutate(*args: Any, **kwargs: Any) -> str:
            digest = original(*args, **kwargs)
            case.tool.write_bytes(b"changed after admitted input inventory")
            return digest

        monkeypatch.setattr(node_ci, "_installed_wheel_binding", mutate)
    with pytest.raises(AiflowError):
        node_ci.verify_node_ci(
            case.source,
            "TASK-0001",
            run_dir=case.attempt,
            output=case.attempt / "evidence.json",
            payload_root=case.attempt / "payload",
        )
    assert case.steps == []
    assert not (case.attempt / "evidence.json").exists()
    assert not (case.attempt / "control/admission.json").exists()


@pytest.mark.parametrize(
    "fault", ["empty-checks", "missing-binding", "evidence-reserve", "copy-drift", "spent"]
)
def test_public_producer_preserves_partial_package_and_rejects_writer_faults(
    producer_coordination: Any, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from aiflow import node_ci
    from aiflow import node_execution as node
    from aiflow.errors import AiflowError

    case = producer_coordination
    replay = node.replay_ci_node
    copy_tree = node._copy_tree
    write_package = node_ci._write_package

    def faulty_replay(**kwargs: Any) -> Any:
        facts = replay(**kwargs)
        if fault == "empty-checks":
            facts["checks"] = []
        elif fault == "missing-binding":
            facts["node_binding"] = None
        elif fault == "evidence-reserve":
            totals = node_ci._transport_totals(kwargs["role_manifests"], b"{}", level="V2")
            caps = node_ci.CI_CAPS["V2"]
            monkeypatch.setattr(
                node_ci, "CI_CAPS", {**node_ci.CI_CAPS, "V2": (totals["entries"], *caps[1:])}
            )
        return facts

    def drifting_copy(source: Path, destination: Path, inventory: Any) -> Any:
        copied = copy_tree(source, destination, inventory)
        if source == case.source:
            (source / "fixture.py").write_bytes(b"value = 999\n")
        return copied

    def spent_package(*args: Any, **kwargs: Any) -> Any:
        (case.attempt / "package").mkdir()
        return write_package(*args, **kwargs)

    if fault == "copy-drift":
        monkeypatch.setattr(node, "_copy_tree", drifting_copy)
    elif fault == "spent":
        monkeypatch.setattr(node_ci, "_write_package", spent_package)
    else:
        monkeypatch.setattr(node, "replay_ci_node", faulty_replay)
    with pytest.raises(AiflowError) as caught:
        node_ci.verify_node_ci(
            case.source,
            "TASK-0001",
            run_dir=case.attempt,
            output=case.attempt / "evidence.json",
            payload_root=case.attempt / "payload",
        )
    assert (case.attempt / "package").is_dir()
    assert not (case.attempt / "package/index.json").exists()
    assert not (case.attempt / "evidence.json").exists()
    if fault in {"empty-checks", "missing-binding"}:
        assert caught.value.code == "NODE_CI_ORIGINALS_INVALID"
    elif fault == "evidence-reserve":
        assert caught.value.code == "NODE_CI_LIMIT_EXCEEDED"
    elif fault == "copy-drift":
        assert caught.value.code == "NODE_MATERIALS_DRIFT"
        assert (case.attempt / "package/originals/source/fixture.py").read_bytes() != (
            case.source / "fixture.py"
        ).read_bytes()


@pytest.mark.parametrize("authorization", ["url-userinfo", "authorization-header"])
def test_public_producer_rejects_real_git_authorization_before_engine_or_claim(
    producer_coordination: Any, monkeypatch: pytest.MonkeyPatch, authorization: str
) -> None:
    from initialization_helpers import fixture_git

    from aiflow import node_ci
    from aiflow.errors import ContractError

    case = producer_coordination
    if authorization == "url-userinfo":
        fixture_git(
            case.source,
            "config",
            "remote.origin.url",
            "https://synthetic-user:synthetic-pass@github.com/example/synthetic-target.git",
        )
    else:
        fixture_git(
            case.source,
            "config",
            "http.https://github.com/.extraHeader",
            "Authorization: Basic c3ludGhldGljOnB1YmxpYy1maXh0dXJl",
        )
    config = case.source / ".git/config"
    original = config.read_bytes()
    attempted_engine: list[bool] = []

    def forbid_engine(*_args: Any, **_kwargs: Any) -> None:
        attempted_engine.append(True)
        raise AssertionError("Persisted Git authorization passed admission; no package produced")

    monkeypatch.setattr(node_ci, "_authenticate_engine", forbid_engine)
    with pytest.raises(ContractError) as caught:
        node_ci.verify_node_ci(
            case.source,
            "TASK-0001",
            run_dir=case.attempt,
            output=case.attempt / "evidence.json",
            payload_root=case.attempt / "payload",
        )
    assert "persisted authentication" in str(caught.value)
    assert attempted_engine == [] and case.steps == []
    assert case.content_bindings == [] and case.source_contract_calls == []
    assert config.read_bytes() == original
    assert not (case.attempt / "control").exists()
    assert not (case.attempt / "package").exists()
    assert not (case.attempt / "evidence.json").exists()


@pytest.mark.parametrize(
    "dimension", range(5), ids=("entries", "bytes", "manifests", "index", "archive")
)
def test_public_producer_rejects_known_tier_aggregate_before_any_claim_or_kernel(
    producer_coordination: Any, monkeypatch: pytest.MonkeyPatch, dimension: int
) -> None:
    from aiflow import installed_mutations, node_ci
    from aiflow import node_execution as node
    from aiflow.errors import ContractError

    case = producer_coordination
    admit = node_ci._admit_known_ci_materials
    observations, forbidden_calls = [], []

    def reject_aggregate(*args: Any, **kwargs: Any) -> Any:
        totals = admit(*args, **kwargs)
        observations.append(totals)
        inventories = [
            node._inventory(root)
            for root in (
                case.source,
                case.attempt / "artifact",
                case.attempt / "engine",
                case.attempt / "payload/node",
                case.attempt / "payload/dependencies/node_modules",
            )
        ]
        assert all(len(value["entries"]) < totals["entries"] - 1 for value in inventories)
        assert all(value["total_bytes"] < totals["original_bytes"] - 1 for value in inventories)
        assert totals["original_bytes"] == sum(value["total_bytes"] for value in inventories) + sum(
            len(raw) for files in args[4:6] for raw in files.values()
        )
        caps = list(node_ci.CI_CAPS[kwargs["level"]])
        caps[dimension] = list(totals.values())[dimension] - 1
        assert caps[dimension] > 0
        monkeypatch.setattr(node_ci, "CI_CAPS", {**node_ci.CI_CAPS, kwargs["level"]: tuple(caps)})
        return admit(*args, **kwargs)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        forbidden_calls.append("write-or-kernel")
        raise AssertionError("Known aggregate overflow reached writes or a physical phase")

    monkeypatch.setattr(node_ci, "_admit_known_ci_materials", reject_aggregate)
    for module, names in (
        (node_ci, ("_write_new",)),
        (node, ("_write_new", "prepare_ci_materials", "execute_ci_node")),
        (installed_mutations, ("record_ci_pairs",)),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    before = case.snapshot(case.attempt)
    with pytest.raises(ContractError) as caught:
        node_ci.verify_node_ci(
            case.source,
            "TASK-0001",
            run_dir=case.attempt,
            output=case.attempt / "evidence.json",
            payload_root=case.attempt / "payload",
        )
    assert caught.value.code == "NODE_CI_LIMIT_EXCEEDED"
    assert observations and all(value > 0 for value in observations[0].values())
    assert forbidden_calls == case.steps == []
    assert case.snapshot(case.attempt) == before
    assert not (case.attempt / "control").exists() and not (case.attempt / "host").exists()


@pytest.mark.parametrize("fault", ["missing", "wrong-head", "blob-sha", "different-blob"])
def test_public_producer_authenticates_the_exact_python_lock_before_any_claim(
    producer_coordination: Any, fault: str
) -> None:
    from test_node_ci_platform import _blob

    from aiflow import node_ci
    from aiflow.errors import ContractError

    case = producer_coordination
    if fault in {"missing", "wrong-head"}:
        case.transcript[case.lock_endpoint] = {"message": "Not Found"}
        if fault == "wrong-head":
            other = case.lock_endpoint.rsplit("=", 1)[0] + "=" + "9" * 40
            case.transcript[other] = _blob(case.provision.lock_raw)
    elif fault == "blob-sha":
        case.transcript[case.lock_endpoint]["sha"] = "0" * 40
    else:
        case.transcript[case.lock_endpoint] = _blob(
            case.provision.lock_raw + b"# other source blob\n"
        )
    with pytest.raises(ContractError):
        node_ci.verify_node_ci(
            case.source,
            "TASK-0001",
            run_dir=case.attempt,
            output=case.attempt / "evidence.json",
            payload_root=case.attempt / "payload",
        )
    assert case.lock_endpoint in case.calls
    assert case.steps == [] and not (case.attempt / "control").exists()
    assert not (case.attempt / "host").exists()


@pytest.mark.parametrize("fault", [None, "missing", "extra"])
def test_public_original_reader_closes_the_eight_provisioned_input_roles(
    producer_coordination: Any, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from aiflow import node_ci
    from aiflow.errors import ContractError

    case = producer_coordination
    write_package, public_reader = node_ci._write_package, node_ci.validate_ci_originals
    observed = []

    def package_with_input_variant(*args: Any, **kwargs: Any) -> Any:
        path = case.attempt / "control/input-materials.json"
        inputs = json.loads(path.read_bytes())
        if fault == "missing":
            del inputs["python_provision"]
        elif fault == "extra":
            inputs["unbound_extra"] = inputs["python_provision"]
        path.write_bytes(node_ci._canonical(inputs))
        return write_package(*args, **kwargs)

    def observe_public(*args: Any, **kwargs: Any) -> Any:
        inputs = json.loads((args[0] / "originals/control/input-materials.json").read_bytes())
        observed.append(set(inputs))
        return public_reader(*args, **kwargs)

    monkeypatch.setattr(node_ci, "_write_package", package_with_input_variant)
    monkeypatch.setattr(node_ci, "validate_ci_originals", observe_public)

    def invoke() -> Any:
        return node_ci.verify_node_ci(
            case.source,
            "TASK-0001",
            run_dir=case.attempt,
            output=case.attempt / "evidence.json",
            payload_root=case.attempt / "payload",
        )

    if fault is None:
        invoke()
        inputs = case.content_bindings[0]
        assert observed == [set(inputs)] and len(inputs) == 8
        assert (
            inputs["python_provision"]["source"]["head"]
            == case.attested["engine_artifact"]["source_head"]
        )
        assert (case.attempt / "control/provision.json").read_bytes() == node_ci._canonical(
            inputs["python_provision"]
        )
        assert (case.attempt / "control/provision/uv.lock").read_bytes() == case.provision.lock_raw
        admission = json.loads((case.attempt / "control/admission.json").read_bytes())
        assert admission["input_materials_sha256"] == node_ci._sha(node_ci._canonical(inputs))
    else:
        with pytest.raises(ContractError):
            invoke()
        assert observed and ("python_provision" in observed[0]) is (fault == "extra")
        assert not (case.attempt / "evidence.json").exists()


@pytest.mark.parametrize(
    "fault", [None, "head", "blob", "wheel-ref", "requirements-ref", "control-lock"]
)
def test_public_original_reader_recomputes_portable_python_provision_associations(
    producer_coordination: Any, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from test_installed_mutation_transactions import pure_guard
    from test_node_ci_execution import forbid_producing_paths

    from aiflow import node_ci
    from aiflow import node_execution as node
    from aiflow.errors import ContractError

    case = producer_coordination
    writer, reader = node_ci._write_package, node_ci.validate_ci_originals
    reached, provision_reads, control_reads = [], [], []

    class ProvisionRelationsPassed(Exception):
        pass

    def downstream_context(*_args: Any, **_kwargs: Any) -> None:
        reached.append(True)
        raise ProvisionRelationsPassed

    def mutate_control(*args: Any, **kwargs: Any) -> Any:
        path = case.attempt / "control/provision.json"
        document = json.loads(path.read_bytes())
        if fault == "head":
            document["source"]["head"] = "9" * 40
        elif fault == "blob":
            document["source"]["git_blob_sha"] = "0" * 40
        elif fault == "wheel-ref":
            document["wheels"][0]["wheel"]["ref"] = document["requirements"]["ref"]
        elif fault == "requirements-ref":
            document["requirements"]["ref"] = document["source"]["raw"]["ref"]
        elif fault == "control-lock":
            (case.attempt / "control/provision/uv.lock").write_bytes(
                case.provision.lock_raw + b"\n"
            )
        path.write_bytes(node_ci._canonical(document))
        return writer(*args, **kwargs)

    def portable_public(*args: Any, **kwargs: Any) -> Any:
        # Public closed-input parsing, physical Ref/role validation, and the
        # actual pure replay/provision association all remain production code.
        monkeypatch.setattr(node, "replay_ci_node", case.replay_reader)
        monkeypatch.setattr(node, "_ci_context", downstream_context)
        provision_reader, original_reader = node_ci._python_provision, node._ci_original

        def read_provision(*values: Any, **options: Any) -> Any:
            result = provision_reader(*values, **options)
            provision_reads.append(result)
            return result

        def read_original(package: Path, role: str, name: str) -> bytes:
            data = original_reader(package, role, name)
            if role == "control" and name.startswith("provision"):
                control_reads.append(name)
            return data

        monkeypatch.setattr(node_ci, "_python_provision", read_provision)
        monkeypatch.setattr(node, "_ci_original", read_original)
        with forbid_producing_paths(monkeypatch, case.attempt / "engine"), pure_guard(monkeypatch):
            return reader(*args, **kwargs)

    monkeypatch.setattr(node_ci, "_write_package", mutate_control)
    monkeypatch.setattr(node_ci, "validate_ci_originals", portable_public)

    def invoke() -> Any:
        return node_ci.verify_node_ci(
            case.source,
            "TASK-0001",
            run_dir=case.attempt,
            output=case.attempt / "evidence.json",
            payload_root=case.attempt / "payload",
        )

    if fault is None:
        with pytest.raises(ProvisionRelationsPassed):
            invoke()
        assert reached == [True]
    else:
        with pytest.raises(ContractError):
            invoke()
        assert reached == []
    assert len(provision_reads) == 1 and "provision.json" in control_reads
    if fault in {None, "control-lock"}:
        assert "provision/uv.lock" in control_reads


@pytest.mark.parametrize("bound", ["entries", "bytes", "exact-boundary"])
def test_ci_input_collectors_share_actual_physical_inventory_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bound: str
) -> None:
    from initialization_helpers import fixture_git

    from aiflow import installed_mutations, node_ci
    from aiflow import node_execution as node
    from aiflow.errors import ContractError

    source = tmp_path / "source"
    payload = tmp_path / "payload"
    roots = {
        "source": source,
        "runtime": payload / "node",
        "dependencies": payload / "dependencies/node_modules",
        "engine": tmp_path / "engine",
        "host_tools": tmp_path / "host",
    }
    public_bytes = b"x" * 256
    for root in roots.values():
        root.mkdir(parents=True)
        (root / "public.txt").write_bytes(public_bytes)
    fixture_git(source, "init", "-b", "codex/public-budget")
    fixture_git(source, "config", "user.name", "Public Fixture")
    fixture_git(source, "config", "user.email", "fixture@example.invalid")
    fixture_git(source, "add", "public.txt")
    fixture_git(source, "commit", "-m", "Public bounded inventory fixture")
    subject = node._git(source, "rev-parse", "HEAD").decode().strip()
    monkeypatch.setattr(node, "MAX_ENTRIES", 4 if bound == "entries" else 5)
    total_bytes = 5 * len(public_bytes)
    monkeypatch.setattr(node, "MAX_TOTAL_BYTES", total_bytes - (bound == "bytes"))
    actual_source, actual_inventory = node._source, node._inventory
    received: list[tuple[str, Any]] = []

    def read_source(root: Path, selected: str, *, budget: Any = None) -> Any:
        assert root == source and selected == subject
        received.append(("source", budget))
        return actual_source(root, selected, budget=budget)

    def inventory(root: Path, *, budget: Any = None) -> Any:
        assert root == roots["runtime"]
        received.append(("runtime", budget))
        return actual_inventory(root, budget=budget)

    def dependencies(root: Path, lock: Any, *, revision: int, budget: Any = None) -> Any:
        assert root == roots["dependencies"] and lock == {"public": "lock"} and revision == 2
        received.append(("dependencies", budget))
        return actual_inventory(root, budget=budget)

    def engine(*, budget: Any = None) -> Any:
        received.append(("engine", budget))
        return actual_inventory(roots["engine"], budget=budget)

    def host(*, budget: Any = None) -> Any:
        received.append(("host_tools", budget))
        return actual_inventory(roots["host_tools"], budget=budget)

    def contract(root: Path, value: Any, *, revision: int) -> Any:
        assert root == source and value["subject_commit"] == subject and revision == 2
        return {}, {"public": "lock"}

    def no_pairs() -> None:
        raise AssertionError("V1 must not enter the separate installed-pair materials domain")

    monkeypatch.setattr(node, "_source", read_source)
    monkeypatch.setattr(node, "_inventory", inventory)
    monkeypatch.setattr(node, "_source_contract", contract)
    monkeypatch.setattr(node, "_dependencies", dependencies)
    monkeypatch.setattr(node, "_engine", engine)
    monkeypatch.setattr(node, "_host_tools", host)
    monkeypatch.setattr(installed_mutations, "_materials", no_pairs)
    # This isolated five-domain accounting fixture supplies inventories rather
    # than installed metadata; Python provision has its own real-byte tests.
    monkeypatch.setattr(node_ci, "_python_provision", lambda *_: {"synthetic": "separate-domain"})
    inputs = {
        "binding": {"subject_commit": subject, "verification_level": "V1"},
        "engine_artifact": {"synthetic": "not-executed"},
    }
    if bound == "exact-boundary":
        collected = node_ci._ci_input_materials(source, payload, inputs)
        assert collected["pair_materials"] is None
    else:
        with pytest.raises(ContractError, match="Combined material inventory exceeds"):
            node_ci._ci_input_materials(source, payload, inputs)
    assert [role for role, _ in received] == [
        "source",
        "engine",
        "runtime",
        "dependencies",
        "host_tools",
    ]
    shared = received[0][1]
    assert shared is not None and all(budget is shared for _, budget in received)
    if bound == "exact-boundary":
        assert shared == [0, 0]


@pytest.mark.parametrize(
    "config_key,config_value",
    [
        ("remote.origin.proxy", "https://synthetic-user:synthetic-pass@proxy.example:8080"),
        ("http.proxy", "synthetic-user:synthetic-pass@proxy.example:8080"),
    ],
    ids=["remote-proxy", "http-proxy-without-scheme"],
)
def test_public_producer_rejects_actual_git_proxy_credentials_before_claim(
    producer_coordination: Any,
    monkeypatch: pytest.MonkeyPatch,
    config_key: str,
    config_value: str,
) -> None:
    from initialization_helpers import fixture_git

    from aiflow import node_ci
    from aiflow.errors import ContractError

    case = producer_coordination
    fixture_git(case.source, "config", config_key, config_value)
    config = case.source / ".git/config"
    original = config.read_bytes()
    attempted_engine: list[bool] = []

    def forbid_engine(*_args: Any, **_kwargs: Any) -> None:
        attempted_engine.append(True)
        raise AssertionError(
            "Persisted Git proxy credentials passed admission; no package produced"
        )

    monkeypatch.setattr(node_ci, "_authenticate_engine", forbid_engine)
    with pytest.raises(ContractError) as caught:
        node_ci.verify_node_ci(
            case.source,
            "TASK-0001",
            run_dir=case.attempt,
            output=case.attempt / "evidence.json",
            payload_root=case.attempt / "payload",
        )
    assert "persisted authentication" in str(caught.value)
    assert attempted_engine == [] and case.steps == []
    assert case.content_bindings == [] and case.source_contract_calls == []
    assert config.read_bytes() == original
    assert not (case.attempt / "control").exists()
    assert not (case.attempt / "package").exists()
    assert not (case.attempt / "evidence.json").exists()


@pytest.mark.parametrize(
    "config_key,config_value",
    [
        ("remote.origin.url", "git@github.com:example/synthetic-target.git"),
        ("remote.origin.proxy", "https://proxy.example:8080"),
        ("http.proxy", "proxy.example:8080"),
    ],
    ids=["passwordless-scp", "anonymous-remote-proxy", "anonymous-schemeless-proxy"],
)
def test_actual_git_authentication_guard_allows_noncredential_url_forms(
    tmp_path: Path, config_key: str, config_value: str
) -> None:
    from initialization_helpers import fixture_git

    from aiflow.node_ci import _reject_source_git_authentication

    source = tmp_path / "source"
    source.mkdir()
    fixture_git(source, "init", "-b", "codex/public-proxy")
    fixture_git(source, "config", config_key, config_value)
    config = source / ".git/config"
    original = config.read_bytes()
    assert _reject_source_git_authentication(source) is None
    assert config.read_bytes() == original


@pytest.fixture
def control_blob_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    import hashlib
    from types import SimpleNamespace

    from aiflow import node_execution

    data = b'{"control":"raw bytes"}\n'
    oid = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    name, head = ".ai/tasks/TASK-0001/spec.md", "1" * 40
    row = (
        b"100644 blob "
        + oid.encode()
        + b" "
        + str(len(data)).encode()
        + b"\t"
        + name.encode()
        + b"\0"
    )
    state = dict(listing=row, body=data, scalar_size=len(data), scalar_error=None, calls=[])

    def git(root: Path, *arguments: str) -> bytes:
        assert root == tmp_path
        state["calls"].append(arguments)
        if arguments[0] == "ls-tree":
            assert arguments == ("ls-tree", "-lz", "--full-tree", head, "--", ":(literal)" + name)
            value = state["listing"]
            if isinstance(value, BaseException):
                raise value
            return value
        if arguments == ("rev-parse", head + ":" + name):
            if state["scalar_error"] is not None:
                raise state["scalar_error"]
            return oid.encode() + b"\n"
        if arguments == ("cat-file", "-s", oid):
            return str(state["scalar_size"]).encode() + b"\n"
        assert arguments == ("cat-file", "blob", oid)
        return state["body"]

    monkeypatch.setattr(node_execution, "_git", git)
    return SimpleNamespace(
        root=tmp_path, head=head, name=name, oid=oid, data=data, row=row, state=state
    )


def test_control_blob_consumes_fresh_size_and_authenticates_body_with_two_queries(
    control_blob_git: Any,
) -> None:
    from aiflow import node_ci
    from aiflow.errors import ContractError

    case = control_blob_git
    assert node_ci._git_blob(case.root, case.head, case.name) == case.data
    assert len(case.state["calls"]) == 2
    assert case.state["calls"][-1] == ("cat-file", "blob", case.oid)
    # A later consumption must obtain its own size, even at the same immutable head.
    case.state["listing"] = case.row.replace(
        b" " + str(len(case.data)).encode() + b"\t",
        b" " + str(node_ci.MAX_JSON_BYTES + 1).encode() + b"\t",
    )
    with pytest.raises(ContractError) as caught:
        node_ci._git_blob(case.root, case.head, case.name)
    assert caught.value.code == "NODE_CI_LIMIT_EXCEEDED"
    assert [call[0] for call in case.state["calls"]] == ["ls-tree", "cat-file", "ls-tree"]


@pytest.mark.parametrize(
    "fault",
    [
        "empty",
        "not-bytes",
        "unterminated",
        "multiple",
        "missing-tab",
        "bad-fields",
        "foreign-path",
        "nonblob",
        "bad-oid",
        "bad-size",
        "nonascii-oid",
        "transport",
        "timeout",
    ],
)
def test_control_blob_metadata_failure_preserves_the_original_scalar_chain(
    control_blob_git: Any, fault: str
) -> None:
    import subprocess

    from aiflow import node_ci
    from aiflow.errors import ContractError

    case = control_blob_git
    case.state["listing"] = {
        "empty": b"",
        "not-bytes": None,
        "unterminated": case.row[:-1],
        "multiple": case.row + case.row,
        "missing-tab": b"broken\0",
        "bad-fields": b"broken\t" + case.name.encode() + b"\0",
        "foreign-path": case.row.replace(case.name.encode(), b"other.md"),
        "nonblob": case.row.replace(b" blob ", b" tree "),
        "bad-oid": case.row.replace(case.oid.encode(), b"g" * 40),
        "bad-size": case.row.replace(b" " + str(len(case.data)).encode() + b"\t", b" invalid\t"),
        "nonascii-oid": case.row.replace(case.oid.encode(), b"\xff" * 40),
        "transport": ContractError("Optional Git query unavailable", code="NODE_GIT_INVALID"),
        "timeout": subprocess.TimeoutExpired("git", 30),
    }[fault]
    assert node_ci._git_blob(case.root, case.head, case.name) == case.data
    assert case.state["calls"][1:] == [
        ("rev-parse", case.head + ":" + case.name),
        ("cat-file", "-s", case.oid),
        ("cat-file", "blob", case.oid),
    ]
    case.state["scalar_error"] = ContractError("Original fact unavailable", code="NODE_GIT_INVALID")
    with pytest.raises(ContractError, match="Original fact unavailable"):
        node_ci._git_blob(case.root, case.head, case.name)


@pytest.mark.parametrize("fault", ["negative-size", "oversize", "body-length", "body-hash"])
def test_control_blob_metadata_keeps_pre_read_limits_and_raw_git_identity(
    control_blob_git: Any, fault: str
) -> None:
    from aiflow import node_ci
    from aiflow.errors import ContractError

    case = control_blob_git
    before_body = fault in {"negative-size", "oversize"}
    if before_body:
        size = -1 if fault == "negative-size" else node_ci.MAX_JSON_BYTES + 1
        case.state["listing"] = case.row.replace(
            b" " + str(len(case.data)).encode() + b"\t", b" " + str(size).encode() + b"\t"
        )
    elif fault == "body-length":
        case.state["body"] = case.data + b"x"
    else:
        case.state["body"] = b"[" + case.data[1:]
    with pytest.raises(ContractError) as caught:
        node_ci._git_blob(case.root, case.head, case.name)
    assert caught.value.code == ("NODE_CI_LIMIT_EXCEEDED" if before_body else "NODE_CI_INVALID")
    assert len(case.state["calls"]) == (1 if before_body else 2)


def test_control_blob_argument_validation_still_precedes_git_queries(
    control_blob_git: Any,
) -> None:
    from aiflow import node_ci
    from aiflow.errors import ContractError

    case = control_blob_git
    with pytest.raises(ContractError):
        node_ci._git_blob(case.root, "invalid", case.name)
    with pytest.raises(ContractError):
        node_ci._git_blob(case.root, case.head, "../outside")
    assert not case.state["calls"]


def test_control_blob_actual_git_literal_path_uses_only_metadata_and_body_queries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    from initialization_helpers import fixture_git

    from aiflow import node_ci, node_execution

    source = tmp_path / "committed"
    source.mkdir()
    (source / ".ai").mkdir()
    name = ".ai/control[proof].json"
    data = b"first\r\nsecond\n\0raw"
    (source / name).write_bytes(data)
    (source / ".ai/controlp.json").write_bytes(b"different glob candidate")
    fixture_git(source, "init", "-b", "fixture")
    fixture_git(source, "add", ".")
    fixture_git(
        source,
        "-c",
        "user.name=Public Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        "Retain exact control bytes",
    )
    head = fixture_git(source, "rev-parse", "HEAD")
    original = node_execution._git
    calls = []

    def observe(root: Path, *arguments: str) -> bytes:
        calls.append(arguments)
        return original(root, *arguments)

    monkeypatch.setattr(node_execution, "_git", observe)
    assert node_ci._git_blob(source, head, name) == data
    oid = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert calls == [
        ("ls-tree", "-lz", "--full-tree", head, "--", ":(literal)" + name),
        ("cat-file", "blob", oid),
    ]
