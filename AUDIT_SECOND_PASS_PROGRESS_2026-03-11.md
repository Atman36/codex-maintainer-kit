# Second Pass Progress

## Verified On Current Tree

Commands run from repo root on 2026-03-11:
- `python3 tools/validate_skills.py`
- `python3 -m unittest tools.tests.test_contracts`
- `python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_default_artifact_dir_is_repo_relative`
- `python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_expand_template_accepts_artifact_dir_placeholder`
- `python3 -m unittest tools.tests.test_contracts.ContractRegistryTests.test_root_docs_are_scanned_for_unknown_placeholders`
- `. .venv/bin/activate && python -m unittest discover -s tools/tests -p 'test_*.py'`
- `rg -n "/Users/Apple/Developer/pr-factory-kit/analysis_report/" skills prompts README.md AGENTS.md tools specs FRAMEWORK_IMPROVEMENTS_2026-03-11.md`
- `rg -n "low-risk|approve|scope minimization|strategic" prompts/agent-critic.md skills/pr-factory-critic/SKILL.md prompts/gatekeeper.md skills/pr-factory-gatekeeper/SKILL.md`
- targeted source checks against `tools/run_pipeline.py`, `tools/contract_registry.py`, `README.md`

Confirmed done:
- Repository-level skill validation is green on the current checkout.
- Contract registry tests pass on the current checkout.
- Metadata `*_JSON` path-vs-object contract drift is no longer present in scanned PR Factory skills.

Confirmed still open:
- `collect_top_improvements()` still ignores `data.candidate`, so architecture mode can still lose its primary signal.
- Pipeline summary artifacts still default outside the new analysis artifact placeholder contract.

## Done

- Fixed all scanned `metadata.json` `*_JSON` inputs to use `type: "string"`.
- Replaced scanned legacy alias placeholders with canonical names.
- Added `requirements.txt` with `jsonschema>=4.0`.
- Fixed the duplicate `How tested` condition in `tools/quality_gate.py`.
- Added regression coverage for lowercase `how tested`.
- Added a repository smoke test that expects zero contract issues.
- Updated CI and `tools/README.md` to remove stale `pyyaml`, switch examples to `python3`, and document the current Critic `ExecutionResult` format.
- Tightened gatekeeper semantics so PR fan-out now requires both `decision="pr"` and top-level `status="success"`.
- Added regression coverage to block fan-out when `gatekeeper` returns `needs_human` alongside otherwise valid `pr_spec` / `data.pr_specs`.
- Added root `README.md` and `AGENTS.md` to static contract scans, replaced dead `{{CONTEXT}}` in `README.md`, and added regression coverage for unknown placeholders in root docs.
- Replaced hardcoded analysis artifact paths in prompts/skills/docs with portable `{{ARTIFACT_DIR}}` guidance and documented the repo-relative `analysis_report/` default.
- Added runner support for `ARTIFACT_DIR` placeholder expansion with a deterministic repo-relative default.
- Rebalanced Critic/Gatekeeper prompt policy so narrow docs/tests/DX/bugfix work has an explicit fast-approve path and Gatekeeper focuses on post-approval scope shaping.

## Remaining

- Preserve architect `data.candidate` in `top_improvements`.
- Stabilize pipeline summary output into the repo-owned artifact contract.
- Optional packaging follow-up: `pyproject.toml` / editable install support.
- Optional feature follow-ups: run ID lineage and pipeline mode config extraction.

## GitHub Actions

- Checked failed push run `22938078456` on branch `codex/publisher-stage-and-user-prompts`.
- Failure was in `Validate skills and contracts` and matched the audit findings: alias warnings plus 8 metadata type errors.
- Local state after fixes:
  - `python3 tools/validate_skills.py` passes
  - full `tools/tests` passes in a fresh venv after `pip install -r requirements.txt`
