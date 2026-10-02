# V2 verification declaration alignment

The frozen specification remains
`957685c8b21d7b1fe2ce69d3e4d1f0319db2f344b5dc3b3cb1cd5dfb620a74f9`.
The owner approved this specification and authorized eventual push and merge in
the current conversation. Implementation and verification remain local and bounded.

The active V2 Policy requires the existing five-safeguard targeted mutation runner.
The initial decision unit omitted its explicit targeted-mutation declaration and
the runner's action-approval permission. Those declarations are now aligned with
the already frozen requirement: `targeted_mutation_required: true` and
`permission_requirements: [action_approval]`. No source behavior, allowed scope,
Policy, verification threshold, or frozen specification text is expanded.

This changes classification input facts, so the prior classification is stale.
Preserve the current implementation, synchronize its committed subject, and use
same-route specification-fact invalidation and evidence-backed reclassification.
Keep REVIEW/V2, freeze the unchanged specification, and obtain a fresh independent
design assessment of the declarations. Reuse the existing owner specification
approval only if the CLI reports it current.

`design-context-003.json` is a historical, unapproved preparation snapshot built
before successful reclassification. It is not an admission context or verification
evidence. A subsequent current context and review will identify the actual admission.

The bounded local targeted-mutation action is recorded separately against the
eventual exact subject and fresh classification input. Push/merge authorization
will be recorded separately for the complete publication candidate. Provider calls,
real external-report recording, deployment, and phase expansion remain outside
this implementation.
