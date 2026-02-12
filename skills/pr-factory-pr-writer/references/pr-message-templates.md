# PR Message Templates

Comprehensive guide for writing excellent PR messages by change type.

## General Principles

### Concise > Verbose

**Concise (good):**
```markdown
## What
Adds edge case test for `validateEmail('')` returning false.

## Why
Current coverage: 75%. Missing this edge case.

## How to verify
```bash
npm test -- validation.test.ts
npm run coverage
```
```

**Verbose (bad):**
```markdown
## What
This pull request implements a comprehensive test suite enhancement by adding
an edge case test for the validateEmail function. The test specifically covers
the scenario where an empty string is passed to the function, which is a common
user input pattern that wasn't previously tested in our codebase.

## Why
After conducting a thorough analysis of our test coverage metrics using industry-standard
tools, I discovered that the validateEmail function only had 75% code coverage...
```

**Why concise is better:**
- Faster to review
- Gets to the point
- Respects maintainer's time
- Easier to scan

### Factual > Marketing

**Factual (good):**
```markdown
## What
Fixes null pointer exception in parseURL when url is null.

## Why
Function crashes when passed null. Reported in issue #123.
```

**Marketing (bad):**
```markdown
## What
This incredible improvement revolutionizes the parseURL function by implementing
a robust null safety mechanism that will dramatically enhance code reliability!

## Why
Our amazing team discovered this critical issue that was causing catastrophic failures...
```

**Why factual is better:**
- Maintainers trust it more
- Sounds professional
- Focuses on value, not hype

## Templates by Change Type

### Test Addition

```markdown
## What
Adds [test description] for [function/module].

## Why
[Reason: coverage gap, edge case, regression prevention, etc.]

## How to verify
```bash
[test command]
[coverage command]
```

## Notes
[Optional: coverage before/after, related tests]
```

**Example:**
```markdown
## What
Adds test for `validateEmail()` with empty string input.

## Why
Current coverage: 75%. Missing edge case for empty string.

## How to verify
```bash
npm test -- validation.test.ts
npm run coverage
```

## Notes
Coverage increases from 75% to 90% with this test.
```

### Bug Fix

```markdown
## What
Fixes [specific bug description].

## Why
[Impact: what breaks, when it breaks, issue link if available]

## How to verify
```bash
[test command]
[manual reproduction steps if applicable]
```

## Notes
[Optional: backward compatibility, breaking changes, migration notes]
```

**Example:**
```markdown
## What
Fixes null pointer exception in `parseURL()` when url is null.

## Why
Function crashes when passed null/undefined. Reported in issue #123.

## How to verify
```bash
npm test -- parseURL.test.ts
# Manual test: parseURL(null) should return null
```

## Notes
Backward compatible - returns null for invalid input instead of crashing.
```

### Documentation

```markdown
## What
[Updates/Adds/Fixes] [documentation type] for [topic].

## Why
[Reason: outdated, missing, incorrect, unclear]

## How to verify
[Manual check: read the docs, verify links work, etc.]

## Notes
[Optional: related docs, examples added]
```

**Example:**
```markdown
## What
Fixes broken API documentation link in README.

## Why
Link returns 404. Correct URL is documented in docs/API.md.

## How to verify
Open README.md and verify link works: https://example.com/docs/api

## Notes
No code changes, documentation only.
```

### CI/DX Improvement

```markdown
## What
[Adds/Updates/Fixes] [CI/DX tool] to [purpose].

## Why
[Reason: missing check, broken CI, improve developer experience]

## How to verify
```bash
[CI command locally]
[Push to branch and check CI]
```

## Notes
[Optional: impact on existing workflows, breaking changes]
```

**Example:**
```markdown
## What
Adds ESLint check to GitHub Actions CI workflow.

## Why
Repo has ESLint configured but CI only runs tests. This catches style issues early.

## How to verify
```bash
npm run lint  # Verify works locally
# Push to branch and check CI passes
```

## Notes
No changes to code or existing CI steps, purely additive.
```

### Refactoring

```markdown
## What
[Refactoring description: extract, rename, simplify, etc.]

## Why
[Benefit: reduce duplication, improve clarity, easier to maintain]

## How to verify
```bash
[test command]
[verification that behavior is unchanged]
```

## Notes
No behavior changes, tests confirm functionality preserved.
```

**Example:**
```markdown
## What
Extracts duplicate email regex into `EMAIL_REGEX` constant.

## Why
Regex is duplicated in 3 places. Single constant is easier to update.

## How to verify
```bash
npm test -- validation.test.ts
# Verify all 3 call sites use EMAIL_REGEX
```

## Notes
No behavior changes, purely structural improvement.
```

### Dependency Update

```markdown
## What
Updates [dependency] from [old version] to [new version].

## Why
[Reason: security fix, bug fix, new features needed]

## How to verify
```bash
[test command]
[build command]
```

## Notes
[Breaking changes, migration steps, changelog link]
```

**Example:**
```markdown
## What
Updates lodash from 4.17.20 to 4.17.21.

## Why
Security fix for CVE-2021-23337 (prototype pollution).

## How to verify
```bash
npm test
npm run build
```

## Notes
Patch version, no breaking changes. Changelog: https://github.com/lodash/lodash/releases/tag/4.17.21
```

## What/Why/How/Notes Details

### What Section

**Purpose:** Describe the change clearly and concisely.

**Good examples:**
- "Adds test for `validateEmail('')` returning false"
- "Fixes null check in `parseURL()`"
- "Updates README link to API docs"
- "Extracts `EMAIL_REGEX` constant from duplicated regex"

**Bad examples:**
- "Changes code" (too vague)
- "Updates validation" (which part?)
- "This PR adds a test..." (don't start with "This PR")
- "I implemented..." (avoid first person)

**Guidelines:**
- Start with verb (Add, Fix, Update, Extract, etc.)
- Be specific (mention function/file/module)
- Keep it 1-2 sentences
- No "This PR" or "I"

### Why Section

**Purpose:** Explain the motivation and value.

**Good examples:**
- "Current coverage: 75%. Missing this edge case."
- "Function crashes when passed null. Reported in issue #123."
- "Link returns 404. Correct URL is in docs/API.md."
- "Regex duplicated in 3 places. Single constant easier to update."

**Bad examples:**
- "It's better this way" (not specific)
- "I thought it would be good to..." (too subjective)
- "This is a best practice" (says what, not why)

**Guidelines:**
- Focus on value/impact
- Link to issues if applicable
- Keep it factual
- Answer "Why now?" or "Why is this a problem?"

### How to Verify Section

**Purpose:** Provide exact steps to verify the change works.

**Good examples:**
```bash
npm test -- validation.test.ts
npm run coverage
```

```bash
npm test
# Manual: parseURL(null) should return null
```

```
Open README.md and verify link works
```

**Bad examples:**
- "Run tests" (which tests?)
- "Test it" (how?)
- "It works" (not verifiable)

**Guidelines:**
- Include exact commands
- Use code blocks for bash commands
- If manual, specify exact steps
- If not tested, say "Recommended verification:"

### Notes Section (Optional)

**Purpose:** Additional context that doesn't fit elsewhere.

**When to include:**
- Breaking changes or migration needed
- Trade-offs or alternatives considered
- Future work or follow-ups
- Coverage/performance impact
- Compatibility notes

**Good examples:**
- "Coverage increases from 75% to 90%"
- "Backward compatible - returns null instead of throwing"
- "Breaking change: requires Node 18+"
- "Follow-up: add integration tests"

**Bad examples:**
- "Thanks for reviewing!" (save for comments)
- "Let me know if you have questions" (obvious)
- Long explanations (should be in Why)

## Disclosure Line Examples

AI assistance must be disclosed. Keep it short and factual.

### Good Disclosure Lines

**Test:**
- "Test generated with AI assistance (Claude Code PR Factory)"
- "Test implementation assisted by AI"

**Bug fix:**
- "Bug fix implemented with AI assistance (Claude Code)"
- "Implementation assisted by AI agent"

**Docs:**
- "Documentation updated with AI assistance"

**CI:**
- "CI configuration generated with AI assistance"

**Refactor:**
- "Refactoring assisted by AI (Claude Code PR Factory)"

### Bad Disclosure Lines

**Too long:**
- "This incredible PR was created using the revolutionary Claude Code PR Factory system, which is an advanced AI agent that autonomously generates pull requests..."

**Too vague:**
- "AI helped"
- "Made by AI"

**Too apologetic:**
- "Sorry if the AI made mistakes, please review carefully"

**Marketing:**
- "Powered by cutting-edge AI technology"

**No disclosure:**
- "" (empty - must disclose if AI was used)

### Format

Always in `ai_assistance.disclosure_line`:
```json
{
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
```

## Complete Examples

### Example 1: Test Addition (Excellent)

```markdown
Title: Add test for validateEmail with empty string

## What
Adds edge case test for `validateEmail('')` returning false.

## Why
Current coverage: 75%. Missing this edge case.

## How to verify
```bash
npm test -- validation.test.ts
npm run coverage
```

## Notes
Coverage increases from 75% to 90% with this test.

---
Test generated with AI assistance (Claude Code PR Factory)
```

### Example 2: Bug Fix (Excellent)

```markdown
Title: Fix null check in parseURL to prevent crash

## What
Adds null check in `parseURL()` before calling `toLowerCase()`.

## Why
Function crashes when passed null/undefined. Reported in issue #123.

## How to verify
```bash
npm test -- parseURL.test.ts
# Manual: parseURL(null) should return null
```

## Notes
Backward compatible - returns null for invalid input instead of crashing.

---
Bug fix implemented with AI assistance (Claude Code)
```

### Example 3: Documentation (Excellent)

```markdown
Title: Fix broken API docs link in README

## What
Updates broken API documentation link in README.

## Why
Link returns 404. Correct URL is documented in docs/API.md.

## How to verify
Open README.md and verify link works: https://example.com/docs/api

## Notes
No code changes, documentation only.

---
Documentation updated with AI assistance
```

### Example 4: CI Improvement (Excellent)

```markdown
Title: Add ESLint check to CI workflow

## What
Adds ESLint check to GitHub Actions CI workflow.

## Why
Repo has ESLint configured but CI only runs tests. This catches style issues early.

## How to verify
```bash
npm run lint  # Verify works locally
# Push to branch and check CI passes
```

## Notes
No changes to code or existing CI steps, purely additive.

---
CI configuration generated with AI assistance
```

## Common Mistakes to Avoid

### Mistake 1: Starting with "This PR"

❌ Bad:
```markdown
This PR adds a test for validateEmail...
```

✅ Good:
```markdown
Adds test for validateEmail...
```

### Mistake 2: Using First Person

❌ Bad:
```markdown
I implemented a fix for the null check...
```

✅ Good:
```markdown
Fixes null check in parseURL...
```

### Mistake 3: Vague Commands

❌ Bad:
```markdown
## How to verify
Run the tests and make sure they pass.
```

✅ Good:
```markdown
## How to verify
```bash
npm test -- validation.test.ts
npm run coverage
```
```

### Mistake 4: Marketing Language

❌ Bad:
```markdown
This amazing improvement revolutionizes the validation system...
```

✅ Good:
```markdown
Adds test for edge case in validation...
```

### Mistake 5: Long Explanations

❌ Bad:
```markdown
## What
This pull request implements a comprehensive test suite enhancement by adding
multiple edge case tests for the validateEmail function, specifically covering
scenarios where empty strings, null values, and undefined values are passed...
[continues for 200 words]
```

✅ Good:
```markdown
## What
Adds edge case tests for `validateEmail()` with empty string and null input.
```

## Summary Checklist

Before finalizing PR message:

- [ ] Title is imperative, specific, <120 chars
- [ ] What section: 1-2 sentences, starts with verb
- [ ] Why section: explains value/impact
- [ ] How to verify: exact commands or steps
- [ ] Notes (if applicable): additional context
- [ ] No "This PR", "I", "we"
- [ ] No marketing language
- [ ] Disclosure line present and concise
- [ ] Commands are copy-pasteable
- [ ] Honest about what was/wasn't tested
