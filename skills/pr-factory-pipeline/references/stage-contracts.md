# Stage Contracts

Use this file to keep stage handoffs deterministic.

## Full Mode

1. `pr-factory-scout`
- Input: `REPO_ROOT`, `REPO_URL`, `BASE_BRANCH`
- Output: candidates JSON (`ExecutionResult`)

2. `pr-factory-analyst`
- Input: `REPO_ROOT`, optional `FOCUS`
- Output: refined candidates JSON

3. `pr-factory-critic`
- Input: proposed changes/candidates + optional policy constraints
- Gate: `decision == approve`

4. `pr-factory-gatekeeper`
- Input: candidates JSON + `MAX_PRS`
- Gate: `decision == pr` and valid PRSpec

5. `pr-factory-implementer`
- Input: approved PRSpec + `HEAD_BRANCH`
- Gate: `status == success`

6. `pr-factory-pr-writer`
- Input: implementer output (+ optional diff summary)
- Output: final PR message and complete PRSpec

## Quick-Win Mode

`scout -> gatekeeper -> implementer -> pr-writer`

Use when obvious low-risk change is enough.

## Architecture Mode

`architect -> critic -> gatekeeper -> implementer -> pr-writer`

Use when goal is targeted structural improvement (<200 LOC).

## Stop Conditions

- Any stage returns `failed`.
- Critic returns `reject` or `revise`.
- Gatekeeper returns `issue` or `skip`.
- Implementer returns `failed` or `needs_human`.
