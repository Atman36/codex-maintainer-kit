# Tools

## `quality_gate.py`

Pre-publish safety gate for PR Factory runs.

### What it does
1) Lists changed/untracked files.
2) Flags forbidden tool-state paths (agent directories, local env files, etc.).
3) Runs a conservative regex scan for secret-like tokens in changed text files.
4) Computes a local-only merge probability heuristic.
5) Optionally enforces `pr_spec.files_touched` and can auto-clean out-of-scope changes.

### Usage

```bash
python tools/quality_gate.py --repo /path/to/repo --base-ref origin/main
python tools/quality_gate.py --repo /path/to/repo --base-ref origin/main --prspec prspec.json --json
python tools/quality_gate.py --repo /path/to/repo --prspec prspec.json --enforce-files-touched
python tools/quality_gate.py --repo /path/to/repo --prspec prspec.json --enforce-files-touched --autoclean-unplanned
```

Exit codes:
- `0` => gate passed
- `2` => failed gate (forbidden paths / potential secrets / unplanned files)

### Tuning
- Override forbidden globs:
  `--forbidden ".agentplane/**" ".opencode/**" ...`
- Adjust regexes and patterns inside `quality_gate.py` as needed.

## `run_pipeline.py`

Deterministic orchestrator for staged PR Factory execution.

### What it does
1) Enforces strict stage order by mode (`full`, `quick-win`, `architecture`).
2) Executes stage commands passed from CLI.
3) Applies quality gates (`critic=approve`, `gatekeeper=pr`, `implement/reviewer/pr_writer=success`).
4) Adds self-healing loop for Implementer (default: up to 3 attempts).

### Usage

```bash
python tools/run_pipeline.py \
  --repo-root /path/to/repo \
  --mode full \
  --stage-command scout='cat /tmp/scout.json' \
  --stage-command analyst='cat /tmp/analyst.json' \
  --stage-command critic='cat /tmp/critic.json' \
  --stage-command gatekeeper='cat /tmp/gatekeeper.json' \
  --stage-command implement='cat /tmp/implement.json' \
  --stage-command reviewer='cat /tmp/reviewer.json' \
  --stage-command pr_writer='cat /tmp/pr_writer.json'
```

Placeholders supported in each stage command:
- `{{REPO_ROOT}}`, `{{REPO_URL}}`, `{{BASE_BRANCH}}`, `{{FOCUS}}`, `{{MODE}}`, `{{MAX_PRS}}`, `{{CONTEXT_PATH}}`
- `{{SCOUT_JSON}}`, `{{ANALYST_JSON}}`, `{{CRITIC_JSON}}`, `{{GATEKEEPER_JSON}}`, `{{IMPLEMENT_JSON}}`, `{{REVIEWER_JSON}}`
