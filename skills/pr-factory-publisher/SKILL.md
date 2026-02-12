---
name: pr-factory-publisher
description: |
  Publish an already-implemented PRSpec: create a fork (if needed), push the branch, and open a PR.

  Use when:
  - Implementation is complete and committed on a head branch
  - User explicitly asked to create a PR / fork / push
  - Need deterministic, verifiable publish steps (no “claimed” PRs without URLs)

  Outputs structured JSON (ExecutionResult) with PR URL and publishing metadata.
license: MIT
---

# Role: Publisher

Publish an implemented change as a GitHub pull request.

## Inputs

- `{{REPO_ROOT}}` - Local repository path
- `{{REPO_URL}}` - Upstream repository URL (preferred)
- `{{BASE_BRANCH}}` - Base branch (default: `main`)
- `{{HEAD_BRANCH}}` - Head branch (must exist locally and be checked out)
- `{{PRSPEC_JSON}}` - Final PRSpec JSON (from PR Writer or Pipeline)

## Preconditions

- Work is already implemented and committed (Publisher should not edit code).
- User explicitly requested publishing (fork/push/PR). If not requested, return `status="skipped"`.

## Process

1. **Verify git state**
   - `git status --porcelain` is empty (or only expected files)
   - Current branch is `{{HEAD_BRANCH}}`
   - Branch has commits ahead of base

2. **Run safety gate (recommended)**
   - Scan for forbidden tool-state files and secret-ish strings before pushing.
   - If PR Factory kit tools are available, run (from the kit repo root):
     - `python tools/quality_gate.py --repo {{REPO_ROOT}} --base-ref origin/{{BASE_BRANCH}}`
   - If the repo has no `origin/{{BASE_BRANCH}}`, run against `HEAD` or skip and record a warning.

3. **Check GitHub CLI readiness**
   - `gh auth status` (must be logged in)
   - Avoid depending on external `jq` binary; prefer `gh` built-ins (`--json`, `--jq`, `--template`).

4. **Fork (if needed) + configure remote**
   - `gh repo fork {{REPO_URL}} --clone=false` (idempotent for existing forks)
   - Ensure a git remote exists (e.g. `fork`) pointing to your fork.

5. **Push**
   - `git push -u <fork-remote> {{HEAD_BRANCH}}`

6. **Create PR**
   - Use PRSpec `title` and `body_markdown`.
   - Only claim success if you have the PR URL.
   - Verify via `gh pr view` and capture URL/number.

## Output Format

Return JSON conforming to `../../schemas/execution_result.schema.json`:

```json
{
  "schema_version": "1.0",
  "id": "publish-<timestamp>",
  "stage": "publish",
  "status": "success",
  "summary": "Opened PR for <owner>/<repo> from <forkOwner>:<headBranch>",
  "started_at": "2026-02-12T16:12:00Z",
  "finished_at": "2026-02-12T16:14:00Z",
  "exit_code": 0,
  "stdout": "",
  "stderr": "",
  "artifacts": [],
  "metrics": {
    "duration_ms": 120000,
    "cost_usd": 0.0,
    "tokens_in": 0,
    "tokens_out": 0
  },
  "errors": [],
  "warnings": [],
  "data": {
    "fork": {
      "url": "https://github.com/<you>/<repo>",
      "owner": "<you>",
      "remote_name": "fork"
    },
    "push": {
      "remote": "fork",
      "branch": "<headBranch>"
    },
    "pr": {
      "url": "https://github.com/<upstreamOwner>/<repo>/pull/123",
      "base": "main",
      "head": "<you>:<headBranch>"
    },
    "commands_run": [
      "gh auth status",
      "gh repo fork ... --clone=false",
      "git push -u fork <headBranch>",
      "gh pr create ...",
      "gh pr view ... --json url,number"
    ],
    "notes": []
  }
}
```

## Quality Standards

- Never publish unless explicitly requested by the user.
- Never claim a PR exists without an actual PR URL.
- Keep the publishing steps minimal and reproducible.
