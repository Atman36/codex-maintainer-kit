# Second Pass Progress

## Done

- Fixed all scanned `metadata.json` `*_JSON` inputs to use `type: "string"`.
- Replaced scanned legacy alias placeholders with canonical names.
- Added `requirements.txt` with `jsonschema>=4.0`.
- Fixed the duplicate `How tested` condition in `tools/quality_gate.py`.
- Added regression coverage for lowercase `how tested`.
- Added a repository smoke test that expects zero contract issues.
- Updated CI and `tools/README.md` to remove stale `pyyaml`, switch examples to `python3`, and document the current Critic `ExecutionResult` format.

## Remaining

- Replace hardcoded `analysis_report/` absolute paths with a portable placeholder (`REPORT_PATH` or `ARTIFACT_DIR`).
- Optional packaging follow-up: `pyproject.toml` / editable install support.
- Optional feature follow-ups: run ID lineage and pipeline mode config extraction.

## GitHub Actions

- Checked failed push run `22938078456` on branch `codex/publisher-stage-and-user-prompts`.
- Failure was in `Validate skills and contracts` and matched the audit findings: alias warnings plus 8 metadata type errors.
- Local state after fixes:
  - `python3 tools/validate_skills.py` passes
  - full `tools/tests` passes in a fresh venv after `pip install -r requirements.txt`
