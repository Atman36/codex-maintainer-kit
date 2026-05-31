# Codex for OSS — Application Draft

## Project description

Codex Maintainer Kit is an open-source maintainer automation toolkit that helps OSS maintainers produce small, reviewable, policy-checked improvements using the Codex CLI. It provides repo-local skills, deterministic quality gates, and machine-readable audit artifacts — all with explicit human approval before any publication.

## How Codex credits will be used

Codex credits power maintainer automation: PR diff analysis, test-gap detection, issue triage, changelog drafting, and security-focused review. All outputs remain advisory; human maintainers approve every label, comment, and merge.

*(Character count: 298)*

## Evidence of maintenance activity

- `ROADMAP.md` — four maintainer workflows planned (PR review analysis, issue triage, release readiness, security-aware review) and three 3–6-month milestones.
- `case-studies/001-self-improvement.md` — dogfooding analysis of `tools/quality_gate.py` with real PRSpec and diff.
- `case-studies/002-external-repo.md` — analysis of `pallets/click` with a concrete, reviewable improvement.
- `SAFETY.md` — documents enforced quality gates (forbidden-file scanner, secret detection, `files_touched` enforcement, merge-probability heuristic, autoclean).

## Human-in-the-loop model

Codex Maintainer Kit never publishes without an explicit maintainer request. See `SAFETY.md`:

> The `pr-factory-publisher` stage is optional and runs only after an explicit maintainer request. Analysis, implementation, review, and PR drafting do not imply permission to fork, push, or open a pull request.

All automated outputs are advisory. Write permissions are granted only for an approved implementation stage, and the Publisher stage is gated by an explicit human opt-in.
