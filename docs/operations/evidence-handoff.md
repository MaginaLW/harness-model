# 本地证据移交

`tools/evidence/bundle.py` 将明确选定的文件按原始字节保存为 ZIP，并提供不解压的
独立校验。它只处理本地文件，不联网、不调用 Git、不写账本，不产生批准或 Gate 结论。
已有任务的证据摘要与原件保持不变；移交清单中的 SHA256 是所复制文件的字节摘要。

## 准备选择清单

先核实接收方所需的规格、审核记录、运行原件、工具环境及重现步骤，再逐文件选择。
将以下 JSON 保存为树外的 `<HANDOFF_ROOT>/selection.json`；路径相对于相应输入根，
使用 `/`。没有通配符、递归目录或自动包含项。未列出的文件不会读取或导出。

```json
{
  "version": 1,
  "files": [
    {"kind": "git-text", "path": "spec.md"},
    {"kind": "git-text", "path": "verification-closeout-001.md"},
    {"kind": "runtime-original", "path": "evidence.json"},
    {"kind": "runtime-original", "path": "environment.txt"},
    {"kind": "runtime-original", "path": "reproduce.md"},
    {"kind": "runtime-original", "path": "logs/full-test.stdout.log"}
  ]
}
```

`git-text` 从 `--task-dir` 读取，`runtime-original` 从 `--raw-dir` 读取。前者是选择者
声明的来源标签，不自动证明文件已入 Git、等于某个 Git blob 或属于某个提交。所有文件
均原样复制，包括工作树中可能存在的 CRLF；工具不会将其自动转换为 Git LF 文本。
需要证明提交身份时，另行核对具体 Git blob/提交并显式选择相应说明材料。

运行原件可能包含私密命令路径或敏感数据。清单和生成的 manifest 不记录输入根的机器
绝对路径，但文件正文以及选择的相对文件名会原样保留。工具不自动识别凭据、不脱敏，
不能将“未记录根路径”解释为内容已可公开。不要选择凭据；仅通过适合材料保密等级的
渠道移交。需要公开摘要时，另行制作摘要，保留原件及其历史摘要。

## 导出与接收方校验

输出的父目录须已存在；ZIP 必须位于所有输入根及任何 Git 仓库之外，且尚不存在。
即使全部输入来自树外 staging，也拒绝写入其他仓库或 worktree。输出父目录及其祖先
出现任何 `.git` 标记即拒绝；识别源码仓库和输出仓库时均以 `lstat` 检查标记，不跟随
`.git` 符号链接，也不读取 worktree 标记中的私密目标路径或调用 Git。
输出文件名拒绝 NTFS alternate data stream、保留设备名及尾随点或空格等不安全形式。
源码根、选定文件、输出父目录中的符号链接和 Windows junction/reparse point 均拒绝。
Windows 在读取元数据前拒绝 UNC、设备命名空间及非绝对盘符路径，并通过本地
`GetDriveTypeW` 拒绝映射网络盘和未知盘；允许固定盘、可移动盘、光盘及 RAM 盘。
普通相对路径按当前目录展开后执行相同检查。本地盘类别不证明 ACL、身份或安装可信；
其他系统的挂载点是否本地须由操作者确认，工具不检查挂载来源。
运行期间保持输入目录和文件静止；导出同时核对读取句柄及当前路径的设备、文件标识、
大小和修改时间，发现修改或原子替换即失败。本工具不提供对恶意并发文件系统修改的隔离保证。

```powershell
python tools/evidence/bundle.py export `
  --task-dir "<REPO_ROOT>/.ai/tasks/TASK-0049" `
  --raw-dir "<ARTIFACT_ROOT>/TASK-0049" `
  --selection "<HANDOFF_ROOT>/selection.json" `
  --output "<HANDOFF_ROOT>/TASK-0049-handoff-001.zip"

python tools/evidence/bundle.py verify "<HANDOFF_ROOT>/TASK-0049-handoff-001.zip" `
  --expected-sha256 "<BUNDLE_SHA256>"
```

仅导出 `git-text` 时可省略 `--raw-dir`。示例文件名需按实际已核查文件调整；不存在的
文件不会被跳过。重复导出使用新的名称，不覆盖已有交付物。导出后自动读回校验，标准
输出给出文件数、字节数和整个 ZIP 的 SHA256。校验成功退出 `0`，失败退出 `1`，参数
错误退出 `2`；操作错误只输出错误码，不打印机器路径或文件正文。

ZIP 内只有 `manifest.json` 和按两种来源标签分组的文件。manifest 固定版本为 `1`，
只记录 `format`、`version`、`files`；每项仅含 `kind`、`path`、`size`、`sha256`。
校验拒绝未知字段、重复 JSON 键、重复/多余/缺失 ZIP 项、大小或摘要不符、路径穿越、
大小写碰撞和链接项。校验读取压缩包，不执行原件、不解压、不恢复环境、不写任何文件。
边界为 10,000 个文件、4 MiB manifest、单文件 512 MiB、原件合计 2 GiB；实际累计
字节在每次写入前检查，源文件增长也不能越过总预算。校验在构造 ZIP 成员列表前先读取
固定长度 EOCD，并以 8 MiB 上限逐项检查中央目录和真实条目数，不信任声明的较小计数。
只支持普通单卷 ZIP，拒绝 ZIP64、压缩包备注/尾随数据、加密，以及 stored/deflate 之外
的压缩算法；导出不会升级为 ZIP64。若压缩后布局触发 Python 的普通 ZIP 限制，也会失败。
超过限制时保留原件，另行设计适合大材料的移交。

接收方应从可信渠道独立获得整个 ZIP 的摘要，再使用 `--expected-sha256`。省略该参数
只验证包内字节一致性；攻击者可同时替换原件与 manifest。即使摘要一致，仍不证明生成
者身份、运行成功、检查充分、环境可复现、批准有效或 Gate 通过。输出固定报告
`source_authenticated: false` 和 `governance_effect: "none"`。

定向验证：`python -m pytest tests/unit/test_evidence_bundle.py -q`。
