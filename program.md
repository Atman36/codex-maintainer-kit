# PR Factory Kit Program

Use this file as the shortest agent-facing entrypoint for the repository.

## What this repo is for

`pr-factory-kit` is a maintainer automation toolkit that prepares small, safe, reviewable pull requests through an ordered pipeline:

`Scout -> Analyst/Architect -> Critic -> Gatekeeper -> Implementer -> Reviewer -> PR Writer -> Publisher`

The goal is to reduce open-source maintainer review load with explicit human approval boundaries, quality gates, and machine-readable JSON output.

## In-scope files

Read these first:

1. `README.md` for repository overview.
2. `GUIDE.md` for operator-facing usage and common scenarios.
3. `prompts/pipeline.md` for the end-to-end workflow contract.
4. `tools/run_pipeline.py` if you need deterministic orchestration details.

Open other files only as needed.

## Default operating mode

When the user asks to analyze or improve another repository with PR Factory:

1. Collect the target repo path, optional repo URL, base branch, and optional `deepresearch/` context.
2. Prefer the ordered PR Factory flow instead of ad hoc editing.
3. Use `pr-factory-pipeline` for full runs, or `pr-factory-code-editor` only for clearly scoped direct edits.
4. Keep the selected change minimal, reviewable, and likely to merge.

## Hard rules

- Prefer deterministic orchestration with `tools/run_pipeline.py` over a single manager prompt.
- Do not publish a PR unless the user explicitly asks for fork/push/PR creation.
- Do not claim artifacts exist unless they were actually written.
- Keep diffs narrow; avoid broad refactors unless the requested mode is architectural.
- Use external context from `deepresearch/` selectively: only facts that affect risk, scope, style, or constraints.

## Fast paths

- For full analysis and implementation: use `prompts/pipeline.md`.
- For analysis only: use `prompts/user-analysis-only.md`.
- For direct user-ready phrasing: use `prompts/user-pipeline-full.md`.

## Expected outputs

- Agent stages return JSON matching `schemas/execution_result.schema.json`.
- Final implementation should be followed by review and PR writing before any publish step.
