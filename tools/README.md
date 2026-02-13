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

## `run_pipeline.py`

Deterministic orchestrator for staged PR Factory execution.

### What it does

1. Enforces strict stage order by mode (`full`, `quick-win`, `architecture`)
2. Executes stage commands passed from CLI or config
3. Applies quality gates at each stage:
   - `critic` → must be `approve`
   - `gatekeeper` → must be `pr`
   - `implementer`, `reviewer`, `pr_writer` → must be `success`
4. Self-healing loop for Implementer (default: up to 3 attempts)
5. Passes outputs between stages via JSON

### Pipeline Modes

| Mode | Stages Executed | Use Case |
|------|-----------------|----------|
| `full` | scout → analyst → critic → gatekeeper → implementer → reviewer → pr_writer | Complete analysis |
| `quick-win` | scout → gatekeeper → implementer → reviewer → pr_writer | Obvious improvements |
| `architecture` | architect → critic → gatekeeper → implementer → reviewer → pr_writer | Refactoring focus |

### Usage Examples

#### Full Pipeline

```bash
python tools/run_pipeline.py \
  --repo-root /path/to/repo \
  --repo-url https://github.com/owner/repo \
  --mode full \
  --focus tests \
  --max-prs 1 \
  --stage-command scout='python -m skills.pr_factory_scout' \
  --stage-command analyst='python -m skills.pr_factory_analyst' \
  --stage-command critic='python -m skills.pr_factory_critic' \
  --stage-command gatekeeper='python -m skills.pr_factory_gatekeeper' \
  --stage-command implement='python -m skills.pr_factory_implementer' \
  --stage-command reviewer='python -m skills.pr_factory_reviewer' \
  --stage-command pr_writer='python -m skills.pr_factory_pr_writer'
```

#### Quick-Win Mode

```bash
python tools/run_pipeline.py \
  --repo-root /path/to/repo \
  --mode quick-win \
  --stage-command scout='python -m skills.pr_factory_scout' \
  --stage-command gatekeeper='python -m skills.pr_factory_gatekeeper' \
  --stage-command implement='python -m skills.pr_factory_implementer' \
  --stage-command reviewer='python -m skills.pr_factory_reviewer' \
  --stage-command pr_writer='python -m skills.pr_factory_pr_writer'
```

#### With External Context

```bash
python tools/run_pipeline.py \
  --repo-root /path/to/repo \
  --context-path /path/to/deepresearch \
  --mode full \
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
| `{{SCOUT_JSON}}` | Scout output | Previous stage |
| `{{ANALYST_JSON}}` | Analyst output | Previous stage |
| `{{CRITIC_JSON}}` | Critic output | Previous stage |
| `{{GATEKEEPER_JSON}}` | Gatekeeper output | Previous stage |
| `{{IMPLEMENT_JSON}}` | Implementer output | Previous stage |
| `{{REVIEWER_JSON}}` | Reviewer output | Previous stage |

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

### Configuration File

Instead of CLI arguments, you can use a config file:

```bash
python tools/run_pipeline.py --config pipeline.yaml
```

Example `pipeline.yaml`:

```yaml
repo_root: /path/to/repo
repo_url: https://github.com/owner/repo
mode: full
focus: tests
max_prs: 1
stages:
  scout:
    command: python -m skills.pr_factory_scout
    timeout: 300
  analyst:
    command: python -m skills.pr_factory_analyst
    timeout: 600
  critic:
    command: python -m skills.pr_factory_critic
    timeout: 300
  gatekeeper:
    command: python -m skills.pr_factory_gatekeeper
    timeout: 300
  implement:
    command: python -m skills.pr_factory_implementer
    timeout: 600
    max_retries: 3
  reviewer:
    command: python -m skills.pr_factory_reviewer
    timeout: 300
  pr_writer:
    command: python -m skills.pr_factory_pr_writer
    timeout: 300
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Pipeline completed successfully |
| `1` | Usage error |
| `2` | Stage execution failed |
| `3` | Quality gate rejected |
| `4` | Timeout |

---

## Development

### Running Tests

```bash
# Validate JSON schemas
python -m jsonschema schemas/execution_result.schema.json -i <(echo '{...}')
python -m jsonschema schemas/prspec.schema.json -i <(echo '{...}')

# Dry-run pipeline
python tools/run_pipeline.py --repo-root /path/to/repo --mode full --dry-run
```

### Debugging

Enable verbose output:

```bash
export PR_FACTORY_DEBUG=1
python tools/run_pipeline.py ...
```

Save intermediate outputs:

```bash
python tools/run_pipeline.py \
  --repo-root /path/to/repo \
  --mode full \
  --save-intermediates /tmp/pr-factory \
  ...
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
