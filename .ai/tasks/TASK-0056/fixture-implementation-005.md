# Initial repository qualification details

This records implementation decisions within the frozen specification
3a782321645c40b71cf4921a7322872bf45285bf009218edb3e1d4d9310c53ce
and actual independent REV-0005/r1. It is not a test or V2 pass.

The original minimal environment has no applicable global configuration or
attributes path. The real recognized `git var` queries returned 1 with empty
stdout/stderr; only this quiet recognized result denotes no applicable path.
Other query failures remain ineligible. The official
[Git 2.55 var implementation](https://github.com/git/git/blob/v2.55.0/builtin/var.c)
returns 1 when its recognized reader has no value. Child environment is unchanged.

The installed ordinary system attributes file exists and is 515 bytes. Requiring
every attributes file to be absent would make this environment permanently cold.
The frozen specification allows a proved inactive initial input; REV-0005 states
absent/inactive. The independent reviewer explicitly confirmed this interpretation
without widening scope or lowering verification. The more conservative private
interface proposal is superseded only on this point.

Only the recognized system file may qualify after the first real successful
target repository proves strict empty output from its original owned ten-second
`git check-attr -z --all --` invocation over every initial working-tree file.
The command reports associated attributes; see the
[official check-attr documentation](https://git-scm.com/docs/git-check-attr).
No output is parsed or echoed when it is nonempty; qualification is refused.
Global, worktree, Git info and default-template attributes remain absent.
Current complete source/config/environment/Git/template/system-file bytes and
absence facts must agree before and after qualification and on every warm use.
Changes, uncertainty, read errors or query failures preserve cold behavior.
No filter or credential helper is executed for this proof.

A private original-helper probe over the 36 initial paths reported empty actual
Git output. Its saved stdout is a 69-byte wrapper JSON, SHA256
ddf8e7801221f6db87b1baef2f2b3f50adcba137cfbe432062158390d3089f52;
it is not a zero-byte raw Git-output file or completed fixture acceptance.

Additional review obligations are a current Git locator on every warm use,
standard Popen/helper identity, ordinary complete owner ancestry, and complete
seed template/hook correspondence without hidden active hooks. Portable warm
tests may be inapplicable only on a specifically proved unsupported environment;
generic publication, copy, parsing or inconsistent-input failures are not skip
conditions. The current original runtime must actually qualify and execute all
new warm acceptance cases with no additional skip. All original test statements
and assertions, full selectors, deadlines, MINENV and gates remain mandatory.

The final complete-guard benchmark executed twenty actual warm copies and twenty
original builders serially. Warm calls averaged 0.113194 seconds; original
builders averaged 0.373655 seconds. First builder, qualification and snapshot
took 1.111814 seconds. The benchmark exited 0 with one passed case in 14.61
seconds, no timeout and no extra skip. Its result SHA256 is
c697e367c76030ce30c94d5d3d7d0242c8549fc033a0c68b4ab6c2b516140d5a.
This is measured complete-guard cost, not a full integration or native V2 pass.

The original begin/close module passed all 34 cases in 40.01 seconds. The new
module passed 49 cases in 59.07 seconds before the final base identity, mode and
exception refinements. The final fourteen affected cases passed in 15.03 seconds
with 39 deselected; final collection is 53. All three runs exited 0 without
timeout or additional skip. The complete final module awaits full integration.
Ruff, format and whitespace checks exited 0. Independent root AST comparison
confirmed every original integration test function unchanged and the extracted
populate body equal to the original builder after its original target mkdir.
