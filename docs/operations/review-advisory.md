# 只读任务准备建议

`tools/analysis/review_advisory.py` 为本仓自然发生的治理任务提供非评分建议。
它复用原生 `summarize_task`；只有任务处于 `APPROVED_FOR_MERGE` 时才读取原生
`evaluate_gate`。它不重新计算状态、Gate、权限或批准，不执行建议，不写账本。

使用完整克隆及 Quickstart 已配置的 Python 环境：

```powershell
python tools/analysis/review_advisory.py TASK-0001
python tools/analysis/review_advisory.py TASK-0001 --repository <完整克隆根目录>
```

`--repository` 是显式根目录，默认取工具所属完整克隆。工具不发现其他仓库、不初始化
缺失配置，也不回退历史快照。调用目录不影响默认仓库；从其他目录调用时需要使用工具
本身的正确路径。目标仍须具有自己的 AI Flow 身份、Policy、Schema 和任务原件。

输出为 JSON，固定 `probability_status: "unestimated"`、`execution_allowed: false`。
正常读取退出码为 `0`，包括 Gate 拒绝；读取失败退出码为 `1`。退出码不代表批准、
执行或合并许可。参数解析仍使用 argparse 的帮助和错误契约。

`native_status` 仅投影闭合状态、路由、验证等级、新鲜度和 dirty 布尔值。
`native_gate` 仅包含是否实际读取、原生 passed 布尔值及已知原因码。
这些字段保留原生含义，不能把新鲜度标签解释成新的验证结果。
工具不输出目标、actor、文件内容、dirty 文件名、绝对路径或错误详情。
未知原生字段只产生固定 unknown 代码，不以自由文本输出，也不推测对应动作。

| 建议代码 | 需要准备或核对的事项 |
| --- | --- |
| `PREPARE_CLASSIFICATION_FACTS` | 按实际范围填写分类事实，再按原生流程处理。 |
| `CHECK_CLASSIFICATION_ROUTE` | 核对原生分类与当前路由，定位实际缺项。 |
| `PREPARE_SPEC_FREEZE` | 准备完整规格与范围，以原生冻结要求为准。 |
| `CHECK_IMPLEMENTATION_PREREQUISITES` | 核对状态、现有批准和范围，准备实现。 |
| `PREPARE_IMPLEMENTATION_RESULT` | 准备当前实现结果与必要验证材料。 |
| `CHECK_VERIFICATION_READINESS` | 核对当前验证计划、输入和已有授权。 |
| `CHECK_FINAL_ROUTE` | 核对验证后的原生路由与收尾缺项。 |
| `CHECK_STALE_BINDINGS_AND_VERIFICATION_READINESS` | 定位失效绑定及当前验证前提；不自动重跑。 |
| `DECIDE_ASK_DIRECTION` | ASK 缺少真实方向选择，需由项目所有者决定。 |
| `CHECK_EXISTING_APPROVALS_AND_STANDING_AUTHORIZATION` | 先核已有批准、新鲜度、独立审核和常设授权覆盖；不能一概要求新增人类批准。 |
| `CHECK_GATE_AND_EXTERNAL_ACTION_AUTHORIZATION` | 使用原生 Gate，并核对具体外部动作的既有授权；Gate passed 本身不授予执行权。 |
| `CHECK_DIAGNOSIS_SCOPE_AND_EXISTING_AUTHORIZATION` | 定位失败、阻塞或升级的真实条件，核对诊断、范围与现有授权；不自行重试。 |

`FAILED`、`BLOCKED`、`ESCALATED` 保留原生状态，只给诊断核对项。
`MERGED` 保留历史投影，不列待重跑或待批准。工具不评价常设授权是否实际覆盖，
因此始终记录 `AUTHORIZATION_COVERAGE_NOT_EVALUATED`；概率也始终未估计。

未知与错误代码包含 `NATIVE_STATUS_FIELD_UNRECOGNIZED`、
`NATIVE_MISSING_CONDITION_UNRECOGNIZED`、`NATIVE_GATE_REASON_UNRECOGNIZED`、
`ADVISORY_INPUT_INVALID`、`NATIVE_STATUS_READ_FAILED`、`NATIVE_GATE_READ_FAILED`。
读取失败保留已有安全投影并明确报错，不形成可执行建议或历史成功兜底。

入口是单个同步 CLI 调用。独立工具进程在导入原生 AI Flow 前禁用 bytecode 写入，
因此普通 `python` 调用也不会创建仓库内的 `__pycache__`；导入工具模块不会修改
调用者的 bytecode 设置。它用 `contextlib.chdir` 暂时进入目标根目录，并在两次原生
读取期间共同设置 `GIT_OPTIONAL_LOCKS=0`，避免 Git status 刷新 index；退出时恢复 cwd
与原环境值。其他 Git 环境保持原样。此入口不提供进程内并发库 API，读取也不是原子
快照；任务或仓库同时发生变化时，应重新读取当前原件再作决定。

该工具是离线建议能力，不证明置信度校准、人工打断减少、provider 接入、真实执行
试点或阶段三退出已完成。
