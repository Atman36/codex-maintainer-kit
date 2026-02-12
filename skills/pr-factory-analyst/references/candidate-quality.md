# Candidate Quality Criteria

Deep dive into what makes a high-quality, merge-worthy PR candidate.

## The Four Pillars of Quality

### 1. Necessity (Why This Matters)

**Question:** Is there a real problem or clear value?

**High Necessity:**
- Fixes reported bug (issue link)
- Closes coverage gap (missing test for edge case)
- Fixes broken functionality (404 link, failing example)
- Addresses user pain (poor error message, missing docs)
- Improves measurable metric (perf benchmark, coverage %)

**Low Necessity:**
- "Would be nice to have"
- Subjective improvement ("cleaner")
- Premature optimization (no proof)
- Feature creep (adding functionality without request)

**Examples:**

✅ High Necessity:
```json
{
  "title": "Fix null check in parseURL - crashes on null input",
  "details": "Function crashes when passed null. Reported in issue #123. Affects users calling parseURL(null) in error handling paths."
}
```

❌ Low Necessity:
```json
{
  "title": "Refactor parseURL to be more functional",
  "details": "Current implementation is imperative. Functional style would be cleaner."
}
```

### 2. Maintainer Fit (Will They Want This?)

**Question:** Does this align with project direction and style?

**Good Fit Signals:**
- Follows CONTRIBUTING.md guidelines
- Matches existing code style
- Similar PRs accepted recently
- Addresses known pain point (in issues/discussions)
- Small, focused improvement

**Bad Fit Signals:**
- Goes against stated project direction
- Introduces new patterns/dependencies without discussion
- Large architectural change without RFC
- Mass changes (formatting, renaming)

**How to Check:**
- Read CONTRIBUTING.md
- Check recently merged PRs (similar scope/style?)
- Check rejected PRs (what patterns to avoid?)
- Check issues (is this requested?)

**Examples:**

✅ Good Fit:
```json
{
  "title": "Add test for validateEmail edge case",
  "details": "Repo has strong test culture (95% coverage target in CONTRIBUTING.md). Adding edge case test aligns with project standards. Similar test-only PRs merged recently (#456, #478)."
}
```

❌ Bad Fit:
```json
{
  "title": "Replace Jest with Vitest",
  "details": "Vitest is faster and more modern. Would improve DX.",
  "notes": "No discussion in issues. Maintainer recently rejected similar tool change PR (#789)."
}
```

### 3. Scope Control (Is This Minimal?)

**Question:** Can we make this smaller and still deliver value?

**Minimal Scope Checklist:**
- [ ] <100 LOC changed (prefer <50)
- [ ] <5 files touched (prefer 1-3)
- [ ] One clear value (not "fix bug AND add tests AND update docs")
- [ ] No scope creep (don't fix nearby issues while you're there)

**Scope Reduction Techniques:**

**Split into multiple PRs:**
```
❌ "Improve validation module"
✅ PR 1: "Add test for validateEmail edge case"
✅ PR 2: "Add docstring for validateEmail"
✅ PR 3: "Fix null check in parseURL"
```

**Remove nice-to-haves:**
```
❌ "Add test for parseURL edge cases (10 new tests)"
✅ "Add test for parseURL with null input" (1 test)
```

**Focus on one file/function:**
```
❌ "Add tests for all util functions"
✅ "Add test for validateEmail with empty string"
```

**Examples:**

✅ Minimal Scope:
```json
{
  "title": "Add test for validateEmail with empty string",
  "est_loc": 8,
  "targets": ["src/utils/validation.test.ts"],
  "details": "Single test case for empty string input. No changes to other tests or production code."
}
```

❌ Scope Creep:
```json
{
  "title": "Improve validation module testing",
  "est_loc": 200,
  "targets": [
    "src/utils/validation.test.ts",
    "src/utils/validation.ts",
    "src/utils/parseURL.test.ts",
    "src/utils/parseURL.ts",
    "docs/API.md"
  ],
  "details": "Adds 20 new tests, fixes 3 bugs found during testing, refactors validation.ts for testability, updates docs."
}
```

### 4. Verifiability (Can We Prove It Works?)

**Question:** How do we know this change works and doesn't break anything?

**High Verifiability:**
- Automated tests pass
- Exact commands provided
- Clear success criteria
- Manual verification if needed (with exact steps)

**Low Verifiability:**
- "Should work"
- "Run tests" (which tests?)
- No success criteria
- Requires deep knowledge to verify

**Verification Plan Template:**

```json
{
  "verification": {
    "commands": [
      "npm test -- validation.test.ts",
      "npm run coverage",
      "Manual: verify coverage increased from 75% to 90%"
    ]
  }
}
```

**Examples:**

✅ High Verifiability:
```json
{
  "title": "Add test for validateEmail with empty string",
  "verification": {
    "commands": [
      "npm test -- validation.test.ts",
      "npm run coverage",
      "Manual: coverage/index.html shows validation.ts coverage increased"
    ]
  }
}
```

❌ Low Verifiability:
```json
{
  "title": "Improve validation logic",
  "verification": {
    "commands": ["Test it manually"]
  }
}
```

## Good Candidate Examples by Type

### Example 1: Documentation (Excellent)

```json
{
  "id": "cand-docs-1",
  "title": "Add missing docstring for parseURL function",
  "change_type": "docs",
  "risk": "low",
  "est_loc": 8,
  "targets": ["src/utils/parseURL.ts"],
  "details": "Function parseURL is public API (exported from index.ts) but has no JSDoc. Users have to read implementation to understand parameters and return type. Similar functions (validateEmail, formatDate) all have docstrings.",
  "verification": {
    "commands": [
      "npm run docs:generate",
      "Manual: verify docstring appears in generated docs at docs/api/parseURL.html"
    ]
  },
  "notes": "Match existing docstring style from validateEmail. Include @param, @returns, @example."
}
```

**Why excellent:**
- Necessity: Public API without docs (user pain)
- Fit: Existing pattern (other functions have docstrings)
- Scope: Single function, ~8 lines
- Verifiability: Clear commands and success criteria

### Example 2: Test Coverage (Excellent)

```json
{
  "id": "cand-test-1",
  "title": "Add test for validateEmail with empty string",
  "change_type": "test",
  "risk": "low",
  "est_loc": 12,
  "targets": ["src/utils/validation.test.ts"],
  "details": "Current coverage: 75%. Missing edge case test for empty string input. Function has tests for valid/invalid emails but not for empty/null. Coverage report shows line 23 (empty check) never executed.",
  "verification": {
    "commands": [
      "npm test -- validation.test.ts",
      "npm run coverage",
      "Manual: coverage increased from 75% to 90%"
    ]
  },
  "notes": "Test both empty string ('') and null. Expect both to return false."
}
```

**Why excellent:**
- Necessity: Coverage gap (measurable)
- Fit: Repo has coverage target (95% in CONTRIBUTING.md)
- Scope: Single test file, ~12 lines
- Verifiability: Coverage report shows improvement

### Example 3: Bug Fix (Excellent)

```json
{
  "id": "cand-bug-1",
  "title": "Fix null check in parseURL to prevent crash",
  "change_type": "bugfix",
  "risk": "low",
  "est_loc": 5,
  "targets": ["src/utils/parseURL.ts"],
  "details": "Function crashes when passed null/undefined (TypeError: Cannot read property 'toLowerCase' of null). Reported in issue #123. Occurs in error handling paths where URL may be null.",
  "verification": {
    "commands": [
      "npm test -- parseURL.test.ts",
      "Manual: parseURL(null) should return null, not throw"
    ]
  },
  "notes": "Add null check before toLowerCase(). Return null for null/undefined input. Backward compatible - doesn't change behavior for valid inputs."
}
```

**Why excellent:**
- Necessity: Crashes (reported bug)
- Fit: Obvious fix, low controversy
- Scope: Single function, ~5 lines
- Verifiability: Clear behavior change

### Example 4: CI Improvement (Excellent)

```json
{
  "id": "cand-ci-1",
  "title": "Add ESLint check to CI workflow",
  "change_type": "ci",
  "risk": "low",
  "est_loc": 5,
  "targets": [".github/workflows/ci.yml"],
  "details": "Repo has ESLint configured (package.json has 'lint' script) but CI only runs tests. Adding lint step catches style issues before merge. Aligns with CONTRIBUTING.md guideline: 'All PRs must pass lint'.",
  "verification": {
    "commands": [
      "npm run lint  # Verify works locally",
      "Push to branch and check CI passes"
    ]
  },
  "notes": "Add step after test step. Use existing 'npm run lint' command. No changes to lint rules."
}
```

**Why excellent:**
- Necessity: Enforces stated requirement (CONTRIBUTING.md)
- Fit: Extends existing CI, no new tools
- Scope: Single CI file, ~5 lines
- Verifiability: CI run shows lint step

## Bad Candidate Examples (Avoid)

### Anti-Pattern 1: Subjective Improvement

```json
{
  "id": "bad-1",
  "title": "Refactor validation module for better architecture",
  "change_type": "refactor",
  "risk": "medium",
  "est_loc": 300,
  "targets": [
    "src/utils/validation.ts",
    "src/utils/validation.test.ts"
  ],
  "details": "Current code is procedural. Converting to class-based architecture would be cleaner and more maintainable."
}
```

**Why bad:**
- ❌ No necessity: "Would be cleaner" is subjective
- ❌ No fit check: Is class-based preferred in this repo?
- ❌ Large scope: 300 LOC, multiple files
- ❌ Risk: May introduce bugs, hard to review

### Anti-Pattern 2: Speculative Feature

```json
{
  "id": "bad-2",
  "title": "Add dark mode support to documentation site",
  "change_type": "feat",
  "risk": "medium",
  "est_loc": 150,
  "targets": ["docs/theme.css", "docs/layout.html"],
  "details": "Many users prefer dark mode. Adding this would improve UX."
}
```

**Why bad:**
- ❌ No necessity: "Many users" unsupported claim
- ❌ No fit check: Is this requested? On roadmap?
- ❌ Feature scope: Requires design decisions
- ❌ No proof: No issue/request linked

### Anti-Pattern 3: Mass Formatting

```json
{
  "id": "bad-3",
  "title": "Format all files with Prettier",
  "change_type": "chore",
  "risk": "low",
  "est_loc": 5000,
  "targets": ["src/**/*.ts"],
  "details": "Code style is inconsistent. Prettier would make it consistent."
}
```

**Why bad:**
- ❌ Huge scope: 5000 LOC, 50+ files
- ❌ Hard to review: Can't verify functional correctness
- ❌ Conflicts: Will conflict with ongoing PRs
- ❌ Low value: No functional improvement

### Anti-Pattern 4: Dependency Churn

```json
{
  "id": "bad-4",
  "title": "Replace lodash with ramda",
  "change_type": "refactor",
  "risk": "high",
  "est_loc": 200,
  "targets": ["package.json", "src/**/*.ts"],
  "details": "Ramda is more functional and modern. Would improve code quality."
}
```

**Why bad:**
- ❌ No necessity: Works fine with lodash
- ❌ High risk: May introduce bugs, breaks existing code
- ❌ No discussion: Requires maintainer buy-in
- ❌ Subjective: "More functional" is opinion

## Stack-Specific Patterns

### JavaScript/TypeScript

**Good candidates:**
- Missing type definitions
- strict: true in tsconfig.json
- Missing test for edge case
- No lint script in package.json

**Bad candidates:**
- Replace JS with TS (too large)
- Add new bundler (requires discussion)
- Update all deps (high risk)

### Python

**Good candidates:**
- Missing type hints on public functions
- Missing docstrings
- No requirements-dev.txt
- Missing `__init__.py`

**Bad candidates:**
- Convert to dataclasses (subjective)
- Add new framework (requires discussion)
- Rewrite in async (too large)

### Go

**Good candidates:**
- Missing error handling
- No examples in README
- Missing godoc comments

**Bad candidates:**
- Add new dependency (requires discussion)
- Refactor to interfaces (subjective)
- Rewrite with generics (too large)

### Rust

**Good candidates:**
- Missing doc comments
- No Clippy in CI
- Missing examples

**Bad candidates:**
- Unsafe rewrite (high risk)
- Add new crate (requires discussion)
- Refactor to macros (subjective)

## Merge Probability Assessment

Estimate likelihood maintainers will merge.

### High Probability (0.8-1.0)

**Signals:**
- Fixes reported bug
- Addresses stated goal (CONTRIBUTING.md, roadmap)
- Small scope (<50 LOC)
- Low risk (tests only, docs only)
- Similar PRs merged recently
- Clear value, no controversy

**Example:**
```json
{
  "merge_expectation": {
    "overall": "high",
    "rationale": [
      "Fixes reported bug #123",
      "Test-only change (zero risk)",
      "Aligns with 95% coverage goal",
      "Similar test PR merged last week (#456)"
    ]
  }
}
```

### Medium Probability (0.5-0.7)

**Signals:**
- Good idea but not requested
- Moderate scope (50-100 LOC)
- Medium risk (production code changes)
- Some subjective decisions
- Unclear maintainer preference

**Example:**
```json
{
  "merge_expectation": {
    "overall": "medium",
    "rationale": [
      "Clear improvement (better error message)",
      "But not explicitly requested",
      "Medium scope (3 files, 80 LOC)",
      "Requires review of error message wording"
    ]
  }
}
```

### Low Probability (0.0-0.4)

**Signals:**
- Subjective improvement
- Large scope (>100 LOC)
- High risk (API changes, breaking)
- No discussion/request
- Goes against project style

**Example:**
```json
{
  "merge_expectation": {
    "overall": "low",
    "rationale": [
      "Large refactor (200 LOC)",
      "Subjective benefit ('cleaner code')",
      "No issue/discussion",
      "Similar refactor PR rejected (#789)"
    ]
  }
}
```

## Summary Checklist

Before proposing a candidate:

- [ ] **Necessity**: Clear problem or value
- [ ] **Fit**: Aligns with project direction/style
- [ ] **Scope**: Minimal (<100 LOC, <5 files)
- [ ] **Verifiability**: Exact commands and success criteria
- [ ] **Risk**: Honest assessment (low/medium/high)
- [ ] **One value**: Can describe in one sentence
- [ ] **No speculation**: Based on actual code/issues, not "might be useful"
- [ ] **Merge probability**: Realistic estimate (>0.5 preferred)
