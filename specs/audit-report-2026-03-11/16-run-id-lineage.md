# Spec 16: Add `run_id` and artifact lineage to pipeline outputs

Источник:
- `deepresearch/external-audits/audit-2026-03-11-second-pass.md`
- `AUDIT_SECOND_PASS_PROGRESS_2026-03-11.md`

## Why This Spec Exists

The runner already emits machine-readable summaries, but there is still no first-class `run_id` tying together:
- the pipeline invocation
- stage payloads
- extracted PRSpecs
- final summary
- later publish evidence

That makes auditability and future eval harness work weaker than it should be.

## Goal

Give each pipeline run a stable `run_id` and expose artifact lineage in machine-readable outputs.

## Scope

Touch only:
- `tools/run_pipeline.py`
- `schemas/pipeline_summary.schema.json`
- supporting tests in `tools/tests/test_run_pipeline.py`

Keep this spec focused on identifiers and lineage fields, not on full artifact storage redesign.

## Smallest Safe Change

- Generate a UUID-like `run_id` at pipeline start.
- Include it in the pipeline summary payload.
- Thread it into stage artifact metadata where feasible.
- Add lineage fields for known outputs such as stage payload paths and extracted PRSpec paths.
- Add regression coverage for summary shape and `run_id` presence.

## Acceptance Criteria

- Every pipeline run produces a non-empty `run_id`.
- Summary schema includes and validates `run_id`.
- Summary exposes enough lineage to connect pipeline summary to stage outputs and PRSpecs.

## Verification

Run exactly:

```bash
python3 -m unittest tools.tests.test_run_pipeline
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Manual check:
- Run a sample pipeline and confirm the same `run_id` appears consistently in the summary and related artifact references.

## Reviewer Concerns To Preempt

- Scope creep into a full artifact manifest: keep the first slice minimal and testable.
- Filename changes: avoid breaking existing consumers unless clearly documented.

## Out Of Scope

- Publish safety policy-as-code
- Artifact garbage collection
- Cost aggregation redesign

## Suggested Commit Message

```text
feat(runner): add run id and artifact lineage to pipeline summary
```
