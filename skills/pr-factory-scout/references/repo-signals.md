# Repository Signals and Scoring

Detailed guidance for analyzing repository maturity and generating quality candidates.

## CI/CD Detection

Check for these files (in order of preference):

- `.github/workflows/*.yml` - GitHub Actions (most common)
- `.circleci/config.yml` - CircleCI
- `.travis.yml` - Travis CI
- `azure-pipelines.yml` - Azure Pipelines
- `.gitlab-ci.yml` - GitLab CI
- `Jenkinsfile` - Jenkins

**What to extract:**
- Test commands run in CI
- Build commands
- Linting/formatting tools
- Deployment steps

## Test Detection

Look for:
- `test/` or `tests/` or `__tests__/` directories
- `*.test.ts`, `*.spec.ts`, `*.test.js` files
- Test configuration: `jest.config.js`, `vitest.config.ts`, `pytest.ini`, etc.

**Coverage signals:**
- `.coveragerc`, `coverage/` folder
- Coverage badges in README
- Coverage thresholds in package.json or CI

## Stack Detection Patterns

**JavaScript/TypeScript:**
- `package.json` → check "scripts", "dependencies", "devDependencies"
- Common frameworks: react, vue, angular, express, next, nest

**Python:**
- `requirements.txt`, `setup.py`, `pyproject.toml`
- Common frameworks: django, flask, fastapi, pytest

**Go:**
- `go.mod` → check module dependencies
- Common tools: go test, golangci-lint

**Rust:**
- `Cargo.toml` → check dependencies
- Common tools: cargo test, cargo clippy

**Ruby:**
- `Gemfile` → check gems
- Common frameworks: rails, sinatra, rspec

## Contributing Guidelines Analysis

Read `CONTRIBUTING.md` or `.github/CONTRIBUTING.md` for:

- **Required checks**: "All PRs must pass tests"
- **Code style**: "Use Prettier/Black/gofmt"
- **Commit format**: "Follow Conventional Commits"
- **PR size**: "Keep PRs small and focused"
- **Issue linking**: "Link PR to issue"

## Scoring Heuristics (0-10)

### High Score Indicators (7-10)
- Active maintenance (commits in last 7 days)
- CI/CD configured and passing
- Test coverage > 60%
- Clear CONTRIBUTING.md
- Issue templates present
- Recent merged PRs from external contributors

### Medium Score Indicators (4-6)
- Commits in last 30 days
- Some CI (but maybe failing)
- Tests exist but coverage unknown
- README has contribution section
- Few external PRs

### Low Score Indicators (0-3)
- No commits in 6+ months
- No CI/CD
- No tests
- No contribution guidelines
- No external PRs merged

### Blockers (auto-reject)
- Archived repository
- No commits in 12+ months
- LICENSE explicitly prohibits modifications
- README says "not accepting PRs"

## Candidate Generation Strategies

### Docs Improvements
- Fix typos in README/docs (use spell checker output)
- Add missing code examples
- Update outdated links
- Add missing API docs

**Risk**: Very low
**Est LOC**: 5-30 lines
**Verification**: Manual review, link checker

### Test Coverage
- Add missing unit test for existing function
- Add edge case test
- Add integration test for happy path

**Risk**: Low
**Est LOC**: 10-50 lines
**Verification**: Run test suite, check coverage report

### Bug Fixes
- Fix obvious bug (null check, off-by-one, typo in code)
- Fix deprecation warning
- Fix broken example

**Risk**: Low-Medium
**Est LOC**: 5-20 lines
**Verification**: Tests pass, manual verification

### CI/DX Improvements
- Add missing CI step (e.g., linting if tests exist but no lint)
- Fix failing CI (if quick fix)
- Add editor config (.editorconfig, .vscode/settings.json)
- Add pre-commit hooks

**Risk**: Low
**Est LOC**: 10-50 lines
**Verification**: CI runs successfully

### Refactoring (BE CAREFUL)
- Extract duplicate code into function
- Rename confusing variable
- Simplify conditional logic

**Risk**: Medium
**Est LOC**: 20-100 lines
**Verification**: Tests pass, manual code review

**Anti-pattern**: Avoid mass formatting, renaming everything, adding new dependencies

## Good Candidate Examples

**Example 1: Missing test**
```json
{
  "id": "cand-1",
  "title": "Add test for validateEmail with empty string",
  "change_type": "test",
  "risk": "low",
  "est_loc": 12,
  "likely_paths": ["src/utils/validation.test.ts"],
  "rationale": "Function validateEmail is missing edge case test for empty string input. Current coverage: 75%, this brings it to 90%.",
  "test_plan": [
    "npm test -- validation.test.ts",
    "npm run coverage"
  ]
}
```

**Example 2: Docs fix**
```json
{
  "id": "cand-2",
  "title": "Fix broken link in README to API docs",
  "change_type": "docs",
  "risk": "low",
  "est_loc": 1,
  "likely_paths": ["README.md"],
  "rationale": "Link to API docs returns 404. Correct URL is available in docs/API.md.",
  "test_plan": [
    "Open README.md and verify link works"
  ]
}
```

**Example 3: CI improvement**
```json
{
  "id": "cand-3",
  "title": "Add linting step to CI workflow",
  "change_type": "ci",
  "risk": "low",
  "est_loc": 5,
  "likely_paths": [".github/workflows/ci.yml"],
  "rationale": "Repo has ESLint configured (package.json) but CI only runs tests. Adding lint step catches style issues early.",
  "test_plan": [
    "npm run lint (verify it works locally)",
    "Push to branch and check CI passes"
  ]
}
```

## Bad Candidate Examples (Avoid)

**❌ Example 1: Mass formatting**
```json
{
  "id": "bad-1",
  "title": "Format all files with Prettier",
  "rationale": "Code is inconsistently formatted"
}
```
**Why bad**: Mass formatting creates huge diffs, hard to review, likely to conflict with ongoing work.

**❌ Example 2: New dependency**
```json
{
  "id": "bad-2",
  "title": "Replace lodash with ramda for better FP",
  "rationale": "Ramda is more functional"
}
```
**Why bad**: Adding/replacing dependencies requires maintainer buy-in, increases bundle size, may break things.

**❌ Example 3: Refactor everything**
```json
{
  "id": "bad-3",
  "title": "Refactor utils/ folder to use classes",
  "est_loc": 500
}
```
**Why bad**: Large scope, subjective improvement, high risk of breaking changes.

**❌ Example 4: Speculative feature**
```json
{
  "id": "bad-4",
  "title": "Add dark mode support",
  "rationale": "Users might want dark mode"
}
```
**Why bad**: Feature request without issue/discussion. May not align with project roadmap.

## Stack-Specific Patterns

### JavaScript/TypeScript
- Missing `strict: true` in tsconfig.json
- Missing lint script in package.json
- Outdated dependencies (check with `npm outdated`)
- Missing type definitions

### Python
- Missing `__init__.py` in package
- No type hints on public functions
- Missing docstrings
- No `requirements-dev.txt`

### Go
- Missing error handling
- No go.mod tidy
- Missing examples in README

### Rust
- Missing `cargo fmt` check in CI
- No Clippy lints
- Missing documentation comments

## Verification Commands

Always verify your suggested commands actually work:

```bash
# Before suggesting "npm test"
cd {{REPO_ROOT}} && npm test

# Before suggesting "cargo test"
cd {{REPO_ROOT}} && cargo test

# Before suggesting "pytest"
cd {{REPO_ROOT}} && pytest
```

If a command fails, adjust the candidate or report it as a blocker.
