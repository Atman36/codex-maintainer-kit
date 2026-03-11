# PR Factory Workflow

Comprehensive guide to the PR Factory pipeline, stage details, and decision points.

## Table of Contents

1. [Pipeline Overview](#pipeline-overview)
2. [Stage Details](#stage-details)
3. [Decision Points](#decision-points)
4. [Data Flow](#data-flow)
5. [Quality Gates](#quality-gates)
6. [Error Handling](#error-handling)
7. [Usage Scenarios](#usage-scenarios)

## Pipeline Overview

The PR Factory pipeline consists of analysis stages, per-PR execution stages, and an optional publish step:

**Main Pipeline:**
1. **Scout** - Quick triage and candidate discovery
2. **Analyst** - Deep analysis (used in `full` mode after Scout)
3. **Gatekeeper** - Candidate selection and PRSpec creation
4. **Implementer** - Safe implementation
5. **Reviewer** - Post-implementation diff quality gate
6. **PR Writer** - Excellent PR message creation
7. **Publisher** - Fork/push/open PR (only if user explicitly requests publishing)

**Optional Agents:**
- **Critic** - Pre-implementation quality gate (recommended)
- **Architect** - Architectural improvement discovery (alternative to Scout/Analyst)

### Typical Flow

```
Repository → Scout → Critic → Gatekeeper → Implementer → Reviewer → PR Writer → Publisher
                ↓
            Analyst (optional, if more depth needed)
                ↓
            Architect (optional, if refactor focus)
```

## Stage Details

### Stage 1: Scout (Quick Triage)

**Purpose:** Quickly assess repo and find 3-7 mergeable candidates.

**Inputs:**
- `{{REPO_ROOT}}` - Local repository path
- `{{REPO_URL}}` - Repository URL
- `{{BASE_BRANCH}}` - Target branch

**Process:**
1. Read README, CONTRIBUTING, LICENSE
2. Identify test/lint/build commands and their config file paths
3. Check repo signals (CI, tests, commits)
4. Generate 3-7 candidates

**Output:** ExecutionResult with:
```json
{
  "stage": "scout",
  "status": "success",
  "data": {
    "repo_profile": {
      "stack_hints": ["typescript", "react"],
      "ci_detected": ["github-actions"],
      "commands": {"test": "npm test", "lint": "npm run lint"},
      "config_paths": {"test": ["pytest.ini"], "lint": [".eslintrc.json"], "ci": [".github/workflows/ci.yml"]}
    },
    "candidates": [
      {
        "id": "cand-1",
        "title": "Add test for edge case",
        "change_type": "test",
        "risk": "low",
        "est_loc": 15
      }
    ],
    "repo_score": {"score_0_10": 8, "reasons": [...]}
  }
}
```

**Success Criteria:**
- 3-7 candidates found
- Repo score ≥ 5/10
- No hard blockers

**Next Step:**
- High score (8-10) → Critic or Gatekeeper
- Medium score (5-7) → Analyst for deeper analysis
- Low score (<5) → Stop or Analyst to find opportunities

### Stage 2: Analyst (Deep Analysis)

**Purpose:** Focused deep analysis producing 5 high-quality candidates.

**Inputs:**
- `{{REPO_ROOT}}` - Workspace path
- `{{FOCUS}}` - Analysis focus (docs/tests/bugfix/perf/refactor/ci/dx)

**Process:**
1. Understand focus area
2. Analyze codebase deeply
3. Identify opportunities
4. Assess quality (necessity, fit, scope, verifiability)
5. Rank by merge probability

**Output:** ExecutionResult with:
```json
{
  "stage": "analysis",
  "status": "success",
  "data": {
    "candidates": [
      {
        "id": "cand-1",
        "title": "Add missing docstring",
        "change_type": "docs",
        "risk": "low",
        "est_loc": 8,
        "targets": ["src/utils/parseURL.ts"],
        "details": "...",
        "verification": {"commands": [...]}
      }
    ],
    "merge_expectation": {
      "overall": "high",
      "rationale": [...]
    }
  }
}
```

**Success Criteria:**
- 3-5 candidates found
- Each has clear necessity
- Merge expectation ≥ medium

**Next Step:**
- Critic (quality gate) or Gatekeeper (if candidates are obvious wins)

### Stage 2 Alternative: Architect (Refactoring Focus)

**Purpose:** Find ONE small architectural improvement (<200 LOC).

**Inputs:**
- `{{REPO_ROOT}}` - Workspace path

**Process:**
1. Analyze codebase structure
2. Identify pain points (duplication, coupling, complexity)
3. Find one improvement
4. Sketch design
5. Plan verification

**Output:** ExecutionResult with:
```json
{
  "stage": "analysis",
  "status": "success",
  "data": {
    "candidate": {
      "id": "arch-1",
      "title": "Extract EMAIL_REGEX constant",
      "change_type": "refactor",
      "risk": "low",
      "est_loc": 25,
      "targets": [...],
      "rationale": "...",
      "design_sketch": "...",
      "verification": {...}
    }
  }
}
```

**Success Criteria:**
- One improvement found
- Scope <200 LOC
- Clear benefit (reduce duplication/coupling/complexity)

**Next Step:**
- Critic (recommended for refactors) or Gatekeeper

### Gate: Critic (Pre-Implementation Evaluation)

**Purpose:** Evaluate proposed changes BEFORE implementation to reduce rejection risk.

**Inputs:**
- `{{REPO_URL}}` - Repository URL
- `{{BASE_BRANCH}}` - Base branch
- `{{PROPOSED_CHANGES}}` - Proposed changes (from Scout/Analyst/Architect)
- `{{POLICY_BRIEF}}` - Policy brief (optional)
- `{{TIME_BUDGET}}`, `{{RISK_BUDGET}}` - Constraints (optional)

**Process:**
1. Evaluate against 7 criteria:
   - Necessity
   - Maintainer Fit
   - Scope Control
   - Risk
   - Testability
   - Reviewability
   - Opportunity Cost
2. Make decision: approve/revise/reject
3. Cut scope if needed
4. Provide detailed reasoning

**Output:** `ExecutionResult` with Critic details under `data.*`:
```json
{
  "schema_version": "1.0",
  "id": "critic-<timestamp>",
  "stage": "critic",
  "status": "success",
  "summary": "Critic decision: approve",
  "started_at": "<iso8601>",
  "finished_at": "<iso8601>",
  "exit_code": 0,
  "artifacts": [],
  "metrics": { "duration_ms": 0, "cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0 },
  "errors": [],
  "warnings": [],
  "data": {
    "decision": "approve",
    "top_reasons": [...],
    "must_fix_before_implement": [],
    "scope_cut": {
      "keep": [...],
      "drop": [...],
      "split_into_separate_prs": [...]
    },
    "acceptance_criteria": [...],
    "test_plan": [...],
    "reviewer_notes": "...",
    "merge_probability": {
      "estimate": 0.9,
      "drivers_positive": [...],
      "drivers_negative": [...]
    },
    "go_no_go_next_step": "approve → Implementer"
  }
}
```

**Decision Logic:**
- **approve**: Proceed to Gatekeeper
- **revise**: Return to Analyst with `must_fix_before_implement`
- **reject**: Stop, don't implement

**Success Criteria:**
- Decision: approve
- Merge probability ≥ 0.5
- No blocking issues

**Next Step:**
- approve → Gatekeeper
- revise → Analyst
- reject → Stop

### Stage 3: Gatekeeper (Selection & PRSpec Creation)

**Purpose:** Select best candidates and create minimal, mergeable PRSpecs.

**Inputs:**
- `{{REPO_ROOT}}` - Workspace path
- One candidate payload from the active analysis path: `{{SCOUT_JSON}}`, `{{ANALYST_JSON}}`, or `{{ARCHITECT_JSON}}`
- `{{MAX_PRS}}` - Maximum PRs to select (default: 1)

**Process:**
1. Evaluate each candidate
2. Make decision: pr/issue/skip
3. Create PRSpec for approved candidates
4. Ensure minimal scope

**Output:** ExecutionResult with:
```json
{
  "stage": "gatekeeper",
  "status": "success",
  "data": {
    "selected": [
      {
        "candidate_id": "cand-1",
        "decision": "pr",
        "reasons": [...],
        "blockers": []
      }
    ]
  },
  "pr_spec": {
    "schema_version": "1.0",
    "id": "prspec-...",
    "repo": {...},
    "base": {"branch": "main"},
    "head": {"branch": "test/validate-email"},
    "title": "Add test for validateEmail with empty string",
    "body_markdown": "...",
    "change_type": "test",
    "risk": "low",
    "files_touched": [...],
    "test_plan": [...],
    "ai_assistance": {...}
  }
}
```

**Decision Logic:**
- **pr**: Create PRSpec, proceed to Implementer
- **issue**: Recommend opening issue first (status: needs_human)
- **skip**: Reject candidate (too risky, not needed)

**Success Criteria:**
- At least 1 candidate approved
- PRSpec complete (all required fields)
- Decision: pr

**Next Step:**
- Implementer (with PRSpec)

### Stage 4: Implementer (Safe Implementation)

**Purpose:** Implement PRSpec safely with minimal diff.

**Inputs:**
- `{{REPO_ROOT}}` - Workspace path
- `{{HEAD_BRANCH}}` - Head branch (already checked out)
- `{{PRSPEC_JSON}}` - PRSpec from Gatekeeper
- `{{CONSTRAINTS}}` - Additional constraints (optional)
- `{{ALLOWED_COMMANDS}}` - Allowed commands (optional)

**Process:**
1. Verify clean worktree
2. Implement changes (follow PRSpec exactly)
3. Run verification (tests, lint, build)
4. If verification fails: Fix from stderr and retry (up to 3 attempts)
5. Summarize results

**Output:** ExecutionResult with:
```json
{
  "stage": "implement",
  "status": "success",
  "data": {
    "changed_files": [...],
    "commands_run": [...],
    "tests": {
      "ok": true,
      "commands": [...],
      "logs_path": "..."
    },
    "diff_stats": {
      "files": 1,
      "insertions": 12,
      "deletions": 0
    },
    "followups": [...]
  }
}
```

**Safety Rules:**
- Never create tool state files (`.claude/`, `.agentplane/`, etc.)
- Touch only necessary files
- No mass formatting
- Follow PRSpec exactly
- For untrusted repos, prefer isolated runtime (Docker/microVM)

**Success Criteria:**
- Status: success
- Tests pass (tests.ok: true)
- Diff matches PRSpec est_loc (±20%)
- No tool state files

**Next Step:**
- Reviewer (with implementation result)

### Stage 5: Reviewer (Post-Implementation Gate)

**Purpose:** Review git diff quality and scope discipline before PR message generation.

**Inputs:**
- `{{REPO_ROOT}}` - Workspace path
- `{{PRSPEC_JSON}}` - Approved PRSpec
- `{{IMPLEMENT_JSON}}` - Implementation result from Implementer
- `{{DIFF_SUMMARY}}` - Git diff summary (optional)

**Output:** ExecutionResult with:
```json
{
  "stage": "reviewer",
  "status": "success",
  "data": {
    "decision": "pass",
    "required_fixes": [],
    "scope_check": {
      "unexpected_files": []
    }
  }
}
```

**Success Criteria:**
- No unexpected files outside the PRSpec `files_touched` list
- No obvious debug/noise leftovers

**Next Step:**
- PR Writer (with reviewer + implementer outputs)

### Stage 6: PR Writer (PR Message Creation)

**Purpose:** Write excellent, concise PR message from implementation results.

**Inputs:**
- `{{REPO_ROOT}}` - Workspace path
- `{{IMPLEMENT_JSON}}` - Implementation result from Implementer
- `{{DIFF_SUMMARY}}` - Git diff summary (optional)

**Process:**
1. Review implementation results
2. Generate git diff summary (if needed)
3. Draft PR title (clear, imperative, <120 chars)
4. Write PR body (What/Why/How tested/Notes)
5. Create complete PRSpec

**Output:** ExecutionResult with:
```json
{
  "stage": "pr_writer",
  "status": "success",
  "pr_spec": {
    "title": "Add test for validateEmail with empty string",
    "body_markdown": "## What\n...\n\n## Why\n...\n\n## How to verify\n```bash\n...\n```",
    "ai_assistance": {
      "used": true,
      "tools": [...],
      "disclosure_line": "Test generated with AI assistance (Claude Code PR Factory)"
    }
  }
}
```

**Quality Rules:**
- Be concise (no marketing, no AI story)
- Be accurate (don't claim what you can't verify)
- Be specific (exact commands, not "run tests")
- Be honest (if not tested, say "Recommended verification:")

**Success Criteria:**
- Title <120 chars, clear, imperative
- Body has What/Why/How tested
- Disclosure line present

**Next Step:**
- Publish PR (manual or via `pr-factory-publisher`)

### Stage 7: Publisher (Open PR)

**Purpose:** Publish the change as a PR (fork/push/open PR) **only when the user explicitly requests publishing**.

**Inputs:**
- `{{REPO_ROOT}}` - Local repository path
- `{{REPO_URL}}` - Upstream repository URL
- `{{BASE_BRANCH}}` - Base branch
- `{{HEAD_BRANCH}}` - Head branch (already committed)
- Final PRSpec JSON (title/body)

**Process:**
1. Verify clean worktree + correct branch
2. Run safety gate (forbidden tool state / secret-ish scan) if possible
3. Ensure `gh` is authenticated
4. Fork (if needed) and configure remote
5. Push head branch
6. Create PR using PRSpec title/body
7. Verify PR and capture URL

**Output:** `ExecutionResult` with:
```json
{
  "stage": "publish",
  "status": "success",
  "data": {
    "pr": { "url": "https://github.com/owner/repo/pull/123" }
  }
}
```

**Success Criteria:**
- PR URL is present (never claim a PR exists without it)

## Decision Points

### After Scout

| Condition | Next Step |
|-----------|-----------|
| Repo score 8-10 | Critic → Gatekeeper |
| Repo score 5-7 | Analyst (deeper analysis) |
| Repo score <5 | Stop or Analyst to find opportunities |
| No candidates | Stop or try Architect |

### After Analyst

| Condition | Next Step |
|-----------|-----------|
| 3-5 high-quality candidates | Critic (recommended) or Gatekeeper |
| <3 candidates | Try Architect or Stop |
| Merge expectation low | Revise focus or Stop |

### After Critic

| Decision | Next Step |
|----------|-----------|
| approve | Gatekeeper |
| revise | Analyst with must_fix_before_implement |
| reject | Stop |

### After Gatekeeper

| Decision | Next Step |
|----------|-----------|
| pr | Implementer |
| issue | needs_human (open issue first) |
| skip | Stop |

### After Implementer

| Status | Next Step |
|--------|-----------|
| success | Reviewer |
| failed | Fix errors or needs_human |
| needs_human | Manual intervention |

### After Reviewer

| Status | Next Step |
|--------|-----------|
| success | PR Writer |
| retryable | Implementer (fix required) |
| needs_human | Manual intervention |

## Data Flow

### Scout → Critic/Gatekeeper

```json
{
  "candidates": [
    {
      "id": "cand-1",
      "title": "...",
      "change_type": "test",
      "risk": "low",
      "est_loc": 15,
      "likely_paths": [...],
      "rationale": "...",
      "test_plan": [...]
    }
  ]
}
```

### Analyst → Critic/Gatekeeper

```json
{
  "candidates": [
    {
      "id": "cand-1",
      "title": "...",
      "change_type": "docs",
      "risk": "low",
      "est_loc": 8,
      "targets": [...],
      "details": "...",
      "verification": {"commands": [...]}
    }
  ]
}
```

### Critic → Gatekeeper

```json
{
  "decision": "approve",
  "scope_cut": {
    "keep": ["Add null check"],
    "drop": [],
    "split_into_separate_prs": []
  },
  "acceptance_criteria": [...],
  "test_plan": [...]
}
```

### Gatekeeper → Implementer

```json
{
  "pr_spec": {
    "schema_version": "1.0",
    "id": "prspec-...",
    "repo": {...},
    "base": {"branch": "main"},
    "head": {"branch": "..."},
    "title": "...",
    "body_markdown": "...",
    "change_type": "test",
    "risk": "low",
    "files_touched": [...],
    "test_plan": [...],
    "ai_assistance": {...}
  }
}
```

### Implementer → Reviewer

```json
{
  "data": {
    "changed_files": [...],
    "commands_run": [...],
    "tests": {"ok": true, "commands": [...]},
    "diff_stats": {"files": 1, "insertions": 12, "deletions": 0}
  }
}
```

## Quality Gates

### Gate 1: Scout → Next Stage

**Criteria:**
- ✅ At least 3 candidates
- ✅ Repo score ≥ 5/10
- ✅ No blockers (archived, no license, etc.)

**If fails:**
- Try Analyst with different focus
- Try Architect for refactor opportunities
- Stop (repo not suitable)

### Gate 2: Analyst → Critic/Gatekeeper

**Criteria:**
- ✅ 3-5 candidates with clear necessity
- ✅ Each candidate <100 LOC
- ✅ Merge expectation ≥ medium

**If fails:**
- Revise focus area
- Lower expectations
- Stop

### Gate 3: Critic → Gatekeeper

**Criteria:**
- ✅ Decision: approve
- ✅ Merge probability ≥ 0.5
- ✅ No must_fix_before_implement

**If fails:**
- revise: Return to Analyst
- reject: Stop

### Gate 4: Gatekeeper → Implementer

**Criteria:**
- ✅ At least 1 candidate with decision: pr
- ✅ PRSpec complete (all required fields)
- ✅ Test plan defined

**If fails:**
- All decisions: issue → needs_human
- All decisions: skip → Stop

### Gate 5: Implementer → Reviewer

**Criteria:**
- ✅ Status: success
- ✅ Tests pass (tests.ok: true)
- ✅ Diff stats match PRSpec (±20%)
- ✅ No tool state files

**If fails:**
- status: failed → Fix and retry
- status: needs_human → Manual intervention

### Gate 6: Reviewer → PR Writer

**Criteria:**
- ✅ Status: success
- ✅ No `required_fixes`
- ✅ No unexpected files outside PRSpec scope

**If fails:**
- status: retryable → Back to Implementer with `required_fixes`
- status: needs_human → Manual intervention

## Error Handling

### Scout Errors

| Error | Handling |
|-------|----------|
| Repo not found | Return status: skipped |
| No README | Continue (not critical) |
| No CI detected | Continue (lower score) |
| No test folder | Continue (lower score) |
| <3 candidates | Try Analyst or Architect |

### Analyst Errors

| Error | Handling |
|-------|----------|
| Focus area unclear | Default to "test" or "docs" |
| No opportunities | Return status: skipped |
| Code analysis fails | Return needs_human |

### Critic Errors

| Error | Handling |
|-------|----------|
| Invalid proposal format | Return needs_human |
| Uncertain evaluation | Default to "revise" (safe) |

### Gatekeeper Errors

| Error | Handling |
|-------|----------|
| No candidates | Return status: skipped |
| All candidates skip | Return status: skipped |
| PRSpec incomplete | Return needs_human |

### Implementer Errors

| Error | Handling |
|-------|----------|
| Dirty worktree | Abort, return failed |
| Tests fail | Try simple fix or return retryable |
| Lint fails | Auto-fix if possible or return retryable |
| Tool state detected | Abort, return failed |

### Reviewer Errors

| Error | Handling |
|-------|----------|
| Unexpected changed files | Return retryable with concrete cleanup list |
| Debug leftovers found | Return retryable with file-level findings |
| Scope conflict with product decision | Return needs_human |

### PR Writer Errors

| Error | Handling |
|-------|----------|
| No implementation result | Return needs_human |
| Diff summary missing | Generate from git diff |
| Title too long | Truncate and add "..." |

## Usage Scenarios

### Scenario 1: Quick Win (Fast Track)

**Goal:** Find and implement obvious improvement quickly.

**Flow:**
```
Scout → Gatekeeper → Implementer → Reviewer → PR Writer
```

**When to use:**
- High-quality repo (score 8-10)
- Obvious improvements available
- Low risk tolerance

**Example:**
- Scout finds: "Fix broken link in README"
- Gatekeeper approves (docs, low risk)
- Implementer fixes link (2 LOC)
- Reviewer confirms clean diff
- PR Writer creates concise PR
- Time: 5-10 minutes

### Scenario 2: Deep Analysis (Comprehensive)

**Goal:** Thoroughly analyze repo and find best opportunities.

**Flow:**
```
Scout → Analyst → Critic → Gatekeeper → Implementer → Reviewer → PR Writer
```

**When to use:**
- Medium-quality repo (score 5-7)
- Unclear what improvements are needed
- Want highest merge probability

**Example:**
- Scout finds: 5 candidates (mixed quality)
- Analyst focuses on "tests" (finds 3 high-quality)
- Critic approves top candidate
- Gatekeeper creates PRSpec
- Implementer adds test (15 LOC)
- Reviewer confirms scope discipline
- PR Writer creates excellent PR
- Time: 15-20 minutes

### Scenario 3: Refactoring Focus

**Goal:** Find and implement small architectural improvement.

**Flow:**
```
Architect → Critic → Gatekeeper → Implementer → Reviewer → PR Writer
```

**When to use:**
- Looking for refactor opportunities
- Code quality improvements
- Want to reduce duplication/coupling

**Example:**
- Architect finds: "Extract EMAIL_REGEX constant (duplicated 4x)"
- Critic approves (clear benefit, low risk)
- Gatekeeper creates PRSpec
- Implementer extracts constant (25 LOC)
- Reviewer confirms no extra refactor noise
- PR Writer creates PR
- Time: 10-15 minutes

### Scenario 4: Manual Review (Interactive)

**Goal:** Human reviews and approves each stage.

**Flow:**
```
Scout → [HUMAN] → Gatekeeper → [HUMAN] → Implementer → [HUMAN] → Reviewer → [HUMAN] → PR Writer
```

**When to use:**
- Learning the system
- High-stakes repositories
- Want full control

**Example:**
- Scout finds: 7 candidates
- Human selects: 2 best candidates
- Gatekeeper creates PRSpecs
- Human reviews PRSpecs, selects 1
- Implementer implements
- Reviewer runs, then human reviews findings
- PR Writer creates PR
- Human reviews and submits
- Time: 30-40 minutes (human review time)

### Scenario 5: Batch Processing

**Goal:** Process multiple repos in parallel.

**Flow:**
```
[Repo 1] Scout → Gatekeeper → Implementer → Reviewer → PR Writer
[Repo 2] Scout → Gatekeeper → Implementer → Reviewer → PR Writer
[Repo 3] Scout → Analyst → Critic → Gatekeeper → Implementer → Reviewer → PR Writer
```

**When to use:**
- Multiple repositories to analyze
- Automated PR campaign
- CI/CD integration

**Example:**
- Process 10 repos
- 7 complete successfully (1 PR each)
- 2 skip (low score)
- 1 needs_human (complex case)
- Time: 5-10 minutes per repo

## Best Practices

### 1. Always Use Critic for Refactors

Refactorings are subjective → always use Critic to validate necessity and scope.

```
Architect → Critic → Gatekeeper
```

### 2. Split Large Scopes

If Critic says "revise" with `split_into_separate_prs`, split and create multiple PRs:

```
Original: "Improve validation module" (200 LOC)
→ PR 1: "Add null check" (5 LOC)
→ PR 2: "Add tests" (15 LOC)
→ PR 3: "Update docs" (8 LOC)
```

### 3. Verify Commands Locally

Before submitting PR, verify all commands in `test_plan` work:

```bash
npm test -- validation.test.ts  # Should pass
npm run coverage                 # Should show increase
```

### 4. Review Diff Before Submit

Always review diff to catch:
- Tool state files (`.claude/`, `.agentplane/`)
- Mass formatting
- Unintended changes

### 5. Start with Low Risk

For first PRs to a repo:
- Choose test-only or docs-only changes
- Avoid production code changes
- Build trust before larger changes

## Summary

The PR Factory workflow is designed to:
1. **Discover** opportunities (Scout/Analyst/Architect)
2. **Validate** quality (Critic)
3. **Select** best candidate (Gatekeeper)
4. **Implement** safely (Implementer)
5. **Review diff quality** (Reviewer)
6. **Communicate** clearly (PR Writer)

Each stage has clear inputs, outputs, and success criteria. Quality gates ensure only high-probability PRs proceed. Error handling ensures graceful failures.

For more details on each skill, see their individual SKILL.md files and references/ directories.
