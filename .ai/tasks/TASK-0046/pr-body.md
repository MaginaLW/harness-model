## 变更

- 恢复同一决策单元 REVIEW+ASK 共同命中时的方向选择义务；回答后仍须规格与代码审核。
- 分类、回答和 Gate 使用一致的 ASK 判定；同级/更低路由丢失 ASK 受降级门保护，BLOCK 优先不变。
- 补充真实 CLI 生命周期、单元绑定、升级/降级及非法分类零写回归。
- 附带已独立提交的低干预效果基线与维护快照；不增加填报、审批或后台采集。

## 验证与审核

- 完整本地 V1：10 项必需检查全部通过，1,657 项全量测试通过。
- 总覆盖率（含分支）87.98%；19 行可执行差异覆盖率 100%。
- Ruff、format、mypy、whitespace、contract、scope、smoke 均通过。
- 独立设计/实施技术审查 REV-0076、REV-0077 通过，项目所有者已批准规格与代码。
- 本地 TASK-0046 Gate PASS；本 PR 仍须远端 required `ai-quality-gate` 成功后才可合并。
- [实现审核包](https://github.com/MaginaLW/harness-model/blob/6e4247d862841d9894569ef66f41ac9afae8976a/.ai/tasks/TASK-0046/review-package.md)

## 边界

不修改 Policy、Schema、CI 门槛、维护模式或分支保护，不支持多个 ASK 单元，不宣称已测得
人工成本下降。推送/创建 PR/CI 成功后合并已有单独授权；不删除分支，不部署，不绕过保护。
合并后仅追加真实合并账本与必要交付说明，不重写既有记录或证据。
