---
name: pr-factory-pipeline
description: |
  Orchestrate PR Factory skills as one ordered pipeline for end-to-end PR preparation.

  Use when:
  - User asks for full PR Factory flow "по порядку" / end-to-end
  - Need one coordinator skill to run Scout → Analyst/Architect → Critic → Gatekeeper → Implementer → PR Writer
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
  - `scout -> analyst -> critic -> gatekeeper -> implementer -> pr-writer`
- `quick-win`:
  - `scout -> gatekeeper -> implementer -> pr-writer`
- `architecture`:
  - `architect -> critic -> gatekeeper -> implementer -> pr-writer`

Detailed per-stage contracts: `references/stage-contracts.md`.

## Process

1. Normalize inputs and select mode.
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
6. Stop early on gate failure and return `needs_human` with reason.
7. On success, return final payload from PR Writer plus stage summary.

## Output Format

Return JSON conforming to `../../schemas/execution_result.schema.json`:

```json
{
  "schema_version": "1.0",
  "agent": "pr-factory-pipeline",
  "status": "success|needs_human|failed",
  "summary": "Pipeline result and stop/success point",
  "artifacts": [
    {
      "type": "json",
      "path": "pipeline/stage-summary.json",
      "description": "Stage-by-stage decisions and outputs"
    },
    {
      "type": "json",
      "path": "pipeline/final-prspec.json",
      "description": "Final PRSpec ready for submission"
    }
  ]
}
```

## Quality Standards

- Keep strict stage order for selected mode.
- Do not skip mandatory gates in `full` and `architecture`.
- Keep PR scope minimal and mergeable.
- Preserve deterministic handoff: each stage consumes structured output from previous stage.
