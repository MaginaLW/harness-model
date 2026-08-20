"""Shared real-service support for the four Chapter 7 golden scenarios."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from aiflow import verification_service
from aiflow.cli import main
from aiflow.scenarios import prepare_scenario_repository
from aiflow.storage import (
    atomic_write_json,
    atomic_write_yaml,
    read_task_json,
    read_task_yaml,
    resolve_task_path,
)
from aiflow.task_service import load_task_record
from aiflow.verification import (
    V0_CHECK_IDS,
    V1_CHECK_IDS,
    VerificationCheck,
    VerificationContext,
    VerificationExecution,
    VerificationPlan,
)

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "TASK-0001"


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result.stdout.strip()


def scenario_input(scenario_id: str) -> dict[str, Any]:
    value = yaml.safe_load(
        (ROOT / "examples" / "scenarios" / scenario_id / "input.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    value = deepcopy(value)
    value["task_id"] = TASK_ID
    return value


def scenario_expected(scenario_id: str) -> dict[str, Any]:
    value = json.loads(
        (ROOT / "examples" / "scenarios" / scenario_id / "expected.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(value, dict)
    return value


def complete_spec(unit: dict[str, Any]) -> str:
    scope = "\n".join(f"- `{path}`" for path in unit["impact_scope"])
    return f"""# Task Specification

## 目标

{unit["goal"]}

## 范围

{scope}

## 非目标

不执行网络、推送、合并、部署或真实外部动作。

## 验收条件

分类、验证证据和 Gate 结论均绑定当前任务版本。

## 禁止动作

不得修改声明范围以外的业务文件。

## 错误行为

缺少回答、批准、备份或验证证据时必须拒绝推进。

## 回滚

仅通过新的本地提交恢复已声明的可逆变更。
"""


def prepare_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario_id: str,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    prepared = prepare_scenario_repository(ROOT, tmp_path / scenario_id, scenario_id)
    repository = prepared.root
    monkeypatch.chdir(repository)
    unit = scenario_input(scenario_id)
    expected = scenario_expected(scenario_id)
    arguments = ["start", "--objective", str(unit["goal"])]
    for scope in unit["impact_scope"]:
        arguments.extend(("--allow", str(scope)))
    assert main(arguments) == 0
    task = read_task_yaml(repository, TASK_ID, "task.yaml", contract_name="task")
    assert isinstance(task, dict)
    task["decision_units"] = [unit]
    atomic_write_yaml(resolve_task_path(repository, TASK_ID, "task.yaml"), task)
    resolve_task_path(repository, TASK_ID, "spec.md").write_text(
        complete_spec(unit), encoding="utf-8"
    )
    return repository, unit, expected


def install_compact_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    def build(_bundle: object, context: VerificationContext, *, level: str) -> VerificationPlan:
        check_ids = V0_CHECK_IDS if level == "V0" else V1_CHECK_IDS
        run_dir = (
            context.repository_root / ".ai" / "tasks" / context.task_id / "logs" / context.run_id
        ).resolve()
        argv = (sys.executable, "-c", "print('golden-checks-passed')")
        checks = tuple(
            VerificationCheck(
                check_id,
                level,
                argv,
                {},
                context.repository_root.resolve(),
                10,
                True,
                "exit_zero",
            )
            for check_id in check_ids
        )
        execution = VerificationExecution(
            "EXEC-GOLDEN", argv, {}, checks[0].cwd, 10, tuple(check_ids)
        )
        return VerificationPlan(
            level,
            run_dir,
            checks,
            (execution,),
            (),
            (),
            context.subject_commit,
        )

    monkeypatch.setattr(verification_service, "parse_verification_plan", build)


def commit_implementation(repository: Path, files: dict[str, str], message: str) -> str:
    for relative, content in files.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        git(repository, "add", relative)
    git(
        repository,
        "-c",
        "user.name=Golden Scenario",
        "-c",
        "user.email=golden@example.invalid",
        "commit",
        "-m",
        message,
    )
    return git(repository, "rev-parse", "HEAD")


def classification(repository: Path) -> dict[str, Any]:
    value = read_task_json(
        repository, TASK_ID, "classification.json", contract_name="classification"
    )
    assert isinstance(value, dict)
    return value


def evidence(repository: Path) -> dict[str, Any]:
    value = read_task_json(repository, TASK_ID, "evidence.json", contract_name="evidence")
    assert isinstance(value, dict)
    return value


def approvals(repository: Path) -> list[dict[str, Any]]:
    value = read_task_json(repository, TASK_ID, "approvals.json")
    assert isinstance(value, list) and all(isinstance(item, dict) for item in value)
    return value


def state(repository: Path) -> str:
    return str(load_task_record(repository, TASK_ID).task["current_state"])


def review_package() -> str:
    return """# Review Package

## 审核目标

确认实现满足已冻结规格并可进入 Gate。

## 背景

本变更来自 Chapter 7 的隔离黄金场景。

## 代码地图

- `.github/workflows/ai-quality-gate.yml`：受审工作流。

## 语义变更

调整质量门的受控行为。

## 风险

错误配置会影响持续集成，已用版本绑定验证缓解。

## 证据

- 已验证：V1 必需类别全部通过。
- 未验证：未执行任何真实外部动作。

## 审核问题

- 实现是否符合冻结规格和当前 Policy？

## 推荐结论

APPROVE
"""


def write_options(repository: Path, expected: dict[str, Any]) -> Path:
    path = resolve_task_path(repository, TASK_ID, "ask-options.json")
    atomic_write_json(
        path,
        {
            "schema_version": "1.0",
            "task_id": TASK_ID,
            "decision_unit_id": "DU-102",
            "generated_at": "2026-08-21T00:00:00Z",
            "options": expected["options"],
        },
    )
    return path
