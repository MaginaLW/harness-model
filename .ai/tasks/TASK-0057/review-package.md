# Review Package

## 审核目标

对 TASK-0057 固定 subject `afff0629a2f68184a3b0e388af4ed5dc08a995e0` 的有限 YAML parser dispatch 资格修复作正式独立实施审查。base 为 `46a78b44ec02a0681528f567e313fe88e109b4d9`，完整验证的 attestation head 为 `7ecd0809f517a4a95b5f343b7c990dbe4a79bf05`。当前 implementation context 为 `bcd564bfbb5f8ebe1fa759e3546b50af81760e44f57362c10c4c4af1ad9deb8c`。

## 背景

累计候选上的真实反例表明，同一 SafeLoader 方法覆盖和 constructor 模块 datetime dispatch 改变后，旧缓存可返回旧解释。TASK-0057 是独立准入的纠正单元；不改写 TASK-0054/0055/0056 历史。审查者 `task57-independent-reviewer-verifier` 未著作 source、tests、spec 或 Policy，并是本次实际原生独立 Verifier；两职责由同一实际非作者承担，不声称两名独立人员。

## 代码地图

- `src/aiflow/document_parsing.py`：`_DispatchGuard` 构造有限资格计划，`unchanged` 检查当前状态，`load_yaml_text` 保持完整文本键、隔离复制和当前解析回退。
- `tests/unit/test_document_parsing.py`：原15个 named tests、decorators 与 fixture AST 保持；只追加 drift、未知配置、异常、副作用、限额和正常恢复用例。
- `docs/operations/pytest-temporary-roots.md`：单独安全提交说明有限资格、并发与完整验证边界。
- `.ai/tasks/TASK-0057/spec.md`、正式 Review/context 和原生 V2：冻结目标、scope、版本事实与验收。

生产文件 SHA-256 为 `b260864a34adee39690e900012e5d960e2fc7363c21f2e985ef9b46d04bf4afc`；测试文件为 `661366a985e848df11fafc6a82c22150cb619fa665ddfd6ce359279d22b260df`；spec 为 `fe6466059ee91d7074c5040bda161d0e4e87226579241804cb71cef87441ec4e`。

## 语义变更

一次编译识别的标准 SafeLoader 完整 MRO、bases、类 namespace、Python 函数 code/default/closure、实际引用 globals/builtins，以及有限 codecs/datetime/base64/binascii/types/Hashable dispatch。可支持的 mutable 内容和 regex 的 nominal immutable payload 纳入资格；Hashable 自身 virtual registry 变化回退，正常 lookup memo 和无关 ABC 注册不判作其配置改变。

资格拥有独立4096对象、状态与 code 扇出限额和深度64；未知 descriptor/callable/metadata、循环、超限或检查异常不获 cache 资格。保留64项、16384字符、4096返回图访问、深度64、原解析异常与 isolated graph；不缓存文件、Schema、Policy、批准或 freshness 结论。解析和复制后再次检查资格，检测到变化不发布缓存。标准未改 dispatch 仍实际命中缓存，恢复原配置可复用原项。

## 风险

资格检查增加真实开销，微基准不证明完整运行加速。它识别有限可观察标准配置，不认证任意 Python、伪造 metadata、解释器/native memory 篡改，也不提供 PyYAML 全局配置并发变化的原子保证。原 schema/path/file/identity/freshness guard、Policy、CI、阈值、selector 和期限均保持。

所有旧记录和真实失败追加保留：初轮 preflight wrapper0 却捕获 action-null，未当作合格准入；两次 driver pre-Popen locator 失败未执行 native/action；一次 readonly audit 因默认 cwd 错误返回1，原件保留，同原脚本明确 managed cwd 后返回0。其后只有一次真实完整原生 verify。已观察 retained launcher 的 identity、exit 与 handle 释放；未观察 engines/descendants 保留 unknown。

## 证据

已验证：独立实际完整 run `run-20261001T121557339455Z` 在固定 source 上完成14/14原检查、12个原 execution，全部 exit0、无 timeout；原5个固定 mutations 全部 killed，baseline0/mutant1、每个原60秒期限。原 budget 总和4110秒不改；4410仅为外层应急边界。单用 action `15512c2d3b36ed76f9421bce8bc32c0afd565a7f2f766cf9afd16ae60b3e2536` 实际消费一次。

- unit1994 passed/128.15s；regression2943 passed、1原 FIFO skip/655.21s；coverage2943 passed、同1原 skip/754.56s。
- 总 line coverage91.48%，diff92%（354 changed lines、27 missing），分别超过原85%和90%。
- acceptance9 passed/0.44s；integration912 passed、同1原 skip/462.99s，低于原600秒。
- 当前 Ruff、format（574文件）、mypy（44 source files）、contract、scope 和 smoke 均实际通过。
- 实际 outer tool 与 retained native 均 exit0，PID/creation/exit GetTimes 匹配并 closed；1869 outside source、foreign TASK-0056的106件、8件 own immutable、225 runtime、index、refs、topology 均 before/after/current 相等。
- 41件 native raw/archive bytes 核对一致，24个 nonnull stdout/stderr refs 对应原12执行。原 named tests AST 实际相等；没有移除 selector 或新增 skip。

原生 snapshot 为 `32ce9ec0a5d65e5759b31144bfe188d4cd8d4f2348b3cdd2fc95d79a41ee52d0`；verifier context 为 `457947b0ecdcfb28fd7cc87a34e9192ae33bb589ec944a1dbaeded080fc1e9af`；pre-evidence raw 为 `3ada352d62d41f182b3edba8553f97df4f5c5d958f1524574cf2269f7a280b77`；mutation canonical 为 `3b811ba38bd1d34e8a6978e2165176e2a931997b3673f618f30de9a89c6bc1a3`。

便携重现：`python -m aiflow verify TASK-0057 --actor task57-independent-reviewer-verifier --pytest-temp-root ${PYTEST_TEMP_ROOT}`；操作者替换占位符为已检查的普通外部父目录。已消费 action 不可重用，复现须按当前 task/版本获得新的实际准入与批准。

未验证：Linux required CI、累计发布和真实目标匹配报告导入。

本次证据属于 Windows Python3.13 的本地原生 V2；不证明 Linux required CI、累计发布或真实目标匹配报告导入。独立完整逐-node collection 未另行保存，不从 stdout 测试数推断该事实。

## 审核问题

- 两类实际 stale-cache 反例是否被 current-parser bypass 和黑盒回归覆盖：是。初始明显 custom/native override、unknown equality/property 和资格异常是否可能被当作标准命中：已读实现保守拒绝。MRO、函数原地 code/default/closure、mutable table、有限 dependency member 和 ABC 边界是否符合冻结 spec：是。原缓存隔离、容量、错误、当前 validation 与原测试、原完整 V2 是否保持：是。当前批准能否替代 finalize/code/Gate/Linux CI/发布：不能；这些是后续独立阶段。

## 推荐结论

APPROVE。实际完整源码、tests、spec、正式上下文和完整原生证据审查未发现冻结边界内的剩余实质 Finding。正式 record 使用 `REV-0002` revision1，绑定上述当前 implementation context；私有预审与历史 source pass 不充当正式记录。下一阶段由同一 actual Verifier 完成一次 finalize，再由 root 做 current code approval、Gate、own ledger commit 与准确 commit 的 Gate；当前审查未执行这些动作。
