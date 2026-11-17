# 验证预算与 schema 性能方向决定（2026-10-04）

当前结论：封存 parsed-JSON/deepcopy registry cache 的 `NO_GO`，不重复运行该候选，不采用其生产补丁。旧的 regression 900 秒、integration 600 秒失败保持原结论。新的纯 schema 表示比较经两名独立 reviewer 静态 PASS，但唯一启动尝试因绑定 workspace 不可用而失败，脚本未启动、没有计时结果；不能据此采用优化或重跑完整 V2。

后续独立新绑定 002 已完成并经非作者终态审计；结果不支持这两种表示继续生产化。
001 的 launcher 失败保留，不改 binding 或补写其 result。完整预算仍未解决，下一步
读取已有完整 raw profile 的直接 caller 分区，区分 legacy 与已实施 c7 的成本，不重跑 suite。
该离线分区现已实际完成；历史计数可核对，当前 c7 的完整 suite 成本仍未测得。

## 已核对的失败与未知项

TASK-0064 原 run `run-20261003T153150710903Z`、source subject `50777d648765a935c265e2d12e292d325fabeb1f` 的 native evidence 为 `failed`，14 项 required checks 中 11 项通过、3 项失败：

| 检查 | 实际结果 | 实际耗时 |
| --- | --- | ---: |
| regression_tests | `RUNNER_TIMEOUT`，无最终 pytest summary | 900301 ms |
| integration | `RUNNER_TIMEOUT`，无最终 pytest summary | 600434 ms |
| coverage_xml | 1 failed、3036 passed、1 skipped；失败用例为 `tests/unit/test_process_runner.py::test_timeout_kills_child_process_tree` | 1118810 ms，pytest summary 1117.53 s |

原 evidence raw SHA256 为 `075d18f5cd317c3077431fb22183e4faf0893eae025dc0ed73e5a704432dd583`，本次只读复核匹配。regression 与 integration stdout 最后完整百分比行均为 87%；各有后续未成行进度符号。进度符号不证明 teardown 完成，也不能提供最终用例数、正在运行的 node/phase/stack。原生失败日志没有逐阶段耗时。

原一次性 action `dd1502a97b726e3b8f8b027a146b5ae730695a625f03700378c62ac6ad91bf22` 已 `SPENT`。TASK-0064 仍为 `FAILED / REVIEW / V2`，缺项为 `retry_reason_or_escalation`；其冻结范围只有 `src/aiflow/git_context.py` 与自身 task 记录。覆盖率 89%、diff coverage 100% 和五个 killed mutations 不改变失败结论。后来单次 process-tree 诊断通过也不解释或改写原失败。

可移植证据入口为目标 worktree 中 `.ai/tasks/TASK-0064/preparation/v2-terminal-summary-001.json`、`process-timeout-diagnostic-summary-001.json` 与原 native logs。私有只读性能审计为 `${RUNTIME_ROOT}/harness-model-followup-20261003-001/task0064-native-timeout-performance-audit-001/audit.json`，raw SHA256 `90508c1abd7115bec9527bf82c3325b41f74a362662523ddcb843b3d1ceb8394`。旧原件不得移动、覆盖或用新 summary 替代。

历史 F timing diagnostic 与当前 native run 分开解释：991 collected、762 started、761 个完整三阶段报告（760 passed、1 skipped）；第 762 个用例在 599.5056346 秒才启动。已报告阶段合计 598.2364486 秒，其中 external-review module 为 202.3274652 秒，repository-fixture module 的不完整观察为 135.4581255 秒。它支持累计预算耗尽，不能证明唯一根因或末尾用例死锁。观察开销、当前 native cache hit/miss、CPU/IO 竞争及完整 suite 各函数成本仍未知。

更早的 TASK-0056 私有完整 integration duration diagnostic 在不同 source 与 867 collected 条件下为 866 passed、1 skipped、639.96 秒，仍超过原 600 秒要求。不能将不同 source、启动方式与 fixture 状态的耗时直接相加、相减或外推为当前通过预算。

## 封存现有 schema 复用候选

现有完整私有实验：`${RUNTIME_ROOT}/harness-model-followup-20261003-001/task0063-contract-registry-prototype-002/`。它保留每次当前 `is_file` 与 UTF-8 `read_text`，按完整、通用换行归一化后的 text 命中，缓存解析树，再通过 `copy.deepcopy` 为新的 Resource/Registry 提供独立树。未缓存 validation 或 Policy 结论。

实际有 15 组动态 case、36 个 asserted A/B comparisons，全部比较相等；五轮交替基准每 leg 40 次调用。高 hit 数不是正收益：

| 路由 | 原 median / 40 次 | 候选 median / 40 次 | 候选相对原耗时 |
| --- | ---: | ---: | ---: |
| registry | 100148200 ns | 154736400 ns | 1.5450742，即慢 54.51% |
| validate-task | 113975300 ns | 168705900 ns | 1.4801970，即慢 48.02% |

候选有 7519 hits、239 parses、7759 reads；这不能抵消 clone/key/LRU 成本。独立报告 `task0063-contract-registry-final-experiment-independent-review-002.json` 明确给出 `NO_GO`，不采用生产补丁，也不为追求该 cache 增加 guard 复杂度。个别 round 可能受噪声影响更快，不能写成每一对都更慢。

本次只读重新计算下列 raw hashes，并与独立报告 sealed002 记录匹配：

| 私有原件 | Raw SHA256 |
| --- | --- |
| `registry_prototype.py` | `96361303d88b5532166afc0856f829c19c1375f460f2df137b1604070766eae9` |
| `run_experiment.py` | `b764839e7b71d1886740e946218afe9ecb78eeb7a34ca488556cce642de440b3` |
| `alias-binding.diff` | `7bfca52fa1bf9a4b2749fa963e3f4602f7dca6173b7c2b40b5b7529cb5282652` |
| `events.ndjson` | `746e2062b19a936739ae17252e9bd8538e9cf5960c92fc7a8e848220caf77e6c` |
| `result.json` | `0c62b8eb6d55bb18cc48a5f70a7f6a80de663a4203924a67d65b4ffc91618451` |
| `source-input-byte-guard.json` | `18e764caed27241cb966d4997b41f427a90a76b13d5ed7574b8807948002044c` |
| 独立 final-experiment review | `2f6b0678a033cf6df42ecdfb114323569ca93007153d11c0e4c7768fcb8b14ee` |

现有 schema primitive 微测量的原 registry median 约 1.25–1.69 ms；每 18 schemas 的私有分段 median 中 JSON parsing 为 0.24435 ms，读 text 为 0.72270 ms。这些分段有未知计时开销，median 不能相加。历史五用例 profile 的 registry JSON-loads edge 为 0.2347222 秒、registry total 为 1.3773061 秒；两者仅属该 profile，不能把整个 registry 成本都称为可省解析成本。另一个 binary-read prototype 没有稳定提升，也不采用。

生产边界尚未被旧原型证明：custom Path/parser、`json.loads` 下游 dispatch 变化、复制失败、并发 LRU 原子性与总内存上限。标准单线程 case 相等不等于生产等价。

## 替代的最小方向

先回答纯解析表示是否存在可测正收益；没有收益就停止该方向，不把 file IO、Resource、Registry 或 validation 复用掺进来。最多比较以下三种算法，包含基线；不重跑已封存的 deepcopy cache：

1. 基线：每次当前 text 都调用原标准 `json.loads`，按原顺序构造新的 Resource 与 Registry。
2. JSON frozen tree：只对标准 parser 产生的精确内建 dict/list/scalars，在 miss 时建立不可变树；命中当前完整 text 后，用专用 materializer 建立新的内建 dict/list。没有 `deepcopy`、共享可变树、Resource 或 Registry。深度/节点数超限直接使用当前 text 的原解析；可选表示处理失败不得代替原成功结果。
3. Compact JSON text：miss 的标准解析成功后保留紧凑标准 JSON 字符串，命中当前完整 text 后仍调用标准 `json.loads`，得到新的树。只复用不可变表示，保留键顺序与标准数值/字符串语义；不缓存异常、Resource、Registry 或验证结论。

以上只是不同于旧 clone cache 的实验算法，收益为 `UNKNOWN`。第二、第三项均不能跳过当前 read、改变 schema 顺序、延后 Resource construction、跳过 `$id/$ref`、FormatChecker 或 cross-field checks。它们不取得 production adoption authority。

若实际收益与边界证据支持后续实现，最小治理 scope 为新的 task 中 `src/aiflow/contracts.py` 的 schema loading/registry construction；若确需独立 JSON 表示模块，先明示增补范围、重新分类与冻结。必要安全 tests/docs 另作 task-free 单元，不混进治理源码 task。不能扩大 TASK-0064 旧 scope。fixture 的 source/type/mode/config/template/snapshot 当前检查、physical copy 独立性及 copy-error/no-retry 合同继续保持。

## 单次纯 schema 微测量方案（准备窗口，测量未执行）

独占输出计划为 `${RUNTIME_ROOT}/harness-model-backlog-20261004-001/schema-representation-cost-001/`。准备前核不存在；只创建本次独占目录，不覆盖或自动换名重试。固定清单为 `plan.md`、`measure_schema.py`、`binding.json`、`run-claim.json`、`events.ndjson`、`result.json`、`source-byte-guard.json` 与本次创建的 `cases/`。`run-claim.json` 以 exclusive create 固定一次启动；存在即停止。无其他输出，无旧 evidence 副本，无仓库或 task 写入。

输入绑定当前目标 worktree 的 `src/aiflow/contracts.py` raw SHA256（本次为 `a4d4ab0084db204a8c4bf7f228d531bc6866380deb5411045b810949407f263b`）、原序 18 个 schema 文件的实际 names/types/bytes/raw SHA256、选用 valid/invalid fixture 的原始 bytes/hash、解释器与 jsonschema/referencing 实际版本。启动设置本区显式 `PYTHONPATH` 并禁用 bytecode 写入；脚本不调用任何 subprocess、shell、Git、pytest、Task CLI、provider，也不创建线程或全局 monkeypatch。

三个私有 pipeline 保持原 `load_schema` 在先，随后 FormatChecker、按原序 registry、validator/errors/cross-field 的次序。用未计时的未改原函数核对私有基线及候选输出/异常；所有输出/错误核对在计时之外。计时记录属于私有完整 pipeline，不冒称原函数的 exclusive profile 或正式 native argv。

固定 cases 包括当前完整 registry、valid task/approval/external-review 与原 invalid fixture；两个不同 schema roots；同长度内容变化且保持原 mtime；缺失后出现、file-to-directory；CRLF/CR 归一化；无效 UTF-8/JSON 与非 object；错误 `$id`、本地 `$ref` 和重复规范 URI；早 Resource 错误与晚 JSON 错误次序；每次返回 Resource 的嵌套 contents 修改隔离。所有变体只写本次 `cases/`，不改任何输入原件。标准 parser、单线程和受限内存是明确实验前提；未涉及的 dispatch/并发行为保留未知。

两个路由为 registry 与 validate-task；各五轮，每轮每算法 40 次，按轮轮转次序。每路由 owner 独立；另记六个 cold call，不加隐藏 warm-up。计划为 1200 个 timed round calls 加六个 cold calls；额外未计时 case 调用在计划中固定并逐项记数。`ns_per_40_calls` 与 `ns_per_call` 分列，旧 NO_GO 的约 100 ms 是 40 次的 leg 耗时。事件记录实际读/parse/materialize/compact-hit 计数、完整 leg elapsed、逐轮顺序、比较结果和输入 bindings；不中途输出 raw schema 内容。

单次总合作预算 45 秒，每个调用前后检查 deadline。它不承诺抢占式 hard wall cap；如果调用超预算，标记 timeout/incomplete，保留实际终端及原件，不自动重试。任一输入 before/after bytes 不相等、原输出/异常不匹配、计数缺项或结束不完整均拒绝收益与采用结论。median、paired delta 与范围分别计算，禁止外推当前 regression900/integration600 PASS。

现已仅准备上述独占目录中的三个文件；静态 AST 解析通过，没有执行脚本、case 或 benchmark，`run-claim.json`、events、result 与 guard 均未生成。准备绑定覆盖 26 个实际输入（source、launcher、六个 fixtures、十八个 schemas）；固定 24 个比较场景加隔离与路由参照共 106 个未计时调用，另有六个 cold calls 和 1200 个 round calls。现有准备文件 raw SHA256：`measure_schema.py` 为 `66d0f1c5b7696ae590d6b2d7000e0d6401c3ba50ec29f039e453c905b41f6cfa`，`plan.md` 为 `dc9060d0b847baede16408357281617d9fc47a5f4b0e09985b7d00a5acc6fd4e`，`binding.json` 为 `a1b0a4378ae517dbf7e893bef65276c6e81f0c58f5587cfafa130dc34135a00c`。结果发生后只追加实际结果，不提前写 PASS。

执行安排：方案与脚本准备串行（0 个额外 sub-agent）；静态审查并行（计划 2 个 sub-agent，分别审查语义/隔离与预算/计数/输出归属，只读且不改同一文件）；独占测量串行（0 个额外 sub-agent）；结果整合与 raw hash/算术独立复核串行（计划 1 个非作者 sub-agent）。只有脚本与固定输入通过静态审查后，主 agent 才执行一次。

## 单次启动的实际终态

`/root/f_recovery` 与 `/root/safe_contract_review` 完成独立静态审查，准备三文件哈希和
26 项输入在审查窗口匹配。唯一 launcher 启动返回 PowerShell exit 1：绑定的 venv
python.exe 路径不可用。随后只读检查发现 26 项绑定输入均不可见；主 agent 复核发现
原性能 worktree 的业务目录不存在，原 F 业务目录为空，两者也不在当前 Git worktree
注册清单中，但原分支 refs 仍指向 `ef5943b` 和 `166fe31`。消失原因/动作来源 UNKNOWN，
不将此解释为执行策略、Windows 权限或性能失败。

脚本没有启动，`run-claim.json`、events、result、guard、cases 全不存在。实际计时、
比较、cold/round calls、原件 before/after guard 和速度结论均无可用结果。没有换解释器、
修改 binding、替代工作区或重试。准备文件原样保留，唯一新增的独立终态记录为
`independent-review-001.json`，raw SHA256
`801269089ef2465c9cacccfdc0e6bbbbb3b2616d8b533ddb0c4830dd8f95a1ca`，终态
`LAUNCH_FAILED_BOUND_WORKSPACE_UNAVAILABLE`。后续如需新测量，先恢复可审查的真实输入和
新绑定，另作明确决定；不能把本次静态 PASS 写成实验通过。

## 新绑定 002 的实际结果与停止方向

新输入绑定稳定主检出及其实际 CPython 3.11.9 / jsonschema 4.26.0 / referencing 0.37.0。
与 001 的26项相比，9项同 bytes/hash、17项不同（launcher、4 fixtures、12 schemas），
原因不推断，旧/新耗时不直接比较。脚本与 001 逐字节相同，002 plan/binding 独立核验，
主 agent 再核全部输入及无既有产物后唯一执行，exit 0；无生产、Task 或子进程调用。

实际为 `COMPLETE_PRIVATE_COMPARISON_ONLY`：24组输出/异常对照、4组隔离、106个未计时
调用、6 cold calls、1200 round calls；30腿每腿保留720 current reads/checks。结果包含
最终 guard 的时间为2.4449978秒，最后事件2.4460628秒，均小于45秒合作预算；不能据此
宣称每个同步调用可抢占。每个路由五轮、每腿40调用，无追加重跑。

| 候选 | registry 同轮 paired median / 调用 | validate-task 同轮 paired median / 调用 |
| --- | ---: | ---: |
| freeze-materialize | −43.8 μs | −2.3 μs |
| compact-string | −7.6725 μs | +44.755 μs |

freeze 的 validate-task 腿中位数为65.9287ms，当前基线67.2573ms，差约1.975%；同轮
paired median 却只改善0.092ms/40调用且波动跨零，不能称稳定2%收益。compact 该路由
paired median 反而慢1.7902ms/40调用。独立判断为不足以支持这两个候选继续生产化，
不改 contracts、不用局部差值外推完整预算 PASS。

producer guard 记录26项运行窗口直接 bytes/mode/mtime 比较相等；只保存比较布尔与post
hash，未保存before原字节及具体metadata值。独立审计另核当前26输入和审计双读稳定，
不将其扩大为重建原窗口证明。另发现 `SCHEMA002-EVENT-CLOCK-001`：6条cold事件的
`elapsed_ns` 被该调用duration覆盖，其他事件才是自claim累计时间；82条不能解释成
统一单调时间轴。这不改变deadline实现、leg计时和对照，但原日志不改、不重跑。

原件位于 `${RUNTIME_ROOT}/harness-model-backlog-20261004-001/schema-representation-cost-002/`：

| 原件 | Raw SHA256 |
| --- | --- |
| `plan.md` | `8799f98203c8eb6d38275bf53dc8711eeea62cfbf020141c737c227c0fa8e4c9` |
| `binding.json` | `05ed32a30df4646d990d6edf71529bc0605fcc4defcb2575d02f36c739665cc5` |
| `events.ndjson` | `3cdc4da50f11c8ecfa8643b59b9a7e1ee8f24e32a458647312006717f023827f` |
| `result.json` | `0b856c4a8678d7488cb5e4b968143fe86cdc5014764b73767dc6a526669a17cd` |
| `source-byte-guard.json` | `b0af66b4c349bb3ad88a0a5921ba22809c948d71e74f8783b2df1b12217f91a4` |

同父目录的 `schema-representation-cost-002-independent-terminal-review-001.json`
raw SHA256 为 `ae5a737c23d62354b6d77fc9f09af019f207a14505b3625f78ac2eb06786dc1e`。
当前停止该表示方向，原 NO_GO、001 未执行与002实际结果各自保留。

## 历史 profile 离线分区的实际结果（2026-10-05）

原 offline 准备 001 未执行，独立静审拒绝了 caller tuple 次序错误及 guard 缺口；
四个输入和 NO_GO 原件保留。独立新版本 002 修正 caller total/index0、primitive/index1，
保留 raw tuple 和递归残差；两个版本没有重绑或覆盖。

002 经非作者静审后，root 仅一次以固定 `-I -S -B` 启动，exit 0，实际结论为
`OFFLINE_INVENTORY_COMPLETE`，分析耗时 180867600 ns。脚本无 business import，
audit 记录 child/network attempts 均 0；这仅为解释器内观察，不证明宿主全局进程状态。
脚本 35 项 before/after 均相等，root 独立启动前及终态再次核对 35 项 bytes/SHA256
相等，binding 保持；原 profile、当前来源与准备文件未改。没有新 profile 或 suite 运行。

原完整 profile 的 `subprocess.run` 8,571 次调用按直接 caller 完整分区如下：

| 历史 caller 家族 | total / primitive calls |
| --- | ---: |
| GitContext 的 `_run_git`、`_read_branch`、`_is_ancestor` | 5,769 / 5,769 |
| external-review Git wrapper | 1,270 / 1,270 |
| scope Git wrapper | 764 / 764 |
| fixture Git / Python timeout 的合并标签 | 1 / 1 |
| 其他或 argv 未知 | 767 / 767 |

合计与 callee 的 total/primitive 均相等。Popen constructor 9,732、communicate 9,734、
CreateProcess 9,732 的 direct caller total/primitive 也分别对账为零残差。
递归 copytree 的 total 13,570 完整对账，但 caller primitive 合计 1,718 与 callee
primitive 1,178 相差 540；原递归语义/标签限制保留，不强制归零或虚构额外调用。

这些记录属于历史 source。当前 c7 已有正常两查询及明确 fallback，外部审查 wrapper
也发生来源变化；AST 比较只证明 main/c7 某函数语法是否相同，历史 byte identity 仍
UNKNOWN。不能将旧 5,769 次和旧累计耗时当作当前 c7 成本，也不能把主线程 communicate
等待称作 child CPU、把嵌套累计耗时相加、把 fixture 合并标签全称 Python 启动。
两份五用例记录的 CreateProcess 146→143 保留为各自小窗口，不外推完整预算 PASS。

原件为 `${RUNTIME_ROOT}/harness-model-backlog-20261004-001/` 内：

| 原件 | Raw SHA256 |
| --- | --- |
| `budget-next-diagnostic-preparation-002/result.json` | `99e3f2fa81f36e1edc6e72cb8ffde6aa87c3fdca2f1128fa15cb12188ee1632b` |
| `budget-next-diagnostic-preparation-002/run-claim.json` | `9fa57526b5dc5c2591619e4cfa744c5d9f94da29d9a7ef7146a994dc34269e56` |
| `budget-next-diagnostic-preparation-002/binding.json` | `a45f28598ffa5e56bb924b5777f226023f250d57fbb1b5d02b61df1a2d1e2d8c` |
| `budget-next-diagnostic-static-review-002.json` | `64a6d896bac373a7b23769ee41198cc10e211479fb63df88d1b039a8bb94d025` |
| `budget-next-root-execution-002/terminal.json` | `243d29eaa1e131df4e520bac5380a9d2c32e3c99a6dfca2ddb938f537e27c626` |

stdout 为 28 bytes 的完成 marker，stderr 为零 bytes，均在实际终态后独占保存。20 秒
是合作式期限，不承诺抢占同步解析。一次 claim 已消费，不重跑该诊断。下一步以固定
生产候选的实际资格及原生全套结果核定预算；若失败需要新优化，另定范围和准入，
不再次提出已实施的 Git batching / fixture copy，也不采用已拒绝的 schema cache。

## 后续完整验收边界

任何生产候选需要自己的真实 spec/classification、独立 Design Review、native `status Missing:` 所需批准与实际提交绑定；不能从实验正收益推导权限。完成候选后才准备新的具体 mutation action，旧 actions 永不复用。

完整验收仍为原 14 checks、原 selectors/顺序，unit300、regression900、integration600、coverage1200，85% overall、90% diff coverage、whitespace、Ruff、format、mypy、independent Review/finalize/code approval/Gate，以及 main 保护与 required CI。本文与任何私有微测量均不改变这些要求，也不构成 retry V2、F acceptance、push、merge、deploy 或 provider 授权。
