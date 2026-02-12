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
- Output **JSON only** (`ExecutionResult`) with either:
  - data.candidate (a single candidate PR) or
  - status = needs_human with an Issue proposal if risky.

## Output (JSON)
Return `ExecutionResult` stage=`analysis` with:
- data.candidate: {id,title,change_type:"refactor",risk,est_loc,targets[],rationale,design_sketch,verification:{commands[]}}
