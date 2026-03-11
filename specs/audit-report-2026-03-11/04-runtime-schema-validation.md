# Spec 04: Validate stage payloads against `ExecutionResult` and `PRSpec` schemas at runtime

Источник:
- [Audit Report.md](../../Audit%20Report.md)
- Section: `Top issues -> 2`
- Section: `Best 7 -> 4`
- Section: `Ready-to-Implement PR Specs -> PRSpec 4`

## Why This Spec Exists

The audit highlights that `run_pipeline.py` currently does `json.loads(...)` and then inspects only a few fields. That means parseable but invalid payloads can move through several stages before failing far away from the actual source of the contract bug.

Concrete evidence from the audit:
- `analysis_report/critic-20260213T184308Z.json` is not an `ExecutionResult`; it is a raw decision payload.
- Legacy critic and gatekeeper artifacts exist in inconsistent shapes.
- The runtime tolerates this today because schema validity is not enforced.

## Goal

Validate every stage payload against `schemas/execution_result.schema.json` and validate any `pr_spec` / `data.pr_specs[]` payloads against `schemas/prspec.schema.json` immediately after parsing stage output.

## Scope

Touch only:
- `tools/run_pipeline.py`
- `tools/pr_factory_lib/json_utils.py` or a new helper like `tools/pr_factory_lib/schema_utils.py`
- `tools/tests/test_run_pipeline.py`

Keep the scope focused on validation and clear error reporting. Do not combine with placeholder alias work or broader compatibility cleanup.

## Problem Statement

Without runtime schema checks:
- malformed stage payloads remain "accepted" if they parse as JSON;
- invalid `pr_spec` objects fail late and indirectly;
- legacy drift survives because nothing enforces the canonical schema path-by-path.

## Smallest Safe Change

- Load the existing JSON Schemas from `schemas/`.
- Immediately validate every parsed stage payload as `ExecutionResult`.
- Additionally validate:
  - top-level `pr_spec`
  - `data.pr_specs[]`
- Return structured errors that include the failing schema path and field name.
- Decide explicitly whether any legacy raw critic payloads still need a compatibility path; if yes, make it narrow and test-covered.

## Acceptance Criteria

- Invalid `ExecutionResult` payloads fail at the stage boundary.
- Invalid `pr_spec` payloads fail before implementation stages consume them.
- Error messages identify the schema path or failing field.
- Existing valid stage payloads continue to pass.

## Tests To Add Or Update

- invalid stage payload rejected early
- invalid `pr_spec` rejected with structured error
- invalid `data.pr_specs[]` rejected
- raw critic JSON is either rejected or handled through an explicit compatibility path

## Verification

Run exactly:

```bash
python3 -m unittest tools/tests/test_run_pipeline.py
python3 -m jsonschema schemas/execution_result.schema.json -i schemas/examples/execution_result.example.json
```

If `jsonschema` is not available locally, note that gap and still run the unittest coverage.

## Reviewer Concerns To Preempt

- Whether to add a new dependency on `jsonschema`
- How `$ref` resolution is handled for `prspec.schema.json`
- Whether legacy artifacts need temporary compatibility

## Out Of Scope

- Static contract lint
- Placeholder alias resolution
- CI workflow
- Publish dry-run

## Suggested Commit Message

```text
feat(pipeline): enforce execution and prspec schemas at runtime
```
