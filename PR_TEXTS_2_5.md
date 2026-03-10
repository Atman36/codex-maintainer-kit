# Prepared PR Drafts 2-5 (2026-03-11)

Source context:
- `/Users/Apple/Developer/pr-factory-kit/СС-PR.md`
- `/Users/Apple/Developer/pr-factory-kit/Log Pro.md`

Notes:
- PR 1 is already prepared separately and is not repeated here.
- PRs 2-5 are implemented locally and committed in their own worktree branches.
- Local verification was performed before commit, but no test files were added to the PR branches.

## PR 2: Respect days_back in backfill

- `repo:` `/Users/Apple/Developer/claude-code`
- `base:` `origin/main` at `f6dbf44`
- `worktree:` `/Users/Apple/Developer/claude-code-pr2`
- `branch:` `fix/backfill-days-back`
- `commit:` `57c2a591a0c398355c55a6b3a609d99f1763fd80`
- `status:` implemented locally, verified, not published
- `files:` `scripts/backfill-duplicate-comments.ts`
- `local verification:`
  - inline Node assertions for `parseBackfillConfig`, `isBackfillCandidate`, `shouldFetchNextPage`, and `collectCandidateIssues`

**PR title**

Respect days_back in backfill

**PR body**

````md
## What
Make `scripts/backfill-duplicate-comments.ts` honor `DAYS_BACK` by filtering issues on `created_at` instead of issue-number ranges.

Derive the repository from GitHub environment variables, skip pull requests and locked issues, stop pagination once the time window is exhausted, and only sleep between dispatches when `DRY_RUN=false`.

## Why
The workflow already exposes a `days_back` input, but the script ignored it and scanned a hardcoded repository by issue number.

That drift made the workflow harder to trust, did more work than necessary, and could try to backfill the wrong repository context.

## How to verify
```bash
GITHUB_TOKEN=... GITHUB_REPOSITORY=anthropics/claude-code DAYS_BACK=90 DRY_RUN=true bun run scripts/backfill-duplicate-comments.ts
```

## Notes
The request helper now tolerates empty `204 No Content` workflow-dispatch responses so live dispatches do not fail after a successful API call.
````

## PR 3: Validate plugin catalog in CI

- `repo:` `/Users/Apple/Developer/claude-code`
- `base:` `origin/main` at `f6dbf44`
- `worktree:` `/Users/Apple/Developer/claude-code-pr3`
- `branch:` `fix/validate-plugin-catalog`
- `commit:` `d0b59060581bc559e5f39733f56485fb2e9363ba`
- `status:` implemented locally, verified, not published
- `files:` `.github/workflows/validate-plugin-catalog.yml`, `scripts/validate-plugin-catalog.mjs`, `plugins/plugin-dev/.claude-plugin/plugin.json`, `plugins/security-guidance/README.md`
- `local verification:`
  - `node scripts/validate-plugin-catalog.mjs`

**PR title**

Validate plugin catalog in CI

**PR body**

````md
## What
Add a lightweight `scripts/validate-plugin-catalog.mjs` validator and a GitHub Actions workflow that runs it whenever marketplace metadata or bundled plugins change.

Normalize the current catalog by adding the missing `plugin-dev` manifest and the missing `security-guidance` README so the validator passes on the current tree.

## Why
The plugin catalog spans plugin directories, per-plugin manifests, `plugins/README.md`, and `.claude-plugin/marketplace.json`, but nothing in CI checked that those sources stayed aligned.

That made it easy for catalog drift to land silently and break plugin discoverability for both humans and agents.

## How to verify
```bash
node scripts/validate-plugin-catalog.mjs
```

## Notes
The validator currently checks for missing plugin READMEs, missing manifests, mismatched manifest names, mismatched marketplace sources, and set drift between plugin directories, `plugins/README.md`, and `marketplace.json`.
````

## PR 4: Upgrade dedupe to Sonnet 4.6

- `repo:` `/Users/Apple/Developer/claude-code`
- `base:` `origin/main` at `f6dbf44`
- `worktree:` `/Users/Apple/Developer/claude-code-pr4`
- `branch:` `fix/dedupe-sonnet46`
- `commit:` `e26c681fbb2206926985d1ea5ed3d11460242031`
- `status:` implemented locally, verified, not published
- `files:` `.github/workflows/claude-dedupe-issues.yml`
- `local verification:`
  - assert the workflow contains `claude-sonnet-4-6` and no longer contains `claude-sonnet-4-5-20250929`

**PR title**

Upgrade dedupe to Sonnet 4.6

**PR body**

````md
## What
Update the issue-dedupe workflow to run Claude Code with `claude-sonnet-4-6` instead of the older Sonnet 4.5 model string.

## Why
This workflow is instruction-heavy and benefits directly from the current Sonnet baseline for stronger reliability and prompt following.

Keeping the model string current also removes one more piece of avoidable drift from the repository.

## How to verify
```bash
rg 'claude-sonnet-4-6|claude-sonnet-4-5-20250929' .github/workflows/claude-dedupe-issues.yml
```

## Notes
Scope is intentionally limited to the workflow model selection.
````

## PR 5: Tighten dedupe guidance

- `repo:` `/Users/Apple/Developer/claude-code`
- `base:` `origin/main` at `f6dbf44`
- `worktree:` `/Users/Apple/Developer/claude-code-pr5`
- `branch:` `fix/dedupe-instructions`
- `commit:` `5f09fd6690180c023548734605474ad08c8fd292`
- `status:` implemented locally, verified, not published
- `files:` `.claude/commands/dedupe.md`
- `local verification:`
  - assert the command now contains the new precision rules and anti-improvisation guardrails

**PR title**

Tighten dedupe guidance

**PR body**

````md
## What
Strengthen `.claude/commands/dedupe.md` with higher-precision duplicate-detection guidance.

The updated command now requires a structured issue summary, explicit filtering on root-cause match, stronger rejection rules for platform/provider mismatches, and a hard stop when confidence is not high.

## Why
False-positive duplicate comments are more damaging than missed matches in this workflow.

Clearer guardrails improve consistency across agents and reduce the chance that title similarity or vague product overlap turns into a duplicate comment.

## How to verify
```bash
rg 'Precision matters more than recall here|Treat title similarity as a weak hint|Do not improvise alternate workflows|If confidence is below high' .claude/commands/dedupe.md
```

## Notes
The change only tightens instructions; it does not alter workflow permissions or add new tools.
````
