# TASK-0025 historical H1 replay bundle record

- Bundle manifest: `.ai/tasks/TASK-0025/historical-snapshots/h1-fe30565/manifest.json`
- Bundle content commit: `51eadb142151f69ac50c4248110275a02b83b51f`
- Bundle SHA-256: `4076b379a431e45a831a591efd2586492b955acf3c6e9b237232ccb720c26580`
- Source subject: `fe30565e669aa047088b0c25c085effeb2b4bdbc`
- Source governance commit: `ef1f32d42b935ef2f7d8acfdc805a95399b33317`
- Historical implementation review: `REV-0045 r0001 REQUEST_CHANGES`

This record is intentionally committed after the bundle content so the manifest does not
self-reference the commit that contains it. The bundle is `historical_non_current`: it may
only be replayed in a pytest-owned local clone under the digest and non-task-input rules in
the manifest. It must not be copied into current TASK-0025 evidence, used as a current
approval, or treated as Gate/readiness evidence for a later subject.

The targeted-mutation action digest
`9740af8fafb53760e829f94fd3c34d252a742fd42f2928e16272f32ee91d2cfa` was consumed for the
source subject and cannot be reused. Any targeted mutation for a current subject requires a
new exact action and a separate single-use approval.
