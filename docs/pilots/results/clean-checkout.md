# 干净检出预验收

- source_commit: `5b3db9dd3354a2b3107dc7f50f69e177506e0d68`
- clone_directory: `D:/Repos/harness-model-acceptance-clean-20260821-1125`
- clone_mode: local clone with no hardlinks, detached at source commit
- python: `3.11`
- install_command: `python -m pip install -e ".[dev]"`
- cli_command: `python -m aiflow --help`
- test_command: `python -m pytest -q`
- result: `575 passed, 3 skipped in 145.89s`
- conclusion: `passed`

三个 skip 均是 Windows 环境无法创建测试符号链接；其他测试、安装和 CLI 启动均通过。克隆目录已保留，未删除、推送、合并或部署。
