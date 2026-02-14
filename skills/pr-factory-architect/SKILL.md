---
name: pr-factory-architect
description: |
  Find small architectural improvements that reduce complexity without big rewrites.

  Use when:
  - Looking for refactoring opportunities beyond simple cleanups
  - Want to reduce duplication, coupling, or complexity
  - Need architectural improvement that fits in small PR (<200 LOC)
  - Seeking to clarify boundaries or isolate side-effects

  Builds structured JSON (ExecutionResult) with one architectural improvement candidate.
  Saves it to `/Users/Apple/Developer/pr-factory-kit/analysis_report/` and returns only the saved path in chat.
license: MIT
---

# Role: Architect

Find **one** small architectural improvement that reduces complexity.

## Inputs

- `{{REPO_ROOT}}` - Workspace path

## Goal

Find **one** architectural improvement that:
- Implementable as small PR (<200 LOC)
- Reduces complexity/duplication/coupling
- Does NOT change public API (unless already unstable/internal)
- Has clear verification path (tests/build)

## Examples of Good Improvements

### 1. Isolate Side-Effect
Extract side-effect (I/O, network, file system) behind interface for testability.

**Example:**
```
Current: Business logic directly calls fs.readFileSync()
Improvement: Extract FileReader interface, inject dependency
Benefit: Business logic testable without file system
```

### 2. Extract Duplicate Logic
Multiple places have same/similar code → extract into shared module.

**Example:**
```
Current: Email validation regex duplicated in 4 files
Improvement: Extract EMAIL_REGEX constant to validation/constants.ts
Benefit: Single source of truth, easier to update
```

### 3. Reduce Circular Imports
Module A imports B, B imports A → hard to understand, test, and maintain.

**Example:**
```
Current: user.ts ↔ auth.ts (circular)
Improvement: Extract shared types to user-types.ts
Benefit: Clear dependency direction
```

### 4. Clarify Boundaries
Core logic mixed with adapters/CLI → hard to test and reuse.

**Example:**
```
Current: Business logic in CLI handler
Improvement: Extract to core/ module, CLI calls core
Benefit: Core testable independently, reusable in API
```

### 5. Consistent Error Handling
Errors thrown inconsistently (string, Error, custom) → hard to handle.

**Example:**
```
Current: throw "Invalid input", throw new Error(), throw custom
Improvement: Introduce AppError base class
Benefit: Consistent error handling, better error context
```

For detailed patterns and examples, see [references/refactoring-patterns.md](references/refactoring-patterns.md).

## Rules

- **Don't propose big rewrites**: Keep it <200 LOC
- **Don't propose new frameworks**: Use existing tools
- **Don't add dependencies** unless truly necessary
- **Don't change public API** unless internal/unstable
- **Schema-valid JSON payload**: Build payload conforming to `ExecutionResult`
- **Persist analysis JSON**: Write payload to `/Users/Apple/Developer/pr-factory-kit/analysis_report/architect-<timestamp>.json`
- **Chat output format**: Return only `SAVED_JSON_PATH=<absolute_path_to_json>`

## Process

1. **Analyze codebase structure**: Understand current architecture
2. **Identify pain points**: Duplication, coupling, complexity
3. **Find ONE improvement**: Most impactful + smallest scope
4. **Sketch design**: How would it look after refactor?
5. **Plan verification**: How to test it works?

## Output Format

1. Build JSON conforming to `../../schemas/execution_result.schema.json`:

```json
{
  "schema_version": "1.0",
  "id": "architect-<timestamp>",
  "stage": "analysis",
  "status": "success",
  "summary": "Found architectural improvement: extract duplicate email regex",
  "started_at": "2024-01-15T11:00:00Z",
  "finished_at": "2024-01-15T11:05:00Z",
  "exit_code": 0,
  "artifacts": [],
  "metrics": {
    "duration_ms": 300000,
    "cost_usd": 0.10,
    "tokens_in": 20000,
    "tokens_out": 5000
  },
  "errors": [],
  "warnings": [],
  "data": {
    "candidate": {
      "id": "arch-1",
      "title": "Extract EMAIL_REGEX constant from 4 duplicate definitions",
      "change_type": "refactor",
      "risk": "low",
      "est_loc": 25,
      "targets": [
        "src/utils/validation.ts",
        "src/auth/email-validator.ts",
        "src/api/user-handler.ts",
        "src/lib/email-utils.ts",
        "src/constants/validation.ts"
      ],
      "rationale": "Email regex is duplicated in 4 files with slight variations. This creates inconsistency (different regex = different validation) and makes updates hard (need to change 4 places). Extract to single constant.",
      "design_sketch": "Create src/constants/validation.ts with EMAIL_REGEX. Update 4 files to import from constants. Remove local definitions. Use most strict regex version (from validation.ts).",
      "verification": {
        "commands": [
          "npm test -- validation.test.ts",
          "npm test -- email-validator.test.ts",
          "npm test",
          "grep -r 'EMAIL_REGEX' src/ (verify single definition)"
        ]
      },
      "notes": "Low risk - tests will catch any behavior change. All 4 call sites currently have tests."
    }
  }
}
```

## Alternative: Recommend Issue

If improvement is **risky** or requires **discussion**, return `status: needs_human`:

```json
{
  "schema_version": "1.0",
  "id": "architect-<timestamp>",
  "stage": "analysis",
  "status": "needs_human",
  "summary": "Found architectural improvement but requires maintainer discussion",
  "data": {
    "issue_proposal": {
      "title": "Proposal: Extract FileReader interface for better testability",
      "body": "Currently business logic directly calls fs.readFileSync in 12 places. This makes testing hard (need real files). Propose extracting FileReader interface.\n\nBenefit: Testable without file system\n\nRisk: Changes 12 call sites, may affect error handling\n\nRecommendation: Discuss approach before implementing"
    }
  }
}
```

2. Save the JSON file to:

`/Users/Apple/Developer/pr-factory-kit/analysis_report/architect-<timestamp>.json`

3. Return to chat only:

```text
SAVED_JSON_PATH=/Users/Apple/Developer/pr-factory-kit/analysis_report/architect-<timestamp>.json
```

## Quality Standards

- **One improvement only**: Not "improve architecture" (too vague)
- **Concrete target**: Specific files/modules, not "entire codebase"
- **Clear benefit**: Reduced duplication/complexity/coupling (measurable)
- **Small scope**: <200 LOC, <10 files touched
- **Verifiable**: Existing tests confirm behavior unchanged
- **Low controversy**: Obvious improvement, not subjective
