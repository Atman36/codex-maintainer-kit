# Spec 17: Move pipeline mode definitions out of `run_pipeline.py`

Источник:
- `deepresearch/external-audits/audit-2026-03-11-second-pass.md`
- `FRAMEWORK_IMPROVEMENTS_2026-03-11.md`
- `AUDIT_SECOND_PASS_PROGRESS_2026-03-11.md`

## Why This Spec Exists

`MODE_ANALYSIS_STAGE_ORDER` is still hardcoded in `tools/run_pipeline.py`. Any new pipeline mode currently requires a code edit instead of a data/config change. The second-pass audit and the framework follow-up file both call this out as still open.

## Goal

Move mode graph configuration into a data file, keeping runner behavior deterministic while reducing code-level drift.

## Scope

Touch only:
- new config file such as `config/pipeline_modes.json`
- `tools/run_pipeline.py`
- tests that cover mode loading / validation

Do not add parallel execution in this spec.

## Smallest Safe Change

- Create a config file defining analysis stage order per mode.
- Load mode definitions from config in the runner.
- Validate required modes and stage names early.
- Keep current supported modes unchanged: `full`, `quick-win`, `architecture`.

## Acceptance Criteria

- Runner no longer hardcodes `MODE_ANALYSIS_STAGE_ORDER`.
- Existing modes behave the same as before.
- Invalid or missing config fails with a clear error.

## Verification

Run exactly:

```bash
python3 -m unittest tools.tests.test_run_pipeline
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

## Reviewer Concerns To Preempt

- Overengineering risk: keep config limited to current mode graph, not a general workflow engine.
- Validation: ensure the runner fails early on invalid config instead of silently falling back.

## Out Of Scope

- Parallel analysis stages
- Dynamic plugin systems
- Artifact lineage

## Suggested Commit Message

```text
refactor(runner): load pipeline modes from config
```
