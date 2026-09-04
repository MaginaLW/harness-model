# Task 4.3 执行计划

**目标：** 校验完整审核包，实现互不替代的 `spec`、`code`、`action` 三类版本绑定批准与失效判断。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `95e43bb5e0364753019bd9d8ff62877f43346746`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 批准会影响实现与合并门，必须绑定当前规格、Policy、被审 commit 和证据，并覆盖失效与幂等；阶段一仍不执行任何真实外部动作。
- allowed scope: `src/aiflow/review.py`、`src/aiflow/approval.py`、`src/aiflow/cli.py`、必要的 task_service/state/git/schema/storage 邻接修正、`tests/unit/test_review_package.py`、`tests/integration/test_approve_command.py`、直接相关 fixture、本计划和 Chapter 4/总体状态。
- forbidden actions: 不推送、不合并、不部署、不执行 action 文件描述的动作；不同批准类型不得互相替代。

## 完成边界

1. 审核包八个必需节非空，证据明确区分已验证/未验证，至少一个审核问题，推荐结论属于固定枚举。
2. spec 批准只允许 `WAITING_FOR_SPEC_REVIEW`，绑定当前冻结规格、Policy 与基础代码上下文并推进 `READY_TO_IMPLEMENT`。
3. code 批准只允许 `WAITING_FOR_FINAL_REVIEW`，要求完整审核包、通过且新鲜 evidence、无治理目录外漂移，并推进 `APPROVED_FOR_MERGE`。
4. action 批准校验精确动作、目标、参数摘要、适用 commit、条件、有效期和单次使用，只记录不执行。
5. `approvals.json` 保存当前集合，事件保留历史；完全相同批准幂等，理由或版本变化生成新事件，版本或目标变化使旧批准失效。
6. 三类批准、错误状态、审核包/evidence/工作树/版本失效、动作到期和仅治理记录变化测试通过。
7. 定向测试、CLI help、累计回归、Ruff、Mypy 与 diff 检查通过后完成 Task 4.3 并本地提交。
