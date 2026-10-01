# TASK-0056 当前源码独立累积 implementation Review

审查产物生成时间：2026-10-01T07:07:36Z。

## 审核目标

本审查由实际未参与源码、测试或规格 amendment 编写的 recovery reviewer 完成，actor 为 `e4-cumulative-independent-reviewer-recovery`。该 actor 追溯当前独立审查员，不用改名替代职责分离证明。本次仅进行只读复核并创建两个私有 create-only 产物，不执行 native record、resolve、approve、finalize、Gate、测试或 Git refs 写入。

审查对象是从 base `ef92b795da729566870ff4878f100a4ffe319db5` 到 source `9dca04dc18e1551dc86987eb594f84f9d37b47ad` 的完整累计实现及其限定行为。实际验证 attestation HEAD 为 `4bb8a60d2d3b67e95789e8fd2ff4b203044ac8aa`。新的 implementation context 为 `d648288382379be6cfb21afe49a6bc9249c1f5403992fd3c5477f1688ef9e2b7`，verification snapshot 为 `6a71bbf1c66efcf7c5addf96a0a522e2147c694214f7109d117005044303e046`。正式候选输入为 REV-0010/r1；本包和输入尚未写入任务账本。

## 背景

冻结 spec SHA256 为 `992b927ce833a8fa9876c7e278d024eca7903763621ea84391c2ad4c09f6916c`，Policy 为 `d21a386779147dfad962a0fc0656bef61bc581e27f63c4789dcc06520fa10ff1`，classification input 为 `365b5f52294b6fb528012f3bcff322294933d788d5eb6b35b7df35e5d6f279f6`。逐段读取冻结 spec 全文，包括显式外部目录、解析复用、初始仓库复制、Windows metadata、完整 core Git 入口及并发复制修订；后续修订仅按其明示范围覆盖早期排除。

旧 source113 的 native pass 与 REV-0009/r1 REQUEST_CHANGES 保留。其 RF-001 是成功 Popen 后非超时异常没有恢复原 retained 直接进程 kill/recovery 的真实兼容回退；旧 context `6bb1dde030ecf2ccd6bf2f1c1af73a4a5a3ce21112c4235be6c7190c71c22dad`、outcome、原字节和全部旧失败记录不重写。原 subprocess.run 的 KeyboardInterrupt 短等待不被夸大为旧终态保证。未保留的 exited-parent descendant 能力边界不是另一个新增回退。

累计 Git diff 有119路径：24个源码/测试/说明路径及95个 Task56 自有治理路径。实际读取累计路径清单，24路径完全等于当前 context allowed_scope。当前工作文件与 source commit 的24个 blob 在仅 CRLF/LF规范化后全部相同；raw SHA逐一绑定当前实际文件。23个路径与旧完整源码审查逐字节一致，唯一后来变化为 begin-close helper 文件。复用已完整阅读的旧测试/说明审查指针；本轮另完整重读生产累计diff、321行目录守卫、1152行复制夹具，以及当前helper和全部新增case。此结论不是由空 Finding 或测试 PASS 推导。

## 代码地图

完整24路径按接口与消费者列出：

- `src/aiflow/verification_temporary.py`；`src/aiflow/verification.py`；`src/aiflow/verification_service.py`；`src/aiflow/process_runner.py`；`src/aiflow/cli.py`。
- `src/aiflow/document_parsing.py`；`src/aiflow/policy.py`；`src/aiflow/storage.py`；`src/aiflow/external_review.py`。
- `tests/integration/conftest.py`；`tests/integration/repository_fixture.py`；`tests/integration/test_repository_fixture.py`；`tests/integration/test_begin_close_commands.py`；`tests/integration/test_external_review_command.py`；`tests/integration/test_verify_command.py`。
- `tests/unit/test_verification_temporary.py`；`tests/unit/test_verification_plan.py`；`tests/unit/test_process_runner.py`；`tests/unit/test_document_parsing.py`；`tests/unit/test_policy.py`；`tests/unit/test_storage.py`；`tests/unit/test_external_review_metadata.py`。
- `docs/operations/pytest-temporary-roots.md`；`docs/operations/external-review-import.md`。

关键控制点为 repository_fixture 的 warm admission:533、parallel eligibility:669、start前worker归属:803、按提交序排空:961、实际shutdown/join:1080；begin-close 的 cleanup:33、初始运行及首次异常:78、真实中断后 retained-child 终态断言:967。当前 begin-close raw SHA 为 `5c48579f53030d0746ad7f544eb44febc8965970f72bb83933c6302b99af2084`。

## 语义变更

外部 pytest root 是显式运行选项。词法拒绝、logical/physical祖先与 .git/bare标记检查、目录身份、原子独占容器、初次不存在叶、最终argv匹配均实际执行。仅五种既有 pytest类别在原 Policy校验后追加固定 basetemp；check与去重execution同步。默认调用不分配目录。finalize/abandon混用在加载任务前拒绝；本地执行期守卫异常记FAILED，CI沿用只读账本约束。运行参数不进入verifier context，重现命令以占位符保留。

YAML复用仅以完整当前文本为键，最多64项/单项16384字符。每次仍实际读取文件并执行路径、schema、Policy交叉语义、摘要和freshness。返回值独立复制，alias关系保留；cycle/深图/自定义值、parser配置漂移、超限及复制问题保持本次原解析，错误不缓存。没有缓存治理结论或改读文件为mtime捷径。

Windows report identity仅在属性存在时选择birthtime，包括合法零值，缺失回退ctime；POSIX仍用ctime。其他身份分量、双次有界读取、raw byte比较、path/handle与link守卫保留。Task55 Git transport及writer没有在此范围实施。

初始仓库复制保留原mkdir与真实cold builder；完整成功且尚未启动治理才可发布私有snapshot。每次warm前读取源、Git wrapper/core实体、配置来源、模板/attributes、环境、owner、snapshot和mode。未知输入及可恢复资格读取异常走原builder；actual copy失败直接传播且保留partial，不重试builder。物理copy2不共享Git对象、index、refs、工作区或任务结论。

parallel仅从该owner的已资格warm snapshot、普通空target和至多256文件选择。至多4实际workers和至多256累计job分别受限。保持真实DirEntry、unsorted DFS和原postorder目录metadata；进入递归前排空连续文件batch，按提交逻辑顺序保留原OSError三元组/shutil.Error展开及首次fatal对象，后来的协调器或cleanup错误不覆盖已有原失败。每个Thread在start前保留，Done只证明主体结束；无证明的native终态不能变成成功，原外层owned进程期限兜底。当前正式host为已准入3.13.15，原CI仍3.11。

RF-001修复将成功Popen后尚未drained的首次BaseException转入原owned回收。原argv/cwd、UTF-8、capture/check与communicate10保留。平台owned终止、helper wait5及fallback1、direct wait5、final drain5配置有界；secondary错误不覆盖首次原异常，bare raise保留对象和args；仅成功drain后关闭stream。完成的nonzero仍是原CalledProcessError且不额外清理。POSIX已reaped父进程不按旧数值PGID发送组信号。

## 风险

守卫拒绝普通碰撞和可检测身份漂移，不是同用户恶意替换的OS沙箱。并发同batch后继文件可在首次non-OS中断后写完，worker audit callback线程和跨文件事件顺序可改变；这些partial与事件差异是冻结规格明示边界。标准函数身份不证明不存在已注册audit hook。没有每线程OS-copy新期限；未知startup或3.11最终join中断终态保持未完成并由原owned外层回收，不能把Done/is_alive或重复join当独立终态证明。

配置的cleanup wait上限不是whole-call硬墙钟证明。Windows exited父进程的未保留后代与未完成reader仍可能无终态证明，既不做全局scan也不按未知PID清理。当前完整native的资源交还只覆盖原retained native Popen handle的实际PID/creation一致和exit0，以及driver tool exit0；没有单独retained engine退出证据或历史后代全局不存在结论。

operations文档的阶段诊断与静态预计数保留其历史时间边界，最新当前native事实另见本task追加025/026。后续Task55自身重新准入、其实现和Gate，以及固定PR head的Python3.11 required CI、真实远端验收与F均有各自进入条件。

## 证据

已验证：当前native默认完整V2 `run-20261001T060444519719Z`，所有14项 required checks实际exit0、timed_out=false，逐项duration低于原预算。原regression900、coverage1200、integration600秒保持；outer4410未触发，cleanup为null。原MINENV算法、selectors、Policy、thresholds、uv.lock和5个固定mutations未放宽。实际native环境只有原PATH/SystemRoot两项；所选完整core Git使实际PATH变化，并由新preflight绑定，未声称ENV字节与旧endpoint相同。

| 原完整检查 | 实际结果 | Pytest秒数 |
| --- | --- | --- |
| unit | 1888 passed | 133.17 |
| regression | 2831 passed / 1既有FIFO平台skip | 775.69 |
| coverage | 2831 passed / 1既有FIFO平台skip | 798.85 |
| acceptance | 9 passed | 0.36 |
| integration | 906 passed / 1既有FIFO平台skip | 545.48 |

integration原生duration为545738ms，低于600000ms。实际coverage XML line-rate91.42%（7487/8190）；diff stdout报告97%，304 changed/9 missing，原85/90门槛保持。全部24个非空stdout/stderr原件引用均在归档，stderr均为零字节。contract/scope、Ruff、format、smoke、mypy同时真实通过，targeted_mutation及independent_verifier为原生14项的另两项。原FIFO skip在原日志的 `tests/integration/test_external_review_command.py:1376`，不是本修复新增skip。

已验证：MUT-V2-001至005按原manifest `phase-02-critical`及原detector/operator，baseline0、mutant1、无timeout、全部killed；main tree unchanged。逐个原始log SHA与mutation evidence匹配。action006 canonical `b1e35fc69bd138767e611a67d1334130f96ffa4eebc4caafa38bfe1c938b0c27`在原event107于2026-10-01T06:42:24Z消耗，receipt recorded且不可复用；原events108/109到VERIFIED/WAITING_FOR_FINAL_REVIEW。

已验证：本人用实际磁盘原件独立复算40份native archive、5份driver artifact、当前24source和9份旧材料，零mismatch；前置preflight与completed的24/9 raw SHA map完全一致。两context的规范hash（去自身字段）、V2 snapshot的原projection（去phase/self/implementation-ref）、mutation的unsigned canonical hash均按实际源实现复算一致。不是仅信handback中的bool。

核心绑定如下，raw与canonical种类明确：

- `implementation-context.json` raw `b7564d854c2de14a1fa332abc006b28d4dbb9ff0e8c8afa16bfcd535dd9fead7`，canonical d648…如审核目标全文。
- pre-implementation `evidence.json` raw `28e9b4dce0f196e385338516371aedcef937af137267a38019b70e7d92408a5d`；snapshot6a71…如审核目标。
- verifier context canonical `bc219ede3636f454d72066ad6f6a7e99fa54af19d63a892c6d03740ff065519c`。
- mutation evidence canonical `9121e6ce452825ade6ed3d3ea3915dfd385b34a79f20e101df0bf753ffea7ea4`，raw `ea37a7c67a29595d1704a45e97cc336df00053d03a80bed12c139dd818f6fc2f`。
- `native-independent-handback-006.json` raw `60eade39b8bee791c14403d43f73c1c2e2b497d0b6a95a82e01b4a9181c26601`。
- `completed.json` raw `760ad8b52650c1d77e7bcab81ee4930b339d18123b2a7b94ed5638f4973318f9`；tool-terminal记录独立给出实际tool exit0，原retained native handle前后PID/creation相同并终态exit0。
- consumed receipt raw `96e74c288be5c176a03b5dcd153bcf18cae340801344e1d76f13c215d91c627b`。
- 本task追加便携事实026 raw `ed731624fdbdde4739c312e3a8e0d52ac5793b5c1f7092c59870b27d609b3536`，只作为原件指针，不替代独立审查。

私有原件以 `${PRIVATE_RUNTIME}/future-v2-006-preparation-001/final-binding-001/native-archive-006/`及相邻driver材料定位；新context在 `${PRIVATE_RUNTIME}/task56-post-v2-governance-006-001/implementation-context.json`。便携账本指针为 `.ai/tasks/TASK-0056/fixture-cleanup-current-prerequisites-passed-025.md`和 `native-v2-current-source-passed-026.md`，原run/MUTRUN refs按归档目录完整保留。

已验证：RF-001当前八个新增参数化case覆盖3种首次异常、2种secondary cleanup故障、完成nonzero、真实after-spawn KeyboardInterrupt、已reaped POSIX decode。真实case使用实际CPython base executable及保留Popen，Windows actual GetProcessId/GetProcessTimes/creation一致，原异常identity/args、poll终态/wait0及10/5 drain断言都在test fallback cleanup之前。此前当前模块原件42 passed/28.16s/exit0，现完整V2又实际通过。旧begin-close27个function仅原helper变化，另26个function AST全同，新增helper和5个test function组成8参数化case；不是删旧断言换绿色。该模块原件stdout raw `1ce84d0cdda9193cba408f2144d1e5efca51ddd15030d1b791658a76396bb7d9`。

已验证：此前current prerequisites包括narrow12、fixture97（旧65全保留）、external187/1原skip、integration600的906/1原skip实际529.81s；完整prerequisite collection907，旧867与新增8均零缺失。完整snapshot前后相等，87个已保留owned root有实际匹配终态，独立warm cold1/10命中完整成本median67.5486ms、实体与源pristine证明保留。warm parallel_selection_directly_instrumented=false，不把该时长当并发因果证明。当前完整native本身没有另外逐node collection，使用真实full selector及原件计数，不虚构新的逐node清单。

已验证的复用审查指针是 `source-review-preparation-001.json` raw `56d04275d7a94aeae894b00a7ece7b671b4e9d999988852a0ac60e08d22d0a40`、修正旧KBI/ownership夸大边界的 `source-review-adjudication-002.json` raw `eed4e93626639cb1c68bdda42fc1d05c5316d7a3c0b1260a40935c4b79f2050a`，以及本人当前修复实际阅读 `review-recovery-readonly-followup-008.json` raw `a7f09f6e8d3358322f13edea727becd70d6b22b5eb685ffe5f5a8da040d41bc2`。旧23路径未变使完整旧测试/说明阅读可复用；本轮已另按现值读取上述生产和高风险实现。

未验证：固定PR/publisher head的Python3.11 required CI及远端push/merge/branch protection/ancestry；当前Review正式record、旧RF formal resolution、finalize、code approval、Gate；Task55依赖重新准入、transport实现及其验证/Gate；F真实ZCode报告的来源与目标匹配。当前宿主3.13.15不是远端3.11结果。未观察的历史engine/后代和全局进程不存在保持UNKNOWN，未保留engine退出证据不补造。旧五轮失败、旧source113审查及首次integration002中断的exit/cleanup UNKNOWN仍按原件保存；随后独立通过不改写它们。没有provider/训练/后续阶段执行。

## 审核问题

默认与finalize/CI兼容是否仅由pytest通过推断？答：已读实际argv接入、default None分支、写入前mode拒绝、只读CI路径与verifier context构造；只有运行recipe追加占位符，runtime argv不进入finalize identity。

RF-001是否由新的完整V2自动关闭？答：没有。当前源码的首次BaseException恢复路径、原对象/args保留和真实retained直接子进程终态断言独立满足旧Finding的具体要求，当前完整V2又完成绑定；因此提出追加formal resolution的建议。旧r1/outcome/context保持。

copy Done、helper成功或当前exit0是否证明所有后代终态？答：没有。复制保留actual Thread并要求native join，无法证明时保持未完成；当前资源handback只覆盖有原件的已知retained process，未保留engine和历史后代仍UNKNOWN。

## 推荐结论

APPROVE

当前限定范围未发现新增Finding。建议以当前source9dca、上述源码控制流、当前helper八case/42pass和新的完整native006/snapshot为依据，解决旧REV-0009的RF-001；不将历史pass本身用作旧回退的解决证据。

后续由实际独立审查员在另行native写入GO后，先追加旧REV-0009 RF-001 resolution-r2，再record当前REV-0010/r1，保留旧outcome/context不变。实际latest_review_assessment先选最近implementation record/resolve事件再检查context；若在新Review后resolve旧context，将造成latest stale。此时未执行任何上述native动作。只有机械写入成功并由实际native后续检查认可，才由负责agent推进finalize、code approval和Gate；不提前声称完成。后续发布及Task55/F条件独立保持。

## 原生登记后的事实

本节为主 agent 在独立审查包原文之后追加的机械登记事实；前文描述的是
2026-10-01T07:07:36Z 审查产物生成时的状态，不更改独立审查结论。

实际审查员以相同 actor 执行两次原生 CLI，均退出 0：event110 于
2026-10-01T07:13:15Z 追加 REV-0009/r2 的 RF-001 resolved；event111 于
2026-10-01T07:13:57Z 登记当前 REV-0010/r1 APPROVE。旧 r1、旧 outcome
与 context 字节保留；native latest_review_assessment 实际选中了当前记录。

当前正式记录 raw SHA256：
`00e1bbd740c957304606678b4fd07554d654d73133985f39f704572d3f71e8c9`。
原生审查交还 raw SHA256：
`35f51eb96ccc3b44160088e8601305ea51da0fabac59e827249ba3b4afd45869`。
独立原审查包 raw SHA256：
`5538463733820e971e90a0e3b0ff9cfd5fc3ff87d53f50a503b998fe6aadbd01`。

主 agent 已独立检查实际记录、源码24、原件与事件顺序。当前 context
仍为 d648…、snapshot 仍为 6a71…，全文绑定见审核目标。原生记录实际
UTF-8 文本没有 replacement character；展示通道编码不作为原件修改依据。

此附录写入时，同一实际独立 verifier 已受委派执行单次 finalize；
其结果、代码批准与 Gate 尚未交还，后续实际结果以追加完成记录为准。
