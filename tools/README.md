# Tools

Helper scripts for PR Factory pipeline execution and validation.

## Requirements

```bash
# Python 3.8+
pip install jsonschema pyyaml

# For Publisher stage (optional)
# Install GitHub CLI: https://cli.github.com/
gh auth login
```

---

## `quality_gate.py`

Pre-publish safety gate for PR Factory runs.

### What it does

1. Lists changed/untracked files
2. Flags forbidden tool-state paths (agent directories, local env files, etc.)
3. Runs a conservative regex scan for secret-like tokens in changed text files
4. Computes a local-only merge probability heuristic
5. Optionally enforces `pr_spec.files_touched` and can auto-clean out-of-scope changes

### Usage

#### Basic Check

```bash
python tools/quality_gate.py --repo /path/to/repo --base-ref origin/main
```

#### Check with PRSpec validation

```bash
python tools/quality_gate.py \
  --repo /path/to/repo \
  --base-ref origin/main \
  --prspec prspec.json \
  --json
```

#### Strict enforcement (fail on unplanned files)

```bash
python tools/quality_gate.py \
  --repo /path/to/repo \
  --prspec prspec.json \
  --enforce-files-touched
```

#### Auto-clean unplanned changes

```bash
python tools/quality_gate.py \
  --repo /path/to/repo \
  --prspec prspec.json \
  --enforce-files-touched \
  --autoclean-unplanned
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Gate passed |
| `1` | Usage error (bad arguments) |
| `2` | Failed gate (forbidden paths / potential secrets / unplanned files) |

### Tuning

Override forbidden globs:

```bash
python tools/quality_gate.py \
  --repo /path/to/repo \
  --forbidden ".agentplane/**" ".opencode/**" ".claude/**" ".kimi/**"
```

### JSON Output Format

With `--json` flag, outputs structured result:

```json
{
  "passed": true,
  "findings": {
    "forbidden_paths": [],
    "secret_patterns": [],
    "unplanned_files": []
  },
  "merge_probability": {
    "score": 0.85,
    "factors": ["low risk", "minimal scope"]
  }
}
```

---

## `validate_skills.py`

Validates integrity of local skill packages in `skills/`.

### What it checks

1. `SKILL.md` exists for each skill
2. `SKILL.md` includes frontmatter with required keys (`name`, `description`)
3. `metadata.json` exists, is valid JSON, and includes `version`
4. PR Factory prompts, skills, and docs use only placeholders from [`tools/contract_registry.py`](./contract_registry.py)
5. Legacy placeholder aliases are reported explicitly as warnings
6. Metadata `*_JSON` inputs are declared as `type: "string"` because runtime passes file paths, not embedded objects

### Usage

```bash
python tools/validate_skills.py
```

Optional root override:

```bash
python tools/validate_skills.py --root /path/to/repo
```

Validation policy:

- Unknown placeholders fail validation.
- Legacy aliases such as `{{IMPLEMENT_RESULT_JSON}}` and `{{CANDIDATES_JSON}}` warn but do not fail by themselves.
- Metadata entries like `IMPLEMENT_RESULT_JSON` / `PRSPEC_JSON` / `SCOUT_JSON` fail if they claim `type: "object"`.

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Validation passed |
| `1` | Validation failed |

---

## `run_pipeline.py`

Deterministic orchestrator for staged PR Factory execution.

### What it does

1. Runs a mandatory `preflight` stage before any long-running pipeline work.
2. Supports runner adapters: `--runner auto|task|cli`.
3. Enforces strict stage order by mode (`full`, `quick-win`, `architecture`).
4. Executes analysis stages once, then runs implementation stages per PRSpec (multi-PR).
5. Applies quality gates at each stage:
   - `critic` → must be `approve`
   - `gatekeeper` → must be `pr`
   - `implement`, `reviewer`, `pr_writer`, `publish` → must be `success`
6. Self-healing loop for Implementer (default: up to 3 attempts).
7. Writes machine-readable `pipeline-summary.json` and embeds structured error blocks.
8. Supports legacy placeholder aliases and fails fast if any `{{PLACEHOLDER}}` remains unresolved after expansion.

### Pipeline Modes

| Mode | Analysis stages | Per-PR stages |
|------|-----------------|---------------|
| `full` | scout → analyst → critic → gatekeeper | implement → reviewer → pr_writer (+ publish if requested) |
| `quick-win` | scout → gatekeeper | implement → reviewer → pr_writer (+ publish if requested) |
| `architecture` | architect → critic → gatekeeper | implement → reviewer → pr_writer (+ publish if requested) |

### Usage Examples

#### Full Pipeline (`auto` runner)

```bash
python tools/run_pipeline.py \
  --repo-root /path/to/repo \
  --repo-url https://github.com/owner/repo \
  --mode full \
  --focus tests \
  --max-prs 2 \
  --runner auto \
  --stage-command scout='python tools/stages/scout.py --repo {{REPO_ROOT}}' \
  --stage-command analyst='python tools/stages/analyst.py --input {{SCOUT_JSON}}' \
  --stage-command critic='python tools/stages/critic.py --input {{ANALYST_JSON}}' \
  --stage-command gatekeeper='python tools/stages/gatekeeper.py --input {{ANALYST_JSON}} --max-prs {{MAX_PRS}}' \
  --stage-command implement='python tools/stages/implement.py --prspec {{PRSPEC_JSON}}' \
  --stage-command reviewer='python tools/stages/reviewer.py --prspec {{PRSPEC_JSON}} --impl {{IMPLEMENT_JSON}}' \
  --stage-command pr_writer='python tools/stages/pr_writer.py --prspec {{PRSPEC_JSON}} --impl {{IMPLEMENT_JSON}}' \
  --summary-output /tmp/pipeline-summary.json
```

#### Force CLI Runner

```bash
python tools/run_pipeline.py \
  --repo-root /path/to/repo \
  --mode quick-win \
  --runner cli \
  --stage-command scout='python tools/stages/scout.py --repo {{REPO_ROOT}}' \
  --stage-command gatekeeper='python tools/stages/gatekeeper.py --input {{SCOUT_JSON}} --max-prs {{MAX_PRS}}' \
  --stage-command implement='python tools/stages/implement.py --prspec {{PRSPEC_JSON}}' \
  --stage-command reviewer='python tools/stages/reviewer.py --prspec {{PRSPEC_JSON}} --impl {{IMPLEMENT_JSON}}' \
  --stage-command pr_writer='python tools/stages/pr_writer.py --prspec {{PRSPEC_JSON}}'
```

#### Task Runner Wrapper

```bash
python tools/run_pipeline.py \
  --repo-root /path/to/repo \
  --mode full \
  --runner task \
  --task-runner-cmd 'task run --stage {{STAGE}} --command {{COMMAND}}' \
  --stage-command scout='python tools/stages/scout.py --repo {{REPO_ROOT}}' \
  ...
```

### Placeholders

The following placeholders are supported in stage commands:

| Placeholder | Description | Populated By |
|-------------|-------------|--------------|
| `{{REPO_ROOT}}` | Repository root path | CLI argument |
| `{{REPO_URL}}` | Repository URL | CLI argument |
| `{{BASE_BRANCH}}` | Base branch | CLI argument (default: main) |
| `{{FOCUS}}` | Analysis focus | CLI argument |
| `{{MODE}}` | Pipeline mode | CLI argument |
| `{{MAX_PRS}}` | Max PRs to generate | CLI argument (default: 1) |
| `{{CONTEXT_PATH}}` | External context path | CLI argument |
| `{{PR_INDEX}}` | Current PRSpec index in multi-PR loop | Runtime |
| `{{PRSPEC_JSON}}` | Current PRSpec JSON path | Runtime |
| `{{HEAD_BRANCH}}` | Normalized head branch (`codex/<slug>`) | Runtime |
| `{{SCOUT_JSON}}` | Scout output | Previous stage |
| `{{ANALYST_JSON}}` | Analyst output | Previous stage |
| `{{CRITIC_JSON}}` | Critic output | Previous stage |
| `{{GATEKEEPER_JSON}}` | Gatekeeper output | Previous stage |
| `{{IMPLEMENT_JSON}}` | Implementer output | Previous stage |
| `{{REVIEWER_JSON}}` | Reviewer output | Previous stage |

Legacy aliases kept for backward compatibility:

| Alias | Resolves To |
|-------|-------------|
| `{{CANDIDATES_JSON}}` | First available of `{{ANALYST_JSON}}`, `{{ARCHITECT_JSON}}`, `{{SCOUT_JSON}}` |
| `{{IMPLEMENT_RESULT_JSON}}` | `{{IMPLEMENT_JSON}}` |

If a stage command still contains any unresolved `{{...}}` placeholder after expansion, the runner fails that stage before executing the shell command and surfaces a deterministic error.

### Stage Output Contract

Each stage must output valid JSON to stdout:

#### ExecutionResult (most stages)

```json
{
  "schema_version": "1.0",
  "id": "stage-<timestamp>",
  "stage": "scout|analyst|gatekeeper|implement|reviewer|pr_writer|publish",
  "status": "success|failed|retryable|needs_human|skipped",
  "summary": "Brief description",
  "started_at": "2026-02-13T12:00:00Z",
  "finished_at": "2026-02-13T12:05:00Z",
  "exit_code": 0,
  "artifacts": [],
  "metrics": {
    "duration_ms": 300000,
    "cost_usd": 0.1,
    "tokens_in": 10000,
    "tokens_out": 2000
  },
  "errors": [],
  "warnings": [],
  "data": {},
  "pr_spec": {}
}
```

#### Critic Decision (special format)

```json
{
  "decision": "approve|revise|reject",
  "top_reasons": ["..."],
  "must_fix_before_implement": [],
  "scope_cut": {
    "keep": [],
    "drop": [],
    "split_into_separate_prs": []
  },
  "merge_probability": {
    "estimate": 0.9,
    "drivers_positive": [],
    "drivers_negative": []
  }
}
```

### Key Flags

| Flag | Description |
|------|-------------|
| `--runner` | Execution backend: `auto`, `task`, `cli` |
| `--task-runner-cmd` | Wrapper for task adapter (`{{COMMAND}}`, `{{STAGE}}`) |
| `--allow-dirty` | Disable clean-worktree preflight enforcement |
| `--base-drift-policy` | Drift handling before publish: `needs_human`, `warn`, `ignore` |
| `--summary-output` | Path for machine-readable pipeline summary JSON |
| `--publish` | Enable publish stage in per-PR loop |

### Troubleshooting

| Symptom | Root cause | Fix |
|---------|------------|-----|
| `Detected skill names used as shell commands` | Skill ID passed as executable command in CLI mode | Use real command (`python ...`) or configure `--runner task` + `--task-runner-cmd` |
| `Missing stage command(s)` | Not all required stage commands were provided | Add each missing `--stage-command stage=command` |
| `Working tree is dirty` | Preflight clean-worktree policy | Commit/stash changes or rerun with `--allow-dirty` |
| `Missing origin/<base>` | Base branch SHA cannot be resolved | `git fetch origin <base>` and rerun |
| Publish fails at preflight auth | `gh auth status` failed | Run `gh auth login` |
| Publish blocked by base drift | Base changed during long run | Rebase/cherry-pick on latest `origin/<base>` and rerun publish |

### Exit Code

`0` on full success, `1` on any preflight/stage/gate failure (`needs_human` result).

---

## Development

### Running Tests

```bash
# Validate JSON schemas
python -m jsonschema schemas/execution_result.schema.json -i <(echo '{...}')
python -m jsonschema schemas/prspec.schema.json -i <(echo '{...}')
python -m jsonschema schemas/pipeline_summary.schema.json -i <(echo '{...}')
# Run pipeline integration tests
python -m unittest tools/tests/test_run_pipeline.py
```

---

## `fetch_pr_comments.py`

Fetch PR comments from GitHub for analysis and research.

### What it does

- Downloads **issue comments** (general PR discussion)
- Downloads **review comments** (line-specific code review)
- Supports both GitHub CLI (`gh`) and PyGithub
- Uses parallel per-PR requests (configurable worker pool) for faster fetch on larger repos
- Retries transient API/rate-limit errors with exponential backoff
- Exports to JSON or CSV format
- Supports filtering by author and date

### Requirements

```bash
# Option 1: GitHub CLI (preferred - faster with pagination)
gh auth login

# Option 2: PyGithub (Python library)
pip install PyGithub
export GITHUB_TOKEN=your_token_here
```

### Usage Examples

#### Fetch all comments (JSON)

```bash
python tools/fetch_pr_comments.py \
  owner/repo \
  --output pr_comments.json
```

#### Fetch only review comments (CSV for Excel)

```bash
python tools/fetch_pr_comments.py \
  owner/repo \
  --type review \
  --format csv \
  --output code_reviews.csv
```

#### Filter by authors

```bash
python tools/fetch_pr_comments.py \
  owner/repo \
  --authors "maintainer1,maintainer2" \
  --output maintainer_comments.json
```

#### Filter by date

```bash
python tools/fetch_pr_comments.py \
  owner/repo \
  --since 2024-01-01 \
  --output recent_comments.json
```

#### Speed up large repos with parallel workers

```bash
python tools/fetch_pr_comments.py \
  owner/repo \
  --max-prs 200 \
  --workers 16 \
  --output fast_comments.json
```

#### Strict mode (fail if any PR request fails)

```bash
python tools/fetch_pr_comments.py \
  owner/repo \
  --max-prs 100 \
  --strict-errors \
  --output strict_comments.json
```

#### Incremental sync with resume state

```bash
python tools/fetch_pr_comments.py \
  owner/repo \
  --state-file artifacts/pr_comments_state.json \
  --output incremental_comments.json
```

If `--since` is not provided, the script uses the timestamp from `--state-file`.

#### Use PyGithub (if gh CLI not available)

```bash
python tools/fetch_pr_comments.py \
  owner/repo \
  --prefer-pygithub \
  --token $GITHUB_TOKEN \
  --output comments.json
```

### Output Formats

**JSON** (recommended for further processing):
```json
{
  "meta": {
    "exported_at": "2026-02-13T...",
    "total_comments": 1250,
    "by_type": {
      "issue_comment": 800,
      "review_comment": 450
    }
  },
  "comments": [...]
}
```

**CSV** (for Excel/spreadsheet analysis):
```
pr_number,pr_title,comment_id,author,body,created_at,...
123,Fix bug,987654321,reviewer,"Looks good!",2024-01-15T10:30:00Z,...
```

### Comment Types

| Type | API Endpoint | Content |
|------|--------------|---------|
| `issue_comment` | `/issues/{number}/comments` | General PR discussion, questions, approvals |
| `review_comment` | `/pulls/{number}/comments` | Line-specific feedback on code changes |

### Rate Limits

- GitHub CLI: Uses your normal API quota (5000 req/hour for authenticated users)
- PyGithub: Same 5000 req/hour limit
- Use `--since` to reduce API load for incremental runs
- Use `--workers` carefully (higher values are faster but increase request burst rate)
- Use `--state-file` to resume from last successful sync automatically

---

## License

MIT - See LICENSE file in repository root.
