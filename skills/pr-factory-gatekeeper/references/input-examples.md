# Gatekeeper Input Examples

Examples of inputs for the Gatekeeper skill for testing and development.

## Example 1: Scout Output → Gatekeeper

### SCOUT_JSON (candidate payload from Scout)

```json
{
  "schema_version": "1.0",
  "id": "scout-20260213-120000",
  "stage": "scout",
  "status": "success",
  "summary": "Found 5 low-risk candidates in active repo",
  "started_at": "2026-02-13T12:00:00Z",
  "finished_at": "2026-02-13T12:02:00Z",
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
      "stack_hints": ["typescript", "nodejs"],
      "ci_detected": ["github-actions"],
      "commands": {
        "test": "npm test",
        "lint": "npm run lint"
      },
      "config_paths": {
        "test": ["jest.config.js"],
        "lint": [".eslintrc.json"],
        "ci": [".github/workflows/ci.yml"]
      }
    },
    "candidates": [
      {
        "id": "cand-1",
        "title": "Add test for validateEmail with empty string",
        "change_type": "test",
        "risk": "low",
        "est_loc": 12,
        "likely_paths": ["src/utils/validation.test.ts"],
        "rationale": "Function missing edge case test",
        "test_plan": ["npm test -- validation.test.ts"]
      },
      {
        "id": "cand-2",
        "title": "Fix broken link in README",
        "change_type": "docs",
        "risk": "low",
        "est_loc": 1,
        "likely_paths": ["README.md"],
        "rationale": "API docs link returns 404",
        "test_plan": ["Manual: verify link works"]
      }
    ],
    "repo_score": {
      "score_0_10": 8,
      "reasons": ["Active maintenance", "CI present", "Tests exist"],
      "blockers": []
    }
  }
}
```

### Other Inputs

```json
{
  "REPO_ROOT": "/path/to/repo",
  "MAX_PRS": 1
}
```

### Expected Output

- Select top 1-2 candidates
- Create PRSpec for approved candidates
- Decision: "pr" for best candidate

---

## Example 2: With Critic Constraints

### ANALYST_JSON (candidate payload from Analyst)

```json
{
  "schema_version": "1.0",
  "id": "analyst-20260213-130000",
  "stage": "analysis",
  "status": "success",
  "data": {
    "resolved_focus": "tests",
    "candidates": [
      {
        "id": "cand-1",
        "title": "Add comprehensive test suite for validation module",
        "change_type": "test",
        "risk": "low",
        "est_loc": 150,
        "targets": [
          "src/utils/validation.test.ts",
          "src/utils/parseURL.test.ts"
        ],
        "details": "Add 20 new tests covering all edge cases"
      }
    ]
  }
}
```

### CRITIC_JSON (with scope cut)

```json
{
  "decision": "approve",
  "top_reasons": ["Good idea but scope too large"],
  "must_fix_before_implement": ["Split into smaller PRs"],
  "scope_cut": {
    "keep": ["Add test for validateEmail with empty string"],
    "drop": ["Add tests for parseURL"],
    "split_into_separate_prs": [
      "PR 1: validateEmail test (priority: high)",
      "PR 2: parseURL tests (priority: medium)"
    ]
  }
}
```

### Expected Behavior

- Respect scope_cut constraints
- Create PRSpec only for "keep" items
- Update title/loc based on scope cut

---

## Example 3: Multiple Candidates with Selection

### Candidate payload

```json
{
  "data": {
    "candidates": [
      {
        "id": "cand-1",
        "title": "Add test for validateEmail",
        "change_type": "test",
        "risk": "low",
        "est_loc": 10
      },
      {
        "id": "cand-2",
        "title": "Format all code with Prettier",
        "change_type": "chore",
        "risk": "low",
        "est_loc": 500
      },
      {
        "id": "cand-3",
        "title": "Refactor to class-based architecture",
        "change_type": "refactor",
        "risk": "high",
        "est_loc": 300
      }
    ]
  }
}
```

### Other Inputs

```json
{
  "MAX_PRS": 2
}
```

### Expected Decisions

| Candidate | Decision | Reason |
|-----------|----------|--------|
| cand-1 | pr | Low risk, clear value |
| cand-2 | skip | Mass formatting |
| cand-3 | issue | Too large, needs discussion |

---

## Example 4: Edge Case - No Valid Candidates

### Candidate payload

```json
{
  "data": {
    "candidates": [
      {
        "id": "cand-1",
        "title": "Rewrite in Rust",
        "change_type": "refactor",
        "risk": "high",
        "est_loc": 10000
      }
    ]
  }
}
```

### Expected Output

```json
{
  "status": "skipped",
  "summary": "No suitable candidates found",
  "data": {
    "selected": [
      {
        "candidate_id": "cand-1",
        "decision": "skip",
        "reasons": [],
        "blockers": ["Massive scope", "High risk"]
      }
    ]
  }
}
```
