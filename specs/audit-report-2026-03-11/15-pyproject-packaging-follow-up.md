# Spec 15: Add `pyproject.toml` for editable-install packaging

Источник:
- `deepresearch/external-audits/audit-2026-03-11-second-pass.md`
- `AUDIT_SECOND_PASS_PROGRESS_2026-03-11.md`

## Why This Spec Exists

`requirements.txt` already solves the immediate local DX problem, but packaging is still incomplete. There is no `pyproject.toml`, so contributors cannot use a normal editable install workflow such as `pip install -e .`.

The second-pass audit calls this out as a follow-up, not an urgent blocker.

## Goal

Add minimal packaging metadata so the toolkit can be installed in editable mode for local development.

## Scope

Touch only:
- new `pyproject.toml`
- optional small README/setup note if needed

Do not reorganize the repo into a packaged library in this spec.

## Smallest Safe Change

- Add a minimal `pyproject.toml` with modern build metadata.
- Declare the package requirements needed for local tool usage.
- Keep `requirements.txt` if it is still useful for CI/bootstrap; do not force a migration in the same change.

## Acceptance Criteria

- `pip install -e .` works from repo root.
- Existing `python3 tools/...` entrypoints keep working unchanged.
- Packaging metadata is small and does not introduce runtime coupling that the repo does not need.

## Verification

Run exactly:

```bash
python3 -m pip install -e .
python3 tools/validate_skills.py
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

## Reviewer Concerns To Preempt

- Whether packaging is necessary for a harness repo: this is a DX improvement, not a mandatory runtime dependency.
- Whether `requirements.txt` should be removed: no, not in this slice.

## Out Of Scope

- Publishing to PyPI
- Major repo layout changes
- CLI entrypoint wrappers

## Suggested Commit Message

```text
build: add minimal pyproject metadata for editable installs
```
