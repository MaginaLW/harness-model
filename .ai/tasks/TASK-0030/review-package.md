# Review Package

## 审核目标

决定是否接受 TASK-0030 在 subject `acff6cac45c8c7be64bb8a83dbf264fd039e3f17`
上的完整实现。当前增量只修复 GitHub Actions run `33445448671` 暴露的两项 Linux 测试
自包含性问题；生产 Policy、verification runner、状态机、检查集合和阈值均不改变。审核通过后
仅可请求当前版本的代码批准并执行本地只读 Gate；merge 仍未授权。

## 背景

TASK-0030 已完成 Policy `2.2.0` timeout、精确 PR head SHA branch attachment 和 formal
runner/Python temporary-root 对齐。subject `ebea414fc168f35e0b0abd810f2c27bc1ad71964`
通过本地 V1、独立实现审查和代码批准后，真实 run `33445448671` 已进入 formal V1，但
regression 与 coverage 各报告同两项失败：

- clean-checkout E2E 在 uv-created active Python 无 `pip` 时，从 runner 有意收敛的最小
  `PATH=/bin:/usr/bin` 查找 `uv`，因此错误失败；
- V0/V1 evidence reproduction 用例没有使用文件内已定义的 controlled full-category plan，
  而是递归执行 host 的真实 V1 toolchain；首次 evidence 失败后，状态机正确拒绝从 `FAILED`
  直接 replay，`Task is not ready for verification` 是次生错误。

本次冻结规格为 `089ef571afc432f5e1f5068fb9593e3bb025cbe6144d0cbd01c64fd737fdd124`，
active Policy 为 `1f684f4bf4bd2e3c28b7a04903628790f7be40f88a1dbf54587b09b90230267f`，
classification input 为 `1613b7d38b31071260068d75e26c1d25fe05e6ed12011b168a9a3dc6de123761`。
设计审查 `REV-0065` / context
`6f7cb2c37c1a1c489f79e470fbd66a051f04cde940495ebf3d78615500fac071` 无 findings，
所有者已批准该规格。旧 evidence、review、approval 与失败 CI run 仅作为追加式历史保留。

## 代码地图

- `tests/e2e/test_clean_checkout.py`：active interpreter 有 `pip` 时保留原安装路径；无 `pip`
  时验证 `sys._base_executable` 指向存在文件，并由 base interpreter 执行同一
  `pip install --disable-pip-version-check --no-deps --target`。后续文档命令仍使用 active
  interpreter 与隔离 `PYTHONPATH`。新增 focused test 固定无-pip 分支的解释器和完整 argv。
- `tests/integration/test_verification_evidence_flow.py`：V0/V1 evidence reproduction 显式将
  `verification_service.parse_verification_plan` 绑定到文件内既有 `_full_category_plan()`；
  首次验证、recorded replay、全部 required check identity 与 Gate 断言保持不变。
- `.ai/tasks/TASK-0030/**`：保存规格扩展、设计审查、批准、subject sync、V1 evidence 和本次
  implementation review 绑定，不修改任何其他 task artifact。

## 语义变更

仅测试夹具语义变化。clean-checkout 测试不再要求 `uv` 暴露在 verification runner 的继承 PATH；
当 active interpreter 缺少 `pip` 时，改由其有效 base interpreter 承担安装，安装目标、参数、
后续解释器和隔离环境不变。evidence reproduction 测试使用原已存在的 controlled plan，仍生成
完整 V0/V1 check identity 并验证 recorded replay 与 Gate，但不再递归执行环境敏感的真实
Policy toolchain。

没有修改 `.ai/policy/**`、`.github/workflows/**`、`src/aiflow/**`、依赖、锁文件、覆盖率要求、
diff coverage 门槛、FAILED 状态的重验前置条件或自动重试行为。

## 风险

- base interpreter 不存在或不可执行时必须继续 fail closed；实现先验证属性存在及目标为文件，
  安装命令 nonzero 仍由原 `_run` 断言暴露。
- 错误切换解释器可能使文档命令不再验证 active environment；实现只用 base interpreter 安装，
  后续命令继续显式使用 `sys.executable`。
- controlled plan 若漏掉类别会弱化 evidence contract；测试继续将实际 check tuple 与完整
  `V0_CHECK_IDS` / `V1_CHECK_IDS` 精确比较，并执行首次 verify、recorded replay 和 Gate。
- 本地 Windows symlink capability 的四项 skip 仍存在；它们不是本次新增或被掩盖的失败。
- 未执行 merge、deploy、发布、凭据访问、付费调用、分支删除或 GitHub 配置变更。

## 证据

- 已验证：current V1 evidence 为 `passed`，10/10 required checks 全部 passed，canonical
  evidence SHA-256 为 `553e81970629f8cddd7b3c966acda784932597b627c782705c556d3480e1d3ec`，
  `unverified_scenarios: []`。
- 已验证：unit 为 `1085 passed, 3 skipped`（36.05 秒）；regression 为
  `1599 passed, 4 skipped`（768.20 秒）；coverage 为 `1599 passed, 4 skipped`
  （793.67 秒）并生成 XML；mypy、contract、scope、Ruff、format、smoke 和 diff coverage
  全部 passed。
- 已验证：两文件组合 focused suite 为 `6 passed`；另强制 active interpreter 无 `pip` 的
  真实 clean-clone 安装、文档命令和安全任务示例完整通过。
- 已验证：业务 diff 只新增上述两份获批测试文件的修改；Policy、workflow、生产运行时代码、
  TASK-0025/TASK-0029 与其他测试均无本轮差异。
- 未验证：subject `acff6cac45c8c7be64bb8a83dbf264fd039e3f17` 的真实 GitHub
  `ai-quality-gate` 尚未运行；它必须在新的 implementation review、代码批准、本地 Gate 和推送
  后通过。run `33445448671` 保持 failed 历史，不得改写或复用为成功 evidence。

## 审核问题

- 无-pip fallback 是否只选择有效 base interpreter，并保持完整 pip 参数、安装目标与后续
  active-interpreter 隔离执行？
- 是否完全移除了对最小 PATH 中 `uv` 的依赖，而没有扩大 runner 环境或修改生产安装逻辑？
- controlled plan 是否仍覆盖完整 V0/V1 check identity、首次 evidence、recorded replay 和 Gate？
- 是否存在对 FAILED 状态重验、真实 Policy plan、runner、workflow、阈值或范围的隐式放宽？
- 当前 evidence、spec、Policy、classification 与 subject 是否精确绑定且无未披露动作？

## 推荐结论

若独立 implementation reviewer 确认上述边界、diff 和 evidence 一致且无未关闭的 high/critical
finding，建议 `APPROVE`，随后请求所有者对当前 subject 与 evidence 进行新的代码批准。
