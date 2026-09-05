# 分类期治理面守卫设计

状态：`design_input`。本文是设计输入，**不是实施计划，也不构成任何授权**。它不授权修改
Policy、schema、引擎或 CI，不授权推进原 Chapter B1，也不改变阶段三边界。任何落地都须
另行立项、分类并按当时生效的 Policy 取得批准。

前序记录：TASK-0040（REV-0001，8 条 open 发现）与 TASK-0041（REV-0001，8 条 open 发现）
两轮设计均被独立审核否决，结论见
[执行目录](../plans/2026-09-03-approval-overhead-and-open-task-consolidation-directory.md)
的 Chapter B0 与 B1。

## 1. 要解决的问题

`AGENTS.md` 把 `.github/workflows/**`、`.ai/policy/**`、`.ai/schemas/**`、`src/aiflow/**`、
`.gitignore` 与 `.gitattributes`、任务账本本身列为必须走 AI Flow 的升级清单。但**没有任何
可执行规则强制它**：

- `HARD-REVIEW-SECRETS-AUTH` 与 `HARD-REVIEW-CI-CD` 的条件都是 `missing: no_match`，
  而 `impact_categories` 在 `decision-unit.schema.json` 中不是必填 —— 字段一缺，规则静默失效。
- `impact_categories` 的封闭枚举是
  `documentation/ci/cd/secrets/authentication/production_data/external_action`，
  **没有 policy 或 governance 取值**，治理面变更根本无法被表达。

结果：清单是散文，引擎不认。

## 2. 两轮失败的共同模式

| | 错在哪 |
|---|---|
| TASK-0040 | 把 `priority` 当作路由仲裁机制。实际是 `routing.py:245` 按 `ROUTE_ORDER` 严重度取最大，`priority` 只决定写进证据的 `rule_id` |
| TASK-0041 | 把 `impact_scope` 里声明的 **glob 模式**当作变更**触及的文件** |

两次都是「推理文档与字段名，而非执行时真正发生的事」。本文的每一条机制论断都附代码位置，
第 4 节的核心原语附可复现的实测，第 5 节给出杀伤面与覆盖率的实测。

## 3. 决定：守卫置于分类期

项目所有者已决定：守卫置于**分类期**。本节明确该选择的能力边界。

分类期只能看到决策单元的自声明，看不到真实 diff（`aiflow scope` 在验证期才读 git）。
因此分类期守卫**守的是声明，不是现实**。这不是缺陷，前提是把它和验证期的强制拼成闭链
（第 6 节）。

## 4. 正确的原语：重叠，不是匹配

TASK-0041 的致命缺陷不是覆盖面，是语义。它拿声明的模式去和治理面模式做**匹配**，
而 `task_service.py:203` 默认直接以 `allowed_scope` 填充 `impact_scope` —— 两边都是模式。
用模式匹配模式，激励是反的：**声明越宽，越不会被捕获**。

正确的问题不是「这个声明等于治理面模式吗」，而是：

> **这个声明所允许的路径集合，与治理面路径集合是否可能相交？**

即**重叠**（语言相交），不是匹配。实测对比（保守过近似实现，宁可多判 REVIEW）：

| 声明的 `impact_scope` | 匹配判定 | 重叠判定 | 说明 |
|---|---|---|---|
| `src/**` | `False` | **`True`** | 合法允许改 `src/aiflow/` |
| `**` | `False` | **`True`** | 声明全仓库 |
| `.ai/**` | `False` | **`True`** | 合法允许改 `.ai/policy/` |
| `.ai/policy` | `False` | **`True`** | 裸目录条目 |
| `src/aiflow/predicates.py` | `True` | `True` | 精确声明 |
| `docs/**` | `False` | `False` | 无关，正确放过 |
| `tests/**` | `False` | `False` | 无关，正确放过 |

激励方向因此反转：**声明越宽，越会被捕获**。`**` 与一切治理面重叠，必然 REVIEW。

实现须复用 `src/aiflow/scope.py` 的分段方言（`_matches_parts`：`*` 不跨 `/`，`**` 匹配零或
多段），**不得引入 `fnmatch` 作为第二套方言** —— 两者在裸目录条目上结果相反。

## 5. 实测：杀伤面与当前覆盖率

设计不能只论证正确性，还须给出代价与收益的量级。以下两组数据在 `main` 提交
`f258477` 上复算，方法与口径一并给出，便于重放与质疑。

### 5.1 守卫会把多少现有 AUTO 翻成 REVIEW

对账本中全部 9 个 AUTO 决策单元，用第 4 节的重叠判定比对第 7 节的治理面清单
（保留「当前 task 自己的账本目录」系统例外）：

| | |
|---|---|
| AUTO 决策单元总数 | 9 |
| 翻为 REVIEW | **3（33%）** |
| 其中误报 | **0** |

三个被捕获的单元及其触及内容：

| Task | 触及 | 判断 |
|---|---|---|
| TASK-0003 | `src/aiflow/__init__.py` | 引擎源码，应当 REVIEW |
| TASK-0007 | `.gitignore`、其他 task 的账本日志 | 治理面，应当 REVIEW |
| TASK-0039 | `.ai/tasks/TASK-0031/evidence-failed-*.json` | **改写另一个 task 的追加式证据**，应当 REVIEW |

其余 6 个保持 AUTO 的单元，`impact_scope` 全部限于 `docs/**`、`tests/**` 与单个文档文件。

结论：在当前账本上，重叠判定的保守过近似**未产生任何误报**，守卫不会侵蚀 AUTO 路由的
适用面。TASK-0039 的例子说明它能抓到真实问题 —— 该单元改写了另一个 task 的证据文件，
而 `AGENTS.md` 明确要求既有记录不得重写。

### 5.2 治理面变更有多少发生在 AI Flow 之外

守卫只对已进入 AI Flow 的变更生效。因此须先量化「根本没走 AI Flow」的比例。

口径：取 `main` 上全部非 merge 提交，筛出触及治理面路径者；对每个 task 展开其
`base_commit..subject_commit` 区间作为窗口；判断该提交是否落在任一窗口内。

| | |
|---|---|
| 触及治理面的非 merge 提交 | 78 |
| 账本纪元之前（`2026-08-21T11:21:30Z` 之前） | 32 |
| 纪元之后 · 落在某 task 窗口内 | 39 |
| 纪元之后 · 不在任何窗口内 | **7** |

账本纪元取最早 task 的 `created_at`。此前章节 1–7 由 `docs/superpowers/state/` 跟踪，
CLI 本身尚在构建中，不存在可比的账本，因此这 32 条不计入缺口。

**纪元之后的覆盖率为 39/46 ≈ 85%。**

7 条缺口全部发生在 `2026-08-30` 同一天，其中 4 条直接改动 `.ai/bootstrap-mode.yaml`
或读取它的 `.github/workflows/ai-quality-gate.yml`：

```
ca4cfaf5  governance: exit bootstrap self-development   .ai/bootstrap-mode.yaml
fe4fa6c6  chore: add bootstrap auto mode                .ai/bootstrap-mode.yaml + workflow
8e82e3c3  ci: harden bootstrap quality gate             workflow
9837fc32  ci: fix cross-platform bootstrap checks        workflow
```

**未验证的解读（标注为推断，非测量）：** 这批提交看起来是治理开关本身被切换、治理尚未
生效的那段过渡期产物，即自举系统的先有鸡还是先有蛋，而非常态泄漏。该解读基于「7 条同日」
与「4 条直接触及 bootstrap 开关」两项事实，但未经独立复核。

**方法的已知局限：** 窗口按当前 `main` 的提交图展开。若某 task 的区间在后续 rebase 或
合并中被改写，其提交可能不再落在今天的窗口内。因此 7 条是缺口的**上界**，不是精确值。

### 5.3 这两组数对设计的影响

1. 分类期守卫**有效且代价可控**：覆盖已进入 AI Flow 的 85%，零误报。
2. 「治理面变更必须先有 task」的**入口强制仍然需要，但优先级低于本守卫**：它要堵的是
   约 15%，且其中多数集中于一次性的 bootstrap 过渡。
3. `.ai/bootstrap-mode.yaml` 进入治理面清单的理由由此获得实测支撑，不再只是推理 ——
   7 条缺口里有 2 条直接改动它。

## 6. 闭合的防御链

分类期守声明、验证期守现实，两段拼成闭链：

1. **声明得窄以逃避守卫** → 分类期不命中，但验证期
   `scope.py` 的 `assess_auto_scope` 要求每个提交路径**同时**匹配 task scope 与某个 AUTO
   单元的 `impact_scope`；实际触及的治理面文件会落进 `out_of_scope`，Gate 失败。
   **逃得过分类，提交不了。**
2. **声明得宽以便能提交** → 重叠判定命中 → REVIEW。

两条路都堵死。这也解释了为什么原语必须是重叠：只有重叠判定才让第 2 条成立。

## 7. 治理面清单

守卫应覆盖 `AGENTS.md` 升级清单的全部路径项，加上一处清单未列但实际更关键的：

- `.github/workflows/**`、`.ai/policy/**`、`.ai/schemas/**`、`src/aiflow/**`
- `.gitignore`、`.gitattributes`
- `.ai/tasks/**`（任务账本）
- **`.ai/bootstrap-mode.yaml`** —— `.github/workflows/ai-quality-gate.yml` 以它决定
  `aiflow verify` 与 `gate` 是否在 CI 中运行。它是整个治理引擎的开关，却不在
  `AGENTS.md` 的路径清单里（受该文件另一条「未经项目所有者明确决定不得移除」约束）。

`.ai/tasks/**` 需要一处例外：`scope.py:142` 的 `is_task_governance_path` 已把「当前 task
自己的账本目录」作为系统例外；守卫应保持同一豁免，否则每个 task 都会因写自己的账本而被
强制 REVIEW。

## 8. 未解决的张力（落地前必须先有结论）

1. **REVIEW 吞掉 ASK —— 已确认为既有缺陷，非本守卫引入。**
   用真实引擎（`load_policy_bundle` + `route_decision_unit` + `classification_service._target`）
   实测三个场景：

   | 场景 | 单元路由 | 任务状态 | 命中规则 |
   |---|---|---|---|
   | 仅 `business_direction_count=2` | `ASK` | `WAITING_FOR_ASK` | `ROUTE-ASK-MULTIPLE-DIRECTIONS` |
   | 同上 + `impact_categories=[ci]` | `REVIEW` | **`WAITING_FOR_SPEC_REVIEW`** | `HARD-REVIEW-CI-CD`，**`ROUTE-ASK-MULTIPLE-DIRECTIONS`** |
   | 仅 `impact_categories=[ci]` | `REVIEW` | `WAITING_FOR_SPEC_REVIEW` | `HARD-REVIEW-CI-CD` |

   第二行是关键：ASK 规则**确实命中了**（出现在 `matched_rules` 中），但
   `routing.py:245` 的 `max` 把单元路由压成 REVIEW，`classification_service.py:74` 的
   `any(entry.route == "ASK")` 因此看不到它 —— 该检查读的是**单元的有效路由**，不是命中
   规则集合。**今天 `HARD-REVIEW-CI-CD` 就已经在静默丢弃 ASK 义务。**

   因此这不是本守卫的设计缺陷，而是引擎既有缺陷：**任何 REVIEW 路由规则与 ASK 规则在
   同一决策单元上共同命中时，用户选择义务都会消失**。本守卫会扩大该缺陷的暴露面
   （治理面变更将更常触发 REVIEW），但不制造它。

   账本实测：`business_direction_count >= 2` 的决策单元共 1 个（TASK-0034/DU-001），
   且该单元同时触及治理面 —— 即历史上唯一的 ASK 用例正好落在碰撞条件上。样本量为 1，
   不足以推断发生率。

   修复方向（须单独立项，不在本守卫范围内）：让 `_target` 读 `matched_rules` 而非单元
   有效路由，或把 ASK 义务移出 route 维度。**本守卫落地前应先记录该缺陷，落地时须在
   验收中固定其行为，使其不因扩大暴露面而被遗忘。**
2. **`missing` 策略无处安放。** `impact_scope` 是 schema 必填，`missing: match` 的
   fail-closed 分支**永不可达**；写了也只是装饰，不应作为验收条件。
3. **`impact_categories` 的 `governance` 取值。** 若守卫锚定 `impact_scope`，该取值不被任何
   规则读取，则 REV-0001/RF-003（规则依赖可选字段而静默失效）并未关闭。要么让某条规则读它，
   要么不新增该取值、并明确记录 RF-003 由本守卫以另一路径关闭。
4. **本守卫只约束已进入 AI Flow 的变更。** 实测（第 5.2 节）：账本纪元之后触及治理面的
   46 条提交中 39 条落在某个 task 窗口内，覆盖率约 85%；7 条缺口全部集中在
   `2026-08-30` 的 bootstrap 过渡期。因此该边界是真实的但量级有限，不构成放弃本守卫的
   理由；「治理面变更必须先有 task」的入口强制应单独立项，优先级低于本守卫。
   另须如实记录：只要 `.ai/bootstrap-mode.yaml` 处于 active，CI 就跳过 `aiflow verify`
   与 `gate`，第 6 节第 1 条的验证期强制在 CI 中并不执行 —— 落地时不得声称「已在 CI 中验证」。

## 9. 与原 Chapter B1 的关系

B1（放宽 AUTO 的 `impact.level`）在本守卫落地并验证前保持 `blocked`。但须注意：**本守卫
不足以让 B1 自动成立**。B1 另有两处独立缺陷未被本文处理 ——
`_AUTO_GUARDS`（`routing.py:15`，`routing.py:164` 要求超集）是引擎级 AUTO 守卫下限，
放宽它会降低所有现有与未来 AUTO 规则的门槛；以及 B1 的立论依据本身（「17 个只差
`impact.level`」测的是哪个守卫挡住了 AUTO，而非是否需要人类审核；其中 4 个实际收到 8 条
审核 finding 与 7 次 `REQUEST_CHANGES`）。这两点须各自单独解决。

## 10. 非目标

- 不修改 `_AUTO_GUARDS`，不新增或放宽任何 AUTO 规则。
- 不把 `impact_categories` 改为必填 —— 会使 41 个历史 task 记录不再通过 schema 校验。
- 不改动既有八条 `HARD-*` 规则的 id、priority、条件或命中结果。
- 不改动 CI 质量门禁的检查项与阈值，不改 `main` 分支保护。
- 不引入第二套 glob 方言。
