# Spec 11: Validate pipeline summary at runtime and write it to a stable artifact dir

Источник:
- [Audit Report.md](/Users/Apple/Developer/pr-factory-kit/Audit%20Report.md)
- `AUDIT_SECOND_PASS_PROGRESS_2026-03-11.md`

## Why This Spec Exists

The runner already validates stage payloads, but `pipeline_summary` is still assembled and written without equivalent runtime validation. On top of that, the default summary path still depends on `Path.cwd()`, which makes artifact location nondeterministic.

This is a contract and reproducibility issue, not just a docs issue.

## Goal

- Validate the final summary payload against `schemas/pipeline_summary.schema.json` before writing it.
- Change the default output location to a toolkit-controlled stable artifact directory.
- Keep `--summary-output` as an explicit override.

## Scope

Touch only:
- `tools/run_pipeline.py`
- `tools/pr_factory_lib/schema_utils.py`
- `tools/tests/test_run_pipeline.py`

## Smallest Safe Change

- Add a `validate_pipeline_summary()` helper alongside existing schema helpers.
- Call it before writing summary JSON.
- Replace `Path.cwd()`-based default output with a stable repo-owned directory such as `<toolkit_root>/analysis_report/`.
- Add tests for:
  - invalid summary payload fails before write
  - default summary path is independent of caller CWD

## Acceptance Criteria

- Invalid summary payloads fail deterministically.
- Default summary output path is stable and repo-controlled.
- `--summary-output` still works as an override.

## Verification

Run exactly:

```bash
python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_pipeline_summary_payload_is_validated
python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_default_summary_output_uses_stable_artifact_dir
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

## Reviewer Concerns To Preempt

- Existing scripts that expect a summary in caller CWD: direct them to `--summary-output` if they need explicit placement.
- Scope: this is artifact-contract tightening, not lineage-manifest work.

## Out Of Scope

- Full lineage manifest
- Run ID propagation
- Publish evidence recording

## Suggested Commit Message

```text
fix(runner): validate pipeline summary and stabilize default artifact path
```
