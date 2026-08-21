# 阶段一验收报告

## 结论

阶段一十二项验收全部 `passed`，本地发布基线版本为 `0.1.0`。本结论是仓库内可安装、可验证、可审计的 MVP 基线，不代表已执行 push、merge、deploy、tag 或 package publish。

逐项实现、定向测试、命令、证据和限制见 [阶段一验收矩阵](phase-01-acceptance-matrix.md)；矩阵的自动追踪测试为 `tests/integration/test_acceptance_traceability.py`。

| 范围 | 结论 | 权威证据 |
|---|---|---|
| ACC-01—ACC-09：任务、分流、治理、失效、验证、CI 和升级 | passed | `docs/implementation/phase-01-acceptance-matrix.md` 及各行定向测试 |
| ACC-10：AUTO/ASK/REVIEW/BLOCK 真实试点 | passed | `docs/pilots/results/PILOT-*/result.md`、`../harness-model-pilot-artifacts/PILOT-*/` |
| ACC-11：本地/CI 一致性 | passed | `tests/integration/test_gate_parity.py`、`docs/implementation/chapter-06-agent-ci.md` |
| ACC-12：干净检出安装、测试和示例 | passed | `tests/e2e/test_clean_checkout.py`、`docs/operations/quickstart.md`、`../harness-model-pilot-artifacts/TASK-0002/` |

## 四个真实受控试点

| 试点 | 分支 | subject | attestation HEAD | 结论 |
|---|---|---|---|---|
| AUTO | `pilot/auto-doc` | `2b1900a0207d106147d21e0d9c7e85a8d450fa4b` | `7f73a6de232fb362ece6021a868cf1d3013dbe0f` | V0、CI 和 Gate passed，无批准 |
| ASK | `pilot/ask-report` | `e72e5f17d01216210bb05f3811c5ac0c78ec1766` | `74d4d1570249273dfbb5e095475a3c0239988f61` | 用户选择 OPT-01 后 V1、CI 和 Gate passed |
| REVIEW | `pilot/review-policy` | `f3d70bd41768dab583e3f2582d13ad9088a2630b` | `2d229c325d68529b5f507b030d802fcb88e7cb4e` | Policy/spec 失效恢复、独立批准、V1、CI 和 Gate passed |
| BLOCK | `pilot/block-dry-run` | `7c3e32d6a38b966e2892251068647d83aa295a23` | `da8ac8990485a1c52ec327d099132ce7d19ab674` | 初始拒绝；用户确认 no-delete dry-run 后恢复并通过 Gate |

报告任务 `TASK-0001` 在 subject `5bb9ea4ae041a6e792c1fadf81a3c735dcec7d8f`、attestation `83c9b3b873a66468719fcd27e88217d137e623c5` 上以 V1 通过 10 项 CI 检查和 Gate。它只汇总脱敏 artifact 及 SHA-256，没有在主 HEAD 重跑四个旧试点 Gate。

## 完整验证命令

```powershell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy src
python -m pytest
python -m pytest --cov=aiflow --cov-branch --cov-report=term-missing --cov-fail-under=85
python -m pytest tests/e2e -q
python -m aiflow --version
git diff --check
```

Task 7.6 的最新通过 run 为 584 passed、3 skipped；coverage XML 记录 4,276 行中 3,795 行覆盖（line rate 88.75%），1,414 分支中 1,085 分支覆盖（branch rate 76.73%）。发布命令仍以 `--cov-fail-under=85` 作为总覆盖门；最终数字以 `TASK-0003` 的 evidence 为准。

## CI 一致性

- 本地/CI Gate 使用相同核心、Policy 和 reason-code 契约，parity fixture 通过。
- `TASK-0001` 报告任务和 `TASK-0002` 干净检出任务都在操作系统临时目录产生 CI evidence，随后 Gate passed。
- CI 失败 run 不被覆盖；`TASK-0002` 曾因不稳定的预 attestation 假设被拒绝，修正、新 subject 和全量重验后才通过。

## 未验证场景与风险接受

- Windows 当前环境没有测试符号链接创建权限，三个 symlink 逃逸测试显式 skip；其他范围和路径攻击测试已通过。本地 `0.1.0` 基线接受该平台限制，但不将 skip 记为已验证。
- 没有执行 push、merge、deploy、tag、package publish、凭据或付费外部调用；因此不接受对这些外部动作成功性的任何声明。
- V2/V3、独立 Verifier、变异测试、完整 Hooks 和真实模型路由是明确非目标，不被本次风险接受扩大为已交付能力。
- 用户已批准本地受控推进，高风险外部动作仍需对精确动作单独批准。

## 需求与质量复核

需求复核对照《AI 代码协同分流与模型路由设计 V0.1》、《AI 代码协同系统实施总体规划 V0.2》、获批 MVP 设计和验收矩阵。质量复核以可重放测试、可操作错误、干净环境文档执行和非目标扫描为准。两项最终结论将绑定 `TASK-0003` 的 subject、attestation、CI evidence 和 Gate。
