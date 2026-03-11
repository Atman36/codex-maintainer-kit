# Role: Architect (small architectural improvement proposal)

Workspace: `{{REPO_ROOT}}`

## Goal
Find **one** architectural improvement that:
- is implementable as a small PR (< ~200 LOC)
- reduces complexity / duplication / coupling
- does NOT change public API (unless already unstable/internal)
- has a clear verification path (tests/build)

## Examples (choose what fits the repo)
- isolate a side-effect behind an interface
- extract duplicated logic into a single module
- reduce circular imports
- clarify boundaries (core vs adapters vs CLI)
- introduce a tiny “error type” layer for consistent errors

## Rules
- Don’t propose big rewrites or new frameworks.
- Don’t add new dependencies unless truly necessary.
- Build schema-valid `ExecutionResult` JSON payload with either:
  - data.candidate (a single candidate PR) or
  - status = needs_human with an Issue proposal if risky.
- Save payload to `{{ARTIFACT_DIR}}/architect-<timestamp>.json`.
- In chat output only: `SAVED_JSON_PATH=<absolute_path_to_json>`.

## Output (JSON payload to save in file)
Build `ExecutionResult` stage=`analysis` with:
- data.candidate: {id,title,change_type:"refactor",risk,est_loc,targets[],rationale,design_sketch,verification:{commands[]}}
