# Golden Scenarios

These files are static contracts for the first-stage AUTO, ASK, REVIEW, and BLOCK semantics.
They are inputs and expected outputs for a future classification engine; they are not claims that
runtime classification has already been implemented or executed.

Each scenario contains:

- `input.yaml`: one decision unit that satisfies the machine contract;
- `expected.json`: stable route, verification, Policy rule, ordered reasons, and next-state data.

Expected files deliberately exclude timestamps and absolute checkout paths so later engines can
compare deterministic fields directly.
