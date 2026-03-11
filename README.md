# PR Factory Kit

Open toolkit for deterministic multi-agent PR pipelines: prompts, JSON schemas, quality gates, and orchestration tools for small, mergeable improvements.

This kit is designed for a multi-agent PR pipeline:
Scout → Analyst → Critic → Gatekeeper → Implementer → Reviewer → PR Writer → Publisher.

## Fastest agent entrypoint

If you want a single file to hand to an agent, start with `program.md`.
It plays the same role as a compact "operating program": what to read first, which workflow to prefer, and which constraints are non-negotiable.

## What’s inside

- `program.md` — shortest agent-facing entrypoint for the whole repo.
- `prompts/` — compact role prompts (stack-agnostic).
- `schemas/` — strict JSON Schemas:
  - `PRSpec` — what we intend to ship as a PR.
  - `ExecutionResult` — uniform result envelope for *any* CLI/agent run.
- `tools/quality_gate.py` — forbidden-files scanner + merge-probability heuristic + files_touched enforcement.
- `tools/run_pipeline.py` — deterministic DAG orchestrator (stage order + gate checks + implement retries).
- `tools/fetch_pr_comments.py` — fetch PR comments (issue + review) from GitHub for analysis.
- `tools/README.md` — how to run the gate locally / in CI.

## Placeholders

Prompts use placeholders like:
- `{{REPO_ROOT}}`, `{{REPO_URL}}`, `{{BASE_BRANCH}}`, `{{HEAD_BRANCH}}`
- `{{CONSTRAINTS}}` (plain bullet list)
- `{{ALLOWED_COMMANDS}}` (plain bullet list)
- `{{CONTEXT_PATH}}` (optional external context path)
- `{{ARTIFACT_DIR}}` (default: repo-local `analysis_report/`)
- `{{REPORT_PATH}}` (default: repo-local `analysis_report/runs/<run_id>/report.md`)
- `{{RUNNER}}` (selected execution backend, for example `cli` or `task`)

## Output rule (important)

All role prompts request **JSON only**, conforming to `schemas/execution_result.schema.json`.
Role-specific details go into `ExecutionResult.data`.

## Local setup

For editable installs during local development:

```bash
python3 -m pip install -e .
```

`requirements.txt` remains available for lightweight bootstrap and CI-style installs.

## Usage note

- Hand `program.md` to a chat agent when you want the shortest possible entrypoint.
- Use `prompts/pipeline.md` when you need the end-to-end workflow contract directly.
- Use `tools/README.md` for the fully expanded `run_pipeline.py` CLI examples.

## License

MIT. See `LICENSE`.
