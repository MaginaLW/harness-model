# TASK-0190 Policy Changed Resolution Note

- Condition: `policy_changed`
- Cause: Implementation commit `bb21d3bc0344bf766d39be9597c8a9b8d898196d` updated `.ai/policy/verification-levels.yaml` (V1/V2 `mypy` command updated to `["{python}", -m, mypy]`) and `.ai/policy/hard-rules.yaml` (added `setup.py`, `MANIFEST.in`, `tools/hooks/**` to `HARD-REVIEW-GOVERNANCE-SURFACE`), keeping `policy_version: "2.6.0"` unchanged across all 4 `.ai/policy/*.yaml` files.
- Verification: `mypy` passed on 57 `src` + `tools` files, `ruff check .` and `ruff format --check .` passed, and targeted tests (80 passed) passed.
- Governance check: `spec.md` (`spec_sha256`) is unchanged; next steps are to re-classify, freeze, obtain independent `REV-0002` design review under the updated Policy, and re-record `spec` approval under conditional pre-authorization + standing delegation.
