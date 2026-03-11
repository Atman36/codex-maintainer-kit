# Spec 10: Preserve architect candidate in `top_improvements`

Источник:
- [Audit Report.md](../../Audit%20Report.md)
- `AUDIT_SECOND_PASS_PROGRESS_2026-03-11.md`

## Why This Spec Exists

`collect_top_improvements()` currently reads only `data.candidates`, but architecture mode is allowed to emit a single `data.candidate`. That means the pipeline summary can still show empty `top_improvements` even when `architect` returned a valid improvement.

This is a summary-layer bug, not a prompt problem.

## Goal

Make `top_improvements` preserve both valid contract shapes:
- `data.candidates`
- `data.candidate`

## Scope

Touch only:
- `tools/run_pipeline.py`
- `tools/tests/test_run_pipeline.py`

## Smallest Safe Change

- Update `collect_top_improvements()` to also accept a single-object `data.candidate`.
- Normalize it into a one-item list for summary output.
- Add a regression test for architecture mode showing that `top_improvements` is non-empty.

## Acceptance Criteria

- Architecture mode summary includes the architect candidate when only `data.candidate` is present.
- Existing list-based analysis payloads keep working unchanged.

## Verification

Run exactly:

```bash
python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_architecture_mode_surfaces_single_candidate_in_top_improvements
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

## Reviewer Concerns To Preempt

- Why support two shapes: because both already exist in contracts and dropping one loses audit signal.
- Scope: this change is additive and isolated to summary collection.

## Out Of Scope

- Candidate schema redesign
- Mode graph extraction
- Artifact lineage

## Suggested Commit Message

```text
fix(runner): include architect candidate in top improvements
```
