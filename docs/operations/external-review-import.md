# 本地外部审查报告预检与记录

`aiflow external-review` 接收已经由操作者核定的 ZCode envelope 和本地原报告。
它比较当前任务、原件摘要、来源受审对象及映射；只保管附属来源事实，不执行报告
内容、不访问链接、不产生正式 Review、Finding、批准、验证证据或 Gate。

先按 `external-review` 1.0 契约准备 envelope，将原件和输入保存在任务目录之外的
受控本地普通文件中。操作者负责确认原文实际受审仓库、阶段、base/subject 和
`source_subject.confirmation`；SHA256 只绑定字节，不认证这些声明。
design 目标须处于规格审核或实现就绪状态；implementation 目标须处于验证或最终
审核状态，并有当前通过的验证证据。已关闭、失败、阻塞或仍在实施的目标拒绝。

先运行零写预检：

```text
python -m aiflow external-review preflight TASK-ID --envelope <INPUT_ROOT>/envelope.json --report <INPUT_ROOT>/report.bin
```

来源使用仓库 locator 时，另传 `--repository-mapping <INPUT_ROOT>/mapping.json`。
mapping 是独立的 `external-review-repository-mapping` 1.0 封闭 JSON，包含定位符、
映射 ID、目标 UUID 和操作者核定记录；须逐字匹配来源。UUID 来源不传 mapping。
工具不从仓库简称、大小写或 `.git` 后缀猜测映射。

成功结果包含 `preflight_sha256` 和拟相对记录路径，不创建 task、context、日志或目录。
它可能报告 `ready`、`already_recorded` 或提交后尚有临时材料的 `cleanup_required`。
确认当前写入范围得到授权后，显式记录并提供本次预检摘要：

```text
python -m aiflow external-review record TASK-ID --envelope <INPUT_ROOT>/envelope.json --report <INPUT_ROOT>/report.bin --expected-preflight-sha256 <PREFLIGHT_SHA256>
```

record 重读原件、envelope、mapping、当前任务及版本事实；变化或同版本内容冲突
均拒绝。输入相同的重放返回 `no_op`；JSON 空白/键序变化可在重新预检后语义重放。
新版本只追加，引用原链头；版本字符串不是排序依据。变更来源定位符声明新的来源
系列，工具不认证报告身份或识别定位符别名。

历史 import 的 suggested Finding 同样须引用本 task 的精确 Review、revision 和
Finding，并与该 import 保存的目标 context 一致。有效旧 context 可继续作为版本链
基础；正式引用缺失、错配或损坏会拒绝追加。预检摘要也绑定这些历史 Review/context
的原始字节，引用变化后须重新预检，不把旧引用提升为当前正式审核。

成功返回 `recorded`，只新增 `.ai/tasks/<TASK-ID>/external-reviews/` 中的不可变
import，不复制原件、不改 task/events/formal Review/approval/evidence，也不改 Git index。
原件、运行日志和私有路径继续按其保管等级保存。附属记录会形成真实 Git 变更；
后续检查仍核对实际 dirty 状态，不隐藏文件以使 Gate 通过。

envelope 上限 256 KiB，mapping 64 KiB，原件 16 MiB；JSON 深度最多 32，重复键、
BOM、非有限数和未知字段拒绝。输入/目标拒绝链接、reparse、设备和路径逃逸；
Windows 网络路径/网络映射盘拒绝。错误采用固定原因，不打印输入正文、未知键名
或本机路径。输入不得包含凭据；自由叙述不执行，也不声称能识别任意文本中的所有秘密。

原子 create-only 发布是提交点。提交前拒绝保持任务目录零写；提交后清理失败仍
保留新记录并返回 `EXTERNAL_REVIEW_COMMITTED_CLEANUP_REQUIRED`。结果输出中断时
不要推断没有提交，先重跑零写 preflight 查明完整已提交记录及临时材料。
遗留 guard 或不完整版本链禁止继续 record；核对原件、任务和已提交记录后，只处理
本次明确识别的临时材料，再重新预检。不删除、覆盖或重写历史 import。
守卫只协调本服务的来源系列写入，不构成对任意 task writer 的 OS 沙箱或原子快照。

Windows 创建身份兼容修订约定：运行时提供 `st_birthtime_ns` 时采用该字段
（包括合法零值），旧运行时仅在属性缺失时回退 `st_ctime_ns`；POSIX 保留
`st_ctime_ns`。dev/ino/size/mtime、两次当前有界读取、原始 bytes 比较和路径
守卫继续执行，未变的原子发布输入与等长替换/读间改写都须实际验证。

只读 Git 查询保留原每次 10 秒通信期限。启动失败、超时和运行中的 I/O 错误仍以
固定 `EXTERNAL_REVIEW_GIT_BINDING_STALE` 拒绝；部分输出不能变成成功结果。成功启动
后的异常会清理本次拥有的子进程，KeyboardInterrupt、SystemExit 和意外异常保留原义。
正常安全拒绝仍清理本次 writer 临时材料；突然中断的 guard/temp 保留原有恢复边界。

清理只使用本次 retained 进程：Windows 在父进程仍存活时尝试其进程树，POSIX 只对
未回收的本次父进程所属 session 发信号，已退出的父进程不按数值 PID/group 追杀。
随后只做一次有界的直接进程清理和 5 秒 drain；未 drain 的 PIPE 不强行关闭。
Windows 配置等待项之和最多 21 秒，已退出父进程及 POSIX 为 15 秒，含原 10 秒期限；
这是等待项之和，不是整体预检的 wall-clock 上界。进程创建、调度、逃逸或已 orphan 的
未 retained 后代仍有边界；不保证全树释放，不执行全局进程搜索或未知 PID 清理。
