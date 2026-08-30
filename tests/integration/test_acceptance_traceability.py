"""Executable traceability checks for published phase-one and phase-two acceptance indexes."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs/implementation/phase-01-acceptance-matrix.md"
PHASE_TWO_MATRIX = ROOT / "docs/implementation/phase-02-acceptance-matrix.md"
PHASE_TWO_INDEX = ROOT / "docs/implementation/phase-02-evidence-index.md"
PHASE_TWO_DESIGN = ROOT / "docs/superpowers/specs/2026-08-22-phase-02-review-verification-design.md"
PHASE_TWO_PLAN = (
    ROOT
    / "docs/superpowers/plans/2026-08-22-phase-02-review-verification-implementation-directory.md"
)
CHAPTER_TWELVE = ROOT / "docs/implementation/chapter-12-runtime-observations-hooks.md"
QUICKSTART = ROOT / "docs/operations/quickstart.md"
RESULTS = ROOT / "docs/pilots/results"
ROW = re.compile(r"^\| (ACC-\d{2}) \|(.+)\|$", re.MULTILINE)
BACKTICK = re.compile(r"`([^`]+)`")
TEST_NODE = re.compile(r"^(tests/[^:]+\.py)::([A-Za-z_][A-Za-z0-9_]*)$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
PHASE_TWO_ID = re.compile(r"^\| (P2-[A-Z0-9]+-\d{2}) \|(.+)\|$", re.MULTILINE)

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


def test_phase_two_matrix_has_six_fixed_traceable_inputs() -> None:
    text = PHASE_TWO_MATRIX.read_text(encoding="utf-8")
    assert "状态：`completed`" in text
    rows = PHASE_TWO_ID.findall(text)
    assert [identifier for identifier, _ in rows] == [
        "P2-REV-01",
        "P2-V2-01",
        "P2-VER-01",
        "P2-MUT-01",
        "P2-ESC-01",
        "P2-HOOK-01",
    ]
    for _identifier, body in rows:
        cells = [cell.strip() for cell in body.split("|")]
        assert len(cells) == 7
        assert all(cells)
        assert "python -m pytest" in cells[4]
        assert re.search(r"\b(?:[0-9a-f]{40}|[0-9a-f]{64})\b", cells[3])
        assert cells[5]
        assert cells[6]
        local_paths = [
            value
            for value in BACKTICK.findall("|".join(cells[:4]))
            if value.startswith(("docs/", "tests/", "src/", "tools/", ".ai/"))
        ]
        assert local_paths
        assert all((ROOT / path).exists() for path in local_paths)


def test_phase_two_index_preserves_historical_and_final_replay_boundaries() -> None:
    matrix = PHASE_TWO_MATRIX.read_text(encoding="utf-8")
    index = PHASE_TWO_INDEX.read_text(encoding="utf-8")
    assert "状态：`completed`" in index
    assert "## 阶段二总验收" in matrix
    assert "pending final run" not in matrix
    assert "not current approval" in index
    assert "current HEAD approval" in index
    assert "`TASK-0028` H1" in index
    assert "must not be reported as current merge-ready" in index
    assert "`merge_readiness: reverification_required`" in index
    for identifier in (
        "P2-REV-01",
        "P2-V2-01",
        "P2-VER-01",
        "P2-MUT-01",
        "P2-ESC-01",
        "P2-HOOK-01",
    ):
        assert identifier in index
    assert "current action-authorized" not in index
    assert "<CURRENT-TASK>" not in index
    assert "bootstrap 自举例外" in index
    assert "741790f14ccdc79748a1c83a83536c88fd6095bd" in matrix
    assert "741790f14ccdc79748a1c83a83536c88fd6095bd" in index


def test_phase_two_historical_hashes_and_current_subject_match_records() -> None:
    expected = {
        ".ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json": (
            "4fc5729ef5e40f468b8966e35696a84e47b2de05e363d517293ac9e2f9823662"
        ),
        (
            ".ai/tasks/TASK-0028/action-use-"
            "5a3071cd2e446dea89d5b8acb5c6c26399cf69a4ba141da0f3995706bfa28020.md"
        ): ("3d420bb8ec5845287744b6e19b1890997dba58fdfab158803a84a0bcf86eff94"),
    }
    index = PHASE_TWO_INDEX.read_text(encoding="utf-8")
    for relative_path, digest in expected.items():
        assert hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest() == digest
        assert digest in index
    task = yaml.safe_load((ROOT / ".ai/tasks/TASK-0028/task.yaml").read_text(encoding="utf-8"))
    assert task["subject_commit"] == "cb1e15b547a8280ddf7b7515f45367aec14aa490"
    assert task["subject_commit"] in index


def test_phase_two_published_artifact_paths_exist() -> None:
    for document in (PHASE_TWO_MATRIX, PHASE_TWO_INDEX):
        paths = [
            value
            for value in BACKTICK.findall(document.read_text(encoding="utf-8"))
            if value.startswith(("docs/", "tests/", "src/", "tools/", ".ai/")) and "*" not in value
        ]
        assert paths
        assert all((ROOT / path).exists() for path in paths)


def test_phase_two_closeout_documents_distinguish_completion_from_history() -> None:
    design = PHASE_TWO_DESIGN.read_text(encoding="utf-8")
    plan = PHASE_TWO_PLAN.read_text(encoding="utf-8")
    chapter_twelve = CHAPTER_TWELVE.read_text(encoding="utf-8")

    assert "状态：completed（历史设计；" in design
    assert "状态：completed（历史实施目录；" in plan
    assert "状态：proposed" not in design
    assert "状态：proposed" not in plan
    assert "这是 H2 投影时的历史事实" in chapter_twelve
    assert "Chapter 13 exits 与阶段二总验收均已完成" in chapter_twelve
    assert chapter_twelve.count("[阶段二验收报告](phase-02-acceptance-report.md)") == 2


def test_quality_replay_keeps_coverage_artifacts_out_of_repository_root() -> None:
    quickstart = QUICKSTART.read_text(encoding="utf-8")
    index = PHASE_TWO_INDEX.read_text(encoding="utf-8")
    plan = PHASE_TWO_PLAN.read_text(encoding="utf-8")
    unsafe_coverage_command = (
        "python -m pytest --cov=aiflow --cov-branch --cov-report=term-missing --cov-fail-under=85"
    )

    assert "Join-Path ([System.IO.Path]::GetTempPath()) $runId" in quickstart
    assert "$env:COVERAGE_FILE = $coverageFile" in quickstart
    assert '--cov-report="xml:$coverageXml"' in quickstart
    assert "--cov-fail-under=85" in quickstart
    assert "--fail-under=90" in quickstart
    assert "Remove-Item Env:COVERAGE_FILE -ErrorAction SilentlyContinue" in quickstart
    assert unsafe_coverage_command not in quickstart

    assert unsafe_coverage_command not in index
    assert "../operations/quickstart.md#阶段二基线重放" in index
    assert "`COVERAGE_FILE`" in index
    assert "显式 XML 路径" in index
    assert "`diff-cover` 变更覆盖率 90%" in index

    assert "历史命令提示" in plan
    assert "../../operations/quickstart.md#阶段二基线重放" in plan
    assert "不应直接执行其中未隔离" in plan
