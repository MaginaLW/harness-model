# Review Package

## 审核目标

确认 TASK-0078 的 CLI 根定位与 Schema 作用域符合冻结规格，并裁决本地代码批准。发布另以当前 required CI 为门。

## 背景

原 base 为 1694900b1049df55b0861fb3c88a924be16f016e，源码 subject 为 acd05b14a09e16e87394f8920ef854170165a585。项目所有者已批准冻结规格；精确补入两个独立安全 fixture 的累计范围 metadata 后，重新分类仍为 REVIEW/V1。原 TASK-0077 的 REQUEST_CHANGES、BLOCKED 状态及追加式 finding resolution 保留。

## 代码地图

三个源码文件为 src/aiflow/cli.py、src/aiflow/git_context.py、src/aiflow/contracts.py。先前独立提交的验收测试覆盖真实仓内子目录、Git 边界与 Schema 隔离；独立 companion 提交 d44c21a 仅调整 Gate parity 的真实 Git 前提及 UUID 测试的单一身份输入，原断言保留。

## 语义变更

业务 CLI 参数解析后定位一次 Git 根，服务和默认 Schema 使用该根。显式 Schema 目录优先，ContextVar 在 finally 中恢复，主 Schema 与 registry 同源。调用不 chdir；六类用户文件参数保持相对调用目录。帮助、版本、无命令及参数错误保留仓外行为；非 Git、无关根及跨 nested .git 边界拒绝，不外借父仓资源。

## 风险

Git 环境仍按既有方式继承；本次只校验根的祖先关系和 crossed .git 边界，不新增环境净化。完整克隆须具备自身 .ai 资产；本次不提供初始化、身份复制、资源分发或目标 CI 适配，不改变 Policy、Schema、权限或质量门槛。

## 证据

- 已验证：Native V1 原件为 evidence.json，run 为 logs/run-20261011T082238159930Z；十项 required checks 全 passed，三个 pytest 检查共享一次完整执行：1895 passed in 634.96s。总覆盖率 88.66%，diff coverage 97%；Ruff、format、mypy、scope、contract、smoke 和 whitespace 通过。
- 原始 evidence 含本机路径，原字节保持本地 untracked，不入库、不在同路径生成替代件。规范 evidence digest 为 60035166f73b29b29cfbdc0ff9a8b9649e0f7e772298e8640d62f25cf6ca70ea。公开审核绑定不包含本机路径，原件不宣称公开可取。
- 正式独立实现审核直接引用 reviews/REV-0003-r0001.json 和 reviews/REV-0004-r0001.json；均为 APPROVE、无发现，共同绑定 implementation context 2d75e7892b9743d4865909d73f47041a7b7bdaba42f8d509eeb7a33d8422f4a6。
- 首次整合为 212 passed / 8 failed：七项 Gate 旧 fixture 未满足真实 Git 前提，一项 UUID fixture 复制整个 .ai 导致 Windows 路径过长。修正 fixture 后定点 9+1 与整合 220 passed，再执行上述完整 V1；失败没有改判成通过。诊断原件保持原处。
- 复现：使用该克隆的隔离 Python 环境运行 python -m aiflow verify TASK-0078 --actor codex-main。完整测试临时根在 Git 仓外；总覆盖率另以同一 run 的 COVERAGE_FILE 和 python -m coverage report --fail-under=85 检查。
- 尚未验证：当前发布 head 的 GitHub required CI，待 PR 创建后独立核对。没有真实外部项目、provider、评分或高风险执行验收。

## 审核问题

根定位与 cwd/文件参数语义是否同时保持？Schema 优先级、隔离和退出恢复是否同源？Git nested/linked 和继承环境边界是否拒绝错误资源？验证与独立审核是否绑定当前候选并保留失败和未知？

## 推荐结论

APPROVE：两名非作者正式实现审核均 APPROVE，无未关闭发现；当前 Native V1 与额外总覆盖率检查通过。代码批准按常设授权记录；推送和 merge commit 仍须当前 required CI 通过。
