# AI Flow Node 本地验证

普通 wheel 支持封闭 profile `agent-bridge-node@1`、完整目标 Policy `3.1.0` 和 Node evidence `3.1`。运行限 Windows x64、CPython 3.11、本地 NTFS，只支持本地 V0/V1。Policy `3.0` 不受支持，不回退到 Python profile；现有 Python 合同及本仓门禁保持不变。

本页说明固定目标合同。installed 外仓 V2、Node CI 和真实 agent-bridge 采用尚未交付。本地 V0/V1 不代表完整跨仓接入完成，也不扩大推送、合并、部署或私有材料传输权限。后续依赖见[接入方案](sdk-and-engine-plan.md#完整引擎跨仓初始化)。

## 初始化与任务前置条件

先按[资源包说明](resource-bundle.md)在源码树外安装普通 wheel。资源包包含 15 份 Schema、四份 Policy 种子及规格模板，共 20 份资源；种子仍为 Python Policy `2.6.0`，不能作为 Node Policy。Node 必须显式提供只含以下四份完整、同版本 Policy 的候选目录：`hard-rules.yaml`、`routing.yaml`、`verification-levels.yaml`、`permissions.yaml`。只有 verification Policy 声明 `{id: agent-bridge-node, revision: 1}`，四份文件均须通过 Schema 和交叉校验。

```text
python -m aiflow init preview --target <TARGET> --profile agent-bridge-node@1 --policy-candidate-root <POLICY_DIR>
python -m aiflow init apply --target <TARGET> --preview <PREVIEW_JSON> --policy-review <REVIEW_JSON> --policy-candidate-root <POLICY_DIR>
python -m aiflow init inspect --target <TARGET>
python -m aiflow init migration-plan --target <TARGET> --profile agent-bridge-node@1 --policy-candidate-root <POLICY_DIR>
```

目标须有真实 Git 提交，根 `package.json` 有非空 name 及 check/build/test 脚本，首次预览时尚无 `.ai`。预览保存、内容审核、同一候选目录及精确恢复按[初始化用法](initialization.md)执行。安装非覆盖地发布目标自己的 UUID，不复制源仓身份、历史、维护模式或常设授权；升级 wheel 不暗改目标资源。

初始化只校验结构，不准备依赖、不探测 Node/npm、不运行 suite。后续使用目标自己的 task、真实 base/subject、风险 facts、分类、冻结规格及所需审核批准；可编辑安装或以当前目录、`PYTHONPATH` 替换引擎不满足普通安装材料合同。

先依据事实分类，再核对能力。要求 V2 时保留 V2 并阻断，不能降为 V1。Node 不支持 `--check` 部分检查、V2 finalize，或任何带 `--ci`、`--ci-run-dir`、`--output` 的验证组合；这些组合拒绝，不产生 Node 成功证据。

## 显式准备并选择材料

调用者先在当前 task 的独占目录按 subject 锁文件准备完整材料，安装脚本默认关闭，只使用经核对的匿名公开 registry 材料。不要共享活动目标的 node_modules/dist。准备 API 不下载、不安装、不执行 npm ci，也不修改真实目标依赖或 dist。

```text
.ai/tasks/TASK-ID/logs/
  node-payload/PREPARATION-ID/
    node/
      node.exe
      npm.cmd
      node_modules/npm/         # 完整官方 npm 包
    dependencies/node_modules/  # subject 锁文件对应的适用依赖及 .bin shims
  node-prepared/SHA256/
    prepared.json
    source.json
    node.json
    npm.json
    dependencies.json
    engine.json
    host-tools.json
    preflight.json
```

payload 顶层只能包含 node 和 dependencies；`npm.cmd` 须与完整官方 npm 包的 `bin/npm.cmd` 字节相同，不能使用自写 wrapper 或未声明的相邻文件。固定版本为 Node `24.20.0`、npm `11.13.0`、Vitest 及 `@vitest/coverage-v8` `4.1.10`、Vite `8.2.1`。

在受核普通安装的 Python 中，从实际目标 Git 根调用：

```python
from pathlib import Path
from aiflow.node_execution import prepare_node_materials

root = Path.cwd()
task_id = "TASK-ID"
material_sha256 = prepare_node_materials(
    root,
    task_id,
    payload_root=root / ".ai/tasks" / task_id / "logs/node-payload/PREPARATION-ID",
)
print(material_sha256)
```

`prepare_node_materials(root, task_id, *, payload_root: Path) -> str` 重核当前任务、规格、Policy、分类和 subject，执行固定 Node/npm 版本 preflight，并发布不可覆盖的 prepared 清单与本地原件。它还绑定实际普通安装的 Python、引擎源码/资源/必要依赖及 distribution 元数据，以及固定布局的 Git 和 Windows 宿主工具；不能以自报路径替换。清单共用 20,000 项及 512 MiB 预算，单文件最多 128 MiB，拒绝链接越界、遗漏文件、未知 shim 和同版本不同字节。锁文件 integrity 不替代安装后字节重核。

返回值是规范 prepared.json 的 64 位小写 SHA-256，不是路径、执行授权或可信身份凭证。准备目录及失败原件保留；同 subject 换 wheel、工具、依赖或材料时，重新准备并产生新 evidence，按当前规则重做受影响的审核批准。

## 运行与覆盖率

```text
python -m aiflow verify TASK-ID --actor <ACTOR> --node-materials <SHA256>
python -m aiflow status TASK-ID
python -m aiflow gate TASK-ID
```

`--node-materials` 仅选择当前 task 下已准备的摘要，不接收路径、命令、环境或工具选项。verify 不隐式准备材料，仍检查任务状态及所需审核批准；Python profile 使用该参数会拒绝。

| 等级 | 固定检查顺序 | 执行次数 |
|---|---|---|
| V0 | contract、scope、smoke、node_build、node_check、diff_whitespace | 六项检查、八次顶层检查进程；whitespace 分别检查工作区、暂存区、base→subject |
| V1 | 完整同序 V0，再 ts_coverage、ts_total_lines、ts_diff_lines | 九项检查、十次顶层检查进程及两项纯计算；完整 coverage suite 和零命中映射 helper 各一次 |

build 先于 check；check 中既有的 pretest 可以重建 dist，但完整路径、类型、大小及内容摘要必须与独立 build 一致，只有这个成功检查边界允许更换文件身份。两份清单均保留供只读重核，其他阶段继续要求身份不变；引擎不额外重复 build。受核 Node 直接启动固定 npm CLI，使用本次空 user/global config 及 `--offline`；test 脚本固定为 `vitest run --no-cache --configLoader=native`。引擎净化环境并关闭 Node compile cache，不开放任意 shell、loader、NODE_OPTIONS 或自由环境；offline 不等于操作系统网络隔离。

V1 将 subject 全部 tracked `src/local/**/*.ts` 的可执行起始行纳入总体，包含未导入文件；type-only 零行须有真实 AST/映射。完整 coverage JSON 与 summary 必须重算一致，按整数判定总 TS line coverage ≥85%、base→subject 的 changed executable line coverage ≥90%，不按四舍五入放行。零 diff 仅在全集、映射和 diff 完备且交集为空时记 not_applicable。tests 不进入生产分母；其他生产 TS/JS/mjs/ps1/C# 或未覆盖执行入口变化为 unverified 并阻断。目标 TS line 门槛与本仓 Python branch coverage 门槛分别保留。

## 原件与证据消费

验证在本次拥有的固定候选检出中执行，只允许合同推导的 dist、固定 fake fixture 前缀及本次 run 的 coverage/raw/logs；未知输出和缓存拒绝，不豁免整个 ignored 树。原 task 根及 Git 管理区保留完整元数据保护，合法治理变化只按精确事件、路径和摘要合同接受；未知私有文件只核元数据，不读取正文。

Windows 子进程先 suspended 创建，加入禁止 breakaway 的 Job 后再运行。成功要求父进程退出、Job 全空、stdout/stderr EOF 和已确认 cleanup；超时、输出超限、后代存活或清理未知均不可报成功。普通检查各 30 秒，build 300 秒，check 和 coverage suite 各 600 秒，coverage helper 与两项计算各 30 秒；每个输出流最多 1 MiB，deadline 包含后代和管道。

公共 evidence `3.1` 只含固定检查、绑定、摘要/计数与相对原件引用；绝对路径、完整映射、身份和原始报告保留在本地 ignored logs。不要将私有目标材料、凭据或完整原始日志加入公开仓。

`recheck_node_evidence(root, task_id, evidence) -> NodeEvidenceFacts` 是 verify 消费、freshness/status、实现审核、code approval 和 Gate 共用的只读事实入口，不恢复任务、不建目录、不探测工具或运行 suite。它重核当前绑定、材料、prepared/run 原件、进程回执、输出及覆盖率。纯 `validate_node_evidence` 结构检查不能替代它；材料或宿主漂移、原件缺失或未知事实使证据失效并阻断消费，保留已有记录。另一机器仅有公共 JSON 无法重放 PASS，`gate --evidence` 不能把外部 JSON 当作 Node 成功证据。

该合同依赖受审源码、可信宿主、工具和实际安装字节，不认证全部 OS/DLL，也不提供恶意同用户代码沙箱。V2 引擎证据、目标 CI 原件交接及真实目标采用仍须独立交付。
