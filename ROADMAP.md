# Maintainer Automation Roadmap

PR Factory Kit focuses on small, reviewable OSS maintenance tasks with human approval gates.

## Current foundation

- Ordered analysis and implementation stages with machine-readable contracts.
- Forbidden-file scanning, likely-secret detection, PRSpec scope enforcement, and optional cleanup.
- Repo-local Codex maintainer skill under `.agents/skills/pr-factory-maintainer/`.
- Audit artifacts and deterministic pipeline orchestration.

## Next milestones

### PR review analysis

Add a read-only maintainer workflow for diff summaries, risk maps, touched areas, and test gaps.

### Issue triage

Add an advisory workflow that classifies issues, checks reproduction details, and drafts suggested labels and responses for human review.

### Release readiness

Add changelog drafting, migration-note checks, and breaking-change review before release approval.

### Security-aware review

Extend local checks for auth changes, command execution, path handling, dependency risk, and likely credentials.

### GitHub integration

Add an advisory pull-request review workflow using the official `openai/codex-action` pattern. Keep Codex analysis in a least-privilege job and separate any write permissions from API-key access.

## Evidence before application

- Run one self-improvement dogfooding case with a real PRSpec, diff, and verification record.
- Run one external OSS analysis with a real repository URL and reviewable artifact.
- Record only factual adoption and maintenance evidence. Do not create synthetic issues or placeholder metrics.
