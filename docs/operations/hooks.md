# Thin local wrappers and Hooks

These adapters call the executable AI Flow core. They provide earlier feedback; they do not replace CLI validation, CI Gate, repository branch protection, or explicit approval for external actions.

## Verification wrapper

Run `python tools/gauntlet.py --task TASK-ID`. Add `--provisional` for diagnostic evidence that cannot satisfy Gate, and `--format json` for machine-readable output. The wrapper does not read verification Policy or choose checks; `aiflow.verification_service.verify_task` remains authoritative.

## Pre-commit

Run `python tools/hooks/pre_commit.py --task TASK-ID` from a Git pre-commit integration or an Agent before requesting a commit. Omitting `--task` is accepted only when exactly one non-merged task exists. The check delegates task status, changed-path collection, scope matching, and workflow prerequisites to core services. It never runs `git commit`, edits the index, or fixes files.

## Pre-command

Run `python tools/hooks/pre_command.py --action ACTION --target TARGET` before a normalized external action. Phase one accepts an action category, not a shell command; it deliberately does not parse arbitrary shell syntax. Permission Policy denies automatic push, merge, deploy, delete, secret export, and paid external calls until the separately governed action-approval workflow is satisfied. The Hook never performs the action.

Claude Code and other Agents may call these scripts explicitly from their platform Hook configuration. A generic Git client may invoke the pre-commit script from its repository-local Hook. Platforms without such integration remain governed by the AI Flow CLI and CI Gate; phase one does not claim system-wide interception.
