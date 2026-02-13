# Implementer Input Examples

Examples of inputs for the Implementer skill for testing and development.

## Example 1: Test Addition

### PRSPEC_JSON

```json
{
  "schema_version": "1.0",
  "id": "prspec-20260213-140000",
  "repo": {
    "url": "https://github.com/example/utils-lib",
    "owner": "example",
    "name": "utils-lib",
    "default_branch": "main"
  },
  "base": {
    "branch": "main"
  },
  "head": {
    "branch": "test/validate-email-empty"
  },
  "title": "Add test for validateEmail with empty string",
  "body_markdown": "## What\nAdds edge case test for `validateEmail('')` returning false.\n\n## Why\nCurrent coverage: 75%. Missing this edge case.\n\n## How to verify\n```bash\nnpm test -- validation.test.ts\nnpm run coverage\n```",
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
    "tools": [{"name": "Claude Code", "role": "test generation"}],
    "disclosure_line": "Test generated with AI assistance"
  }
}
```

### Other Inputs

```json
{
  "REPO_ROOT": "/path/to/repo",
  "HEAD_BRANCH": "test/validate-email-empty"
}
```

### Expected Implementation

```typescript
// Add to src/utils/validation.test.ts
describe('validateEmail', () => {
  // Existing tests...

  it('returns false for empty string', () => {
    expect(validateEmail('')).toBe(false);
  });
});
```

### Expected Output

```json
{
  "status": "success",
  "data": {
    "changed_files": ["src/utils/validation.test.ts"],
    "commands_run": ["npm test -- validation.test.ts", "npm run coverage"],
    "tests": { "ok": true },
    "diff_stats": { "files": 1, "insertions": 5, "deletions": 0 }
  }
}
```

---

## Example 2: Bug Fix

### PRSPEC_JSON

```json
{
  "schema_version": "1.0",
  "id": "prspec-20260213-150000",
  "repo": {
    "url": "https://github.com/example/utils-lib",
    "owner": "example",
    "name": "utils-lib",
    "default_branch": "main"
  },
  "base": { "branch": "main" },
  "head": { "branch": "fix/null-check-parseurl" },
  "title": "Fix null check in parseURL to prevent crash",
  "body_markdown": "## What\nAdds null check in `parseURL()` before calling `toLowerCase()`.\n\n## Why\nFunction crashes when passed null/undefined. Reported in issue #123.",
  "change_type": "bugfix",
  "risk": "low",
  "breaking_change": false,
  "files_touched": ["src/utils/parseURL.ts"],
  "test_plan": ["npm test -- parseURL.test.ts"],
  "ai_assistance": {
    "used": true,
    "tools": [{"name": "Claude Code", "role": "bug fix"}],
    "disclosure_line": "Bug fix implemented with AI assistance"
  }
}
```

### Expected Implementation

```typescript
// src/utils/parseURL.ts
export function parseURL(url: string | null): URL | null {
  if (url === null || url === undefined) {
    return null;
  }
  try {
    return new URL(url.toLowerCase());
  } catch {
    return null;
  }
}
```

---

## Example 3: With Constraints

### PRSPEC_JSON

```json
{
  "schema_version": "1.0",
  "id": "prspec-20260213-160000",
  "title": "Add missing docstring for parseURL",
  "change_type": "docs",
  "risk": "low",
  "files_touched": ["src/utils/parseURL.ts"],
  "test_plan": ["npm run docs:generate"]
}
```

### CONSTRAINTS

```json
[
  "Do not modify package.json",
  "Match existing JSDoc style from validateEmail function",
  "Maximum 10 lines added"
]
```

### ALLOWED_COMMANDS

```json
["npm run docs:generate", "npx tsc --noEmit"]
```

---

## Example 4: Error Recovery Scenario

### Initial State

Test fails because function not exported:

```typescript
// validation.test.ts - new test
import { validateEmail } from './validation';  // Error: validateEmail not exported
```

### Self-Heal Loop

1. **Attempt 1**: Run tests → FAIL (import error)
2. **Fix**: Add export to validation.ts
3. **Attempt 2**: Run tests → FAIL (different error)
4. **Fix**: Adjust test assertion
5. **Attempt 3**: Run tests → PASS

### Expected Output

```json
{
  "status": "success",
  "data": {
    "changed_files": [
      "src/utils/validation.test.ts",
      "src/utils/validation.ts"
    ],
    "commands_run": ["npm test"],
    "tests": { "ok": true },
    "diff_stats": { "files": 2, "insertions": 15, "deletions": 1 },
    "followups": ["Consider adding more edge case tests"]
  },
  "warnings": ["Fixed missing export during implementation"]
}
```

---

## Example 5: Needs Human Escalation

### PRSPEC_JSON

```json
{
  "schema_version": "1.0",
  "id": "prspec-20260213-170000",
  "title": "Add authentication middleware",
  "change_type": "security",
  "risk": "high",
  "files_touched": ["src/auth/middleware.ts"],
  "test_plan": ["npm test"]
}
```

### Problem

Test suite has pre-existing failures unrelated to changes.

### Expected Output

```json
{
  "status": "needs_human",
  "summary": "Pre-existing test failures in unrelated files",
  "errors": ["3 tests failing in user.test.ts before any changes"],
  "data": {
    "changed_files": [],
    "commands_run": ["npm test"],
    "tests": { "ok": false, "failed_before_changes": true }
  }
}
```
