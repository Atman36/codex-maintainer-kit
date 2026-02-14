---
name: pr-factory-pipeline
description: |
  Orchestrate PR Factory skills as one ordered pipeline for end-to-end PR preparation.

  Use when:
  - User asks for full PR Factory flow "по порядку" / end-to-end
  - Need one coordinator skill to run Scout → Analyst/Architect → Critic → Gatekeeper → Implementer → Reviewer → PR Writer
  - Want stage-by-stage handoff with explicit quality gates between stages
  - Need quick-win or architecture-focused variants of the same pipeline
license: MIT
---

# Role: Pipeline Orchestrator

Coordinate the PR Factory sequence and hand off outputs between stages.

`skills` are instructions, not shell commands. For deterministic automation use `../../tools/run_pipeline.py` with explicit `--stage-command` values.

## Inputs

- `{{REPO_ROOT}}` - Absolute path to target repository (can be outside current workspace)
- `{{REPO_URL}}` - Repository URL (optional but preferred)
- `{{BASE_BRANCH}}` - Base branch (default: `main`)
- `{{CONTEXT_PATH}}` - Optional path to external context (`deepresearch/` directory or a single `.md` file)
- `{{FOCUS}}` - Optional focus (`docs|tests|bugfix|perf|refactor|ci|dx`)
- `{{MODE}}` - Optional mode (`full|quick-win|architecture`)
- `{{MAX_PRS}}` - Optional max PR count for Gatekeeper (default: `1`)
- `{{RUNNER}}` - Optional runner (`auto|task|cli`, default: `auto`)

## Mode Selection

- `full` (default):
  - Analysis once: `scout -> analyst -> critic -> gatekeeper`
  - Then per PRSpec: `implementer -> reviewer -> pr-writer -> (publisher if requested)`
- `quick-win`:
  - Analysis once: `scout -> gatekeeper`
  - Then per PRSpec: `implementer -> reviewer -> pr-writer -> (publisher if requested)`
- `architecture`:
  - Analysis once: `architect -> critic -> gatekeeper`
  - Then per PRSpec: `implementer -> reviewer -> pr-writer -> (publisher if requested)`

Detailed per-stage contracts: `references/stage-contracts.md`.

## Process

1. Normalize inputs and select mode.
   - For automation, use deterministic orchestration via `../../tools/run_pipeline.py`.
   - Select runner: `auto` (default fallback), `task`, or `cli`.
2. If `CONTEXT_PATH` is provided:
   - read only relevant files (prefer `.md` summaries),
   - extract constraints/policies/risk notes,
   - pass concise context forward to Analyst/Critic/Gatekeeper.
3. Run mandatory `preflight` and fail fast on infra/runtime issues.
4. Run analysis stages once and collect JSON output.
5. Feed output JSON into the next stage placeholders.
   - If stage returns `SAVED_JSON_PATH=...`, read JSON from that file and continue handoff.
6. Enforce gates before moving forward:
   - Critic decision must be `approve`.
   - Gatekeeper decision must be `pr`.
7. Extract `pr_specs[]` from Gatekeeper (`data.pr_specs` preferred; fallback to `pr_spec`).
8. For each PRSpec run `implementer -> reviewer -> pr-writer` (and `publisher` if requested).
   - Keep fail/retry isolation per PRSpec.
   - Continue processing other PRSpecs even if one fails.
9. Before publish, run readiness checks and base-drift guard.
10. Return pipeline result with:
   - per-stage summary,
   - per-PR status array,
   - selected runner,
   - machine-readable summary path.

## Runtime Notes

- Task mode: pass `--task-runner-cmd` wrapper (supports `{{COMMAND}}`, `{{STAGE}}`).
- CLI mode: pass executable commands only (`python ...`, `node ...`, etc.).
- Do not pass skill IDs (e.g. `pr-factory-scout`) as shell commands.
- Branch naming policy: normalize to `codex/<slug>`.
- Docs-only PR policy: when selected PRSpec is docs-only (`change_type=docs`, only docs paths), keep verification lightweight and avoid unnecessary build/test stages unless explicitly required by repo policy.

## Output Format

Return JSON conforming to `../../schemas/execution_result.schema.json`:

```json
{
  "schema_version": "1.0",
  "id": "pipeline-<timestamp>",
  "stage": "pipeline",
  "status": "success",
  "summary": "Completed pipeline (full) and produced final PRSpec",
  "started_at": "2026-02-12T16:01:00Z",
  "finished_at": "2026-02-12T16:10:00Z",
  "exit_code": 0,
  "stdout": "",
  "stderr": "",
  "artifacts": [],
  "metrics": {
    "duration_ms": 540000,
    "cost_usd": 0.0,
    "tokens_in": 0,
    "tokens_out": 0
  },
  "errors": [],
  "warnings": [],
  "data": {
    "pipeline_mode": "full",
    "runner_selected": "auto|task|cli",
    "stage_summary": [],
    "pr_results": [],
    "top_improvements": [],
    "selected_prspec": {},
    "selected_prspecs": [],
    "final_pr_message": {},
    "pipeline_summary_path": "/abs/path/pipeline-summary.json"
  },
  "pr_spec": {}
}
```

Notes:
- Keep `artifacts` empty unless you actually wrote those files. If you do write artifacts, prefer `/tmp/pr-factory/<id>/...` to avoid polluting the target repo.
- If `{{REPO_ROOT}}` is not writable in the current environment, stop before implementation/publishing and return `needs_human` (with a concrete next action for the human).
- If you do run Publisher, reflect it explicitly in `summary` and include the PR URL under `data` (so the final message can’t contradict the actual actions taken).

## Quality Standards

- Keep strict stage order for selected mode.
- Do not skip mandatory gates.
- Keep PR scope minimal and mergeable.
- Preserve deterministic handoff: each stage consumes structured output from previous stage.
- Return schema-valid `ExecutionResult`.
- Include actionable failure diagnostics: `reason`, `failed_stage`, `next_action`.
