# TASK-0127 审核包

## 审核目标

交付经过目标 Policy 内容审阅的非覆盖资源初始化，建立新的仓库身份；不把安装完成称作 agent-bridge 或外仓 V2 已接入。

## 背景

真实实施前基线为 fb89032；测试先行并保持独立 task-free 提交。TASK-0126 资源分发及关闭文档已通过 PR138/139 合并，旧任务、失败与批准记录保留。

## 代码地图

initialization.py 管理固定 JSON 合同、资源/Policy、恢复/重放、ready guard 与只读检查；initialization_git.py 提供有界零写 Git 事实；initialization_windows.py 提供句柄绑定和原生独占创建/身份无覆盖发布。cli.py 在常规仓定位前分派 init，并在治理分派前检查状态；policy.py 的默认读取核对新式安装的采用决定。

## 语义变更

新增 preview/apply/inspect/migration-plan 四个入口。写入仅支持 Windows x64、CPython 3.11、本地 NTFS 的全新普通 Git 工作树。可验证 partial 保留原 UUID 并只创建缺失对象；完成重放零写；未知或修改后的对象保留并拒绝。资源和 metadata 保护到身份最后发布；源码包升级不自动替换目标资源。当前仅合成 Python 工程验收，不支持真实 Node 目标安装。

## 风险

摘要和 actor 标签不认证主体或授权。只保证明确测试的观察/发布边界，不声明整棵 Git 工作树原子锁、恶意同用户代码沙箱或断电事务。legacy 无标记仓不迁移；卸载不删除历史。Node 验证、installed-engine V2、目标 CI 和真实接入仍属后续交付。

## 证据

已验证：独立设计 REV-0001 APPROVE；预审发现的材料漂移、诊断缺项、Python 源要求、资源总量和仓内 Git 程序边界均已修复复核。稳定专项为 273 passed、2 项平台限定 skip，新三模块合计分支覆盖率 92%；全仓 Ruff、format、strict mypy、whitespace 通过。普通 wheel 的全模块来源/字节核对通过，但初次真实安装揭示 Win32 FileName NUL 缺口；旧失败 wheel 和现场保留。受控长度/canary 对照找到根因，新增独立回归及原对象发布后完整名称清单检查，修复 source 为 e0b264a2823ed9abd3d858cf2def225a4b14440f。修复后 Winhelper 72 passed、1 平台 skip，四项安装/重放/发布定向测试通过。所有含本机路径的原始材料只留本地忽略日志。

已验证：修复后的 ordinary wheel 完整验收通过，精确 source e0b264a，wheel SHA-256 ec8974ba1ac8a6775459890016e4d422189b342a32fa1f023362730f93faed39。全 47 个引擎 Python 模块与候选字节一致，七份运行依赖及所有加载来源均为独立环境。18 项验收与 33 条记录命令通过：零写预览、实际 NTFS 安装、完成重放、正常任务历史准入、原预览历史漂移拒绝、只读迁移、真实 flush 故障后同 UUID 恢复，以及精确旧版本 57f0676 的五个入口在无历史 partial 上拒绝且零写。原始报告含本机路径，仅本地保留。

当前完整原生 V2 未通过：source e0b264a 在保留的 run-20261031T053007522517Z 中为 4494 passed、2 项平台 skip、3 项真实 Windows 安装失败，用时 1155.68 秒，未超时；coverage/diff 和静态检查通过、五项 native 变异 killed 不替代这三个失败。两个直接 API traceback 位于资源创建前的祖先 CreateFileW；同一目标在两种环境只读重现系统临时目录的 LIST_DIRECTORY 访问拒绝。4070a016 动作已永久消费，失败 evidence、context、receipt 与原始日志保留。

独立权限对照确认：仅 READ_ATTRIBUTES 的句柄不能阻止目录改名，不可作为修复；TRAVERSE 加 READ_ATTRIBUTES 在系统临时目录可打开，且独立自建目录改名竞争被拒绝。后续仅祖先 pin 使用该已核验权限，真正目标根及资源目录保留原有权限/共享保护；不修改 ACL、不移动测试目录。

祖先 pin 修复已提交为 f57ee4f1ea592aacffc94bcbd82920638ffe1b6e，独立 companion 测试在先行提交 6e3ce58。完整初始化专项 283 passed、2 项既有平台 skip（136.61 秒），原三项失败在最小环境下定向通过。新增真实系统临时目录用例先证明自建父目录可改名，再证明安装持柄期间改名被错误 32 拒绝，并核对安装、ready、inspect 和零写重放。静态检查通过。冻结规格中的 0x81 描述历史最小实证组合；后文新目录所需 LIST/TRAVERSE/ATTRIBUTES/SYNCHRONIZE 与既有 public 0x1000A1 一致。独立审核确认本次只为祖先使用 0xA0/share3，未改变目标根和安装目录保护，属于原规格内修复。

f57ee4f 的普通 wheel 重验通过：SHA-256 为 37391cbee8902c8b55b05dafbbe458b8d57eddb84d1139dcd924b9a134f99e3b，47 个引擎模块逐字节对应候选。原 18 项检查、33 条记录命令全部通过；另在仅 PATH 与 SYSTEMROOT 的真实 Native 最小环境中，以同一独立安装的 wheel 在系统 Temp 自建仓完成原三项行为验收：安装/重放、七个对象保护到身份发布、CLI apply/inspect 相同目标与 UUID。报告原件仅保留本地忽略日志。

新一次性 action 9c86e24612b7b9a22ceb9169fde9c5b2619368d2ee018b99c06082ae6883eafb 经独立具体审核 APPROVE、无 critical/high，已依常设授权记录批准，绑定 f57ee4f；旧失败证据与消费记录保留。未验证：当前完整原生 V2、正式实现审核、code 批准、Gate 和远端 required CI 仍待完成。本记录不将旧 action 批准、旧 source 或部分测试当成当前完整证据。

## 审核问题

### 保留的实施预审发现 RF-001（medium，REQUEST_CHANGES）

独立完整源码预审在 f57ee4f 确认：普通 Python equality 会把 JSON 的 bool/int 或 int/等值 float 视为相等。受影响边界为 preview.target、preview Policy files、preview objects，以及 state 的身份对象大小和 Policy files。特别是 preview 资源 size 改为等值 float 后重新绑定摘要，会通过 apply 的比较并写入 state，随后 ready 的严格 int 检查拒绝该成功返回的安装。此发现必须修复，不降级或接受未解决风险。最小修复复用现有 canonical JSON 序列化作类型敏感比较；畸形 preview 应在创建 .ai 前零写拒绝，畸形 state 应 ready 拒绝且 inspect 给非空问题、保持零写。

run-20261031T061944449564Z 的执行会话已不可恢复，原 verifier/pytest 进程消失，只保留前置日志和 context，没有该 run 的完整测试结果或新 evidence。独立 verifier 已通过 CLI abandon 追加中断记录；退出原因和 pipeline cleanup 未确认，不报告测试数量、覆盖率、超时或成功。9c86 动作已用于一次 launch，不复用；因未观察到 mutation 消费回执，不能称已完成变异消费。CLI 当前拒绝生成正式 implementation context（requires passed evidence），本预审发现先保存在本审核包，待当前候选通过后在正式审核中引用并独立复核关闭。

RF-001 本地预审处置：测试提交 038c8a4 在源码提交 fd5f8f461d2a1bf1c1e1f0ac317324ef04440576 之前。原代码上的 11 案例得到 10 failed、1 passed，修复后同矩阵 11 passed；它们重新绑定摘要与完成标记，避免仅由旧摘要拒绝造成假绿。当前完整初始化专项为 294 passed、2 项既有平台 skip（100.26 秒），真实进程退出码为 0，包含合法安装、恢复和重放。静态检查通过。独立复核确认六处 canonical JSON 比较与精确提交绑定完整、原 medium 发现已满足本地关闭条件；正式实现审核仍等待新候选的完整 Native 证据和有效 context。只为本地验证增加隐藏启动与直接落盘回执，原 CLI、1200 秒预算、85/90 门槛和检查范围不变；它不认证 cleanup，也不声称解决了宿主中断原因。

当前 ordinary wheel 已重验：精确 subject fd5f8f4，wheel SHA-256 0792ffd75ba92197178aa750e9021e873b3525b6809c16d478f9b93cfbfb35b9；18 项检查、33 条命令、47 模块字节与安装来源全部通过。相同独立安装在 PATH/SYSTEMROOT 最小环境的系统 Temp 三项行为及七对象保护通过；另有 8 项 installed-wheel 重签错误数值类型输入，在创建 .ai 前拒绝，目录字节、对象身份与 mtime 均未变。各进程终局 exit 0，原始报告只在本地忽略目录保留。

当前新 action b87a70be610f6ab167cfd8e4911d0aadbed7d1dd9fa6c68e473f43c0e950ed07 已经独立具体审核 APPROVE，无 critical/high，并按常设授权记录批准，仅绑定 fd5f8f4 的一次固定 Native 运行。旧失败、中断、消费和未确认状态均保留。当前完整 Native、正式实施审核、code 批准、Gate 和 exact-head required CI 尚待完成。

当前完整 Native 终局现已通过：source fd5f8f4，run-20261031T071550159376Z，4514 passed、2 项既有 POSIX 行为 skip、929.95 秒，原 1200 秒预算不变。14 项 required checks 全部 passed；core 总 branch+line 覆盖率 89.852184%、diff 998/1072=93.0970%，analysis 总覆盖率 97.503900%、无 changed-covered lines；mypy 58 文件及其余静态检查通过。独立 verifier 重核五项 baseline 0 / mutant 1 / killed、日志原字节摘要和 canonical 证据，main_tree_unchanged=true、run_reason=null；本次 mutation 工作树、临时目录和 owned 进程均无残留。新 action b87a70 的消费回执有效且不可复用。verification snapshot 为 c4a11c2f31637b10f5aec10cd28899e3b97659e2f984627d9c9b4f1d50f7217a；CLI 处于 WAITING_FOR_FINAL_REVIEW，正式实现审核、finalize、code 批准、Gate 和 exact-head required CI 仍须完成。

初始化是否只创建受审清单且最后正确发布身份；中断、漂移、链接、未知状态和损坏是否拒绝且保留字节；新 CLI 是否在治理写入前拒绝不完整状态；legacy 与完整 native 门禁是否保持？

## 推荐结论

APPROVE。当前 fd5f8f4 的独立完整验证、安装验收与正式实现审核 REV-0002 均已通过，RF-001 保留原 medium 严重度并已独立复核 resolved。按常设授权记录当前 code 批准后仍须以 Gate 判断就绪；精确 PR head 的 required CI 通过且目标规则允许后，才能按常设授权 merge commit。
