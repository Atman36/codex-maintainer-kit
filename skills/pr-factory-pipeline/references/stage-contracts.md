# Stage Contracts

Use this file to keep stage handoffs deterministic.

## Preflight (mandatory)

Before any analysis stage:

- Validate `REPO_ROOT` exists and is a git repository.
- Enforce dirty-worktree policy (unless explicitly allowed).
- Resolve `base_sha_at_start` from `origin/<base>`.
- Validate runner compatibility (`auto|task|cli`) and stage commands.
- For publish mode: check `gh auth status` and remote readiness.

Fail fast with:

```json
{
  "status": "needs_human",
  "data": {
    "error_blocks": [
      {
        "reason": "...",
        "failed_stage": "preflight",
        "next_action": "..."
      }
    ]
  }
}
```

## Full Mode (analysis once)

1. `pr-factory-scout`
- Input: `REPO_ROOT`, `REPO_URL`, `BASE_BRANCH`
- Output: candidates JSON (`ExecutionResult`) persisted under `ARTIFACT_DIR` with `SAVED_JSON_PATH`

2. `pr-factory-analyst`
- Input: `REPO_ROOT`, optional `FOCUS`
- Output: refined candidates JSON + `related_files` hints for Implementer context scope (persisted under `ARTIFACT_DIR`)

3. `pr-factory-critic`
- Input: proposed changes/candidates + optional policy constraints
- Gate: `decision == approve`

4. `pr-factory-gatekeeper`
- Input: candidates JSON + `MAX_PRS`
- Gate: `decision == pr`
- Output contract:
  - Preferred: `data.pr_specs[]` (multi-PR first-class)
  - Backward compatible fallback: `pr_spec`

## Per-PR Execution Loop

For each PRSpec from Gatekeeper:

5. `pr-factory-implementer`
- Input: current `PRSPEC_JSON` + `HEAD_BRANCH`
- Gate: `status == success`

6. `pr-factory-reviewer`
- Input: implementer output + current `PRSPEC_JSON` + git diff summary
- Gate: `status == success`

7. `pr-factory-pr-writer`
- Input: reviewer + implementer outputs (+ optional diff summary) + current `PRSPEC_JSON`
- Output: final PR message and complete PRSpec

8. `pr-factory-publisher` (optional; only if user asked to publish)
- Input: final PRSpec + `HEAD_BRANCH`
- Pre-checks: auth readiness + base drift guard (`base_sha_at_start` vs current `origin/<base>`)
- Output: publish JSON (`ExecutionResult`) with PR URL (or `skipped` / `needs_human`)

## Quick-Win Mode

Analysis once:

`scout -> gatekeeper`

Then per-PR loop:

`implementer -> reviewer -> pr-writer -> (publisher if requested)`

Use when obvious low-risk change is enough.

## Architecture Mode

Analysis once:

`architect -> critic -> gatekeeper`

Then per-PR loop:

`implementer -> reviewer -> pr-writer -> (publisher if requested)`

Use when goal is targeted structural improvement (<200 LOC).

## Stop Conditions

- Preflight returns failed check.
- Any analysis stage returns `failed`.
- Critic returns `reject` or `revise`.
- Gatekeeper returns `issue` or `skip`.
- Per-PR: Implementer/Reviewer/PR Writer/Publisher returns non-success.
- Important: failure in one PRSpec must not erase results of other PRSpecs.
