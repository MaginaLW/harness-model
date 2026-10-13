# Task Specification

## 目标

Handle invalid UTF-8 task documents as stable storage errors and make existing JSON-mode CLI domain failures machine-readable without exposing internal error details.

## 范围

Only src/aiflow/storage.py and src/aiflow/cli.py implement this decision unit. The exact additional paths in allowed_scope are independently committed task-free companion tools, tests and durable documentation for the owner-requested batch. They do not change the core decision unit or lower its REVIEW route. Quality Policy and CI expansion is a separate successor task.

## 错误行为

- _read_text catches UnicodeDecodeError as well as its existing OSError handling and raises STORAGE_READ_FAILED with the existing fixed message. Original document bytes remain unchanged.
- After successful argument parsing, status, gate and review show with --format json emit a single JSON object containing only code and message on stderr for AiflowError, leave stdout empty and return 1. ASCII-safe JSON retains Unicode message values when decoded.
- Never serialize details or exception causes. The existing controlled error.message is retained; this is not a new general-purpose redaction guarantee.
- Domain failure before parsed arguments exist uses the existing text fallback. argparse usage failures, help/version and unknown programming exceptions retain their existing behavior.
- Text-mode failures remain message plus newline and exit 1. All successful payloads remain unchanged; a valid negative Gate decision remains stdout JSON and exit 2.

## 验收条件

The owner explicitly requested these repairs after the demonstrated findings. An independent frozen design review and contract validation precede implementation. The separate task-free regression baseline deliberately preserves 17 failures and 38 passes before the repair; a RED specification test is not claimed as verification success. Implementation approval, Gate and publication require complete native verification and independent APPROVE under the standing authorization, with no open critical/high finding. CI retains all checks and 85 percent total / 90 percent diff coverage.

Run tests/unit/test_cli_error_output.py and tests/unit/test_storage.py for encoding, all three JSON commands, repository resolution, error privacy, text compatibility, successful JSON, argparse and unexpected exception behavior. Run the complete suite and existing lint, format, typing and whitespace checks before publication.

## 禁止动作

No authorization files, Policy, Schema, route, verification level, external action or archived record changes. No new collection, model calls, scoring or observation window. Publish only under the existing standing authorization after required CI succeeds. Deployment, data deletion, credential export, paid calls and history rewriting remain forbidden.

## 回滚

Revert the source implementation commit to restore prior error behavior. Preserve task events, reviews, failed baseline evidence and companion commit history.
