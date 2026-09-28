# E4.1 判别对象诊断澄清

独立设计审查 `REV-0004` 发现：`source_subject.repository`、`source.location` 和
`findings[].mapping` 使用 `oneOf`。向这些对象加入未知字段时，现有验证器返回
已知父对象位置的 `oneOf` 约束，且不回显未知字段名或值。

`diagnostic-amendment-001.md` 所写的 `unexpected property` 约束说明，限定为
直接由 `additionalProperties` 报告的对象。对上述三类判别对象，父位置的
`oneOf` 约束也满足 C5；不解析或回显其未经信任的字段名。安全测试须覆盖这三类
判别对象、根对象、普通嵌套对象和旧契约诊断兼容。

这份追加记录澄清验收行为，不扩大 E4.1 的导入、写入或真实性核查范围；
`REV-0004` 的发现须在当前规格重新冻结和独立复审后正式关闭。
