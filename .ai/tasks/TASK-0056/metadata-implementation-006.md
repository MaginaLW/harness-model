# Fixed creation identity candidate

Actual frozen specification is
2cefeedd6fb99f26b0e7562ff4fc57f5b1beadab0b397802455b04af14f673a1.
Independent REV-0006/r1 approved design, followed by current owner specification
approval and native begin. Current state is IMPLEMENTING, not verification passed.

Production commit be69e7d changes only four added lines and one tuple component
in external_review._metadata_identity. Windows selects available birthtime_ns,
retains zero and legacy attribute-absence fallback; POSIX retains ctime_ns.
Every other function AST in external_review.py is unchanged. Ruff, format and
mypy over 44 production files passed. A preliminary actual 3.13 reader smoke
accepted the previous ordinary 1305-byte input with its unchanged raw SHA256;
it is not native MINENV or complete validation evidence.

Separate task-free safety commits are cd1d071 (operating documentation) and
e3790a43bf51b976816a8eaf8770789c7f90a1f2 (new metadata test module). The latter
is the synchronized source subject. The module has 19 parameterized cases;
Ruff, format and AST checks passed, but no pytest matrix has run yet.
Test-module SHA256 is
1155d70fc7dff1a6a7269d4f3d98e5743984e8cd3f3560d5d24a98d65d449e32.

Next steps are independent fixed-source 3.11/3.13/3.14 local safety cases,
complete original external-review module and original integration600 on 3.13.
Only actual completion permits exact runtime selection and a fresh action005
for complete default native V2. All prior failures remain; no new action, full
V2, formal implementation Review, finalization, code approval or Gate PASS is
asserted by this implementation note.
