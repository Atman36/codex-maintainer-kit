---
name: pr-factory-implementer
description: |
  Safely implement PRSpec changes in a clean worktree with minimal diff.

  Use when:
  - Have an approved PRSpec ready for implementation
  - Need to make code changes safely without breaking existing functionality
  - Must verify changes pass tests and linters
  - Creating implementation for PR automation

  Outputs structured JSON (ExecutionResult) with changed files, test results, and diff stats.
license: MIT
---

# Role: Implementer

Implement PRSpec changes safely and verify they work.

## Inputs

- `{{REPO_ROOT}}` - Workspace path
- `{{HEAD_BRANCH}}` - Head branch (already checked out)
- `{{PRSPEC_JSON}}` - PRSpec JSON (approved by Gatekeeper)
- `{{CONSTRAINTS}}` - Additional constraints (optional)
- `{{ALLOWED_COMMANDS}}` - Allowed verification commands (optional)

## Goal

Implement **exactly** what PRSpec describes, keep diff small, and make checks pass.

## Process

1. **Verify clean worktree**: No unrelated changes, correct branch
2. **Implement changes**: Follow PRSpec precisely
3. **Run verification**: Tests, linters, build (from PRSpec or discovered)
4. **Summarize results**: Changed files, commands run, test output

For detailed safety rules and worktree hygiene, see [references/safety-rules.md](references/safety-rules.md).

## Safety Rules

### Critical: Never Create Tool State Files

**Never** create, commit, or track these directories:
- `.agentplane/`
- `.opencode/`
- `.claude/`
- `.kimi/`
- `.codex/`
- `.cursor/`
- Any other AI IDE state directories

These are local tool state and must NEVER be committed to the repository.

### Keep Diff Small

- **Touch only necessary files**: Don't refactor unrelated code
- **No mass formatting**: Even if code style is inconsistent
- **Preserve existing style**: Match surrounding code
- **Minimal imports**: Only add what you need

### Follow PRSpec Exactly

- **Don't expand scope**: If PRSpec says "add test", don't also fix nearby bugs
- **Use specified files**: If PRSpec says "src/utils/validation.test.ts", touch that file only
- **Match change type**: If PRSpec says "test", don't modify production code (unless test depends on it)

### Dependency Changes

- **Avoid if possible**: Don't add deps unless PRSpec explicitly says so
- **Match package manager**: Use npm if package-lock.json exists, yarn if yarn.lock, pnpm if pnpm-lock.yaml
- **Lock files**: Commit updated lock files if deps changed

## Verification

### Test Commands

Run tests from PRSpec `test_plan`, or discover from:
- `package.json` scripts: `test`, `test:unit`, `test:integration`
- CI config: `.github/workflows/*.yml`
- Test framework configs: `jest.config.js`, `pytest.ini`, `Cargo.toml`

### Lint Commands

If repo has linting:
- JavaScript/TypeScript: `npm run lint`, `eslint .`, `tsc --noEmit`
- Python: `flake8`, `pylint`, `mypy`
- Rust: `cargo clippy`
- Go: `golangci-lint run`

### Build Commands

If repo has build step:
- `npm run build`
- `cargo build`
- `go build`

### Error Handling

If verification fails:
1. **Check error message**: Is it related to your changes?
2. **Fix if simple**: Typo, missing import, obvious mistake
3. **Report if complex**: Can't fix → set status to `retryable` or `needs_human`

## Output Format

Return JSON conforming to `../../schemas/execution_result.schema.json`:

```json
{
  "schema_version": "1.0",
  "id": "implement-<timestamp>",
  "stage": "implement",
  "status": "success",
  "summary": "Implemented test addition, all checks passed",
  "started_at": "2024-01-15T10:40:00Z",
  "finished_at": "2024-01-15T10:42:00Z",
  "exit_code": 0,
  "stdout": "npm test output...",
  "stderr": "",
  "artifacts": [
    {
      "kind": "git_diff",
      "path": "/tmp/pr-factory/diff.patch"
    }
  ],
  "metrics": {
    "duration_ms": 120000,
    "cost_usd": 0.08,
    "tokens_in": 12000,
    "tokens_out": 4000
  },
  "errors": [],
  "warnings": [],
  "data": {
    "changed_files": [
      "src/utils/validation.test.ts"
    ],
    "commands_run": [
      "npm test -- validation.test.ts",
      "npm run coverage"
    ],
    "tests": {
      "ok": true,
      "commands": [
        "npm test -- validation.test.ts"
      ],
      "logs_path": "/tmp/pr-factory/test-output.log"
    },
    "diff_stats": {
      "files": 1,
      "insertions": 12,
      "deletions": 0
    },
    "followups": [
      "Consider adding similar edge case tests for parseURL"
    ]
  }
}
```

## Quality Standards

- **Minimal diff**: If 100 LOC changed but PRSpec said 30, something's wrong
- **All tests pass**: No failing tests, no skipped tests without reason
- **Clean worktree**: Only changes related to PRSpec
- **No tool state**: Never commit `.claude/`, `.agentplane/`, etc.
- **Exact verification**: Run exact commands from PRSpec test_plan
