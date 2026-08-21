"""Executable traceability checks for the twelve phase-one acceptance items."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs/implementation/phase-01-acceptance-matrix.md"
RESULTS = ROOT / "docs/pilots/results"
ROW = re.compile(r"^\| (ACC-\d{2}) \|(.+)\|$", re.MULTILINE)
BACKTICK = re.compile(r"`([^`]+)`")
TEST_NODE = re.compile(r"^(tests/[^:]+\.py)::([A-Za-z_][A-Za-z0-9_]*)$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")

PILOTS = {
    "PILOT-AUTO": {
        "branch": "pilot/auto-doc",
        "subject": "2b1900a0207d106147d21e0d9c7e85a8d450fa4b",
        "attestation": "7f73a6de232fb362ece6021a868cf1d3013dbe0f",
        "ci": "adde5eecd7c4886a5a9f670d30229933e1d272e23d549d559e8953c8767e66e1",
        "gate": "dd9567515379ba6bd6583fcff09f22835c853094be01fbadf6db38504e6d7da2",
    },
    "PILOT-ASK": {
        "branch": "pilot/ask-report",
        "subject": "e72e5f17d01216210bb05f3811c5ac0c78ec1766",
        "attestation": "74d4d1570249273dfbb5e095475a3c0239988f61",
        "ci": "931959e02ba297eaaeb21e76c7f82e76b5c9f43479ce0e3f2c8a43738c0f5e22",
        "gate": "640e3edfb2af9e5a3cc0e9ed796297cc32c2d7adac0a47733f9f6c9b179d0ed9",
    },
    "PILOT-REVIEW": {
        "branch": "pilot/review-policy",
        "subject": "f3d70bd41768dab583e3f2582d13ad9088a2630b",
        "attestation": "2d229c325d68529b5f507b030d802fcb88e7cb4e",
        "ci": "b8cc1ef4c06df6dcc6be68536e5c17ef73f42eca85e375421fc8800a2639dbdb",
        "gate": "49a6fd9387efd412d0702191661178409da2fa0e87f6629f89e8813ce1ed65b8",
    },
    "PILOT-BLOCK": {
        "branch": "pilot/block-dry-run",
        "subject": "7c3e32d6a38b966e2892251068647d83aa295a23",
        "attestation": "da8ac8990485a1c52ec327d099132ce7d19ab674",
        "ci": "5ed088ec0771bbd552adf3a2b27cd3b5ff940bdece17c505c038237a582a7830",
        "gate": "dd9567515379ba6bd6583fcff09f22835c853094be01fbadf6db38504e6d7da2",
    },
}


def _metadata(path: Path) -> dict[str, str]:
    pairs = re.findall(r"^- ([a-z_]+): `([^`]+)`", path.read_text(encoding="utf-8"), re.MULTILINE)
    return dict(pairs)


def _source_hashes(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        assert re.fullmatch(r"[0-9a-f]{64}", digest)
        values[name] = digest
    return values


def test_matrix_has_exactly_twelve_complete_passed_rows() -> None:
    text = MATRIX.read_text(encoding="utf-8")
    rows = ROW.findall(text)
    assert [identifier for identifier, _ in rows] == [f"ACC-{index:02d}" for index in range(1, 13)]
    assert len({identifier for identifier, _ in rows}) == 12
    for _identifier, body in rows:
        cells = [cell.strip() for cell in body.split("|")]
        assert len(cells) == 7
        assert cells[-2] in {"passed", "blocked"}
        assert cells[-2] == "passed"
        assert all(cell for cell in cells)


def test_matrix_local_files_and_test_nodes_exist() -> None:
    for _identifier, body in ROW.findall(MATRIX.read_text(encoding="utf-8")):
        cells = [cell.strip() for cell in body.split("|")]
        implementation = BACKTICK.search(cells[1])
        target = BACKTICK.search(cells[2])
        assert implementation and (ROOT / implementation.group(1)).is_file()
        assert target
        matched = TEST_NODE.fullmatch(target.group(1))
        assert matched
        test_path, function = matched.groups()
        source = (ROOT / test_path).read_text(encoding="utf-8")
        assert re.search(rf"^def {re.escape(function)}\(", source, re.MULTILINE)
        evidence_paths = [
            value
            for value in BACKTICK.findall(cells[4])
            if value.startswith(("docs/", "tests/", "src/", ".ai/"))
        ]
        assert evidence_paths and all((ROOT / value).exists() for value in evidence_paths)


def test_four_pilots_have_distinct_branches_and_commit_bindings() -> None:
    branches: set[str] = set()
    subjects: set[str] = set()
    attestations: set[str] = set()
    for pilot, expected in PILOTS.items():
        metadata = _metadata(RESULTS / pilot / "result.md")
        assert metadata["task_id"] == "TASK-0001"
        assert metadata["repository_id"] == "b85e5a53-4935-4436-bdbc-c26a241bfae8"
        assert metadata["pilot_base"] == "01e0e282afaead31b9653391584267f20ccbf13a"
        assert metadata["source_branch"] == expected["branch"]
        assert metadata["subject_commit"] == expected["subject"]
        assert metadata["attestation_commit"] == expected["attestation"]
        assert COMMIT.fullmatch(metadata["subject_commit"])
        assert COMMIT.fullmatch(metadata["attestation_commit"])
        branches.add(metadata["source_branch"])
        subjects.add(metadata["subject_commit"])
        attestations.add(metadata["attestation_commit"])
    assert len(branches) == len(subjects) == len(attestations) == 4


def test_external_artifact_hash_summaries_match_verified_values() -> None:
    for pilot, expected in PILOTS.items():
        hashes = _source_hashes(RESULTS / pilot / "source-hashes.sha256")
        assert hashes["ci-evidence.json"] == expected["ci"]
        assert hashes["gate.json"] == expected["gate"]
        assert hashes["task-id.txt"] == hashlib.sha256(b"TASK-0001\n").hexdigest()
    block = _source_hashes(RESULTS / "PILOT-BLOCK" / "source-hashes.sha256")
    assert block["scenario-hashes-before.txt"] == block["scenario-hashes-after.txt"]


def test_report_task_is_unique_and_in_gate_capable_state() -> None:
    task_id = (RESULTS / "report-task-id.txt").read_text(encoding="utf-8").strip()
    assert task_id == "TASK-0001"
    task = yaml.safe_load((ROOT / ".ai/tasks" / task_id / "task.yaml").read_text(encoding="utf-8"))
    assert task["task_id"] == task_id
    assert task["current_state"] in {
        "IMPLEMENTING",
        "VERIFYING",
        "VERIFIED",
        "APPROVED_FOR_MERGE",
    }
    assert task["allowed_scope"] == [
        "docs/pilots/results/**",
        "docs/implementation/phase-01-acceptance-matrix.md",
        "tests/integration/test_acceptance_traceability.py",
    ]


def test_clean_checkout_evidence_is_passed() -> None:
    evidence = (RESULTS / "clean-checkout.md").read_text(encoding="utf-8")
    assert "- conclusion: `passed`" in evidence
    assert "575 passed, 3 skipped" in evidence
    assert "python -m pip install -e `" not in evidence
    assert "python -m aiflow --help" in evidence
