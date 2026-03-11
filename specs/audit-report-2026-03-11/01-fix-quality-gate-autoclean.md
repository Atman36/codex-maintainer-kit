# Spec 01: Fix `quality_gate.py` autoclean crash and add regression tests

Источник:
- [Audit Report.md](/Users/Apple/Developer/pr-factory-kit/Audit%20Report.md)
- Section: `Best 7 -> 1`
- Section: `Ready-to-Implement PR Specs -> PRSpec 1`

## Why This Spec Exists

`tools/quality_gate.py` currently crashes on the safety path `--autoclean-unplanned` with `NameError: name 'run' is not defined`. The audit explicitly notes that this is a reproduced runtime bug, not a hypothetical issue. A safety tool that crashes while cleaning unplanned paths undermines publish safety and makes later automation less trustworthy.

## Goal

Repair the autoclean code path in `tools/quality_gate.py` and add focused regression coverage for both tracked and untracked unplanned files.

## Scope

Touch only:
- `tools/quality_gate.py`
- `tools/tests/test_quality_gate.py` (new)

Stay within a small bugfix diff. Do not expand into secret-scanning improvements or unrelated quality-gate refactors.

## Problem Statement

Current behavior:
- `python3 tools/quality_gate.py --repo <tmprepo> --prspec <tmpprspec> --enforce-files-touched --autoclean-unplanned --json`
- crashes because `cleanup_unplanned_paths()` calls `run(...)`, but `run` is neither imported nor defined.

Expected behavior:
- unplanned untracked files are removed cleanly;
- unplanned tracked files are restored cleanly;
- without autoclean, the tool still reports unplanned paths instead of mutating repo state.

## Smallest Safe Change

- Replace the invalid `run(...)` usage with a local helper built on `subprocess.run(...)` or equivalent existing subprocess wrapper.
- Preserve current semantics for tracked vs untracked cleanup.
- Add regression tests for the failing path and the non-autoclean reporting path.

## Acceptance Criteria

- `--autoclean-unplanned` no longer crashes.
- Cleanup behavior works for both tracked and untracked files outside `PRSpec.files_touched`.
- Existing reporting mode without autoclean still flags unplanned files.
- No contract, CLI, or schema changes are introduced.

## Tests To Add Or Update

- `test_autoclean_untracked_unplanned_file`
- `test_autoclean_tracked_unplanned_file`
- `test_enforce_files_touched_without_autoclean_still_reports_unplanned`

## Verification

Run exactly:

```bash
python3 -m unittest tools/tests/test_quality_gate.py
python3 tools/quality_gate.py --repo /tmp/qg-repro --prspec /tmp/prspec.json --enforce-files-touched --autoclean-unplanned --json
```

## Reviewer Concerns To Preempt

- Autoclean semantics must not change unexpectedly.
- Cleanup must not damage staged state outside the documented behavior.
- Tests should prove both tracked and untracked handling.

## Out Of Scope

- Secret scanning improvements
- Entropy heuristics
- Publish dry-run
- Any broader quality-gate redesign

## Suggested Commit Message

```text
fix(quality-gate): repair autoclean path and add regression tests
```
