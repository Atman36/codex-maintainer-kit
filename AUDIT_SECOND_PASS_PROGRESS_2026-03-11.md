# Second Pass Progress

## Verified On Current Tree

Commands run from repo root on 2026-03-11:
- `python3 tools/validate_skills.py`
- `python3 -m unittest tools.tests.test_contracts`
- targeted source checks against `tools/run_pipeline.py`, `tools/contract_registry.py`, `README.md`

Confirmed done:
- Repository-level skill validation is green on the current checkout.
- Contract registry tests pass on the current checkout.
- Metadata `*_JSON` path-vs-object contract drift is no longer present in scanned PR Factory skills.

Confirmed still open:
- `gatekeeper` fan-out still ignores top-level `status` and only checks decision / embedded PRSpec presence.
- `collect_top_improvements()` still ignores `data.candidate`, so architecture mode can still lose its primary signal.
- Root docs are still outside `DOC_FILES`, and `README.md` still contains dead `{{CONTEXT}}`.
- Hardcoded `/Users/Apple/Developer/pr-factory-kit/analysis_report/...` paths still exist across prompts/skills/docs.

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
