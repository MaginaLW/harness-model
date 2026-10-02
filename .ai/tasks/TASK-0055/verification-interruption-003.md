# Third V2 interruption for an independently found source defect

Native V2 started at admission HEAD
`5f80ee087438ea62bc597290f5d5587708c9b2d5`, source subject
`28d5184e02dc9b4dee0cc6df942000ad34f8b611`.
While it was running, independent compatibility review reproduced a P2 gap:
a schema-valid historical import could contain a suggested Finding mapped
to another task and still be accepted as the basis of a new version chain.
Historical exact Review/Finding/context binding needs repair within the
unchanged frozen specification.

The independent verifier stopped only its confirmed process tree before
source repair. The five initial native logs remain; unit tests were interrupted
without a final result, and later checks and mutations were not executed.
The owned verification process returned Windows termination code 4294967295,
the outer tool returned 1, and native verify --abandon returned 0.
The native failure event explicitly records a known source defect. This is
not a budget failure, completed test assertion result or passing verification.

Original outer003, stop003, native run logs and verifier context remain.
No old evidence, action, review or event is replaced. Fixing the defect and
its regression tests requires a new fixed subject and complete native V2;
Git identity microbenchmarks do not substitute for that result.
