# Golden scenario dry-run inventory

No files were deleted or modified. This inventory records the files that the rejected request
would have targeted.

| Path | SHA-256 before safe rewrite |
| --- | --- |
| `examples/scenarios/README.md` | `894b6ab35ba3504d9e59ca5423e984d3adc2717e35560df2b88244ce63449be1` |
| `examples/scenarios/ask-conflict-strategy/expected.json` | `e369c9c71d1bde87a4ea164d6cc7b2a0b1131068caca706a5d6c6efa670fe500` |
| `examples/scenarios/ask-conflict-strategy/input.yaml` | `ddb214e0b769f7082b7baef4806a3cae115b18a5ad4bea98707fbe6da180390e` |
| `examples/scenarios/auto-doc-edit/expected.json` | `9fe9287aff3ab6a1a7d022ed0bc7b585ceca51a63c7d5e169112c992918d696b` |
| `examples/scenarios/auto-doc-edit/input.yaml` | `d2e90553109e224ee206ebb62fd26543a2909b0a730a3b5ed3e9bbc3a836986a` |
| `examples/scenarios/block-no-backup/expected.json` | `529f498b288eb03abb54d8354ba70bdc76fc146f585fc1d55f527c292237f192` |
| `examples/scenarios/block-no-backup/input.yaml` | `88dc2346aa42dc5e5d33acd3de631ab74b31d0fa0e8e604a17d9b5896a515b1c` |
| `examples/scenarios/review-workflow-change/expected.json` | `894a37aa30855719ef1856ff97dc809a92f1f5bb14ca895c7b38a596fe62e40b` |
| `examples/scenarios/review-workflow-change/input.yaml` | `931f83b088b602484c78f1b5d5a60c1c8f4b471255e3020d9e16f7301bed4ccf` |

The post-run check compares the same set and hashes before Gate.
