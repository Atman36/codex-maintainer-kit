# Spec 08: Require `gatekeeper.status=success` before PR fan-out

Источник:
- [Audit Report.md](../../Audit%20Report.md)
- `AUDIT_SECOND_PASS_PROGRESS_2026-03-11.md`

## Why This Spec Exists

Current runner behavior is still unsafe: `gatekeeper` can return `status=needs_human`, but if the payload already contains a valid `pr_spec` or `data.pr_specs[]`, the pipeline still continues into `implement`, `reviewer`, and `pr_writer`.

That makes the gate semantically wrong. A gate that says "needs human" must stop automation, regardless of embedded artifacts.

## Goal

Tighten gate semantics so `gatekeeper` only unlocks PR execution when both conditions are true:
- semantic decision is `pr`
- top-level execution `status` is `success`

## Scope

Touch only:
- `tools/run_pipeline.py`
- `tools/tests/test_run_pipeline.py`

Do not change prompt text or stage payload schemas in this spec.

## Smallest Safe Change

- Update `gate_failed()` for stage `gatekeeper` to require both:
  - `gatekeeper_decision(payload) == "pr"`
  - `stage_status(payload) == "success"`
- Add a regression test where gatekeeper returns:
  - `status="needs_human"`
  - valid `data.pr_specs`
  - valid `pr_spec`
- Assert that `implement` does not run and pipeline exits with `needs_human`.

## Acceptance Criteria

- `gatekeeper.status=needs_human` blocks PR fan-out even when a valid PRSpec is present.
- Existing success-path behavior remains unchanged.
- Regression is covered by unit tests.

## Verification

Run exactly:

```bash
python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_gatekeeper_needs_human_with_prspec_blocks_fanout
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

## Reviewer Concerns To Preempt

- Backward compatibility: older unsafe outputs should not keep the pipeline moving.
- Scope: this is a gate correctness fix, not a refactor of extraction logic.

## Out Of Scope

- Stage vocabulary registry
- Lineage manifest
- Gatekeeper prompt calibration

## Suggested Commit Message

```text
fix(runner): require gatekeeper success before pr fan-out
```
