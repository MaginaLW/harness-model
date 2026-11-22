from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from aiflow.gate import GateFacts, evaluate_gate_facts
from tools.ci.resolve_task import _bootstrap_active, classify_pr, main, resolve_task_id

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ai-quality-gate.yml"


def _workflow() -> dict[str, object]:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True, timeout=20
    )
    return result.stdout.strip()


def _attach_event_head_to_source_branch(root: Path, source_branch: str, event_head: str) -> None:
    """Run the workflow's fail-closed branch-attachment contract locally."""
    if not source_branch:
        raise ValueError("PR source branch must be nonempty")
    _git(root, "check-ref-format", "--branch", source_branch)
    if _git(root, "rev-parse", "HEAD") != event_head:
        raise ValueError("checkout HEAD does not match the event head")
    _git(root, "switch", "--force-create", source_branch, event_head)
    if _git(root, "symbolic-ref", "--quiet", "--short", "HEAD") != source_branch:
        raise ValueError("attached branch does not match the PR source branch")
    if _git(root, "rev-parse", "HEAD") != event_head:
        raise ValueError("attached branch changed the event head")


def _repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "checkout"
    root.mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.email", "ci@example.invalid")
    _git(root, "config", "user.name", "CI")
    (root / ".ai").mkdir()
    (root / ".ai" / "repository-id").write_text("repo-stable\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "base")
    return root, _git(root, "rev-parse", "HEAD")


def test_workflow_is_read_only_reproducible_and_bounded() -> None:
    workflow = _workflow()
    text = WORKFLOW.read_text(encoding="utf-8")

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["on"]["pull_request"]["types"] == [
        "opened",
        "synchronize",
        "reopened",
        "ready_for_review",
    ]
    assert "pull_request_target" not in text
    assert "cancel-in-progress: true" in text
    assert "timeout-minutes: 90" in text
    assert "fetch-depth: 0" in text
    assert 'python-version: "3.11"' in text
    assert "actions/checkout@v7" in text
    assert "actions/setup-python@v7" in text
    assert "astral-sh/setup-uv@v10.0.1" in text
    assert 'version: "0.12.5"' in text
    assert "uv lock --check" in text
    assert "uv sync --locked --all-extras" in text
    assert "uv run --locked python -m pytest" in text
    assert "retention-days: 14" in text
    assert "write" not in str(workflow["permissions"])


def test_workflow_attaches_exact_event_head_to_the_pr_source_branch() -> None:
    workflow = _workflow()
    steps = workflow["jobs"]["ai-quality-gate"]["steps"]
    assert isinstance(steps, list)

    marker, checkout = steps[:2]
    assert marker == {
        "name": "Replay request merge=${{ github.sha }} workflow=${{ github.workflow_sha }}",
        "run": ":",
    }
    assert sum(step.get("name") == marker["name"] for step in steps) == 1
    assert checkout["uses"] == "actions/checkout@v7"
    assert checkout["with"] == {
        "fetch-depth": "0",
        "ref": "${{ github.event.pull_request.head.sha }}",
    }

    names = [step.get("name") for step in steps]
    governance_index = names.index("Resolve PR governance")
    attachment_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("env")
        == {
            "PR_HEAD_REF": "${{ github.head_ref }}",
            "PR_HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
        }
    )
    assert governance_index < attachment_index < names.index("Verify and Gate")

    attachment = steps[attachment_index]
    assert attachment["if"] == "steps.governance.outputs.task_id != ''"
    contracts = steps[names.index("Validate contracts")]
    assert contracts["if"] == "steps.governance.outputs.task_id != ''"
    assert governance_index < names.index("Validate contracts")
    assert attachment["env"] == {
        "PR_HEAD_REF": "${{ github.head_ref }}",
        "PR_HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
    }
    assert attachment["shell"] == "bash"

    commands = [
        'test -n "$PR_HEAD_REF"',
        'git check-ref-format --branch "$PR_HEAD_REF"',
        'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
        'git switch --force-create "$PR_HEAD_REF" "$PR_HEAD_SHA"',
        'test "$(git symbolic-ref --quiet --short HEAD)" = "$PR_HEAD_REF"',
        'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"',
    ]
    script = attachment["run"]
    assert isinstance(script, str)
    position = 0
    for command in commands:
        position = script.index(command, position) + len(command)
    assert "git fetch" not in script
    assert "git push" not in script


def test_branch_attachment_preserves_detached_exact_event_head(tmp_path: Path) -> None:
    root, _ = _repo(tmp_path)
    (root / "head.txt").write_text("event head\n", encoding="utf-8")
    _git(root, "add", "head.txt")
    _git(root, "commit", "-m", "event head")
    event_head = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "--detach", event_head)

    _attach_event_head_to_source_branch(root, "feature/task-0030", event_head)

    assert _git(root, "rev-parse", "HEAD") == event_head
    assert _git(root, "symbolic-ref", "--quiet", "--short", "HEAD") == "feature/task-0030"


@pytest.mark.parametrize("source_branch", ["", "bad branch", "refs/heads/"])
def test_branch_attachment_rejects_empty_or_invalid_source_branch(
    tmp_path: Path, source_branch: str
) -> None:
    root, event_head = _repo(tmp_path)

    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        _attach_event_head_to_source_branch(root, source_branch, event_head)


def test_branch_attachment_rejects_initial_event_head_mismatch(tmp_path: Path) -> None:
    root, base = _repo(tmp_path)
    (root / "head.txt").write_text("event head\n", encoding="utf-8")
    _git(root, "add", "head.txt")
    _git(root, "commit", "-m", "event head")
    _git(root, "checkout", "--detach", "HEAD")

    with pytest.raises(ValueError, match="checkout HEAD"):
        _attach_event_head_to_source_branch(root, "feature/task-0030", base)


def test_branch_attachment_rejects_switch_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, event_head = _repo(tmp_path)
    _git(root, "checkout", "--detach", event_head)
    original_git = _git

    def failed_switch(path: Path, *args: str) -> str:
        if args[:2] == ("switch", "--force-create"):
            raise subprocess.CalledProcessError(128, ["git", *args])
        return original_git(path, *args)

    with monkeypatch.context() as patched:
        patched.setitem(globals(), "_git", failed_switch)
        with pytest.raises(subprocess.CalledProcessError):
            _attach_event_head_to_source_branch(root, "feature/task-0030", event_head)


def test_branch_attachment_rejects_post_switch_branch_or_sha_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, event_head = _repo(tmp_path)
    _git(root, "checkout", "--detach", event_head)
    original_git = _git

    def wrong_branch(path: Path, *args: str) -> str:
        if args == ("symbolic-ref", "--quiet", "--short", "HEAD"):
            return "different-branch"
        return original_git(path, *args)

    with monkeypatch.context() as patched:
        patched.setitem(globals(), "_git", wrong_branch)
        with pytest.raises(ValueError, match="attached branch"):
            _attach_event_head_to_source_branch(root, "feature/task-0030", event_head)

    _git(root, "checkout", "--detach", event_head)
    rev_parse_calls = 0

    def changed_head(path: Path, *args: str) -> str:
        nonlocal rev_parse_calls
        if args == ("rev-parse", "HEAD"):
            rev_parse_calls += 1
            if rev_parse_calls == 2:
                return "0" * 40
        return original_git(path, *args)

    with monkeypatch.context() as patched:
        patched.setitem(globals(), "_git", changed_head)
        with pytest.raises(ValueError, match="changed the event head"):
            _attach_event_head_to_source_branch(root, "feature/task-0030", event_head)


def test_governance_outputs_feed_verify_closeout_and_maintenance_checks() -> None:
    steps = {step.get("name"): step for step in _workflow()["jobs"]["ai-quality-gate"]["steps"]}
    governance = steps["Resolve PR governance"]
    assert governance["id"] == "governance"
    assert "tools/ci/resolve_task.py --route" in governance["run"]
    assert "github.event.pull_request.base.sha" in governance["run"]
    assert "github.event.pull_request.head.sha" in governance["run"]

    verify = steps["Verify and Gate"]
    assert verify["if"] == "steps.governance.outputs.task_id != ''"
    assert verify["env"]["TASK_ID"] == "${{ steps.governance.outputs.task_id }}"
    assert verify["env"]["TMPDIR"] == "${{ runner.temp }}"
    assert 'run_dir="$TMPDIR/aiflow"' in verify["run"]
    ordered = [
        'aiflow verify "$TASK_ID" --ci --ci-run-dir "$run_dir" --output "$run_dir/evidence.json"',
        'aiflow gate "$TASK_ID" --evidence "$run_dir/evidence.json"',
        'echo "level=$level" >> "$GITHUB_OUTPUT"',
    ]
    assert [verify["run"].index(command) for command in ordered] == sorted(
        verify["run"].index(command) for command in ordered
    )
    assert (
        steps["Upload AI Flow diagnostics"]["if"]
        == "always() && steps.governance.outputs.task_id != ''"
    )
    closeout = steps["Validate retained task records"]
    assert 'aiflow validate "$task"' in closeout["run"]
    assert (
        'tools.ci.verify_closeout --base "$BASE_SHA" --head "$HEAD_SHA" --task "$task"'
        in closeout["run"]
    )

    quality = steps["Maintenance quality checks"]
    assert quality["if"] == "steps.governance.outputs.bootstrap_active == 'true'"
    assert quality["env"]["VERIFIED_LEVEL"] == "${{ steps.verify.outputs.level }}"
    script = quality["run"]
    assert 'coverage_dir="$RUNNER_TEMP/aiflow"' in script
    fallback = script.index('if [[ "$VERIFIED_LEVEL" != V1 && "$VERIFIED_LEVEL" != V2 ]]')
    assert fallback < script.index("--cov=aiflow --cov-branch") < script.index("\nfi\n")
    assert script.index("\nfi\n") < script.index(
        'check_coverage.py --run-dir "$coverage_dir" --base "$BASE_SHA"'
    )
    assert 'git diff --check "$BASE_SHA..$HEAD_SHA"' in script
    assert (
        "ruff check ." in script
        and "ruff format --check ." in script
        and "uv run --locked mypy" in script
    )


@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        (None, False),
        ("mode: bootstrap_auto\nstatus: active\n", True),
        ("mode: bootstrap_auto\nstatus: disabled\n", False),
        ('mode: "bootstrap_auto"\nstatus: "active"\n', False),
    ],
)
def test_bootstrap_detection_is_canonical_and_fail_closed(
    tmp_path: Path, marker: str | None, expected: bool
) -> None:
    root, _ = _repo(tmp_path)
    if marker is not None:
        (root / ".ai" / "bootstrap-mode.yaml").write_text(marker, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "--allow-empty", "-m", "marker state")

    assert _bootstrap_active(root, _git(root, "rev-parse", "HEAD")) is expected


def test_base_commit_controls_bootstrap_transition(tmp_path: Path) -> None:
    exiting, _ = _repo(tmp_path / "exit")
    exit_marker = exiting / ".ai" / "bootstrap-mode.yaml"
    exit_marker.write_text("mode: bootstrap_auto\nstatus: active\n", encoding="utf-8")
    _git(exiting, "add", "-A")
    _git(exiting, "commit", "-m", "activate bootstrap")
    active_base = _git(exiting, "rev-parse", "HEAD")
    exit_marker.unlink()
    _git(exiting, "add", "-A")
    _git(exiting, "commit", "-m", "exit bootstrap")
    exit_head = _git(exiting, "rev-parse", "HEAD")

    entering, inactive_base = _repo(tmp_path / "enter")
    (entering / ".ai" / "bootstrap-mode.yaml").write_text(
        "mode: bootstrap_auto\nstatus: active\n", encoding="utf-8"
    )
    _git(entering, "add", "-A")
    _git(entering, "commit", "-m", "attempt bootstrap")
    entering_head = _git(entering, "rev-parse", "HEAD")

    assert _bootstrap_active(exiting, active_base) is True
    assert _bootstrap_active(exiting, exit_head) is False
    assert _bootstrap_active(entering, inactive_base) is False
    assert _bootstrap_active(entering, entering_head) is True


@pytest.mark.parametrize("count", [0, 1, 2])
def test_diff_task_resolution_requires_exactly_one(tmp_path: Path, count: int) -> None:
    root, base = _repo(tmp_path)
    for index in range(count):
        task = root / ".ai" / "tasks" / f"TASK-000{index + 1}"
        task.mkdir(parents=True)
        (task / "task.yaml").write_text("task\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "--allow-empty", "-m", "head")
    head = _git(root, "rev-parse", "HEAD")

    if count == 1:
        assert resolve_task_id(root, base, head) == "TASK-0001"
    else:
        with pytest.raises(ValueError, match="exactly one"):
            resolve_task_id(root, base, head)


def test_explicit_task_depends_on_repository_identity_not_checkout_path(tmp_path: Path) -> None:
    first, base = _repo(tmp_path / "one")
    second, _ = _repo(tmp_path / "two")
    for root in (first, second):
        (root / ".ai" / "tasks" / "TASK-0001").mkdir(parents=True)

    assert resolve_task_id(first, base, base, "TASK-0001") == "TASK-0001"
    assert resolve_task_id(second, base, base, "TASK-0001") == "TASK-0001"
    assert first.resolve() != second.resolve()


def test_non_governance_tail_is_rejected_by_shared_gate() -> None:
    decision = evaluate_gate_facts(
        GateFacts(
            task_id="TASK-0001",
            current_state="APPROVED_FOR_MERGE",
            route="AUTO",
            verification_level="V0",
            scope_current=False,
        )
    )

    assert decision.passed is False
    assert "GATE_SCOPE_CHANGED" in decision.reason_codes


def test_diff_task_resolution_ignores_task_directories_only_on_the_base(tmp_path: Path) -> None:
    """An advancing base branch must not add its own task directories to the diff."""
    root, fork_point = _repo(tmp_path)

    _git(root, "checkout", "-b", "advanced-base")
    base_task = root / ".ai" / "tasks" / "TASK-0002"
    base_task.mkdir(parents=True)
    (base_task / "task.yaml").write_text("task\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "base advances with another task")
    advanced_base = _git(root, "rev-parse", "HEAD")

    _git(root, "checkout", "-b", "feature", fork_point)
    head_task = root / ".ai" / "tasks" / "TASK-0001"
    head_task.mkdir(parents=True)
    (head_task / "task.yaml").write_text("task\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "head introduces its own task")
    head = _git(root, "rev-parse", "HEAD")

    assert resolve_task_id(root, advanced_base, head) == "TASK-0001"


def test_diff_task_resolution_still_rejects_two_tasks_introduced_by_the_head(
    tmp_path: Path,
) -> None:
    root, fork_point = _repo(tmp_path)

    _git(root, "checkout", "-b", "advanced-base")
    base_task = root / ".ai" / "tasks" / "TASK-0003"
    base_task.mkdir(parents=True)
    (base_task / "task.yaml").write_text("task\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "base advances")
    advanced_base = _git(root, "rev-parse", "HEAD")

    _git(root, "checkout", "-b", "feature", fork_point)
    for identifier in ("TASK-0001", "TASK-0002"):
        task = root / ".ai" / "tasks" / identifier
        task.mkdir(parents=True)
        (task / "task.yaml").write_text("task\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "head introduces two tasks")
    head = _git(root, "rev-parse", "HEAD")

    with pytest.raises(ValueError, match="exactly one"):
        resolve_task_id(root, advanced_base, head)


def _active_base(root: Path) -> str:
    marker = root / ".ai" / "bootstrap-mode.yaml"
    marker.write_text("mode: bootstrap_auto\nstatus: active\n", encoding="utf-8")
    policy = root / ".ai" / "policy" / "hard-rules.yaml"
    policy.parent.mkdir()
    policy.write_bytes((ROOT / ".ai" / "policy" / "hard-rules.yaml").read_bytes())
    _git(root, "add", ".")
    _git(root, "commit", "-m", "enable maintenance")
    return _git(root, "rev-parse", "HEAD")


def _set_task_state(root: Path, identifier: str, state: str) -> None:
    path = root / ".ai" / "tasks" / identifier / "task.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"task_id: {identifier}\ncurrent_state: {state}\n", encoding="utf-8")


def test_router_distinguishes_maintenance_docs_and_governance_renames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = _repo(tmp_path)
    base = _active_base(root)
    governed = root / ".github" / "CODEOWNERS"
    governed.parent.mkdir()
    governed.write_text("initial\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "tracked governance file")
    base = _git(root, "rev-parse", "HEAD")
    (root / "README.md").write_text("guide\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "ordinary docs")
    head = _git(root, "rev-parse", "HEAD")
    monkeypatch.chdir(root)
    output = tmp_path / "output"
    assert main(["--route", "--base", base, "--head", head, "--output", str(output)]) == 0
    assert output.read_text(encoding="utf-8").splitlines() == [
        "bootstrap_active=true",
        "task_id=",
        "closeouts=",
        "retained=",
    ]
    _git(root, "mv", ".github/CODEOWNERS", "guide.md")
    _git(root, "commit", "-m", "move former governance file")
    with pytest.raises(ValueError, match="implementation task"):
        classify_pr(root, base, _git(root, "rev-parse", "HEAD"))


def test_router_requires_formal_task_for_docs_outside_maintenance(tmp_path: Path) -> None:
    root, base = _repo(tmp_path)
    (root / "README.md").write_text("documentation\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "docs")
    with pytest.raises(ValueError, match="implementation task"):
        classify_pr(root, base, _git(root, "rev-parse", "HEAD"))


def test_router_separates_implementation_from_multiple_closeouts_and_failed_attempt(
    tmp_path: Path,
) -> None:
    root, _ = _repo(tmp_path)
    base = _active_base(root)
    _set_task_state(root, "TASK-0001", "MERGED")
    _set_task_state(root, "TASK-0002", "MERGED")
    (root / "README.md").write_text("documentation\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "close two tasks")
    close_head = _git(root, "rev-parse", "HEAD")
    _set_task_state(root, "TASK-0001", "NEW")  # Routing reads the named commit.
    route = classify_pr(root, base, close_head)
    assert route.task_id is None and route.closeouts == ("TASK-0001", "TASK-0002")
    _git(root, "restore", ".ai/tasks/TASK-0001/task.yaml")
    _set_task_state(root, "TASK-0003", "FAILED")
    _set_task_state(root, "TASK-0004", "APPROVED_FOR_MERGE")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "deliver implementation and retain failed attempt")
    head = _git(root, "rev-parse", "HEAD")
    route = classify_pr(root, base, head)
    assert route.task_id == "TASK-0004" and route.retained == ("TASK-0003",)
    assert route.closeouts == ("TASK-0001", "TASK-0002")
    with pytest.raises(ValueError, match="not an implementation candidate"):
        classify_pr(root, base, head, "TASK-0001")
    _set_task_state(root, "TASK-0005", "APPROVED_FOR_MERGE")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "additional implementation candidate")
    ambiguous = _git(root, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="if ambiguous"):
        classify_pr(root, base, ambiguous)
    assert classify_pr(root, base, ambiguous, "TASK-0005").task_id == "TASK-0005"


@pytest.mark.parametrize(
    "earlier_file", ["README.md", "src/aiflow/version.py", "src/aiflow/old.py"]
)
def test_pr_route_checks_the_implementation_range(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    earlier_file: str,
) -> None:
    root, _ = _repo(tmp_path)
    base = _active_base(root)
    version = root / "src" / "aiflow" / "version.py"
    version.parent.mkdir(parents=True)
    (root / earlier_file).write_text("first revision\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "work before task creation")
    task_base = _git(root, "rev-parse", "HEAD")
    task = "TASK-0007"
    _set_task_state(root, task, "APPROVED_FOR_MERGE")
    with (root / ".ai" / "tasks" / task / "task.yaml").open("a", encoding="utf-8") as stream:
        stream.write(f"base_commit: {task_base}\n")
    if earlier_file == "src/aiflow/old.py":
        (root / earlier_file).rename(version)
    else:
        version.write_text("reviewed revision\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "record the reviewed candidate")
    head = _git(root, "rev-parse", "HEAD")
    monkeypatch.chdir(root)
    result = main(["--route", "--base", base, "--head", head])
    output = capsys.readouterr()
    if earlier_file == "README.md":
        assert result == 0 and f"task_id={task}" in output.out
    else:
        assert result == 1 and f"PR changes precede task base: {earlier_file}" in output.err
