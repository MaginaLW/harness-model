# Golden Scenarios

These files are static contracts for the first-stage AUTO, ASK, REVIEW, and BLOCK semantics.
The golden integration test runs every input through the real classification engine in a fresh Git
repository and compares the durable, non-dynamic classification evidence with `expected.json`.

Each scenario contains:

- `input.yaml`: one decision unit that satisfies the machine contract;
- `expected.json`: stable route, verification, Policy rule IDs, ordered Policy explanations, and
  next-state data.

Expected files deliberately exclude timestamps and absolute checkout paths so runtime results can
be compared deterministically. They do not copy raw task inputs or sensitive values; explanations
come from the active Policy wording.

The Chapter 7 scenario runner copies one scenario plus the governed Policy, schemas, and templates
into a fresh temporary Git repository. Runtime tasks and evidence are created only in that isolated
checkout; the source repository's `.ai/tasks` directory is never used for scenario execution.
