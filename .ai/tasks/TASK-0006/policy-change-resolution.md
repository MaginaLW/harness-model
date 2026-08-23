# TASK-0006 Policy change resolution

- Condition: `policy_changed`
- Previous Policy SHA-256: `166a5cef3d00311b35543cc281ac042494c4244a595f3e4b8b2b0967851a6e1f`
- Current Policy SHA-256: `81699424c71ecf0af58936e449e1683b03e632bac50cb7007a430dea5aa85e60`
- Current Policy version: `2.0.0`
- Subject commit: `52b543e72435afef9e7e5c52c5c09fd1109bd435`

The four active Policy documents now share version `2.0.0`. The verification
Policy contains exactly ordered `V0`, `V1`, and `V2`; V2 retains the complete V1
check definitions as its semantic prefix and appends, in fixed order,
`acceptance`, `integration`, `targeted_mutation`, and `independent_verifier`, all
required. The Policy loader retains an explicit strict 1.x V0/V1 compatibility
branch and rejects unsupported major versions.

The current loader successfully parsed the new bundle and produced the current
digest above. This record authorizes reclassification against the changed Policy;
it is not an approval and does not reuse the previous design review or
specification approval.
