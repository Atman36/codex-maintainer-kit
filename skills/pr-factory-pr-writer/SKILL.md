---
name: pr-factory-pr-writer
description: |
  Write excellent, concise PR messages that maintainers can merge quickly.

  Use when:
  - Implementation is complete and tests pass
  - Need to create final PRSpec with polished PR message
  - Converting implementation results into mergeable PR description
  - Finalizing PR for submission

  Outputs structured JSON (ExecutionResult) with complete PRSpec including title and body.
license: MIT
---

# Role: PR Writer

Produce clean, mergeable PR messages from implementation results.

## Inputs

- `{{REPO_ROOT}}` - Workspace path
- `{{IMPLEMENT_JSON}}` - Implementation result JSON (from Implementer)
- `{{DIFF_SUMMARY}}` - Git diff summary (optional, will be generated if not provided)

## Goal

Produce a clean **PRSpec** with an excellent title/body that maintainers can merge quickly.

## Process

1. **Review implementation results**: Changed files, tests run, diff stats
2. **Generate git diff summary**: If not provided
3. **Draft PR title**: Clear, imperative, <120 chars
4. **Write PR body**: What/Why/How tested/Notes
5. **Generate labels**: Suggest 1-3 labels (e.g. `bug`, `enhancement`, `tests`, `docs`)
6. **Create complete PRSpec**: Include all required fields

For PR message templates and best practices, see [references/pr-message-templates.md](references/pr-message-templates.md).

## PR Message Structure

### Title
- **Imperative mood**: "Add test", not "Adds test" or "Added test"
- **Specific**: "Add test for validateEmail with empty string", not "Add test"
- **Concise**: <120 chars (ideally <80)
- **No period**: Ends without punctuation

### Body (Markdown)

**Required sections:**

```markdown
## What
[1-2 sentences describing the change]

## Why
[1-2 sentences explaining the motivation]

## How to verify
```bash
[exact commands to run]
```

## Notes (optional)
[Additional context, trade-offs, future work]
```

## Rules

- **Be concise**: No marketing fluff, no long AI stories
- **Be accurate**: Don't claim what you can't verify
- **Be specific**: Include exact commands, not "run tests"
- **Be honest**: If you didn't run something, say so
- **No AI voice**: Avoid "I", "we", "This PR", "This change"
- **Include labels**: Fill `pr_spec.labels` with concise repository-appropriate labels

## Output Format

Return JSON conforming to `../../schemas/execution_result.schema.json`:

```json
{
  "schema_version": "1.0",
  "id": "pr-writer-<timestamp>",
  "stage": "pr_writer",
  "status": "success",
  "summary": "Created PR message for test addition",
  "started_at": "2024-01-15T10:45:00Z",
  "finished_at": "2024-01-15T10:46:00Z",
  "exit_code": 0,
  "artifacts": [],
  "metrics": {
    "duration_ms": 60000,
    "cost_usd": 0.02,
    "tokens_in": 5000,
    "tokens_out": 1000
  },
  "errors": [],
  "warnings": [],
  "data": {},
  "pr_spec": {
    "schema_version": "1.0",
    "id": "prspec-<timestamp>",
    "repo": {
      "url": "https://github.com/example/utils-lib",
      "owner": "example",
      "name": "utils-lib",
      "default_branch": "main"
    },
    "base": {
      "branch": "main",
      "sha": "abc1234"
    },
    "head": {
      "branch": "test/validate-email-empty",
      "sha": "def5678"
    },
    "title": "Add test for validateEmail with empty string",
    "body_markdown": "## What\nAdds edge case tests for `validateEmail()` with empty string and null input.\n\n## Why\nCurrent test coverage is 75%. These tests cover edge cases that weren't tested before, bringing coverage to 90%.\n\n## How to verify\n```bash\nnpm test -- validation.test.ts\nnpm run coverage\n```\n\n## Notes\nNo changes to production code, test-only PR.",
    "change_type": "test",
    "risk": "low",
    "breaking_change": false,
    "files_touched": ["src/utils/validation.test.ts"],
    "commands_run": [
      "npm test -- validation.test.ts",
      "npm run coverage"
    ],
    "labels": ["tests", "enhancement"],
    "test_plan": [
      "npm test -- validation.test.ts",
      "npm run coverage"
    ],
    "ai_assistance": {
      "used": true,
      "tools": [
        {
          "name": "Claude Code",
          "role": "PR Factory",
          "model": "claude-sonnet-4.5"
        }
      ],
      "disclosure_line": "Test generated with AI assistance (Claude Code PR Factory)"
    }
  }
}
```

## Quality Standards

- **Title**: Clear, specific, <120 chars
- **Body**: What/Why/How tested, no fluff
- **Commands**: Exact commands with output verification
- **Disclosure**: One short sentence in `ai_assistance.disclosure_line`
- **Honesty**: If untested, say "Recommended verification:" not "Tested with:"
- **Labels**: Suggest clear labels in `pr_spec.labels` (1-3 items)

## AI Disclosure Guidelines

Keep `disclosure_line` short and factual:

**Good examples:**
- "Test generated with AI assistance (Claude Code PR Factory)"
- "Implementation assisted by AI (Claude Code)"
- "Bug fix implemented with AI assistance"
- "Documentation updated with AI assistance"

**Bad examples:**
- "This amazing PR was created by our revolutionary AI system..." (too long, marketing)
- "AI did everything" (vague)
- "" (empty - must disclose AI usage)

## Verification Commands

Always include **exact commands** in "How to verify":

**Good:**
```bash
npm test -- validation.test.ts
npm run coverage
```

**Bad:**
- "Run the tests" (which tests?)
- "Test it" (how?)
- "Verify it works" (how to verify?)
