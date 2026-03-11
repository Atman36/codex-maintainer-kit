# PR Factory Kit (prompts + contracts + quality gate)

This kit is designed for a multi-agent PR pipeline:
Scout → Analyst → Critic → Gatekeeper → Implementer → Reviewer → PR Writer → Publisher.

## What’s inside

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
- `{{ARTIFACT_DIR}}` / `{{REPORT_PATH}}` (portable artifact locations injected by the orchestrator)

## Output rule (important)

All role prompts request **JSON only**, conforming to `schemas/execution_result.schema.json`.
Role-specific details go into `ExecutionResult.data`.
