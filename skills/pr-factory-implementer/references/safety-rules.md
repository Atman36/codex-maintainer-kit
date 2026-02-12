# Implementation Safety Rules

Comprehensive safety guidelines for implementing PRSpecs without breaking things.

## Critical: Tool State Files

### NEVER Commit These

**Forbidden directories** (auto-reject if in git status):
```
.agentplane/
.opencode/
.claude/
.kimi/
.codex/
.cursor/
.windsurf/
.aider/
.continue/
```

**Why forbidden:**
- Local IDE state, not part of project
- Contains user-specific config
- May contain secrets or tokens
- Bloats repository
- Confuses other contributors

**Detection:**
```bash
# Before committing, check for forbidden dirs
git status --porcelain | grep -E '^\?\? \.(agentplane|opencode|claude|kimi|codex|cursor)/'
# If found, add to .gitignore and never commit
```

**Correct approach:**
1. Add to `.gitignore` if not already there
2. Never `git add .` blindly
3. Add specific files only: `git add src/utils/validation.test.ts`

## Worktree Hygiene

### Before Starting

**Verify clean state:**
```bash
cd {{REPO_ROOT}}

# Check for uncommitted changes
git status --porcelain
# Should be empty or only show expected changes

# Check current branch
git branch --show-current
# Should match {{HEAD_BRANCH}}

# Check for untracked files
git status --short
# Should not show tool state dirs
```

### During Implementation

**Make minimal changes:**
- Touch only files in PRSpec `files_touched`
- Don't refactor unrelated code
- Don't fix nearby bugs unless PRSpec says so
- Don't format unrelated files

**Track what you change:**
```bash
# After making changes, verify diff
git diff --stat
# Should match PRSpec est_loc

git diff
# Review each change: is it necessary?
```

### After Implementation

**Verify only intended files changed:**
```bash
git status --short
# Should show only files from PRSpec

git diff --name-only
# Should match PRSpec files_touched
```

## Minimal Diff Guidelines

### Touch Only Necessary Files

**Good (test-only PR):**
```
M  src/utils/validation.test.ts
```

**Bad (scope creep):**
```
M  src/utils/validation.test.ts
M  src/utils/validation.ts
M  src/utils/parseURL.ts
M  README.md
```

### No Mass Formatting

**Bad example:**
```diff
- function validateEmail(email) {
-   if (!email) return false;
-   return EMAIL_REGEX.test(email);
+ function validateEmail(email) {
+   if (!email) {
+     return false;
+   }
+   return EMAIL_REGEX.test(email);
  }
```

**Why bad:** Changed formatting in existing function when task was "add test".

**Good approach:** Only format code you add, match surrounding style.

### Preserve Existing Style

**Example: Match indentation**
```javascript
// Existing code uses 2 spaces
function existing() {
  const x = 1;
  return x;
}

// New code should also use 2 spaces
function newFunction() {
  const y = 2;  // 2 spaces, matching existing
  return y;
}
```

**Example: Match quotes**
```javascript
// Existing code uses single quotes
const existing = 'hello';

// New code should also use single quotes
const newVar = 'world';  // Not "world"
```

**Example: Match semicolons**
```javascript
// Existing code omits semicolons
const existing = 'hello'

// New code should also omit semicolons
const newVar = 'world'  // Not 'world';
```

## Dependency Management

### Avoid Adding Dependencies

**When to add deps:**
- PRSpec explicitly says "add dependency X"
- Existing repo pattern (e.g., repo already uses lodash, OK to use lodash)
- Standard library doesn't have equivalent

**When NOT to add deps:**
- "This library would make it easier" → Use standard library instead
- "This is a popular package" → Not a reason if not necessary
- "I'm familiar with this tool" → Learn the project's tools instead

### Package Manager Detection

**Detect which package manager:**
```bash
if [ -f "package-lock.json" ]; then
  echo "npm"
elif [ -f "yarn.lock" ]; then
  echo "yarn"
elif [ -f "pnpm-lock.yaml" ]; then
  echo "pnpm"
else
  echo "npm"  # default
fi
```

**Use correct commands:**
- npm: `npm install <package>`, `npm test`
- yarn: `yarn add <package>`, `yarn test`
- pnpm: `pnpm add <package>`, `pnpm test`

### Lock Files

**Always commit updated lock files:**
```bash
# If you run npm install, commit:
git add package-lock.json

# If you run yarn add, commit:
git add yarn.lock

# If you run pnpm add, commit:
git add pnpm-lock.yaml
```

## Error Recovery

### Test Failures

**Strategy 1: Fix if simple**

Example: Missing import
```
FAIL src/utils/validation.test.ts
  ● validateEmail › returns false for empty string

    ReferenceError: validateEmail is not defined
```

**Fix:**
```typescript
import { validateEmail } from './validation';  // Add missing import
```

**Strategy 2: Report if complex**

Example: Existing test broken
```
FAIL src/utils/parseURL.test.ts
  ● parseURL › handles query params

    Expected: "https://example.com?foo=bar"
    Received: undefined
```

**If this test was broken BEFORE your changes:**
```json
{
  "status": "needs_human",
  "errors": ["Pre-existing test failure in parseURL.test.ts"],
  "warnings": ["Test suite has 1 failing test unrelated to changes"]
}
```

### Lint Failures

**Strategy 1: Auto-fix if available**
```bash
# ESLint
npm run lint -- --fix

# Prettier
npx prettier --write src/utils/validation.test.ts

# Black (Python)
black src/utils/validation_test.py
```

**Strategy 2: Manual fix if simple**

Example: Unused variable
```typescript
// Lint error: 'result' is assigned but never used
const result = validateEmail('test');  // Remove or use it
expect(validateEmail('test')).toBe(true);  // Fixed
```

### Build Failures

**TypeScript type errors:**
```
error TS2345: Argument of type 'null' is not assignable to parameter of type 'string'.
```

**Fix:** Add type guard or adjust types
```typescript
// Before
validateEmail(null);

// After
if (url !== null) {
  validateEmail(url);
}
```

## Verification Commands

### Discover Test Commands

**From package.json:**
```bash
cat package.json | grep -A 5 '"scripts"'
# Look for: "test", "test:unit", "test:integration"
```

**From CI config:**
```bash
cat .github/workflows/*.yml | grep -A 2 'run: npm'
# Look for: npm test, npm run test:ci
```

**From test framework:**
```bash
# Jest
if [ -f "jest.config.js" ]; then npm test; fi

# Pytest
if [ -f "pytest.ini" ]; then pytest; fi

# Cargo
if [ -f "Cargo.toml" ]; then cargo test; fi
```

### Run Verification

**Basic verification:**
```bash
# 1. Tests
npm test

# 2. Linting (if exists)
npm run lint

# 3. Type check (if TypeScript)
npx tsc --noEmit

# 4. Build (if build step exists)
npm run build
```

**Targeted verification** (from PRSpec):
```bash
# If PRSpec test_plan says:
# ["npm test -- validation.test.ts", "npm run coverage"]

npm test -- validation.test.ts
npm run coverage
```

### Capture Output

**Save test output:**
```bash
npm test 2>&1 | tee /tmp/test-output.log
```

**Parse exit code:**
```bash
npm test
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
  echo "Tests passed"
else
  echo "Tests failed with exit code $EXIT_CODE"
fi
```

## Clean Implementation Examples

### Example 1: Test Addition (Clean)

**PRSpec:**
- change_type: test
- files_touched: ["src/utils/validation.test.ts"]
- est_loc: 12

**Implementation:**
```typescript
// src/utils/validation.test.ts
describe('validateEmail', () => {
  // Existing tests...

  it('returns false for empty string', () => {  // +1 line
    expect(validateEmail('')).toBe(false);      // +1 line
  });                                            // +1 line
                                                  // +1 line (blank)
  it('returns false for null', () => {          // +1 line
    expect(validateEmail(null)).toBe(false);    // +1 line
  });                                            // +1 line
});
```

**Diff stats:**
- Files: 1 ✅
- Insertions: 7 ✅
- Deletions: 0 ✅

**Verification:**
```bash
npm test -- validation.test.ts  # ✅ Pass
```

### Example 2: Bug Fix (Clean)

**PRSpec:**
- change_type: bugfix
- files_touched: ["src/utils/parseURL.ts"]
- est_loc: 5

**Implementation:**
```typescript
// src/utils/parseURL.ts
export function parseURL(url: string | null): URL | null {
  if (url === null || url === undefined) {  // +1 line (null check)
    return null;                             // +1 line
  }                                          // +1 line

  try {
    return new URL(url.toLowerCase());       // Existing, now safe
  } catch {
    return null;
  }
}
```

**Diff stats:**
- Files: 1 ✅
- Insertions: 3 ✅
- Deletions: 0 ✅

**Verification:**
```bash
npm test -- parseURL.test.ts  # ✅ Pass
npm run lint                   # ✅ Pass
npx tsc --noEmit               # ✅ Pass
```

### Example 3: Documentation (Clean)

**PRSpec:**
- change_type: docs
- files_touched: ["README.md"]
- est_loc: 1

**Implementation:**
```markdown
<!-- README.md -->
## API Documentation

Full API reference: [API.md](https://example.com/docs/api)  <!-- Fixed link -->
```

**Diff stats:**
- Files: 1 ✅
- Insertions: 0 ✅
- Deletions: 0 ✅
- Modifications: 1 ✅

**Verification:**
```bash
# Manual: click link, verify it works
```

## Dirty Implementation Anti-Patterns

### Anti-Pattern 1: Scope Creep

**PRSpec:** "Add test for validateEmail"

**Bad implementation:**
```diff
M  src/utils/validation.test.ts  # Expected
M  src/utils/validation.ts        # NOT in PRSpec
M  src/utils/parseURL.ts          # NOT in PRSpec
M  README.md                       # NOT in PRSpec
```

**Why bad:** Touched 4 files when PRSpec said 1.

**Fix:** Implement ONLY what PRSpec says. Save other improvements for follow-up PRs.

### Anti-Pattern 2: Mass Formatting

**PRSpec:** "Add test for validateEmail"

**Bad implementation:**
```diff
M  src/utils/validation.test.ts  (200 lines changed)
```

**Why bad:** PRSpec said 12 LOC, got 200.

**Diagnosis:**
```bash
git diff src/utils/validation.test.ts
# Shows: entire file reformatted (spaces → tabs)
```

**Fix:**
1. Undo changes: `git checkout src/utils/validation.test.ts`
2. Disable auto-format for this session
3. Implement only the test addition
4. Match existing file style

### Anti-Pattern 3: Tool State Committed

**Bad implementation:**
```diff
M  src/utils/validation.test.ts
A  .claude/memory.json
A  .agentplane/state.db
```

**Why bad:** Committed tool state files.

**Fix:**
```bash
git reset HEAD .claude/ .agentplane/
echo '.claude/' >> .gitignore
echo '.agentplane/' >> .gitignore
git add .gitignore
```

## Summary Checklist

Before marking implementation complete:

- [ ] Only files from PRSpec `files_touched` changed
- [ ] Diff stats match PRSpec `est_loc` (±20%)
- [ ] No tool state files (`.claude/`, `.agentplane/`, etc.)
- [ ] All tests pass
- [ ] All linters pass
- [ ] No unrelated changes
- [ ] Followed existing code style
- [ ] Verification commands match PRSpec `test_plan`
- [ ] Exit code = 0 (success)
