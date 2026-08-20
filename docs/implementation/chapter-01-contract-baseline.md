# Chapter 1 Contract Baseline

This document fixes the first executable contract baseline for the AI Flow MVP. It covers the
package skeleton, machine Schemas, declarative Policy, artifact templates, and four golden
scenarios. It does not claim that task storage, routing, verification execution, or Gate behavior
already exists.

## Schema version rules

All machine records in this baseline use `schema_version: "1.0"`. The meaning of an existing
field, required property, enum member, or cross-field invariant must not change while retaining
that version. An incompatible change requires a new schema version, an explicit migration, and
revalidation of every affected fixture, template, Policy reference, approval, and evidence record.

Schemas reject unknown top-level machine fields. Task records embed decision-unit objects through
the decision-unit Schema reference. Optional classification facts use closed nested objects and
enums; adding them did not remove or weaken the original required decision-unit fields.

`repository_path_at_creation` is diagnostic only. It never participates in repository identity,
version binding, golden comparison, or a future task-content digest.

## Policy change rules

The Policy source is the fixed set of four files under `.ai/policy/`:

- `hard-rules.yaml` owns mandatory BLOCK and minimum REVIEW rules;
- `routing.yaml` owns explicit ASK/AUTO rules and `ROUTE-DEFAULT-REVIEW`;
- `verification-levels.yaml` owns V0/V1 check arrays, timeouts, parsers, safe variables, commands,
  environment overrides, run-directory containment, and the 90 percent diff-coverage threshold;
- `permissions.yaml` owns the actions that cannot run automatically.

Every Policy edit must preserve global rule-ID uniqueness and pass `policy.schema.json` plus the
cross-file contract tests. A semantic rule change increments `policy_version` and invalidates
affected classification, approval, and evidence conclusions. Whitespace or YAML comment changes
alone do not change Policy meaning.

No Python module, Agent file, Hook, or CI workflow may copy the route precedence, permission set,
or verification command table. Later code must load these Policy documents through the core API.

## Directory responsibilities

| Directory | Responsibility |
|---|---|
| `.ai/schemas/` | Versioned JSON Schema definitions for machine records and Policy |
| `.ai/policy/` | Declarative routing, verification, and permission source data |
| `.ai/templates/` | Parseable starting structures for tasks, specs, ASK, review, and evidence |
| `src/aiflow/` | Core package and safe contract-validation interface |
| `tests/fixtures/contracts/` | Positive and negative machine-contract examples |
| `examples/scenarios/` | Static AUTO, ASK, REVIEW, and BLOCK comparison contracts |
| `tests/unit/` | Focused Schema and validation-interface tests |
| `tests/integration/` | Cross-file Policy, template, and golden-scenario invariants |

## Golden scenario purposes

| Scenario | Frozen meaning |
|---|---|
| `auto-doc-edit` | A docs-only, reversible, automatically verifiable change can be `AUTO + V0` only through the explicit AUTO guard rule. |
| `ask-conflict-strategy` | Three reasonable output formats require `ASK + V1` and three complete options. |
| `review-workflow-change` | A CI/CD workflow change is `REVIEW + V1`, requires spec and code approval, and performs no external action automatically. |
| `block-no-backup` | An irreversible broad overwrite without verified backup or dry run is `BLOCK + V1` until backup and scope conditions are met. |

The expected JSON files intentionally omit timestamps and absolute checkout paths. They are static
contracts for a future classifier, not recorded runtime classifications.

## SHA-256 participation rules

Canonical digests operate on UTF-8 data and never include secrets or the local checkout path.

- **Policy digest:** include each fixed Policy filename and the complete `yaml.safe_load` result,
  serialized as normalized JSON with sorted keys. Include schema version, Policy version, rule IDs,
  priorities, conditions, commands, timeouts, parsers, thresholds, and permission values. Exclude
  YAML comments, whitespace, quoting style, and line endings.
- **Classification-input digest:** include every decision-unit machine field, including optional
  scope, impact, protection, verification, category, and direction-count facts. Exclude explanatory
  runtime logs and any diagnostic absolute path.
- **Task version binding:** include stable repository ID, branch, `base_commit`, `subject_commit`,
  dirty-state observation, allowed scope, forbidden actions, current state, and decision units.
  Exclude `repository_path_at_creation`.
- **Approval and evidence binding:** include task and decision-unit IDs, specification digest,
  Policy digest, approval type or verification level, and `subject_commit`; CI evidence also
  includes `attestation_head`. Human display text outside the machine record is not substituted for
  these fields.
- **Golden comparison:** include every field and array order in each scenario `input.yaml` and
  `expected.json`. Exclude the scenario README and dynamic fields that are deliberately absent,
  including generated time and absolute repository path.

Task 3.1 will implement the normalized Policy digest. Later digest implementations must conform to
these participation rules and add decision-table tests before becoming authoritative.

## Contract regression command

Run all Chapter 1 executable contracts with:

```powershell
python -m pytest -m contract -q
```

The selected tests read only repository files and pytest temporary directories. They do not use the
network, user home directory, ambient current time, credentials, or paid services.
