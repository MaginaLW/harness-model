# Review Package

## 审核目标

判断 `package_publish` 自动禁止规则、封闭 Schema 扩展和匹配测试是否满足当前冻结规格。

## 背景

试点要求将包发布保留为独立人工动作，不允许 AI Flow 自动执行。初次 Policy 变更后已显式
升级、解除、重新分类和重新批准规格；一次 V1 因格式检查失败，显式重试后通过。

## 代码地图

- `.ai/policy/permissions.yaml`：新增禁止动作和 deny-automatic 规则。
- `.ai/schemas/policy.schema.json`：在两个封闭动作枚举中加入 `package_publish`。
- `tests/unit/test_permissions_policy.py`：验证动作与独立 action approval 规则。
- `tests/integration/test_templates_and_policy.py`：更新完整禁止动作集合。
- `tests/integration/test_start_command.py`：更新新任务默认禁止动作集合。

## 语义变更

新任务自动继承 `package_publish` 禁止动作；Policy 加载仅接受声明了该动作的 schema-valid
规则。该变化不发布任何包，也不授予执行发布动作的权限。

## 风险

- Schema 与 Policy 不一致会使 Policy 加载失败；契约与全回归已覆盖。
- 遗漏默认动作断言会造成测试漂移；第二轮范围扩展已补齐。
- 此规则仅禁止自动执行；真实发布仍需要单独 action approval，且本试点未执行发布。

## 证据

- 已验证：subject `f3d70bd41768dab583e3f2582d13ad9088a2630b` 的真实 V1 通过。
- 已验证：contract、scope、ruff check/format、smoke、unit、regression、mypy、coverage XML、
  diff coverage 共 10 个 required check 全部 passed。
- 已验证：业务 diff 为 5 个文件，48 insertions、2 deletions；`git diff --check` 通过。
- 已验证：第一次失败 evidence 与第二次通过 evidence 分别保留在独立 run 目录。
- 未验证：没有执行包发布、push、merge、deploy、凭据访问或其他外部动作。

## 审核问题

- Policy、Schema 和三组测试是否共同覆盖 `package_publish` 的自动禁止语义？
- 是否同意当前 passed evidence 支持进入 `APPROVED_FOR_MERGE`？

## 推荐结论

APPROVE
