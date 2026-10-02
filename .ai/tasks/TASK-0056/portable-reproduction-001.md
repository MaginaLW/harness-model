# TASK-0056 portable reproduction decision

The frozen specification requires local absolute paths to remain in private run
materials. The existing Review service copies evidence.reproduce_command into
the immutable implementation context. Therefore the new option is recorded in
that recipe as --pytest-temp-root ${PYTEST_TEMP_ROOT}; the operator must replace
the placeholder with a validated ordinary external parent. Actual process argv
and command summaries retain the concrete owned leaf in ignored evidence. The
native V2 verification snapshot binds that full private evidence, and the
implementation Review binds its exact snapshot digest. No Review service,
contract, Policy, environment allow-list, selector, threshold or budget changed.
This implements the frozen privacy boundary; it does not redact or rewrite old
evidence and does not assert that a placeholder itself is an executable path.

Independent implementation pre-review found that the original native command
redactor can mask a complete basetemp argument even for a legal directory name.
The preceding concrete-leaf statement applies only when that argument is not
masked; native evidence has no separate full argv field. To retain exact binding
without weakening redaction, opt-in pytest command summaries now include
pytest-argv-sha256, computed from the final resolved argv passed to Popen using
JSON ensure_ascii=True, separators=(",", ":") and UTF-8 bytes. The existing
snapshot includes that summary. Default and non-pytest summaries are unchanged.
Two different legal roots that trigger masking must retain different digests
matching an independent recomputation from each actual invocation. This is an
argv commitment, not authentication of executable bytes or external identity.
