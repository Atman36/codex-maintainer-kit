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

## Inputs

- `{{REPO_ROOT}}` - Absolute path to target repository (can be outside current workspace)
- `{{REPO_URL}}` - Repository URL (optional but preferred)
- `{{BASE_BRANCH}}` - Base branch (default: `main`)
- `{{CONTEXT_PATH}}` - Optional path to external context (`deepresearch/` directory or a single `.md` file)
- `{{FOCUS}}` - Optional focus (`docs|tests|bugfix|perf|refactor|ci|dx`)
- `{{MODE}}` - Optional mode (`full|quick-win|architecture`)
- `{{MAX_PRS}}` - Optional max PR count for Gatekeeper (default: `1`)

## Mode Selection

- `full` (default):
  - `scout -> analyst -> critic -> gatekeeper -> implementer -> reviewer -> pr-writer -> (publisher if requested)`
- `quick-win`:
  - `scout -> gatekeeper -> implementer -> reviewer -> pr-writer -> (publisher if requested)`
- `architecture`:
  - `architect -> critic -> gatekeeper -> implementer -> reviewer -> pr-writer -> (publisher if requested)`

Detailed per-stage contracts: `references/stage-contracts.md`.

## Process

1. Normalize inputs and select mode.
   - For automation, prefer deterministic code orchestration via `../../tools/run_pipeline.py`.
   - Use this skill prompt as "chat mode" policy/control-plane guidance.
2. If `CONTEXT_PATH` is provided:
   - read only relevant files (prefer `.md` summaries),
   - extract constraints/policies/risk notes,
   - pass concise context forward to Analyst/Critic/Gatekeeper.
3. Run stage 1 and collect JSON output.
4. Feed output JSON into the next stage placeholders.
5. Enforce gates before moving forward:
   - Critic decision must be `approve`.
   - Gatekeeper decision must be `pr`.
   - Implementer status must be `success`.
   - Reviewer status must be `success`.
6. Stop early on gate failure and return `needs_human` with reason.
7. On success, return final payload from PR Writer plus stage summary.

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
    "stage_summary": [],
    "top_improvements": [],
    "selected_prspec": {},
    "final_pr_message": {}
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
- Do not skip mandatory gates in `full` and `architecture`.
- Keep PR scope minimal and mergeable.
- Preserve deterministic handoff: each stage consumes structured output from previous stage.
- Return schema-valid `ExecutionResult` (no extra top-level keys; required fields present).
