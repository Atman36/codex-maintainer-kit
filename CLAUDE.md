# PR Factory Kit — Project Instructions

## Overview

Multi-agent PR pipeline: Scout → Analyst → Critic → Gatekeeper → Implementer → Reviewer → PR Writer → Publisher.

## Fastest Entrypoint

- Start with `program.md` when you want the shortest agent-facing file for this repository.
- Use it to understand what to read first, which workflow is primary, and which constraints are mandatory.

## Skills

See `AGENTS.md` for the full list of available skills and trigger rules.

## Key Files

- `program.md` — shortest agent-facing entrypoint for the repo
- `tools/quality_gate.py` — forbidden-files scanner + merge-probability heuristic + autoclean (CLI: `--autoclean-unplanned`)
- `tools/run_pipeline.py` — deterministic DAG orchestrator (stage order + gate checks + retries)
- `tools/contract_registry.py` — canonical placeholder registry + static contract validation
- `tools/validate_skills.py` — CI contract check for skills
- `tools/make_agent_audit_archive.py` — builds clean audit archives (excludes nested junk)
- `schemas/execution_result.schema.json` — `ExecutionResult` envelope (all stage outputs must conform)
- `schemas/prspec.schema.json` — `PRSpec` schema (validated at runtime in pipeline)
- `tools/tests/` — regression tests (run with `python3 -m unittest discover -s tools/tests -p 'test_*.py'`)
- `config/pipeline_modes.json` — pipeline mode analysis graphs (loaded at startup, early-validated)
- `pyproject.toml` — minimal editable-install packaging metadata (`pip install -e .`)
- `analysis_report/` — stable repo-owned artifact directory for pipeline summaries and per-run outputs

## Placeholders

Canonical set (enforced by `contract_registry.py`) — key ones:
- `{{REPO_ROOT}}`, `{{REPO_URL}}`, `{{BASE_BRANCH}}`, `{{HEAD_BRANCH}}`
- `{{CONSTRAINTS}}`, `{{ALLOWED_COMMANDS}}`
- `{{ARTIFACT_DIR}}` — where analysis-stage JSON artifacts are written (default: `analysis_report/`)
- `{{REPORT_PATH}}` — where a markdown report should be written (default: `analysis_report/runs/<run_id>/report.md`)
- `{{MODE}}`, `{{FOCUS}}`, `{{STAGE}}`, `{{COMMAND}}`, `{{RUNNER}}`
- Per-stage JSON paths: `{{SCOUT_JSON}}`, `{{ANALYST_JSON}}`, `{{ARCHITECT_JSON}}`, `{{CRITIC_JSON}}`, `{{GATEKEEPER_JSON}}`, `{{IMPLEMENT_JSON}}`, `{{REVIEWER_JSON}}`, `{{PRSPEC_JSON}}`

Unresolved placeholders cause fail-fast in `run_pipeline.py` (preflight check).

## Run Notes

- `tools/run_pipeline.py` is the preferred deterministic orchestrator.
- Do not present `python tools/run_pipeline.py` by itself as a runnable example; real runs require the needed `--stage-command` values.
- For the full CLI shape, refer to `tools/README.md` or start with `python3 tools/run_pipeline.py --help`.

## Rules

- All role prompts output **JSON only** conforming to `ExecutionResult` schema.
- Stage payloads validated at runtime against `ExecutionResult` and `PRSpec` schemas.
- Publish preflight is strict (requires real remote base branch). Non-publish runs allow local fallback with warnings.
- `SAVED_JSON_PATH` supports quoted and space-containing paths.
- Never skip quality gate or autoclean for publish steps.
- Tests live in `tools/tests/` — run `python3 -m unittest discover -s tools/tests -p 'test_*.py'` before committing tool changes.
- PR fan-out requires `gatekeeper.status=success` AND `decision="pr"` — `needs_human` blocks fan-out.
- Each pipeline run emits a `run_id`; per-run artifacts persist under `analysis_report/runs/<run_id>/`.
- Pipeline mode analysis order is defined in `config/pipeline_modes.json` (validated at startup).

## CI

`.github/workflows/` includes a workflow that runs:
1. `python -m unittest discover -s tools/tests -p "test_*.py"` — tool unit tests
2. `python tools/validate_skills.py` — contract validation for prompts, docs, skills, references, and examples
