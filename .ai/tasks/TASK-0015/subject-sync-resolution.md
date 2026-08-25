# TASK-0015 synchronized-subject resolution

- Condition: `spec_changed`
- Previous subject: `17ab98cf879cf913e91dfcdf69861b387eabf7ac`
- Current synchronized subject: `5f5c731fd049d4dfa738c06aeadd054c5b9ad409`
- Required route and verification level: `REVIEW + V2`

The current subject is the local checkpoint created to preserve work produced during
the earlier valid `IMPLEMENTING` interval. Its business paths are limited to the
approved V2 evidence schema, shared mutation consumer, and unit TDD files; all other
paths in the commit are TASK-0015 governance records. `aiflow sync` validated the
commit range against the explicit task scope before recording
`subject_commit_synchronized`.

The specification, Policy, decision units, allowed scope, action restrictions, and
real-runner prohibition are unchanged. `REV-0006-r0001.json` independently reviewed
this synchronized subject and found no new design issue. A reclassification and fresh
subject-bound specification approval are required only because approvals cannot be
carried across a subject change.
