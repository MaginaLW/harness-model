# Chapter 10：独立 Verifier 与 V2 evidence/Gate

状态：completed

本章交付 V2 的 task-local actor 比较、最小 Verifier context、两阶段 evidence 和 Gate 绑定。Chapter 10 已基于 TASK-0009 的 V1 基线验证、结构化审核、代码批准与只读 Gate 事实完成退出核验；这不等同于真实 live V2 passed。

## 退出结论与证据绑定

- 实现 subject 为 `8eee9c1bb3c7c4ac35aa7843a1a3ec85e0fb4326`；基线 Gate attestation HEAD 为 `ed9ef1e5a781713e1798075c3013a4a1727d0375`。
- 在该 attestation HEAD，`aiflow validate TASK-0009` 有效，`aiflow scope TASK-0009` 为 scope-valid，`aiflow gate TASK-0009 --format json` 为 passed；`8eee9c1..ed9ef1e` 仅含 TASK-0009 自身治理路径。
- 当前 evidence、结构化设计/实现审核、代码批准与 Gate 结论均绑定上述 TASK-0009 subject 及其冻结规格、Policy 和 classification 版本。
- TASK-0009 仍是 `APPROVED_FOR_MERGE`；本章节退出没有记录或声称 external merge。

## 已实现边界

- Implementer 取当前实现周期最近一次 `implementation_started` 或 `implementation_retried` 事件；Verifier 取 `aiflow verify --actor`；Reviewer 继续来自结构化 review record。
- actor 只是 trim 后精确比较的 task-local 标签，不作人员、模型或外部身份认证。V2 需要非空、不同的 Implementer/Verifier，并在启动 runner 前拒绝不满足的输入；V0/V1 不倒灌此要求。
- Verifier context 为 hash-addressed、task-local immutable 文件，只含目标、冻结规格、允许范围/代码地图、subject diff 路径和 numstat 摘要、验收条件、限制、复现 argv 与版本绑定。它不含实现对话、内部推理、完整 patch、原始日志或凭据。
- V2 evidence 采用 `pre_implementation_review` → implementation review → `final` 两阶段；稳定 verification snapshot 排除 phase 和 implementation review ref，避免 evidence/review 哈希循环。
- local V2 evidence 是 implementation review 与 code approval 的依据。CI evidence 只服务 Gate attestation，不能替代 local evidence 或 code approval。

## 仍然有效的 live V2 限制

真实 live V2 仅执行既有 V1 前缀。Chapter 11 拥有 acceptance、integration、targeted mutation 的真实执行；在其实现前，这三项均为 `unverified`，因此 live V2 结论必须为 failed，不能进入 implementation review、finalize 或 Gate 的 passed 路径。测试 fixture 中的 passed V2 路径不构成真实 live V2 验证成功。

## 操作顺序

1. 使用不同的 Verifier label 运行 `verify --actor`，生成或复用当前 context 与 pre evidence。
2. 只有 passed pre evidence 才可记录绑定其 snapshot 的 implementation review。
3. 使用同一 Verifier actor 运行 `verify --finalize`；该步骤不解析或运行 checks。
4. 在 current local final evidence 上记录 code approval；随后 CI evidence 可作为 Gate attestation 输入。

任何 subject、规格、Policy、classification 或 context 篡改都会使相关 artifact 失效，必须重新生成并重新取得必要审核/批准。

## 治理-only begin 兼容

`begin` 可接受 `subject_commit..HEAD` 仅包含当前任务 `.ai/tasks/<TASK-ID>/**` 的治理提交，解决同任务治理提交造成的基线死锁。该兼容不接受业务路径、其他任务路径、仓库或分支变化，也不扩大创建时 dirty baseline。
