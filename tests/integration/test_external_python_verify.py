"""Integration tests for cross-repository Python verification without repo-local scripts."""

from __future__ import annotations

import json
import os
import re
import shutil
import site
import subprocess
import sys
import venv
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from aiflow.resource_bundle import POLICIES, build_bundle

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ID = "123e4567-e89b-42d3-a456-426614174000"


def _clean_env() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key != "PYTHONPATH" and not key.startswith(("COVERAGE_", "COV_CORE_", "GIT_"))
    }


def _run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    expected: int = 0,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env if env is not None else _clean_env(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=180,
    )
    assert result.returncode == expected, (argv, result.stdout, result.stderr)
    return result


def _create_isolated_python(venv_dir: Path) -> str:
    """Create a venv that loads aiflow from this checkout even when PYTHONPATH is stripped."""
    venv.create(venv_dir, with_pip=False, symlinks=False)
    site_packages = next(venv_dir.glob("**/site-packages"))
    pth_entries = [str(ROOT / "src"), *site.getsitepackages()]
    (site_packages / "00-aiflow-workspace.pth").write_text(
        "\n".join(pth_entries) + "\n", encoding="utf-8"
    )
    if os.name == "nt":
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        python_exe = venv_dir / "bin" / "python"
    resolved = _run(
        [str(python_exe), "-c", "import aiflow; print(aiflow.__file__)"],
        cwd=venv_dir,
    ).stdout.strip()
    assert Path(resolved).resolve().is_relative_to((ROOT / "src" / "aiflow").resolve())
    return str(python_exe)


@pytest.fixture(scope="module")
def isolated_python(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Create one shared isolated venv for this module's external-repo CLI runs."""
    return _create_isolated_python(tmp_path_factory.mktemp("isolated-python") / "venv")


@pytest.fixture(scope="module")
def built_wheel_python(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, Path]:
    """Build an ordinary wheel strictly in tmp_path and install it into an isolated venv."""
    work_dir = tmp_path_factory.mktemp("built-wheel-python")
    source = work_dir / "source"
    source.mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE", "setup.py", "MANIFEST.in"):
        candidate = ROOT / name
        if candidate.is_file():
            shutil.copyfile(candidate, source / name)
    shutil.copytree(
        ROOT / "src" / "aiflow",
        source / "src" / "aiflow",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_bundled_resources"),
        copy_function=shutil.copyfile,
    )
    for subdir in ("schemas", "policy"):
        shutil.copytree(
            ROOT / ".ai" / subdir,
            source / ".ai" / subdir,
            copy_function=shutil.copyfile,
        )
    (source / ".ai" / "templates").mkdir(parents=True)
    shutil.copyfile(
        ROOT / ".ai" / "templates" / "spec.md",
        source / ".ai" / "templates" / "spec.md",
    )

    wheel_dir = work_dir / "wheel"
    wheel_dir.mkdir()
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--wheel",
            "--outdir",
            str(wheel_dir),
            str(source),
        ],
        cwd=work_dir,
    )
    wheels = list(wheel_dir.glob("*.whl"))
    assert len(wheels) == 1, wheels

    venv_dir = work_dir / "venv"
    venv.create(venv_dir, with_pip=False, symlinks=False)
    site_packages = next(venv_dir.glob("**/site-packages"))
    with zipfile.ZipFile(wheels[0]) as archive:
        archive.extractall(site_packages)
    # Expose only runtime/dev dependencies from the test interpreter; never ROOT/src.
    (site_packages / "00-external-deps.pth").write_text(
        "\n".join(site.getsitepackages()) + "\n", encoding="utf-8"
    )
    python_exe = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(python_exe), venv_dir


def _snapshot_tree(root: Path) -> dict[str, bytes | None]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
    }


def _build_local_bundle(bundle_root: Path) -> Path:
    manifest, resources = build_bundle(ROOT)
    for relative, data in resources.items():
        path = bundle_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (bundle_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle_root


def _create_portable_policy_dir(policy_dir: Path) -> Path:
    policy_dir.mkdir(parents=True, exist_ok=True)
    for filename in POLICIES:
        shutil.copy2(ROOT / ".ai" / "policy" / filename, policy_dir / filename)
    _portable_verification_policy(policy_dir)
    return policy_dir


def _portable_verification_policy(policy_dir: Path) -> None:
    policy_path = policy_dir / "verification-levels.yaml"
    document = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    for level in document["levels"]:
        for check in level["checks"]:
            cmd = check["command"]
            if "--cov=aiflow" in cmd:
                cmd[cmd.index("--cov=aiflow")] = "--cov=sample_pkg"
            elif check["id"] == "diff_coverage":
                check["command"] = [
                    "{python}",
                    "-m",
                    "aiflow.coverage_check",
                    "--run-dir",
                    "{run_dir}",
                    "--base",
                    "{base_commit}",
                    "--source",
                    "src/sample_pkg",
                ]
    policy_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _init_external_repo(
    repo: Path, *, with_ai: bool = True, branch: str | None = "feat/external-change"
) -> None:
    repo.mkdir(parents=True)
    _run(["git", "init", "-b", "main"], cwd=repo)
    if with_ai:
        ai_root = repo / ".ai"
        ai_root.mkdir()
        for subdir in ("schemas", "policy", "templates"):
            shutil.copytree(ROOT / ".ai" / subdir, ai_root / subdir)
        _portable_verification_policy(ai_root / "policy")
        (ai_root / "repository-id").write_text(f"{REPOSITORY_ID}\n", encoding="utf-8")

    (repo / "src" / "sample_pkg").mkdir(parents=True)
    (repo / "src" / "sample_pkg" / "__init__.py").write_text(
        '"""External sample package."""\n\n\n'
        "def classify_sign(value: int) -> str:\n"
        '    """Return sign label."""\n'
        "    if value >= 0:\n"
        '        return "non-negative"\n'
        '    return "negative"\n',
        encoding="utf-8",
    )
    (repo / "tests").mkdir()
    (repo / "tests" / "test_sample.py").write_text(
        "from sample_pkg import classify_sign\n\n\n"
        "def test_classify_sign() -> None:\n"
        '    assert classify_sign(1) == "non-negative"\n'
        '    assert classify_sign(-1) == "negative"\n',
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        "[project]\n"
        'name = "sample-pkg"\n'
        'version = "0.1.0"\n\n'
        "[tool.pytest.ini_options]\n"
        'testpaths = ["tests"]\n'
        'pythonpath = ["src"]\n\n'
        "[tool.coverage.run]\n"
        "branch = true\n"
        'source = ["sample_pkg"]\n\n'
        "[tool.mypy]\n"
        'python_version = "3.11"\n'
        "strict = true\n"
        'files = ["src"]\n\n'
        "[tool.ruff]\n"
        'target-version = "py311"\n'
        "line-length = 100\n",
        encoding="utf-8",
    )
    (repo / ".gitignore").write_text(
        ".pytest_cache/\n.mypy_cache/\n.ruff_cache/\n__pycache__/\n*.pyc\n",
        encoding="utf-8",
    )
    _run(["git", "add", "."], cwd=repo)
    _run(
        [
            "git",
            "-c",
            "user.name=External Repo",
            "-c",
            "user.email=external@example.invalid",
            "commit",
            "-m",
            "initial external package",
        ],
        cwd=repo,
    )
    if branch is not None:
        _run(["git", "switch", "-c", branch], cwd=repo)


def _write_spec(repo: Path, task_id: str) -> None:
    spec_path = repo / ".ai" / "tasks" / task_id / "spec.md"
    spec_path.write_text(
        "# Task Specification\n\n"
        "## 目标\n\n"
        "Verify external package change.\n\n"
        "## 范围\n\n"
        "Only `src/sample_pkg/__init__.py` and `tests/test_sample.py`.\n\n"
        "## 非目标\n\n"
        "No unrelated package changes.\n\n"
        "## 验收条件\n\n"
        "Verification passes and merge gate returns PASS.\n\n"
        "## 禁止动作\n\n"
        "Do not bypass verification.\n\n"
        "## 错误行为\n\n"
        "Fail closed on missing coverage or failed checks.\n\n"
        "## 回滚\n\n"
        "Revert the feature branch commit.\n",
        encoding="utf-8",
    )


def _facts_payload(*, review: bool) -> dict[str, Any]:
    return {
        "scope": {"clear": True},
        "impact": {"level": "medium" if review else "low"},
        "protections": {"verified_backup": True, "dry_run": True},
        "verification": {"automatic": True, "tools_missing": False},
        "impact_categories": [],
        "controlled_actions": [],
        "business_direction_count": 1,
        "change_characteristics": {
            "mechanical": not review,
            "behavior_changed": review,
            "code_modified": review,
            "interaction_scope": "cross_module" if review else "local",
            "regression_risk": review,
            "error_detectability": "low" if review else "high",
        },
        "verification_requirements": {
            "acceptance_required": False,
            "integration_required": False,
            "targeted_mutation_required": False,
            "independent_verifier_required": False,
        },
        "reversibility": "reversible",
        "external_side_effects": [],
        "permission_requirements": [],
    }


def _record_review(
    python_exe: str,
    repo: Path,
    outside_dir: Path,
    task_id: str,
    *,
    stage: str,
    review_id: str,
) -> None:
    context_path = outside_dir / f"{stage}-context.json"
    _run(
        [
            python_exe,
            "-m",
            "aiflow",
            "review",
            "context",
            task_id,
            "--stage",
            stage,
            "--output",
            str(context_path),
        ],
        cwd=repo,
    )
    context_sha = json.loads(context_path.read_text(encoding="utf-8"))["context_sha256"]
    review_input = outside_dir / f"{stage}-review.json"
    review_input.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "review_id": review_id,
                "review_stage": stage,
                "recorded_at": "2026-11-25T00:00:00Z",
                "context_sha256": context_sha,
                "outcome": "APPROVE",
                "summary": f"{stage} approved",
                "findings": [],
            }
        ),
        encoding="utf-8",
    )
    _run(
        [
            python_exe,
            "-m",
            "aiflow",
            "review",
            "record",
            task_id,
            "--input",
            str(review_input),
            "--actor",
            "independent-reviewer",
        ],
        cwd=repo,
    )


def _run_lifecycle_through_verify(
    python_exe: str,
    repo: Path,
    outside_dir: Path,
    *,
    review: bool,
) -> str:
    start_out = _run(
        [
            python_exe,
            "-m",
            "aiflow",
            "start",
            "--objective",
            "Verify external Python package",
            "--allow",
            "src/sample_pkg/**",
            "--allow",
            "tests/**",
        ],
        cwd=repo,
    ).stdout
    match = re.search(r"\b(TASK-[0-9]{4,})\b", start_out)
    assert match is not None, start_out
    task_id = match.group(1)

    _write_spec(repo, task_id)
    facts_file = outside_dir / "facts.json"
    facts_file.write_text(json.dumps(_facts_payload(review=review)), encoding="utf-8")
    _run(
        [
            python_exe,
            "-m",
            "aiflow",
            "facts",
            task_id,
            "--decision-unit",
            "DU-001",
            "--input",
            str(facts_file),
            "--actor",
            "planner",
        ],
        cwd=repo,
    )
    _run([python_exe, "-m", "aiflow", "classify", task_id, "--actor", "classifier"], cwd=repo)
    _run([python_exe, "-m", "aiflow", "freeze", task_id, "--actor", "specifier"], cwd=repo)

    if review:
        _record_review(python_exe, repo, outside_dir, task_id, stage="design", review_id="REV-0001")
        _run(
            [
                python_exe,
                "-m",
                "aiflow",
                "approve",
                task_id,
                "--type",
                "spec",
                "--actor",
                "reviewer",
                "--reason",
                "design approved",
            ],
            cwd=repo,
        )

    _run([python_exe, "-m", "aiflow", "begin", task_id, "--actor", "implementer"], cwd=repo)

    (repo / "src" / "sample_pkg" / "__init__.py").write_text(
        '"""External sample package."""\n\n\n'
        "def classify_sign(value: int) -> str:\n"
        '    """Return sign label."""\n'
        "    if value >= 0:\n"
        '        return "non-negative"\n'
        '    return "negative"\n\n\n'
        "def parity_label(value: int) -> str:\n"
        '    """Return parity label for value."""\n'
        "    if value % 2 == 0:\n"
        '        return "even"\n'
        '    return "odd"\n',
        encoding="utf-8",
    )
    (repo / "tests" / "test_sample.py").write_text(
        "from sample_pkg import classify_sign, parity_label\n\n\n"
        "def test_classify_sign() -> None:\n"
        '    assert classify_sign(1) == "non-negative"\n'
        '    assert classify_sign(-1) == "negative"\n\n\n'
        "def test_parity_label() -> None:\n"
        '    assert parity_label(2) == "even"\n'
        '    assert parity_label(3) == "odd"\n',
        encoding="utf-8",
    )
    _run(["git", "add", "src/sample_pkg/__init__.py", "tests/test_sample.py"], cwd=repo)
    _run(
        [
            "git",
            "-c",
            "user.name=External Repo",
            "-c",
            "user.email=external@example.invalid",
            "commit",
            "-m",
            "add parity_label helper",
        ],
        cwd=repo,
    )
    _run([python_exe, "-m", "aiflow", "sync", task_id, "--actor", "implementer"], cwd=repo)
    _run([python_exe, "-m", "aiflow", "verify", task_id, "--actor", "verifier"], cwd=repo)

    evidence = json.loads(
        (repo / ".ai" / "tasks" / task_id / "evidence.json").read_text(encoding="utf-8")
    )
    assert evidence["conclusion"] == "passed", json.dumps(evidence, indent=2)
    assert evidence["verification_level"] == ("V1" if review else "V0")
    assert all(check["status"] == "passed" for check in evidence["checks"])
    assert not (repo / ".coverage").exists()
    assert not (repo / "coverage.xml").exists()
    if review:
        log_parent = Path(evidence["checks"][0]["stdout_log_ref"]).parent
        run_dir = repo / ".ai" / "tasks" / task_id / log_parent
        assert (run_dir / "coverage.xml").is_file()
        assert (run_dir / "coverage-target.xml").is_file()
    return task_id


def _complete_final_review_and_gate(
    python_exe: str,
    repo: Path,
    outside_dir: Path,
    task_id: str,
    *,
    review: bool,
) -> None:
    if review:
        (repo / ".ai" / "tasks" / task_id / "review-package.md").write_text(
            "# Review Package\n\n"
            "## 审核目标\n\nAccept external Python verification change.\n\n"
            "## 背景\n\nExternal repo uses portable Python coverage checks.\n\n"
            "## 代码地图\n\n- `src/sample_pkg/__init__.py`: added `parity_label`.\n\n"
            "## 语义变更\n\nAdded `parity_label` and unit tests.\n\n"
            "## 风险\n\nLow risk.\n\n"
            "## 证据\n\n- 已验证：V1 verification passed.\n- 未验证：None.\n\n"
            "## 审核问题\n\n- Does implementation match spec?\n\n"
            "## 推荐结论\n\nAPPROVE\n",
            encoding="utf-8",
        )
        _record_review(
            python_exe, repo, outside_dir, task_id, stage="implementation", review_id="REV-0002"
        )
        _run(
            [
                python_exe,
                "-m",
                "aiflow",
                "approve",
                task_id,
                "--type",
                "code",
                "--actor",
                "reviewer",
                "--reason",
                "implementation approved",
            ],
            cwd=repo,
        )

    gate_out = _run(
        [python_exe, "-m", "aiflow", "gate", task_id, "--format", "json"],
        cwd=repo,
    ).stdout
    gate_payload = json.loads(gate_out)
    assert gate_payload["passed"] is True
    assert gate_payload["reason_codes"] == []


@pytest.mark.parametrize("review", [False, True], ids=["V0", "V1"])
def test_external_python_repo_full_verify_and_gate_pass(
    tmp_path: Path, isolated_python: str, review: bool
) -> None:
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    repo = tmp_path / "external_repo"
    _init_external_repo(repo)
    assert not (repo / "src" / "aiflow").exists()
    assert not (repo / "tools").exists()

    task_id = _run_lifecycle_through_verify(isolated_python, repo, outside_dir, review=review)
    _complete_final_review_and_gate(isolated_python, repo, outside_dir, task_id, review=review)


def _initialize_and_verify_external_repo(
    tmp_path: Path,
    isolated_python: str,
    outside_dir: Path,
    bundle_root: Path | None,
    policy_dir: Path,
) -> None:
    repo = tmp_path / "external_repo"
    _init_external_repo(repo, with_ai=False, branch=None)
    assert not (repo / ".ai").exists()
    assert not (repo / "src" / "aiflow").exists()
    assert not (repo / "tools").exists()

    preview_cmd = [
        isolated_python,
        "-m",
        "aiflow",
        "init",
        "preview",
        "--target",
        str(repo),
        "--profile",
        "native-python-v1",
        "--policy-candidate-root",
        str(policy_dir),
    ]
    if bundle_root is not None:
        preview_cmd.extend(["--bundle-root", str(bundle_root)])
    preview_out = _run(preview_cmd, cwd=outside_dir).stdout
    candidate = json.loads(preview_out)
    assert candidate["kind"] == "aiflow-init-preview"
    assert candidate["profile"] == "native-python-v1"

    preview_path = outside_dir / "preview.json"
    review_path = outside_dir / "policy-review.json"
    preview_path.write_text(preview_out, encoding="utf-8")
    review_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "kind": "aiflow-policy-review",
                "preview_sha256": candidate["preview_sha256"],
                "repository_id": candidate["repository_id"],
                "profile": candidate["profile"],
                "policy_version": candidate["policy"]["policy_version"],
                "policies": [
                    {"path": entry["path"], "sha256": entry["sha256"]}
                    for entry in candidate["policy"]["files"]
                ],
                "reviewer": "independent-policy-reviewer",
                "outcome": "APPROVE",
            }
        ),
        encoding="utf-8",
    )

    apply_cmd = [
        isolated_python,
        "-m",
        "aiflow",
        "init",
        "apply",
        "--target",
        str(repo),
        "--preview",
        str(preview_path),
        "--policy-review",
        str(review_path),
        "--policy-candidate-root",
        str(policy_dir),
    ]
    if bundle_root is not None:
        apply_cmd.extend(["--bundle-root", str(bundle_root)])
    apply_out = _run(apply_cmd, cwd=outside_dir).stdout
    apply_payload = json.loads(apply_out)
    assert apply_payload["phase"] == "installed"
    assert apply_payload["repository_id"] == candidate["repository_id"]
    assert (repo / ".ai" / "repository-id").read_text(encoding="utf-8").strip() != (
        ROOT / ".ai" / "repository-id"
    ).read_text(encoding="utf-8").strip()
    assert not (repo / ".ai" / "bootstrap-mode.yaml").exists()

    inspect_out = _run(
        [isolated_python, "-m", "aiflow", "init", "inspect", "--target", str(repo)],
        cwd=outside_dir,
    ).stdout
    inspect_payload = json.loads(inspect_out)
    assert inspect_payload["status"] == "complete"
    assert inspect_payload["repository_id"] == candidate["repository_id"]

    _run(["git", "add", ".ai"], cwd=repo)
    _run(
        [
            "git",
            "-c",
            "user.name=External Repo",
            "-c",
            "user.email=external@example.invalid",
            "commit",
            "-m",
            "initialize aiflow",
        ],
        cwd=repo,
    )
    _run(["git", "switch", "-c", "feat/external-change"], cwd=repo)

    task_id = _run_lifecycle_through_verify(isolated_python, repo, outside_dir, review=True)

    before_advise = _snapshot_tree(repo / ".ai")
    advise_out = _run(
        [isolated_python, "-m", "aiflow", "advise", task_id, "--format", "json"],
        cwd=repo,
    ).stdout
    assert _snapshot_tree(repo / ".ai") == before_advise
    advise_payload = json.loads(advise_out)
    assert advise_payload["execution_allowed"] is False
    assert advise_payload["probability_status"] == "unestimated"
    assert any(
        item["category"] == "residual_human_decision" and item["condition"] == "code_approval"
        for item in advise_payload["advice_items"]
    )

    _complete_final_review_and_gate(isolated_python, repo, outside_dir, task_id, review=True)


def test_initialized_external_python_repo_verify_advise_and_gate_pass(
    tmp_path: Path, isolated_python: str
) -> None:
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    bundle_root = _build_local_bundle(outside_dir / "bundle")
    policy_dir = _create_portable_policy_dir(outside_dir / "policy")
    _initialize_and_verify_external_repo(
        tmp_path, isolated_python, outside_dir, bundle_root, policy_dir
    )


def test_rendered_python_policy_external_repo_verify_advise_and_gate_pass(
    tmp_path: Path, isolated_python: str
) -> None:
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    bundle_root = _build_local_bundle(outside_dir / "bundle")
    policy_dir = outside_dir / "rendered-policy"

    render_out = _run(
        [
            isolated_python,
            "-m",
            "aiflow",
            "init",
            "render-python-policy",
            "--output-dir",
            str(policy_dir),
            "--cov-target",
            "sample_pkg",
            "--source",
            "src/sample_pkg",
            "--bundle-root",
            str(bundle_root),
        ],
        cwd=outside_dir,
    ).stdout
    rendered = json.loads(render_out)
    assert rendered["kind"] == "aiflow-rendered-python-policy"
    assert rendered["cov_target"] == "sample_pkg"
    assert rendered["sources"] == ["src/sample_pkg"]

    _initialize_and_verify_external_repo(
        tmp_path, isolated_python, outside_dir, bundle_root, policy_dir
    )


def test_built_wheel_external_python_repo_verify_advise_and_gate_pass(
    tmp_path: Path, built_wheel_python: tuple[str, Path]
) -> None:
    python_exe, venv_dir = built_wheel_python
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    _run(
        [
            python_exe,
            "-c",
            (
                "import sys; from pathlib import Path; import aiflow; "
                "pkg = Path(aiflow.__file__).resolve(); "
                "assert pkg.is_relative_to(Path(sys.argv[1]).resolve()), pkg; "
                "assert (pkg.parent / '_bundled_resources' / 'manifest.json').is_file()"
            ),
            str(venv_dir),
        ],
        cwd=outside_dir,
    )

    policy_dir = outside_dir / "rendered-policy"
    render_out = _run(
        [
            python_exe,
            "-m",
            "aiflow",
            "init",
            "render-python-policy",
            "--output-dir",
            str(policy_dir),
            "--cov-target",
            "sample_pkg",
            "--source",
            "src/sample_pkg",
        ],
        cwd=outside_dir,
    ).stdout
    rendered = json.loads(render_out)
    assert rendered["kind"] == "aiflow-rendered-python-policy"
    assert rendered["cov_target"] == "sample_pkg"
    assert rendered["sources"] == ["src/sample_pkg"]

    _initialize_and_verify_external_repo(tmp_path, python_exe, outside_dir, None, policy_dir)
