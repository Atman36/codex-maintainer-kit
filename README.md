# Codex Maintainer Kit

Maintainer automation toolkit for safe, reviewable, human-gated pull requests. Repo-local Codex skills, deterministic quality gates, and audit artifacts help open-source maintainers prepare small improvements without bypassing human approval.

The default pipeline is:
Scout → Analyst → Critic → Gatekeeper → Implementer → Reviewer → PR Writer → Publisher.

## Factual status

- **Release status:** first public release is `v0.1.0`.
- **Maintainer status:** this repository is maintained by its primary maintainer and is structured around human-approved OSS maintenance workflows.
- **Adoption status:** early-stage public project; current evidence is dogfooding, documented case studies, and a roadmap for maintainer review, issue triage, release readiness, and security-aware checks.
- **Ecosystem relevance:** intended to reduce review load for small-to-medium open-source projects by turning Codex-assisted analysis into scoped, auditable, maintainer-approved changes.
- **Codex for Open Source fit:** the project maps directly to maintainer workflows covered by the program: pull request review, issue triage, release workflows, maintainer automation, and security-aware review support.

## Quick start

```bash
git clone https://github.com/Atman36/codex-maintainer-kit.git
cd codex-maintainer-kit
python3 -m pip install -e .
```

Start with `CODEX.md` for Codex CLI usage or hand `program.md` to an agent as the shortest repository entrypoint.

## Safety-first design

- **Human-gated publishing:** Publisher runs only after an explicit maintainer request.
- **Quality gates:** forbidden-file scanning, secret detection, `files_touched` enforcement, and a conservative merge-probability heuristic live in `tools/quality_gate.py`.
- **Scoped cleanup:** `--autoclean-unplanned` can restore files outside an approved PRSpec.
- **Audit artifacts:** pipeline runs keep machine-readable summaries under `analysis_report/`.

## Codex entrypoint

Start with `CODEX.md` for Codex CLI usage and `.agents/skills/pr-factory-maintainer/SKILL.md` for the repo-local maintainer workflow.

## Fastest agent entrypoint

If you want a single file to hand to an agent, start with `program.md`.
It plays the same role as a compact "operating program": what to read first, which workflow to prefer, and which constraints are non-negotiable.

## What’s inside

- `program.md` — shortest agent-facing entrypoint for the whole repo.
- `prompts/` — compact role prompts (stack-agnostic).
- `schemas/` — strict JSON Schemas:
  - `PRSpec` — what we intend to ship as a PR.
  - `ExecutionResult` — uniform result envelope for *any* CLI/agent run.
- `tools/quality_gate.py` — forbidden-files scanner + merge-probability heuristic + files_touched enforcement.
- `tools/run_pipeline.py` — deterministic DAG orchestrator (stage order + gate checks + implement retries).
- `tools/fetch_pr_comments.py` — fetch PR comments (issue + review) from GitHub for analysis.
- `tools/README.md` — how to run the gate locally / in CI.
- `SAFETY.md` — human approval boundaries and quality-gate details.
- `ROADMAP.md` — planned maintainer workflows and evidence milestones.

## Placeholders

Prompts use placeholders like:
- `{{REPO_ROOT}}`, `{{REPO_URL}}`, `{{BASE_BRANCH}}`, `{{HEAD_BRANCH}}`
- `{{CONSTRAINTS}}` (plain bullet list)
- `{{ALLOWED_COMMANDS}}` (plain bullet list)
- `{{CONTEXT_PATH}}` (optional external context path)
- `{{ARTIFACT_DIR}}` (default: repo-local `analysis_report/`)
- `{{REPORT_PATH}}` (default: repo-local `analysis_report/runs/<run_id>/report.md`)
- `{{RUNNER}}` (selected execution backend, for example `cli` or `task`)

## Output rule (important)

All role prompts request **JSON only**, conforming to `schemas/execution_result.schema.json`.
Role-specific details go into `ExecutionResult.data`.

## Local setup

For editable installs during local development:

```bash
python3 -m pip install -e .
```

`requirements.txt` remains available for lightweight bootstrap and CI-style installs.

## Usage note

- Hand `program.md` to a chat agent when you want the shortest possible entrypoint.
- Use `prompts/pipeline.md` when you need the end-to-end workflow contract directly.
- Use `tools/README.md` for the fully expanded `run_pipeline.py` CLI examples.

## License

MIT. See `LICENSE`.

## Adoption & Ecosystem

- **Maintainer workflow focus:** Codex Maintainer Kit is designed for maintainers who review and merge contributions.
- **Dogfooding:** The toolkit is actively used to improve its own codebase (see `case-studies/`).
- **Ecosystem importance:** Helps reduce maintainer burden on small-to-medium OSS projects by automating triage, review, and test-gap detection.
- **Projects analyzed:** See `case-studies/` for real-world usage examples.
