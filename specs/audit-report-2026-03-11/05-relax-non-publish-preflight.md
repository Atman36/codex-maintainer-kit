# Spec 05: Relax non-publish preflight for local-only analysis runs

Источник:
- [Audit Report.md](../../Audit%20Report.md)
- Section: `Top issues -> 4`
- Section: `Best 7 -> 5`
- Section: `Ready-to-Implement PR Specs -> PRSpec 5`

## Why This Spec Exists

The audit found that `run_preflight()` requires `origin` and `origin/<base>` even when the pipeline is being used only for local analysis and no publish step is requested. That blocks legitimate local-only use cases:
- offline analysis
- scratch repos
- local clones without remotes
- quick triage before deciding whether to publish

The audit explicitly calls this a poor default for a harness.

## Goal

Allow local-base fallback for non-publish runs while keeping publish-mode checks strict.

## Scope

Touch only:
- `tools/run_pipeline.py`
- `tools/tests/test_run_pipeline.py`
- `tools/README.md`

Do not loosen publish guardrails. This spec is about analysis ergonomics only.

## Problem Statement

Current behavior forces infrastructure requirements that are only needed for publishing. That makes local analysis harder than it should be and encourages fake setup just to get past preflight.

## Smallest Safe Change

When `publish_requested=False`:
- allow missing `origin`
- prefer a local `base_branch` if it exists
- fall back to `HEAD` with a warning if needed

When `publish_requested=True`:
- keep strict remote and auth checks unchanged

## Acceptance Criteria

- A local git repo without `origin` can pass non-publish preflight.
- Publish mode still fails if remotes or auth requirements are missing.
- The runner emits a clear warning when it uses a local fallback instead of a remote base.

## Tests To Add Or Update

- local repo without `origin` passes non-publish preflight
- publish mode still fails without `gh` or remotes
- warning emitted when local fallback is used

## Verification

Run exactly:

```bash
python3 -m unittest tools/tests/test_run_pipeline.py
```

Manual check:

```bash
python3 tools/run_pipeline.py --repo /path/to/local/repo --mode analysis-only
```

Use a repo without `origin` and verify it no longer fails preflight.

## Reviewer Concerns To Preempt

- Publish safety must remain strict
- Fallback precedence: local branch vs `HEAD`
- Whether this should be implicit or behind an explicit flag

## Out Of Scope

- Analysis-only mode itself
- Publish dry-run
- Placeholder registry
- Artifact-path cleanup

## Suggested Commit Message

```text
fix(preflight): allow local-base fallback for non-publish analysis runs
```
