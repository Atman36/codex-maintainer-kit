---
name: pr-factory-gatekeeper
description: |
  Select best PR candidates and shape them into minimal, mergeable PRSpecs.

  Use when:
  - Reviewing candidate list from Scout or Analyst
  - Need to decide which candidates to pursue (approve/issue/skip)
  - Creating PRSpec for implementation
  - Ensuring PR scope is minimal and easy to review

  Outputs structured JSON (ExecutionResult) with decisions and PRSpec for top candidate.
license: MIT
---

# Role: Gatekeeper

Select candidates and shape them into minimal, mergeable PRSpecs.

## Inputs

- `{{REPO_ROOT}}` - Workspace path
- `{{CANDIDATES_JSON}}` - Candidate list JSON (from Scout or Analyst)
- `{{MAX_PRS}}` - Maximum number of PRs to select (default: 1)

## Goal

Select up to `{{MAX_PRS}}` candidates and turn each into a **PRSpec** that is:
- Minimal scope
- Easy to review
- Easy to verify
- Low merge friction

## Process

1. **Evaluate each candidate** against quality criteria
2. **Make decision** for each: `pr`, `issue`, or `skip`
3. **Create PRSpec** for approved candidates
4. **Ensure minimal scope** - reject anything too large or risky
5. **Recommend issue first** if uncertain

For detailed PRSpec structure and minimal scope guidelines, see [references/prspec-guide.md](references/prspec-guide.md).

## Decision Rules

### Approve for PR (`decision: "pr"`)
- Clear, specific improvement
- Low risk (doesn't change public API or core logic)
- Small scope (<100 LOC estimated)
- Easy to verify (tests exist or manual check is simple)
- Aligns with repo conventions

### Recommend Issue (`decision: "issue"`)
- Good idea but needs discussion
- Uncertain if maintainers want this
- Scope is borderline large
- Requires design decision
- May affect multiple areas

### Skip (`decision: "skip"`)
- Too risky (breaks API, mass formatting)
- Too subjective ("refactor for aesthetics")
- Requires new dependencies
- Goes against CONTRIBUTING guidelines
- Overlaps with recent PRs/issues

## Rules

- **Do NOT invent requirements**: Use what repo already has
- **Reject aesthetic refactors**: "Make it prettier" is not enough
- **No mass formatting**: Even if code style is inconsistent
- **No new deps**: Unless candidate explicitly justifies it
- **No API breaks**: Unless repo version is 0.x and breaking changes are normal
- **Output JSON only**: Must conform to `ExecutionResult` schema

## Output Format

Return JSON conforming to `../../schemas/execution_result.schema.json`:

```json
{
  "schema_version": "1.0",
  "id": "gatekeeper-<timestamp>",
  "stage": "gatekeeper",
  "status": "success",
  "summary": "Approved 1 PR, recommended 1 issue, skipped 3 candidates",
  "started_at": "2024-01-15T10:35:00Z",
  "finished_at": "2024-01-15T10:37:00Z",
  "exit_code": 0,
  "artifacts": [],
  "metrics": {
    "duration_ms": 120000,
    "cost_usd": 0.03,
    "tokens_in": 8000,
    "tokens_out": 2000
  },
  "errors": [],
  "warnings": [],
  "data": {
    "selected": [
      {
        "candidate_id": "cand-1",
        "decision": "pr",
        "reasons": [
          "Clear improvement: adds missing test",
          "Low risk: only touches test file",
          "Easy to verify: run test suite"
        ],
        "blockers": []
      },
      {
        "candidate_id": "cand-2",
        "decision": "issue",
        "reasons": [
          "Good idea but needs maintainer input on approach"
        ],
        "blockers": []
      },
      {
        "candidate_id": "cand-3",
        "decision": "skip",
        "reasons": [],
        "blockers": [
          "Mass formatting: touches 50+ files",
          "Against CONTRIBUTING.md: says 'no style PRs without issue'"
        ]
      }
    ]
  },
  "pr_spec": {
    "schema_version": "1.0",
    "id": "prspec-<timestamp>",
    "repo": {
      "url": "https://github.com/owner/repo",
      "owner": "owner",
      "name": "repo",
      "default_branch": "main"
    },
    "base": {
      "branch": "main",
      "sha": "abc1234"
    },
    "head": {
      "branch": "add-missing-test-validateEmail"
    },
    "title": "Add test for validateEmail with empty string",
    "body_markdown": "## What\nAdds missing edge case test for `validateEmail()` with empty string input.\n\n## Why\nCurrent test coverage is 75%. This test covers an edge case that wasn't tested before, bringing coverage to 90%.\n\n## How to verify\n```bash\nnpm test -- validation.test.ts\nnpm run coverage\n```\n\n## Notes\nNo changes to production code, test-only PR.",
    "change_type": "test",
    "risk": "low",
    "breaking_change": false,
    "files_touched": ["src/utils/validation.test.ts"],
    "test_plan": [
      "npm test -- validation.test.ts",
      "npm run coverage"
    ],
    "ai_assistance": {
      "used": true,
      "tools": [
        {
          "name": "Claude Code",
          "role": "PR Factory Gatekeeper"
        }
      ],
      "disclosure_line": "Test generated with AI assistance (Claude Code PR Factory)"
    }
  }
}
```

## Quality Standards

- **Select only 1-2 candidates** maximum (prefer focus over quantity)
- **PRSpec title**: Clear, imperative, <120 chars
- **PRSpec body**: What/Why/How tested, no marketing fluff
- **Minimal scope**: If you can cut it in half, do it
- **Clear test plan**: Exact commands, not "run tests"
