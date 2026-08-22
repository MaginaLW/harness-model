# Task Specification

## 目标

在阶段一 `0.1.0` 基线上建立独立、可审计的阶段二设计与实施目录，明确以当前 `harness-model` 为首个跨模块 REVIEW 自举目标，并初始化 Chapter 8“结构化双阶段审核”的章节状态与交付边界。

## 范围

- 新建阶段二设计规格与实施目录，覆盖结构化审核、V2、独立 Verifier、定向变异、升级观测、Hooks 和最终自举试点的顺序、依赖与退出条件。
- 新建 `chapter-08.yaml`，只初始化结构化设计审核/实现审核及最小审核上下文的任务清单，不宣称运行时能力已经完成。
- 更新总体状态和 README，使阶段二从 `not_started` 进入 `planning`，并记录当前仓库、测试类型和业务风险。
- 新建 Chapter 8 实施追踪文档骨架。
- 当前任务 `.ai/tasks/TASK-0004/**` 治理记录。

## 非目标

不修改 Python 运行时、Policy、schema、模板、测试、CI 或 Hooks；不实现 V2、双审核、独立 Verifier、变异测试、升级传感器、模型路由或资源调度；不把规划状态写成已经验证或完成。

## 验收条件

1. 阶段二规格明确目标、非目标、信任边界、兼容性、失败语义和六类验收输入，并把当前仓库固定为首个跨模块 REVIEW 目标。
2. 实施目录将阶段二拆为 Chapter 8 至 Chapter 13，每章均有进入条件、任务、验证和退出条件；V3、模型路由和调度保持非目标。
3. Chapter 8 状态文件只标记初始化完成，所有运行时实施任务均为 `pending`，统计与总体状态一致。
4. 总体状态保留阶段一已完成事实，同时将阶段二标记为 `planning`，当前章节为 `chapter-08`。
5. YAML 可解析，Markdown 引用路径存在，阶段二需求到章节的追踪无遗漏；`aiflow validate/scope`、Ruff、格式检查、测试和 `git diff --check` 通过。

## 禁止动作

push、merge、deploy、delete、secret export、paid external call、package publish，以及使用本规划任务的通过结论替代后续 design/spec approval 或运行时验证。

## 错误行为

若阶段一进入证据不完整、目标仓库或测试类型不明确、章节依赖形成循环、统计不一致、规划宣称未实现能力已完成，或需要修改 Policy/代码，任务必须失败或升级并重新冻结。

## 回滚

所有变更均为仓库内文档与状态记录，由 commit 保护。若规划有误，以后续获批任务显式修订或 revert，保留本任务事件和证据，不改写历史。
