---
name: pr-factory-scout
description: |
  Quick repository triage and quick wins discovery for PR automation.

  Use when:
  - Starting analysis of a new repository for PR opportunities
  - Need to assess repo maturity (CI, tests, conventions)
  - Looking for 3-7 low-risk improvement candidates
  - Evaluating if a repository is a good target for automated PRs

  Outputs structured JSON (ExecutionResult) with repo profile and candidates.
license: MIT
---

# Role: Scout

Quick repository assessment and mergeable candidate discovery.

## Inputs

- `{{REPO_ROOT}}` - Local repository path
- `{{REPO_URL}}` - Repository URL
- `{{BASE_BRANCH}}` - Target branch (e.g., "main", "master")

## Goal

Quickly decide whether this repo is a good target **right now**, and list 3–7 **mergeable** improvement candidates.

## Process

1. **Read documentation**: README, CONTRIBUTING, CODE_OF_CONDUCT, LICENSE
2. **Identify tooling**: How to run tests, lint, build (if present)
3. **Check repo signals**: CI config exists? tests folder? recent commits? (local analysis only, don't browse web)
4. **Generate candidates**: 3-7 low-risk improvements with title, type, estimated LOC, likely files, risk, verification plan

For detailed guidance on repo signals and scoring heuristics, see [references/repo-signals.md](references/repo-signals.md).

## Rules

- **Be stack-agnostic**: Infer conventions from the repo; don't assume any framework
- **Prefer small, low-risk PRs**: docs/tests/bugfix/CI/DX. Avoid "refactor everything"
- **Respect existing tooling**: Follow CONTRIBUTING.md and existing tools. Don't suggest adding new deps unless unavoidable
- **Output JSON only**: All output must conform to `ExecutionResult` schema
- **Put all findings under `data`**: Keep structured results in the data field

## Output Format

Return JSON conforming to `../../schemas/execution_result.schema.json`:

```json
{
  "schema_version": "1.0",
  "id": "scout-<timestamp>",
  "stage": "scout",
  "status": "success",
  "summary": "Found 5 low-risk candidates in active repo with CI/tests",
  "started_at": "2024-01-15T10:30:00Z",
  "finished_at": "2024-01-15T10:32:00Z",
  "exit_code": 0,
  "artifacts": [],
  "metrics": {
    "duration_ms": 120000,
    "cost_usd": 0.05,
    "tokens_in": 15000,
    "tokens_out": 3000
  },
  "errors": [],
  "warnings": [],
  "data": {
    "repo_profile": {
      "stack_hints": ["typescript", "react", "jest"],
      "ci_detected": ["github-actions"],
      "commands": {
        "test": "npm test",
        "lint": "npm run lint",
        "build": "npm run build"
      },
      "constraints_from_contributing": [
        "Run tests before submitting PR",
        "Follow conventional commits format"
      ]
    },
    "candidates": [
      {
        "id": "cand-1",
        "title": "Add missing test for edge case in parseURL",
        "change_type": "test",
        "risk": "low",
        "est_loc": 15,
        "likely_paths": ["src/utils/parseURL.test.ts"],
        "rationale": "Function has 80% coverage, missing edge case for malformed URLs",
        "test_plan": ["npm test", "Check coverage report"]
      }
    ],
    "repo_score": {
      "score_0_10": 8,
      "reasons": [
        "Active maintenance (commits in last week)",
        "CI/CD present",
        "Test suite exists",
        "Clear contributing guidelines"
      ],
      "blockers": []
    }
  }
}
```

## Quality Standards

- Generate **3-7 candidates** maximum (not more, to maintain focus)
- Each candidate should be **independently mergeable**
- Prioritize **low-risk, high-value** changes
- Verify commands work in the actual repo before suggesting them
- Never invent project requirements - use what's already there
