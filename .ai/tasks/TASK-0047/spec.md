# TASK-0047 风险输入与动作拒绝边界

## 目标

补齐前轮清单中风险输入与本地动作权限的可实施缺口：新分类不能因字段缺失漏判风险，
未知动作不能默认获得本地允许；不把输入修正变成人审，不把本地批准伪装成可信执行授权。

## 范围

本任务包含两个独立分类的治理单元，共同使用一次有界 Policy 升级；最严重路由和所需批准
仍由 CLI 决定。DU-001 是风险输入，DU-002 是动作权限，不创建安全 DU 来降低分级。
源码范围以 task.yaml 的准确路径为准，旧任务目录、状态机、批准、新鲜度和 mutation 执行器
不在修改范围。独立效果/维护文档已在本任务 base 之前按 task-free 提交。

### DU-001：显式风险事实

1. 保留 decision-unit `schema_version: 1.0` 的历史读取兼容，新增可选
   `controlled_actions` 枚举数组，仅接受 `production_data_delete` 和 `deploy`，元素唯一。
   `impact_categories` 保留现有类型与枚举，历史契约层仍允许缺失。
2. `classify_task` 在同身份的既有分类 no-op 之后、任何新路由或写入之前，要求每个 DU
   显式具备 `impact_categories` 与 `controlled_actions`。缺项用稳定错误列出 DU 与字段，
   不修改任务、分类、事件或批准，不进入 WAITING_FOR_ASK / REVIEW；由 Agent 按已读事实
   补齐。类型非法、未知枚举、重复值由契约拒绝，不能从自由文本猜测这些字段。
3. start 仍创建待完善的草稿，不自动把未评估字段填成 `[]` 或 `documentation`。
   模板明确由 Agent 填写；只有确实评估为无相应风险时才显式写 `[]`，不增加人类打卡。
4. 分类 pending 恢复在任何写入或清理前核对当前身份、Policy 及风险输入完整性；旧 Policy
   marker 不能在新 Policy 下恢复成可执行分类。保留正确同身份重放，不利用重放绕过首次分类。
5. 生产删除/部署硬规则的 `match: any` 同时读取受控数组及旧 `planned_actions` 精确 token；
   任一个正向命中都保留 REVIEW。新数组为 `[]` 不能压掉已明确的旧高风险 token。
   自然语言计划继续可读，但不作 NLP 推断，也不能证明真实 shell 将执行什么。
6. categories 及受控字段的硬规则缺失策略为 `error`。分类写前校验负责可恢复的输入错误；
   较低层路由对不完整事实仍保持 fail-closed。不能把读旧账本改为全局强制迁移。
7. 风险事实进入现有 classification digest。旧任务仅在原 Policy/input/base/subject
   完全一致时可保持原分类重放；新建、事实变动或 Policy 变动后的实际重分类必须补齐。
   Gate/status/validate 仍能只读旧记录；旧分类不能满足新 Policy 的 begin/verify/approve/Gate。

### DU-002：默认拒绝的本地边界

1. permissions Policy 增加显式 `allowed_automatic_actions: [read]`，Schema 仅允许该
   已支持的只读类别；字段只适用于 permissions 文档。缺少此集合的历史 Policy 不获得
   隐式允许。保留六项 `forbidden_automatic_actions` 及其一对一 deny 规则，禁止允许/拒绝
   重叠、未知 allow 值或静默丢失原规则，不引入通用 `allow_automatic` 规则。
2. `evaluate_action_permission` 对已明确的 read 返回允许，对六项高风险保持拒绝，
   其他类别返回稳定默认拒绝原因且不把所需批准设成可放行的承诺。保留 trim/casefold 的
   canonical 类别处理；空值继续为确定性非法输入，不把别名、命令或自由文本转成安全类别。
3. pre-command 对未知类别在 task 自动选择、观察追加或批准读取前直接拒绝；畸形输入
   同样拒绝。明确的高风险类别保留既有 observation/refusal 路径，存在任何通用 action
   批准（包括 fresh）都不能改变拒绝、消费批准或执行命令。
4. 不新增 push/merge/deploy 消费器，不把 `freshness.py` 未被生产调用的通用 action 分支
   接入允许路径，不改它的兼容接口。该分支只保留为非执行性工具函数，不能作为已接通
   动作授权的证据。`targeted_mutation_v2` 的锁、二次验证、receipt 和执行器完全保持独立。
5. 可信执行器的最小安全设计与禁止扩大声明见 action-boundary-design.md；本次只实现
   本地拒绝语义。服务端身份根、授权原子消费与真实外部执行仍是未具备的产品能力，
   不声称仅靠本任务就能阻止用户、GUI、其他客户端或自由 shell 绕过 wrapper。

### Policy、自用恢复与安全配套

- 四份 Policy 一次性一致升为 `2.3.0`；routing 和 verification-levels 仅改版本，
  不改任何检查、阈值、超时、级别、V2 前缀、允许命令或运行目录。其余两份仅改上述语义。
- 当前规格按 `2.2.0` 分类/审核；落地最终 Policy 后，按既有 `policy_changed` 升级、
  有据 resolve、重分类、冻结和当前设计/spec 批准推进，不复制旧批准或改旧 hash。
  本任务两个 DU 届时按真实事实补 `controlled_actions: []`。预期一次 Policy 绑定恢复；
  不预先批准未知的新绑定、不承诺零额外批准，也不修改规则来跳过该恢复。
- 文档、测试及夹具为独立 task-free 安全配套阶段，分别提交；最终验证范围显式包含
  这些路径，以免集成时有范围外文件，不为它们创建混入治理任务的安全 DU。
  修改仅限本变更回归、共享输入夹具的显式风险事实、当前 Policy 版本断言及边界文档；
  不批量改写历史 task、旧证据或历史 Policy 绑定断言，不削弱测试。

## 非目标

- 不重开 TASK-0028、7 个历史 BLOCKED 任务、被否决的 B0–B2、已解释的 B3 或暂缓的 B4。
- 不进入阶段三，不实现模型路由、信任评分、费用/隐私采集或后台效果监控。
- 不增加通用权限执行器、身份系统、通用审批消费记录、命令解析器或安全沙箱。
- 不改变维护模式、main 保护、spec/code/action 批准绑定、ASK 义务或验证门槛。

## 验收条件

1. 新分类的两字段单独/同时缺失、非法类型、未知/重复受控动作均拒绝且零写；Agent
   补齐有效事实即可按原流程分类，明确无风险 `[]` 不额外触发 ASK/REVIEW。
2. secrets/auth、ci/cd 分类命中保留；两个受控动作分别及同时命中 REVIEW；旧精确动作
   token 在新 `[]` 下仍命中；普通自然语言不伪匹配，明确区分数据正确与真实动作正确。
3. 覆盖多 DU、已有同身份 no-op、pending 恢复、旧 Policy marker、风险事实改变的新鲜度、
   历史记录只读零写、Policy 更新后旧分类不能推进。TASK-0046 的共同 ASK/REVIEW 回归不退化。
4. read 只有在 Policy 明列时允许；未知/空/大小写/空白、六项高风险、缺/多/指定 task
   场景行为明确。未知拒绝零账本写入，高风险保留原观察；任何通用批准不改变结论且零消费。
5. schema/Policy 允许词表有一致性检查，拒绝 allow/deny 冲突及跨文档误用；旧 Policy 可读
   但不产生隐式允许。确认无新的外部执行入口，既有 targeted mutation 的保护测试通过。
6. 执行 CLI 要求的完整验证，独立检查总覆盖率至少 85%、diff coverage 至少 90%；
   完整 pytest、Ruff、format、mypy、whitespace 均通过。最终以绑定当前 subject 和 Policy
   的 evidence、独立实施审核、所需人类 code 批准及 Gate 为准。远端 CI 尚未运行。

## 禁止动作

不得 push、merge、deploy、delete、导出凭据、发起付费调用，或修改 GitHub/外部系统配置。
新建本地 task、编辑允许范围及阶段提交不授权外部交付；届时单独列出具体动作请求。
不得删除旧 worktree/branch、改写历史账本、降低规则或用本地 actor 字符串模拟身份认证。

## 错误行为

缺风险事实要报可修正的输入错误而不是默认无风险；未知动作默认拒绝而不是要求补一条
本地 action 批准后自动允许。Policy/范围/权限/规格变化按真实状态升级；若完整验证失败，
保留证据并在原授权范围内修复，不伪造通过，不以定向测试代替最终完整验证。

## 回滚

未交付的实现采用有界前向 revert 提交，恢复本任务触及的源码、Schema、模板和 Policy；
Policy 回退也必须走现有重分类与批准，不覆盖历史记录或恢复旧批准 hash。
已交付后另建有界修复任务，保留全部事件与证据；不强推、不删除分支或工作区。
