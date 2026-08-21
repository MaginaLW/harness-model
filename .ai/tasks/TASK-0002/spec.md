# Task Specification

## 目标

交付可从 `git clone` 开始执行的 Quickstart、覆盖八类故障的恢复手册，以及不读取原工作区未跟踪文件的干净克隆端到端测试。

## 范围

- `docs/operations/quickstart.md`
- `docs/operations/recovery.md`
- `tests/e2e/test_clean_checkout.py`
- 当前任务的 `.ai/tasks/TASK-0002/**` 治理记录。

## 非目标

不修改 CLI、Policy、Schema、依赖或打包行为；不执行 push、merge、deploy、delete 或 package publish；不将故障手册写成绕过状态机的直接编辑指南。

## 验收条件

1. Quickstart 同时给出 PowerShell 和平台中立 Python 入口，覆盖 clone、venv、`.[dev]` 安装、测试、新建任务、分类、status 和 Gate，默认无 commit/push。
2. 恢复手册对半创建任务、损坏 JSON/YAML、事件/物化状态不一致、FAILED 重试、BLOCK 解除、stale evidence、Policy 变化和任务无法唯一解析分别给出诊断、可恢复操作和禁止操作。
3. `python -m pytest tests/e2e/test_clean_checkout.py -q` 通过：本地 clone 只含跟踪内容，可构建/安装、执行标记命令、查看帮助并运行无外部动作示例。
4. 测试不依赖用户主目录配置，不递归运行自身，不删除原工作区或外部 artifact。

## 禁止动作

push、merge、deploy、delete、secret export、paid external call、package publish，以及修改用户级 Git/Python 配置。

## 错误行为

克隆不干净、文档标记命令不存在/失败、相对路径缺失、八类恢复情形任一缺失、示例产生外部动作或读取原工作区未跟踪文件时必须失败。

## 回滚

本任务只新增文档、测试和治理记录；后续获批任务可通过显式 revert commit 撤销。端到端测试使用 pytest 临时目录并由 pytest 管理生命周期，不手动删除宽泛路径。
