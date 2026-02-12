# PRSpec Guide

Comprehensive guide for creating well-scoped, mergeable PRSpecs.

## PRSpec Structure

See `../../schemas/prspec.schema.json` for the complete schema.

### Key Fields

**Required fields:**
- `schema_version`: Always "1.0"
- `id`: Unique identifier (e.g., "prspec-20240115-103700")
- `repo`: Repository metadata (url, owner, name, default_branch)
- `base`: Base branch info (branch name, optional sha)
- `head`: Head branch info (branch name, optional sha after implementation)
- `title`: PR title (5-120 chars, clear and imperative)
- `body_markdown`: PR description (What/Why/How tested/Notes)
- `change_type`: One of: docs, test, bugfix, refactor, perf, security, dx, build, ci, chore
- `risk`: One of: low, medium, high
- `files_touched`: Array of file paths (at least 1)
- `test_plan`: Array of verification steps (at least 1)
- `ai_assistance`: Object with `used`, `tools`, `disclosure_line`

**Optional fields:**
- `breaking_change`: Boolean (default false)
- `commands_run`: Array of commands run during implementation
- `checklist`: Array of checklist items for PR description
- `labels`: Array of suggested GitHub labels
- `issues`: Array of related issue numbers
- `maintainer_notes`: Additional notes for maintainers
- `merge_assessment`: Object with probability, reasons, blockers

## Minimal Scope Guidelines

### The Half Rule
**If you can cut the scope in half, do it.**

Example:
- ❌ "Add tests for all util functions" → Too broad
- ✅ "Add test for validateEmail edge case" → Focused

### One Thing Rule
**Each PR should do exactly one thing.**

Example:
- ❌ "Fix bug and add tests and update docs" → Three things
- ✅ "Fix null check bug in parseURL" → One thing
  - Follow-up PR: "Add tests for parseURL edge cases"
  - Follow-up PR: "Update parseURL docs with examples"

### File Count Rule
**Prefer 1-3 files touched. Be suspicious of 5+.**

Exceptions:
- Test file + implementation file = 2 files (OK)
- Renaming/moving file that affects imports = 5-10 files (OK if necessary)
- Mass formatting = 50+ files (AVOID)

### Line Count Rule
**Target <50 LOC changed. Be cautious >100 LOC.**

This is **total lines changed** (insertions + deletions), not LOC count.

Example:
- 30 insertions + 10 deletions = 40 LOC (good)
- 150 insertions + 50 deletions = 200 LOC (review carefully)

## Well-Scoped Examples

### Example 1: Test Addition

```json
{
  "schema_version": "1.0",
  "id": "prspec-test-edge-case",
  "repo": {
    "url": "https://github.com/example/utils-lib",
    "owner": "example",
    "name": "utils-lib",
    "default_branch": "main"
  },
  "base": {"branch": "main"},
  "head": {"branch": "test/validate-email-empty"},
  "title": "Add test for validateEmail with empty string",
  "body_markdown": "## What\nAdds edge case test for `validateEmail('')` returning false.\n\n## Why\nCurrent coverage: 75%. Missing this edge case.\n\n## How to verify\n```bash\nnpm test -- validation.test.ts\nnpm run coverage\n```",
  "change_type": "test",
  "risk": "low",
  "files_touched": ["src/utils/validation.test.ts"],
  "test_plan": [
    "npm test -- validation.test.ts",
    "Verify coverage increased"
  ],
  "ai_assistance": {
    "used": true,
    "tools": [{"name": "Claude Code", "role": "test generation"}],
    "disclosure_line": "Test generated with AI assistance"
  }
}
```

**Why well-scoped:**
- Single file touched (test only)
- ~10-15 LOC added
- Clear verification
- No production code changes

### Example 2: Documentation Fix

```json
{
  "schema_version": "1.0",
  "id": "prspec-fix-readme-link",
  "repo": {
    "url": "https://github.com/example/toolkit",
    "owner": "example",
    "name": "toolkit",
    "default_branch": "main"
  },
  "base": {"branch": "main"},
  "head": {"branch": "docs/fix-api-link"},
  "title": "Fix broken API documentation link in README",
  "body_markdown": "## What\nUpdates broken link to API docs (was returning 404).\n\n## Why\nLink points to old URL. Correct URL is in docs/API.md.\n\n## How to verify\nOpen README.md and click the link.",
  "change_type": "docs",
  "risk": "low",
  "files_touched": ["README.md"],
  "test_plan": ["Verify link works in browser"],
  "ai_assistance": {
    "used": true,
    "tools": [{"name": "Claude Code", "role": "docs fix"}],
    "disclosure_line": "Link updated with AI assistance"
  }
}
```

**Why well-scoped:**
- Single line change
- Zero risk
- Manual verification sufficient

### Example 3: Bug Fix

```json
{
  "schema_version": "1.0",
  "id": "prspec-null-check",
  "repo": {
    "url": "https://github.com/example/parser",
    "owner": "example",
    "name": "parser",
    "default_branch": "main"
  },
  "base": {"branch": "main"},
  "head": {"branch": "fix/null-check-parseurl"},
  "title": "Add null check in parseURL to prevent crash",
  "body_markdown": "## What\nAdds null check before calling `url.toLowerCase()`.\n\n## Why\nFixes crash when `url` is null/undefined. Issue #123.\n\n## How to verify\n```bash\nnpm test\n# Manual test: parseURL(null) should return null\n```\n\n## Notes\nBackward compatible - returns null for invalid input instead of crashing.",
  "change_type": "bugfix",
  "risk": "low",
  "files_touched": ["src/utils/parseURL.ts"],
  "test_plan": [
    "npm test",
    "Manual: parseURL(null) returns null"
  ],
  "issues": ["#123"],
  "ai_assistance": {
    "used": true,
    "tools": [{"name": "Claude Code", "role": "bug fix"}],
    "disclosure_line": "Fix implemented with AI assistance"
  }
}
```

**Why well-scoped:**
- Single function modified
- Clear before/after behavior
- Linked to issue
- Tests verify fix

## Poorly-Scoped Anti-Patterns

### Anti-Pattern 1: Scope Creep

❌ **Bad:**
```json
{
  "title": "Improve validation utils",
  "body_markdown": "Adds null checks, updates tests, fixes typos, adds docs",
  "files_touched": [
    "src/utils/validation.ts",
    "src/utils/validation.test.ts",
    "src/utils/parseURL.ts",
    "src/utils/parseURL.test.ts",
    "docs/API.md",
    "README.md"
  ]
}
```

✅ **Good (split into 3 PRs):**
1. "Add null check in parseURL"
2. "Add tests for validation edge cases"
3. "Fix typos in API docs"

### Anti-Pattern 2: Vague Description

❌ **Bad:**
```json
{
  "title": "Update code",
  "body_markdown": "Makes some improvements to the codebase.",
  "test_plan": ["Run tests"]
}
```

✅ **Good:**
```json
{
  "title": "Extract duplicate email regex into constant",
  "body_markdown": "## What\nExtracts `EMAIL_REGEX` constant used in 3 places.\n\n## Why\nReduces duplication, easier to update regex in future.\n\n## How to verify\n```bash\nnpm test -- validation.test.ts\n```",
  "test_plan": [
    "npm test -- validation.test.ts",
    "Verify all 3 call sites use EMAIL_REGEX"
  ]
}
```

### Anti-Pattern 3: Mass Changes

❌ **Bad:**
```json
{
  "title": "Format all files with Prettier",
  "files_touched": ["src/**/*.ts"],
  "change_type": "chore"
}
```

**Why bad:** Huge diff, hard to review, conflicts with ongoing work.

**Better approach:**
1. Add `.prettierrc` and CI check (1 PR)
2. Format incrementally as files are touched in other PRs
3. OR: Get explicit maintainer approval for mass format

### Anti-Pattern 4: Speculative Changes

❌ **Bad:**
```json
{
  "title": "Add dark mode support",
  "body_markdown": "Users might want dark mode in the future."
}
```

**Why bad:** Feature request without issue/discussion. May not align with roadmap.

**Better approach:**
1. Open issue: "Feature request: dark mode support"
2. Wait for maintainer feedback
3. Create PR only if approved

## Change Type Guidelines

### docs
- README updates
- API documentation
- Code comments
- Examples

**Scope:** 1-3 files, mostly markdown

### test
- New tests
- Test refactoring
- Coverage improvements

**Scope:** Test files only, no production code

### bugfix
- Fixes incorrect behavior
- Null checks
- Off-by-one errors

**Scope:** 1-2 production files + tests

### refactor
- Extract function
- Rename for clarity
- Simplify logic

**Scope:** <100 LOC, behavior unchanged, tests pass

### ci
- GitHub Actions
- CI config
- Build scripts

**Scope:** CI files only

### dx
- Linting setup
- Editor config
- Pre-commit hooks

**Scope:** Config files, no production code

### chore
- Dependency updates
- Version bumps
- Tooling changes

**Scope:** package.json, lockfiles, configs

## Risk Assessment

### Low Risk
- Test-only changes
- Documentation
- CI config (if broken, CI fails, doesn't merge)
- Obvious bug fixes with tests

### Medium Risk
- Production code changes with good test coverage
- Refactoring with comprehensive tests
- Dependency updates (minor/patch)

### High Risk
- Public API changes
- Database migrations
- Security fixes
- Dependency updates (major)
- Logic changes in core functions

**Rule:** Prefer low risk. If medium/high risk is necessary, scope must be **extra minimal** and test coverage **extra thorough**.

## Merge Assessment

Optionally include `merge_assessment` to help maintainers:

```json
{
  "merge_assessment": {
    "probability": 0.85,
    "reasons": [
      "Follows CONTRIBUTING.md guidelines",
      "Similar PR merged recently (#456)",
      "Clear value: improves coverage",
      "Low risk: test-only change"
    ],
    "blockers": []
  }
}
```

Use `probability`:
- `0.9-1.0`: Very likely (trivial fix, clear value)
- `0.7-0.9`: Likely (good fit, minor concerns)
- `0.5-0.7`: Uncertain (needs discussion)
- `<0.5`: Unlikely (recommend issue instead)

## Title Best Practices

**Good titles:**
- "Add test for validateEmail with empty string"
- "Fix null check in parseURL"
- "Update API docs link in README"
- "Extract email regex into constant"

**Bad titles:**
- "Update code" (too vague)
- "Fix bug" (which bug?)
- "Improvements" (what improvements?)
- "Refactor validation utils and add tests and fix docs" (scope creep)

**Format:**
- Imperative mood ("Add", "Fix", "Update", not "Adds", "Fixed", "Updating")
- Start with verb
- Be specific
- <120 chars
- No period at end

## Body Best Practices

**Structure:**
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
[Any additional context, trade-offs, or future work]
```

**What to avoid:**
- Marketing language ("amazing", "incredible")
- Long AI-generated stories
- Unnecessary background
- Claims you can't verify

**What to include:**
- Exact commands for verification
- Links to related issues
- Breaking change warnings
- Compatibility notes
