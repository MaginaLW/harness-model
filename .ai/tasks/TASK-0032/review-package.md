# Review Package

## 审核目标

确认 TASK-0032 的 subject `7a27dd9dda01062f97080d549b31f692bd5214d8` 完整实现冻结规格中的仓库文件卫生改进，并允许进入本地只读 Gate。该批准不授权 push、merge、deploy、删除、task close、网络调用、凭据访问、付费服务或新的 targeted mutation。

## 背景

- Base commit：`5f52afe465e55801597a8ab562d76d24061e3133`
- Subject commit：`7a27dd9dda01062f97080d549b31f692bd5214d8`
- Frozen spec SHA-256：`d7d2a22a988e5ecd34ccc30241baf79913eb491ce2cfcba4073ac042bae481f0`
- Classification input SHA-256：`294ae375b76576c37cae7c3e9d03ed09745f3d0ebba07696bdaf84bcda4c71dc`
- Active Policy SHA-256：`1f684f4bf4bd2e3c28b7a04903628790f7be40f88a1dbf54587b09b90230267f`
- Design review：`REV-0068` / `APPROVE`
- Implementation review：`REV-0069` / `APPROVE` / findings `[]`

## 代码地图

- `.gitignore`：新增仅匹配仓库根目录的 `/.coverage.*`、`/build/`、`/dist/`、`/htmlcov/`，不扩大通用日志或 XML 忽略范围。
- `CLAUDE.md`：缩减为 Claude Code 平台适配入口，明确 `AGENTS.md` 是唯一共同权威。
- `README.md`：同步入口描述和恢复文档导航。
- `docs/operations/recovery.md`：记录 task-local 运行证据保留、精确清理、可恢复性和历史绝对路径不可追溯改写边界。
- `tests/integration/test_agent_entry_files.py` 与 `tests/integration/test_repository_hygiene.py`：覆盖入口权威、根目录/嵌套路径正反例、唯一 task-log 规则、普通日志/XML 可见性和恢复文档契约。

## 语义变更

未来仓库根目录的 Python 构建、分发和 HTML 覆盖率产物会被精确忽略；同名嵌套路径、普通日志、XML 报告和 task-local 审计边界不被扩大隐藏。Claude Code 入口不再复制共享治理规则，文件清理和历史审计路径边界得到明确记录。除 task-local append-only 治理与验证证据外，业务改动仅涉及六个冻结允许路径；未修改运行时代码、Policy、CI、接口或历史审计记录。

## 风险

- 根目录限定规则若被未来改成宽泛通配，可能隐藏包内同名源码目录；正反例集成测试用于阻止该退化。
- task logs 在本地被忽略但不承诺跨 clone 或新 worktree 持久化；恢复文档要求按精确 task、run 和文件保留或批准清理。
- 一次错误使用系统 Python 的失败验证已作为历史证据保留；最终证据只接受仓库 `.venv` 中元数据与运行时均为 `0.2.0` 的重验。

## 证据

- 已验证：Evidence 文件 SHA-256 为 `b2ee5a2866de8c02d3f594e6c4c5f167e426db705dd94c2708062b62671d7d78`；snapshot 为 `fba3d60891ae3f07c69ad849c9948065022cb00cbffd2f27510a5b2d6a4f4afb`；schema `2.0`、mode `local`、phase `final`、conclusion `passed`。
- 已验证：14/14 required checks passed，`unverified_scenarios: []`；unit 1085 passed、3 skipped；regression 与 coverage 1603 passed、4 skipped；integration 481 passed、1 skipped；acceptance 9 passed。所有 skip 均为 Windows 主机不支持测试所需符号链接创建。
- 已验证：Ruff check、Ruff format、mypy、contract、scope、smoke、diff coverage 均通过；`MUT-V2-001` 至 `MUT-V2-005` 全部 killed，最终 mutation evidence SHA-256 为 `1da4eb49db7a9af2f52f4dc1c639ff5ccef8334406be44b92b1ec2549e4f1565`。
- 已验证：独立实施审核 `REV-0069` 为 `APPROVE`，无 findings，并绑定相同 subject、snapshot、spec、Policy 与 classification。
- 未验证：push、merge、deploy、删除、远程 CI、task close、网络调用、凭据访问和付费服务；当前批准不覆盖这些动作。

## 审核问题

- 六个业务文件是否完整满足冻结规格且未越过允许范围？
- 根目录忽略规则、task-local 证据边界和普通日志/XML 可见性是否保持 fail closed？
- final V2 evidence、独立实施复审和版本绑定是否足以允许本地只读 Gate？

## 推荐结论

`APPROVE`：仅批准当前 subject 进入本地只读 Gate；不授权 push、merge、deploy、删除、task close、新 mutation、网络、凭据或付费动作。
