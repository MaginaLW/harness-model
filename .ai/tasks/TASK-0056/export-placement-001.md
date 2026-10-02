# TASK-0056 preparation export placement

Four duplicate CLI exports and review-input preparations were placed in the reserved reviews directory. Native validation requires that directory to contain only canonical REV-ID-rNNNN records. Move only those preparations, preserving exact bytes. The authoritative review-contexts and REV records, events, approvals and historical Git blobs are unchanged. The prior placement remains recoverable from commit 720c1e2.

| Original preparation path | Preserved preparation path | Raw SHA-256 |
| --- | --- | --- |
| reviews/context-design-001.json | preparation/context-design-001.json | 3245e6d102c84bbc78dab4feed2c047c5909c4ec78eb9dc0488916a90aba9645 |
| reviews/context-design-002.json | preparation/context-design-002.json | 7dd16fa1672543aa5475918bb713237f04976e437542c76828d55928d03b3e4c |
| reviews/design-review-input-001.json | preparation/design-review-input-001.json | 1b8b2a9630db2330b2ac4b4162f1803e1bd3e7ed4f9e8739d638400fb08f1b09 |
| reviews/design-review-input-002.json | preparation/design-review-input-002.json | e412c2a4f715b09f339d7e9dca4dc6b84ea94561c16955742e1cc275e3a406f0 |
