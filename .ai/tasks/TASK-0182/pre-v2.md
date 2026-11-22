# TASK-0182 新候选与单次 V2 预算提案

**待所有者决定。** 两项修复已通过独立前置复审。TASK-0182 正式 V2 运行次数为 0，正式变异动作的创建、批准和消费次数均为 0。前驱 TASK-0181 的正式结果为 FAILED，原有额度已消费 1/1。

## 候选绑定

| 项目 | 复核值 |
|---|---|
| 任务、决策单元与分支 | `TASK-0182`，`DU-001`，`codex/receipt-version-fields-candidate` |
| 公开 main 基线 | `d0be6ce67004f11d575e1a135df35e164d712b79` |
| 软件提交 | `ede60b17e4f81f2ef4162f10aef3e785a9e2c6e0` |
| 冻结规格 SHA-256 | `97ba67e355e999d91a552296538423fd477d4ab7611ef1a84af8f0742c64d163` |
| 分类输入 SHA-256 | `61464d199428427e06c72ae2613f1dca601b81a8e80e8dfa08092d0aca9fa6f9` |
| Policy SHA-256 | `72baefa4710edfc7ba10dc3de6b751d93c69226bab86222985f7b5009f11a50e` |
| Ubuntu Git 工具树 SHA-256 | `1da25b4aa4132e02fbf3cbb7007705db9b5971fad753486eb5be41baa94bc40a` |

## 修复和独立复审

Ubuntu 隔离环境在新的只读工具树中补齐发行版的 `git-submodule`、Git shell 助手和运行依赖。上次失败的 `tests/unit/test_git_context.py::test_real_submodule_content_and_untracked_changes_are_dirty` 在前驱测试版本和本次软件提交的全新离线检出中各运行一次，均为 **1 passed in 0.17s**。测试文件、共享 fixture 和受测 Git 模块在两个版本的 Git 对象相同。原失败现场 28 份原件的内容与 inode 清单均已核对。

验签器复用既有字段校验，在读取 V2 证据时要求 `spec_sha256`、`policy_sha256`、`classification_input_sha256` 各为 64 位小写十六进制。它还要求 `decision_unit_ids` 为非空、无重复的列表，每个元素须匹配 `DU-[0-9]{3,}`。回归用例通过正常验签入口输入重新签名的证据，覆盖缺项、错误类型或格式、重复和非 ASCII 数字，以及含四位编号的合法列表。普通质量 workflow 的 Git 对象与公开基线相同，手动验签 workflow 的 Git 对象与前驱候选相同。

独立审核者 `pre-v2-independent-reviewer-182` 对两个修复均给出 **APPROVE**，未关闭发现为 0。审核者直接检查软件提交并独立运行验签与原 workflow 两个测试模块，**106 passed in 23.97s**。两份 Python 文件通过 Ruff 检查与格式核对，验签器通过严格 mypy。环境复核依据为两份脱敏回执、软件 bundle、源码和依赖锁摘要，结论限于该回归用例。正式实施审核仍须绑定本次 V2 的通过快照。

| 本地证据 | SHA-256 |
|---|---|
| 环境修复回执 `ubuntu-git-submodule-regression.json` | `8fed20bfaa625079cd9b136a99d9059369b87fdfbaf28b43994cef4e965898c1` |
| 新软件提交的原用例回执 `TASK-0182-ubuntu-node.json` | `a9a3887a8d210a9b400d9acde95b4c233b7c4fbea17da38c6c9b903d7b9128f4` |
| 精确软件提交的输入 bundle `TASK-0182-subject.bundle` | `f3b7dad173921bdcb0ec99c09351c2d2582564928db0334c4b190c8cd19a635e` |

## 拟批准额度与停止条件

申请 **1 个本地独占 Ubuntu x86-64 槽，1 次正式 V2，90 分钟含清理，至多消费 1 次变异动作**。运行仅使用本候选、公开来源的输入及锁定的依赖。正式执行断外网，隔离环境无宿主盘、凭据和宿主套接字，付费调用为 0。

| 条件 | 约定 |
|---|---|
| 触发源 | 所有者在本提案后明确批准启动。届时重新核对公开 main、软件提交、冻结规格、分类、Policy、CLI 状态和隔离环境的工具、可用资源。由独立审核者核对绑定本任务、决策单元和软件提交的单次 `targeted_mutation_v2` 动作，确认取得覆盖整个窗口的有效批准，并由独立 verifier 执行。绑定漂移先重新核定。 |
| 窗口 | 单次 90 分钟。从正式启动计时，包含回收。沿用 14 项逻辑检查。8 个普通检查进程的时限合计 3750 秒，其中共享 pytest 至多 3000 秒。5 项变异各运行一次 baseline 和一次 mutant，每个进程最多 60 秒。名义合计 4350 秒，余量用于 Git、证据落盘和清理。 |
| 终止条件 | 完成、失败、中断或到期即停，保留原件及实际消费记录。 |
| 连续失败上限 | 1 次，自动重试 0 次。 |

本提案只提交本地执行预算。若 V2 通过，后续正式实施审核须引用同一软件提交和快照，随后由同一 verifier 完成 finalize。原件披露、公开 CI、推送与合并另行处理。
