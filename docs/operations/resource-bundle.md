# AI Flow 资源包

[PR #138](https://github.com/MaginaLW/harness-model/pull/138)已交付版本化资源分发。普通 wheel 提供 15 份 Schema、四份待目标审核的 Policy 种子和规格模板。资源来自同一份源码，清单绑定规范化 UTF-8/LF 字节、大小、SHA-256 和 CLI、资源及 Policy 版本；缺项、额外项、版本不符、损坏或不支持的文件类型均拒绝。

资源包只提供分发和只读 API，不创建目标 `.ai`、身份、任务或批准，也不选择目标验证方案。Policy 种子不构成目标授权，不能把本仓常设授权或维护模式带入外仓。完整跨仓范围见[接入方案](sdk-and-engine-plan.md#完整引擎跨仓初始化)。

## 构建

使用新的隔离环境和项目锁定依赖。`pyproject.toml` 已通过 `[tool.uv] link-mode = "copy"` 将缓存安装设为复制模式，
使各平台的分发验证使用独立文件；保留文件链接数检查。输出参数应替换为各自新建的空目录或实际源码包路径：

```powershell
uv sync --locked --all-extras
.\.venv\Scripts\python.exe -m build --no-isolation --wheel --outdir "<EMPTY_WHEEL_DIR>"
.\.venv\Scripts\python.exe -m build --no-isolation --sdist --outdir "<EMPTY_SDIST_DIR>"
.\.venv\Scripts\python.exe -m build --no-isolation --wheel --outdir "<EMPTY_REBUILT_WHEEL_DIR>" "<SDIST_PATH>"
```

POSIX 环境使用 `.venv/bin/python`。已有环境中的硬链接不会仅因修改配置自动变为独立文件；分发验收使用新建环境并核对链接数。构建或重试遇到现存输出、链接或未知内容时保留现场，改用新的输出目录；不要为重试删除不明文件。源码包不携带仓库身份、历史任务、批准、日志或维护标记。

## 读取

将实际 wheel 安装到独立环境后，可在源码树外读取：

```python
from importlib.resources import files
from aiflow.resource_bundle import read_bundle

manifest, resources = read_bundle(
    files("aiflow").joinpath("_bundled_resources")
)
```

`resources` 的键为包内相对路径，值为规范资源字节。读取先完成整个清单校验，不返回部分结果。普通安装和 `zipfile.Path` 读取均有验证；可编辑安装不提供 `_bundled_resources`，分发验收应使用实际 wheel。

构建检查其负责的源码、资源、缓存、元数据、暂存和输出路径，拒绝检测到的链接或冲突；这些检查不提供并发修改下的原子保证。

资源版本为 `1.0`，兼容 CLI `0.2.0`，Policy 种子版本为 `2.6.0`。摘要证明包内一致性，不认证发行者。运行时 Schema 和 Policy 仍来自目标自己的 `.ai`，升级 Python 包不会自动替换它们。此资源切片不证明非覆盖初始化、目标 npm 验证、外仓 V2 或真实 CI 已接入。
