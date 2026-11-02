"""Transported parser originals, never ordinary-install/Job/GitHub execution proof.

The complete pair fixture uses actual guard/probe bytes and AST overlays, but its
receipts and observations are deliberately synthetic. A successful classification
below establishes only byte-reader behavior, never authenticated CI or LOCAL Current.
"""

from __future__ import annotations

# ruff: noqa: E402 -- Reuse explicitly located synthetic parser helpers only.
import ast
import builtins
import shutil
import sys
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
_original_path = list(sys.path)
try:
    sys.path.insert(0, str(ROOT / "tests/unit"))
    from test_installed_mutation_transactions import parser_phase, pure_guard
    from test_node_ci import _platform
    from test_node_ci_execution import (
        _CI_CONFIG,
        _CI_PRODUCERS,
        _NATIVE_OWNERSHIP_UNIT_BYTES,
        ci_recorded_seeds,  # noqa: F401 -- Immutable real collector/writer protocol results.
        ci_source_seeds,  # noqa: F401 -- Immutable public synthetic Git histories.
        forbid_producing_paths,
        synthetic_materials,
    )
finally:
    sys.path[:] = _original_path

from aiflow import installed_mutations as installed
from aiflow import node_execution as node
from aiflow.errors import AiflowError
from aiflow.node_ci import validate_node_ci_document


def transported_phase(root: Path) -> tuple[Path, dict]:
    phase = root / "originals/pair-0-b"
    for name in ("i", "c", "h", "t", "raw"):
        (phase / name).mkdir(parents=True)
    for name in ("receipt.json", "stdout.raw", "stderr.raw", "stdout.log", "stderr.log"):
        (phase / "raw" / name).write_bytes(b"{}")
    (phase / "report.json").write_bytes(b"{}")
    manifest = {"id": "pair-0-b", **node._inventory(phase)}
    manifest["root"] = str(root / "absent-producer/pair-0-b")
    # Producing identity is data. The transported host necessarily has new inodes.
    for row in [manifest, *manifest["entries"]]:
        row["identity"]["inode"] += 10_000_000
    return phase, manifest


def test_transport_role_uses_new_bytes_and_preserves_old_identity_as_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    phase, manifest = transported_phase(tmp_path)
    with pure_guard(monkeypatch):
        observed = installed._ci_role_inventory(phase, manifest, "pair-0-b")
        node._ci_verify_role(tmp_path, "pair-0-b", manifest)
        node._ci_inventory_in_role(installed._ci_subinventory(observed, "i"), manifest)
    assert observed["identity"]["inode"] != node._inventory(phase)["identity"]["inode"]
    assert not Path(manifest["root"]).exists()


@pytest.mark.parametrize(
    "variant",
    [
        "extra_member",
        "missing_raw",
        "extra_raw",
        "unknown",
        "role",
        "inode",
        "hardlink",
        "budget",
        "case_alias",
    ],
)
def test_transport_phase_rejects_unclosed_or_unsafe_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    phase, manifest = transported_phase(tmp_path)
    if variant == "extra_member":
        (phase / "foreign").write_bytes(b"extra")
    elif variant == "missing_raw":
        (phase / "raw/stdout.raw").unlink()
    elif variant == "extra_raw":
        (phase / "raw/foreign.raw").write_bytes(b"extra")
    elif variant == "unknown":
        manifest["current"] = True
    elif variant == "role":
        manifest["id"] = "pair-0-m"
    elif variant == "inode":
        manifest["identity"]["inode"] = 0
    elif variant == "hardlink":
        next(row for row in manifest["entries"] if row["kind"] == "file")["identity"]["nlink"] = 2
    elif variant == "budget":
        monkeypatch.setattr(node, "MAX_ENTRIES", 1)
    elif variant == "case_alias":
        row = deepcopy(next(row for row in manifest["entries"] if row["path"] == "report.json"))
        row["path"] = "REPORT.json"
        manifest["entries"].append(row)
        manifest["entries"].sort(key=lambda item: item["path"].encode())
        manifest["total_bytes"] += row["size"]
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        installed._ci_role_inventory(phase, manifest, "pair-0-b")


@pytest.mark.parametrize(
    "variant",
    [None, "probe_bytes", "probe_anchor", "operator_origin", "native_identity", "unknown"],
)
def test_retained_probe_and_operator_origins_are_bound_to_the_complete_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str | None
) -> None:
    materials = synthetic_materials(tmp_path, monkeypatch)
    phase = tmp_path / "p"
    phase.mkdir()
    node._copy_tree(
        Path(materials["engine"]["closure"]["root"]), phase / "i", materials["engine"]["closure"]
    )
    if variant == "probe_bytes":
        path = phase / "i/Lib/site-packages/aiflow/installed_probe.py"
        path.write_bytes(path.read_bytes() + b"\n# drift\n")
    elif variant == "probe_anchor":
        materials["probes"]["anchors"][installed.PROBE_IDS[0]]["line"] += 1
    elif variant == "operator_origin":
        materials["operators"]["source"]["path"] = str(tmp_path / "outside.py")
    elif variant == "native_identity":
        materials["operators"]["native_source"]["identity"]["inode"] += 1
    elif variant == "unknown":
        materials["probes"]["current"] = True
    with pure_guard(monkeypatch):
        if variant is None:
            installed._ci_probe_originals(phase, materials)
        else:
            with pytest.raises(AiflowError):
                installed._ci_probe_originals(phase, materials)


def make_pair_parser_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple:
    """Ten structurally valid synthetic reports, not ten executed processes."""
    materials = synthetic_materials(tmp_path, monkeypatch)
    platform = _platform()
    admission = {
        "kind": "aiflow-node-ci-admission",
        "schema_version": "1.0",
        "descriptor_sha256": "a" * 64,
        "platform": platform,
        "input_materials_sha256": node._sha(node._canonical(materials)),
        "engine_content_sha256": node._sha(node._canonical(materials["engine"]["installed"])),
        "claimed_at": "2026-11-02T00:00:00Z",
    }
    # Load and check the trusted checkout reader before the no-executable-compile
    # guard. That guard covers replay of transported bytes, not Python startup.
    validate_node_ci_document(admission, kind="aiflow-node-ci-admission")
    # The fixed producing recipe binds the platform attempt to its source role.
    # These empty source/Node roles are data for the pair reader only; they do
    # not fabricate a full source or Node execution package.
    source_root = tmp_path / "source"
    source_root.mkdir()
    attempt = tmp_path / ".tmp/node-ci" / f"{platform['run_id']}-{platform['run_attempt']}"
    attempt.mkdir(parents=True)
    (attempt / "node").mkdir()
    package = tmp_path / "pkg"
    (package / "originals").mkdir(parents=True)
    manifests, pairs = {}, []
    model = SimpleNamespace(materials=materials)
    for index, probe_id in enumerate(installed.PROBE_IDS):
        pair = {"id": probe_id, "overlay": None, "baseline": None, "mutant": None}
        for suffix, stage_name in (("b", "baseline"), ("m", "mutant")):
            role = f"pair-{index}-{suffix}"
            phase = attempt / role
            phase.mkdir()
            node._copy_tree(
                Path(materials["engine"]["closure"]["root"]),
                phase / "i",
                materials["engine"]["closure"],
            )
            relative = "Lib/site-packages/aiflow/" + installed._TARGETS[probe_id][0]
            original = (phase / "i" / relative).read_bytes()
            if suffix == "m":
                changed = installed._transformed_source(probe_id, original)
                (phase / "i" / relative).write_bytes(changed)
                pair["overlay"] = {
                    "path": relative,
                    "before_sha256": node._sha(original),
                    "after_sha256": node._sha(changed),
                }
            for name in ("c", "h", "t"):
                (phase / name).mkdir()
            stage = {
                "closure": node._inventory(phase / "i"),
                "cache": node._inventory(phase / "c"),
                "receipt": None,
            }
            parser_phase(model, phase, probe_id, stage=stage, mutant=suffix == "m")
            pair[stage_name] = stage
            manifests[role] = {"id": role, **node._inventory(phase)}
            shutil.copytree(phase, package / "originals" / role)
        pairs.append(pair)
    manifests["node"] = {"id": "node", **node._inventory(attempt / "node")}
    manifests["source"] = {"id": "source", **node._inventory(source_root)}
    engine_root = Path(materials["engine"]["closure"]["root"])
    manifests["engine"] = {"id": "engine", **node._inventory(engine_root)}
    shutil.copytree(engine_root, package / "originals/engine")
    document = {
        "admission_sha256": node._sha(node._canonical(admission)),
        "engine_content_sha256": admission["engine_content_sha256"],
        "pairs": pairs,
        "failure": None,
    }
    return package, admission, materials, document, manifests


@pytest.fixture(scope="module")
def pair_parser_seed(tmp_path_factory: pytest.TempPathFactory) -> tuple:
    with pytest.MonkeyPatch.context() as patch:
        return make_pair_parser_package(tmp_path_factory.mktemp("p"), patch)


@pytest.fixture
def pair_parser_package(tmp_path: Path, pair_parser_seed: tuple) -> tuple:
    original, admission, materials, pairs, manifests = pair_parser_seed
    package = tmp_path / "p"
    shutil.copytree(original, package)
    assert (package / "originals/pair-0-b/report.json").stat().st_ino != (
        original / "originals/pair-0-b/report.json"
    ).stat().st_ino
    return package, *deepcopy((admission, materials, pairs, manifests))


@contextmanager
def transported_reader_guard(package: Path, monkeypatch: pytest.MonkeyPatch):
    read = node._read
    compile_source = builtins.compile
    attempted = []

    def package_only(path: Path, **kwargs):
        if not Path(path).is_relative_to(package):
            attempted.append(str(path))
            raise AssertionError("portable replay opened an old producing path")
        return read(path, **kwargs)

    def no_live_materials():
        attempted.append("live-materials")
        raise AssertionError("portable replay discovered current host materials")

    def ast_only(source, filename, mode, flags=0, *args, **kwargs):
        if not flags & ast.PyCF_ONLY_AST:
            attempted.append("executable-compile")
            raise AssertionError("portable replay compiled executable source")
        return compile_source(source, filename, mode, flags, *args, **kwargs)

    def no_exec(*args, **kwargs):
        attempted.append("exec")
        raise AssertionError("portable replay executed source")

    with monkeypatch.context() as patch:
        patch.setattr(node, "_read", package_only)
        patch.setattr(installed, "_materials", no_live_materials)
        patch.setattr(node, "_engine", no_live_materials)
        patch.setattr(node, "_host_tools", no_live_materials)
        patch.setattr(builtins, "compile", ast_only)
        patch.setattr(builtins, "exec", no_exec)
        with pure_guard(patch):
            yield
    assert not attempted


def replay_parser_package(fixture: tuple, monkeypatch: pytest.MonkeyPatch) -> dict:
    package, admission, materials, pairs, manifests = fixture
    with transported_reader_guard(package, monkeypatch):
        facts = installed.replay_ci_pairs(
            package_root=package,
            admission=admission,
            materials=materials,
            pairs=pairs,
            role_manifests=manifests,
        )
    assert set(facts) == {"passed", "results", "reason_codes"}
    return facts


def test_complete_synthetic_pair_parser_preserves_byte_classification_only(
    pair_parser_package: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    facts = replay_parser_package(pair_parser_package, monkeypatch)
    assert facts == {
        "passed": True,
        "results": [[probe, "killed"] for probe in installed.PROBE_IDS],
        "reason_codes": [],
    }


def test_old_pair_originals_cannot_be_retagged_to_a_new_platform_attempt(
    pair_parser_package: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert replay_parser_package(pair_parser_package, monkeypatch)["passed"]
    package, admission, materials, pairs, manifests = pair_parser_package
    replacement = deepcopy(admission)
    replacement["platform"]["run_id"] += 1
    replacement["platform"]["run_attempt"] += 1
    retagged = {**pairs, "admission_sha256": node._sha(node._canonical(replacement))}
    facts = replay_parser_package(
        (package, replacement, materials, retagged, manifests), monkeypatch
    )
    assert not facts["passed"], "old transported originals must not become a fresh platform attempt"
    assert facts["results"] == []
    assert facts["reason_codes"] == ["INSTALLED_MUTATION_ATTEMPT_INVALID"]


def test_pair_copies_cannot_omit_unloaded_installed_distribution_metadata(
    pair_parser_package: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Self-rehashed smaller copies cannot redefine the complete installed closure."""
    package, admission, materials, pairs, manifests = pair_parser_package
    assert replay_parser_package(pair_parser_package, monkeypatch)["passed"]
    relative = "Lib/site-packages/aiflow-0.2.0.dist-info/licenses/LICENSE"
    declared = [
        row
        for distribution in materials["engine"]["installed"]["distributions"]
        for row in distribution["files"]
    ]
    assert any(
        row["path"] == str(Path(materials["engine"]["closure"]["root"]) / relative)
        for row in declared
    )
    engine_before = deepcopy((materials["engine"]["installed"], manifests["engine"]))
    license_before = (package / "originals/engine" / relative).read_bytes()

    def omit(inventory: dict, path: str) -> None:
        row = next(row for row in inventory["entries"] if row["path"] == path)
        inventory["entries"].remove(row)
        inventory["total_bytes"] -= row["size"]

    omit(materials["engine"]["closure"], relative)
    for index, pair in enumerate(pairs["pairs"]):
        for side, key in (("b", "baseline"), ("m", "mutant")):
            role = f"pair-{index}-{side}"
            (package / "originals" / role / "i" / relative).unlink()
            omit(pair[key]["closure"], relative)
            omit(manifests[role], "i/" + relative)
            # Keep the now-empty directory originals; omission must be rejected
            # because the declared installed file is missing, not an unrelated
            # directory-membership or stream/loaded-module parser failure.
            assert (package / "originals" / role / "i" / Path(relative).parent).is_dir()
    admission["input_materials_sha256"] = node._sha(node._canonical(materials))
    pairs["admission_sha256"] = node._sha(node._canonical(admission))
    assert (materials["engine"]["installed"], manifests["engine"]) == engine_before
    assert (package / "originals/engine" / relative).read_bytes() == license_before
    facts = replay_parser_package(pair_parser_package, monkeypatch)
    assert not facts["passed"], "ten smaller copies cannot override the complete installed file set"


@pytest.mark.parametrize("escape", [False, True])
def test_pair_closure_uses_lexical_ordinary_record_script_coordinates(
    pair_parser_package: tuple, monkeypatch: pytest.MonkeyPatch, escape: bool
) -> None:
    package, admission, materials, pairs, _roles = pair_parser_package
    prefix = Path(materials["interpreter"]["prefix"])
    files = [
        row
        for distribution in materials["engine"]["installed"]["distributions"]
        for row in distribution["files"]
    ]
    script = next(row for row in files if Path(row["path"]).name == "aiflow.exe")
    raw = str(
        Path(materials["interpreter"]["site"])
        / ("../../../Scripts/aiflow.exe" if escape else "../../Scripts/aiflow.exe")
    )
    script["path"] = raw
    admission["input_materials_sha256"] = node._sha(node._canonical(materials))
    admission["engine_content_sha256"] = node._sha(
        node._canonical(materials["engine"]["installed"])
    )
    pairs["admission_sha256"] = node._sha(node._canonical(admission))
    pairs["engine_content_sha256"] = admission["engine_content_sha256"]
    assert (package / "originals/engine/Scripts/aiflow.exe").is_file()
    with forbid_producing_paths(monkeypatch, prefix):
        facts = replay_parser_package(pair_parser_package, monkeypatch)
    assert facts["passed"] is not escape, facts["reason_codes"]
    assert script["path"] == raw, "normalization must not rewrite the retained engine metadata"


@pytest.mark.parametrize(
    "variant",
    [
        "mixed_attempt",
        "overlay",
        "foreign_mutant",
        "raw",
        "failure_marker",
        "unknown",
        "zero_run_id",
        "boolean_attempt",
        "foreign_source",
        "shared_identity",
        "copy_budget",
    ],
)
def test_complete_pair_parser_rejects_mixed_or_tampered_originals(
    pair_parser_package: tuple, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    package, admission, materials, pairs, manifests = pair_parser_package
    if variant == "mixed_attempt":
        manifests["pair-4-m"]["root"] = str(package.parent / "other/pair-4-m")
    elif variant == "overlay":
        pairs["pairs"][0]["overlay"]["after_sha256"] = "0" * 64
    elif variant == "foreign_mutant":
        (package / "originals/pair-0-m/i/foreign.py").write_bytes(b"changed")
    elif variant == "raw":
        (package / "originals/pair-0-b/raw/stdout.raw").write_bytes(b"changed")
    elif variant == "failure_marker":
        pairs["failure"] = "FIXTURE_NO_EXECUTION"
    elif variant == "unknown":
        pairs["current"] = True
    elif variant in {"zero_run_id", "boolean_attempt"}:
        key = "run_id" if variant == "zero_run_id" else "run_attempt"
        admission["platform"][key] = 0 if variant == "zero_run_id" else True
        pairs["admission_sha256"] = node._sha(node._canonical(admission))
    elif variant == "foreign_source":
        manifests["source"]["root"] = str(package.parent / "other/source")
    elif variant == "shared_identity":
        manifests["pair-4-m"]["identity"] = deepcopy(manifests["pair-4-b"]["identity"])
    elif variant == "copy_budget":
        monkeypatch.setattr(
            node, "MAX_TOTAL_BYTES", materials["engine"]["closure"]["total_bytes"] * 2
        )
    facts = replay_parser_package(pair_parser_package, monkeypatch)
    assert not facts["passed"]
    assert facts["reason_codes"]


def transport_kernel_case(case) -> tuple[Path, dict]:
    """Transport real fixture bytes, retaining producing identities as data."""
    package = case.workspace / "pkg"
    roots = {
        "source": case.source,
        "artifact": case.attempt / "artifact",
        "engine": Path(case.material["engine"]["closure"]["root"]),
        "runtime": case.payload / "node",
        "dependencies": case.payload / "dependencies/node_modules",
        "host": case.attempt / "host",
        "preflight": case.attempt / "preflight",
        "control": case.attempt / "control",
        "node": case.attempt / "node",
    }
    roots["artifact"].mkdir()
    roots["host"].mkdir()
    for name, row in case.material["host_tools"].items():
        if row is not None:
            (roots["host"] / name).write_bytes((case.attempt / "b/python.exe").read_bytes())
    if case.level == "V2":
        roots.update(
            {
                f"pair-{number}-{side}": case.attempt / f"pair-{number}-{side}"
                for number in range(5)
                for side in ("b", "m")
            }
        )
    manifests = {}
    for role, root in roots.items():
        manifests[role] = {"id": role, **node._inventory(root)}
        shutil.copytree(root, package / "originals" / role)
    return package, manifests


@pytest.fixture(scope="module")
def ci_replay_seeds(ci_recorded_seeds: dict) -> dict:
    """Produce each protocol once; negatives copy these immutable originals."""
    seeds = {}
    for level, (case, prepared, run, _before) in ci_recorded_seeds.items():
        assert run["failure"] is None
        package, manifests = transport_kernel_case(case)
        seeds[level] = (case, package, manifests, prepared, run)
    return seeds


def replay_node_package(
    case, package: Path, manifests: dict, prepared: dict, run: dict, monkeypatch: pytest.MonkeyPatch
) -> dict:
    # These explicitly synthetic pins apply only to the copied protocol fixture.
    # The production pin constants/registration are checked separately.
    monkeypatch.setattr(node, "NODE_V2_CONFIG_SHA256", node._sha(_CI_CONFIG))
    monkeypatch.setattr(
        node, "ISTANBUL_FILES", {name: node._sha(data) for name, data in _CI_PRODUCERS.items()}
    )
    if case.native:
        monkeypatch.setattr(
            node,
            "NATIVE_OWNERSHIP_INPUTS",
            {name: node._sha(data) for name, data in _NATIVE_OWNERSHIP_UNIT_BYTES.items()},
        )
    with transported_reader_guard(package, monkeypatch):
        facts = node._replay_ci_node_kernel(
            package_root=package,
            prepared=prepared,
            run=run,
            role_manifests=manifests,
            execution_contract=case.contract,
        )
    assert set(facts) == {"passed", "checks", "node_binding", "reason_codes"}
    return facts


@pytest.mark.parametrize("level,count", [("V0", 6), ("V1", 9), ("V2", 13)])
def test_private_node_replay_recomputes_the_complete_synthetic_tier(
    ci_replay_seeds: dict, monkeypatch: pytest.MonkeyPatch, level: str, count: int
) -> None:
    case, package, manifests, prepared, run = ci_replay_seeds[level]
    facts = replay_node_package(case, package, manifests, prepared, run, monkeypatch)
    assert facts["passed"], facts["reason_codes"]
    assert len(facts["checks"]) == count
    assert all(row["status"] == "passed" for row in facts["checks"])
    assert facts["node_binding"]["run"]["ref"] == "node/run.json"
    assert facts["node_binding"]["environment_sha256"] == node._sha(
        node._canonical(run["environment"])
    )
    if level == "V2":
        assert [row["check_id"] for row in facts["checks"][-4:]] == [
            "acceptance",
            "integration",
            "targeted_mutation",
            "independent_verifier",
        ]


def reseal_file(package: Path, manifests: dict, role: str, relative: str) -> None:
    """Rehash a corrupt transport member while retaining its producing identity.

    This prevents a negative case from passing merely because the outer byte
    manifest noticed a changed hash before the deeper semantic guard ran.
    """
    data = (package / "originals" / role / relative).read_bytes()
    manifest = manifests[role]
    row = next(row for row in manifest["entries"] if row["path"] == relative)
    manifest["total_bytes"] += len(data) - row["size"]
    row.update(size=len(data), sha256=node._sha(data))
    row["identity"]["size"] = len(data)


@pytest.mark.parametrize(
    "variant",
    [
        "environment",
        "binding",
        "checkout_head",
        "index",
        "checkout_members",
        "runtime",
        "setup_cwd",
        "order",
        "deadline",
        "raw",
        "log",
        "cleanup",
        "npm_config",
        "projection",
        "dist",
        "coverage",
        "summary",
        "catalog",
        "products",
        "pairs",
    ],
)
def test_private_node_replay_rejects_self_rehashed_semantic_corruption(
    ci_replay_seeds: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    case, original, original_manifests, original_prepared, original_run = ci_replay_seeds["V2"]
    package = tmp_path / "p"
    shutil.copytree(original, package)
    assert (package / "originals/node/run.json").stat().st_ino != (
        original / "originals/node/run.json"
    ).stat().st_ino
    manifests, prepared, run = deepcopy((original_manifests, original_prepared, original_run))
    modified = []
    if variant == "environment":
        run["environment"]["TEMP"] = str(tmp_path / "foreign")
    elif variant == "binding":
        run["roots"]["original"]["binding"]["subject_commit"] = "0" * 40
    elif variant == "checkout_head":
        run["roots"]["checkout"]["git"]["head"] = "0" * 40
    elif variant == "index":
        run["roots"]["original"]["git"]["index_sha256"] = "0" * 64
    elif variant == "checkout_members":
        run["roots"]["checkout"]["files"].pop()
    elif variant == "runtime":
        run["inputs"]["runtime"]["root"] = str(tmp_path / "foreign-runtime")
    elif variant == "setup_cwd":
        run["roots"]["clone"]["cwd"] = str(tmp_path / "foreign-source")
        path = "raw/setup-clone/receipt.json"
        (package / "originals/node" / path).write_bytes(node._canonical(run["roots"]["clone"]))
        modified.append(path)
    elif variant == "order":
        run["executions"][0], run["executions"][1] = run["executions"][1], run["executions"][0]
    elif variant in {"deadline", "cleanup"}:
        receipt = run["executions"][0]["receipt"]
        receipt["timeout_seconds" if variant == "deadline" else "cleanup"] = (
            29 if variant == "deadline" else "unknown"
        )
        path = "raw/EXEC-001/receipt.json"
        (package / "originals/node" / path).write_bytes(node._canonical(receipt))
        modified.append(path)
    elif variant in {"raw", "log"}:
        path = "raw/EXEC-001/stdout." + ("raw" if variant == "raw" else "log")
        (package / "originals/node" / path).write_bytes(b"controlled corruption\n")
        modified.append(path)
    elif variant == "npm_config":
        path = "user.npmrc"
        (package / "originals/node" / path).write_bytes(b"registry=https://foreign.invalid/\n")
        modified.append(path)
    elif variant == "projection":
        run["outputs"]["node_inventory"].pop()
    elif variant == "dist":
        run["outputs"]["build_dist"]["entries"][0]["sha256"] = "0" * 64
    elif variant == "coverage":
        run["coverage"]["result"]["total"]["covered"] = 0
    elif variant == "summary":
        path = "coverage/coverage-summary.json"
        value = node._json(package / "originals/node" / path)
        value["total"]["lines"]["covered"] = 0
        (package / "originals/node" / path).write_bytes(node._canonical(value))
        modified.append(path)
    elif variant == "catalog":
        path = "expected-map.json"
        value = node._json(package / "originals/node" / path)
        next(iter(value["files"].values()))["sha256"] = "0" * 64
        (package / "originals/node" / path).write_bytes(node._canonical(value))
        modified.append(path)
    elif variant == "products":
        run["product_tests"]["expected_tests"][0]["sha256"] = "0" * 64
    elif variant == "pairs":
        run["installed_mutation"]["pairs"][0]["overlay"]["after_sha256"] = "0" * 64
    for path in modified:
        reseal_file(package, manifests, "node", path)
    # Output projection is also rehashed so coverage/catalog corruption reaches
    # the semantic parser rather than stopping at the complete output seal.
    if modified:
        run["outputs"]["node_inventory"] = [
            row for row in node._content(manifests["node"]) if row["path"] != "run.json"
        ]
    (package / "originals/node/run.json").write_bytes(node._canonical(run))
    reseal_file(package, manifests, "node", "run.json")
    facts = replay_node_package(case, package, manifests, prepared, run, monkeypatch)
    assert not facts["passed"]
    assert facts["reason_codes"]


@pytest.mark.parametrize("variant", ["selected", "digest", "package", "neighbor"])
def test_runtime_originals_reject_reselected_or_unowned_materials(
    ci_replay_seeds: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    _case, original, roles, _prepared, _run = ci_replay_seeds["V1"]
    package = tmp_path / "p"
    shutil.copytree(original / "originals/runtime", package / "originals/runtime")
    manifests = {
        name: node._json(original / "originals/control" / name)
        for name in ("node.json", "npm.json")
    }
    role = deepcopy(roles["runtime"])
    if variant == "selected":
        manifests["node.json"]["selected"] = "other.exe"
    elif variant == "digest":
        manifests["npm.json"]["runtime_sha256"] = "0" * 64
    elif variant == "package":
        (package / "originals/runtime/node_modules/npm/package.json").write_bytes(
            b'{"name":"foreign","version":"11.13.0"}'
        )
    elif variant == "neighbor":
        # Even a correctly content-addressed neighbor cannot become npm-owned.
        inventory = manifests["node.json"]["runtime"]
        row = deepcopy(next(row for row in inventory["entries"] if row["path"] == "node.exe"))
        row["path"] = "neighbor.exe"
        inventory["entries"].append(row)
        manifests["npm.json"]["runtime_sha256"] = node._sha(node._canonical(inventory))
    with transported_reader_guard(package, monkeypatch), pytest.raises(AiflowError):
        node._ci_runtime_originals(package, manifests, role)


@pytest.mark.parametrize(
    "variant", ["partial_source", "source_hash", "missing_cache", "members", "wire"]
)
def test_native_originals_keep_the_reviewed_pair_exact_cache_and_sidecar_wire(
    ci_replay_seeds: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    case, original, original_roles, _prepared, original_run = ci_replay_seeds["V0"]
    package = tmp_path / "p"
    shutil.copytree(original / "originals/node", package / "originals/node")
    source, fixtures, role = deepcopy(
        (
            original_run["inputs"]["source"],
            original_run["outputs"]["fixtures"],
            original_roles["node"],
        )
    )
    monkeypatch.setattr(
        node,
        "NATIVE_OWNERSHIP_INPUTS",
        {name: node._sha(data) for name, data in _NATIVE_OWNERSHIP_UNIT_BYTES.items()},
    )
    if variant == "partial_source":
        source["files"] = [
            row for row in source["files"] if row["path"] != "scripts/windows-owned-launcher.cs"
        ]
    elif variant == "source_hash":
        next(row for row in source["files"] if row["path"] == "scripts/windows-owned-launcher.cs")[
            "sha256"
        ] = "0" * 64
    elif variant == "missing_cache":
        del fixtures["native_ownership"]
    elif variant == "members":
        inventory = fixtures["native_ownership"]
        removed = inventory["entries"].pop()
        inventory["total_bytes"] -= removed["size"]
        prefix = "checkout/" + node.NATIVE_OWNERSHIP_DIRECTORY + "/"
        role["entries"] = [
            row for row in role["entries"] if row["path"] != prefix + removed["path"]
        ]
    else:
        sidecar = next(
            (package / "originals/node/checkout/.runtime/native-ownership").glob("*.json")
        )
        sidecar.write_bytes(sidecar.read_bytes() + b"\n")
    with transported_reader_guard(package, monkeypatch), pytest.raises(AiflowError):
        node._ci_native_originals(package, source, fixtures, role)


@pytest.mark.parametrize(
    "variant", ["node_top", "node_execution", "node_raw", "preflight_top", "preflight_raw"]
)
def test_transported_process_roles_are_closed_over_empty_directories_and_raw_groups(
    ci_replay_seeds: dict, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    case, package, roles, _prepared, _run = ci_replay_seeds["V1"]
    role = deepcopy(roles["preflight" if variant.startswith("preflight") else "node"])
    if variant.endswith("top"):
        role["entries"].append({"path": "foreign", "kind": "directory"})
    elif variant == "node_execution":
        role["entries"].append({"path": "raw/EXEC-011/stdout.raw", "kind": "file"})
    else:
        name = "node/stdout.raw" if variant == "preflight_raw" else "raw/EXEC-001/stdout.raw"
        role["entries"] = [row for row in role["entries"] if row["path"] != name]
    if not variant.startswith("preflight"):
        from aiflow.verification import _bound_node_plan

        context = node._ci_context(
            case.source,
            case.attempt / "node",
            case.attested["binding"],
            {
                name: node._json(package / "originals/control" / name)
                for name in node.MANIFEST_NAMES
            },
        )
        plan = _bound_node_plan(context, "V1", revision2=True, run_dir=case.attempt / "node")
    with pure_guard(monkeypatch), pytest.raises(AiflowError):
        if variant.startswith("preflight"):
            node._ci_closed_preflight_roles(role)
        else:
            node._ci_closed_node_roles(role, "V1", plan)
